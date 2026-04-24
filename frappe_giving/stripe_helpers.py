"""Thin wrappers around the Stripe SDK for Frappe Giving.

Responsibilities:
- Load API credentials from our `Frappe Giving Settings` singleton (which
  points at a `Stripe Settings` record from the payments app).
- Create/reuse Stripe Customers, tracked on the Donor's payment platforms
  child table.
- Create PaymentIntents (one-time) and Subscriptions (recurring) with the
  Donation name embedded in metadata so webhooks can route back.
"""

import stripe
import frappe
from frappe import _

STRIPE_GATEWAY_NAME = "Stripe"

_FREQUENCY_TO_INTERVAL = {
	"Monthly": {"interval": "month", "interval_count": 1},
	"Quarterly": {"interval": "month", "interval_count": 3},
	"Annual": {"interval": "year", "interval_count": 1},
}


def _settings():
	return frappe.get_cached_doc("Frappe Giving Settings")


def get_stripe_client():
	settings = _settings()
	if not settings.stripe_settings:
		frappe.throw(
			_("Select a Stripe Settings record in Frappe Giving Settings first.")
		)

	stripe_settings = frappe.get_doc("Stripe Settings", settings.stripe_settings)
	secret_key = stripe_settings.get_password("secret_key")
	if not secret_key:
		frappe.throw(_("Stripe Settings is missing the secret key."))

	stripe.api_key = secret_key
	return stripe


def get_publishable_key():
	settings = _settings()
	stripe_settings = frappe.get_doc("Stripe Settings", settings.stripe_settings)
	return stripe_settings.publishable_key


def get_webhook_secret():
	settings = _settings()
	secret = settings.get_password("stripe_webhook_secret", raise_exception=False)
	if not secret:
		frappe.throw(_("Stripe webhook secret is not configured."))
	return secret


def get_or_create_stripe_customer(donor, email, name):
	"""Return a Stripe Customer ID for the donor, creating one if needed.

	The ID is persisted on the donor's `payment_platforms` child table so
	repeat donors don't accumulate duplicate Stripe Customers.
	"""
	existing = _find_platform_customer_id(donor)
	if existing:
		return existing

	get_stripe_client()
	customer = stripe.Customer.create(
		email=email,
		name=name,
		metadata={"donor": donor.name},
	)

	donor.append(
		"payment_platforms",
		{
			"payment_gateway": _stripe_payment_gateway_name(),
			"customer_id": customer.id,
			"is_default": 1,
			"status": "Active",
		},
	)
	donor.save(ignore_permissions=True)
	return customer.id


def _find_platform_customer_id(donor):
	gateway_name = _stripe_payment_gateway_name()
	for row in donor.payment_platforms or []:
		if row.payment_gateway == gateway_name and row.status == "Active":
			return row.customer_id
	return None


def _stripe_payment_gateway_name():
	"""Find the Payment Gateway record name that points at our Stripe Settings.

	Falls back to the literal string 'Stripe' if no record is found — the
	identifier still uniquely tags the child row.
	"""
	settings = _settings()
	name = frappe.db.get_value(
		"Payment Gateway",
		{"gateway_settings": "Stripe Settings", "gateway_controller": settings.stripe_settings},
		"name",
	)
	return name or STRIPE_GATEWAY_NAME


def create_payment_intent(amount, currency, customer_id, donation_name, description):
	get_stripe_client()
	amount_cents = int(round(float(amount) * 100))
	return stripe.PaymentIntent.create(
		amount=amount_cents,
		currency=currency.lower(),
		customer=customer_id,
		description=description,
		metadata={"donation_name": donation_name},
		automatic_payment_methods={"enabled": True},
	)


def create_subscription(
	amount, currency, customer_id, donation_name, frequency, description
):
	get_stripe_client()
	amount_cents = int(round(float(amount) * 100))

	interval_config = _FREQUENCY_TO_INTERVAL.get(frequency)
	if not interval_config:
		frappe.throw(_("Frequency {0} is not supported for recurring.").format(frequency))

	sub = stripe.Subscription.create(
		customer=customer_id,
		items=[
			{
				"price_data": {
					"currency": currency.lower(),
					"product_data": {"name": description},
					"unit_amount": amount_cents,
					"recurring": interval_config,
				}
			}
		],
		payment_behavior="default_incomplete",
		payment_settings={"save_default_payment_method": "on_subscription"},
		metadata={"donation_name": donation_name},
		expand=["latest_invoice.payment_intent"],
	)

	# Stripe does not propagate subscription metadata to the first invoice's
	# PaymentIntent. Patch it in so the webhook handler can find the donation.
	invoice = getattr(sub, "latest_invoice", None)
	pi = getattr(invoice, "payment_intent", None) if invoice else None
	if pi:
		stripe.PaymentIntent.modify(
			pi.id, metadata={"donation_name": donation_name}
		)

	return sub


def construct_webhook_event(payload_bytes, sig_header):
	get_stripe_client()
	secret = get_webhook_secret()
	return stripe.Webhook.construct_event(payload_bytes, sig_header, secret)
