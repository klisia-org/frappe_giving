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


def _resolve_stripe_settings_name():
	"""Return the Stripe Settings record to use.

	Priority:
	  1. The record explicitly selected in Frappe Giving Settings.
	  2. If unset and there's exactly one Stripe Settings record, use it.
	  3. Otherwise, throw with a message pointing the operator at the
	     Frappe Giving Settings screen.
	"""
	settings = _settings()
	if settings.stripe_settings:
		return settings.stripe_settings

	records = frappe.get_all("Stripe Settings", pluck="name")
	if len(records) == 1:
		return records[0]

	frappe.throw(
		_(
			"Open Frappe Giving Settings ({0}) and select which Stripe Settings "
			"record to use."
		).format("/app/frappe-giving-settings")
	)


def get_stripe_client():
	name = _resolve_stripe_settings_name()
	stripe_settings = frappe.get_doc("Stripe Settings", name)
	secret_key = stripe_settings.get_password("secret_key")
	if not secret_key:
		frappe.throw(_("Stripe Settings {0} is missing the secret key.").format(name))

	stripe.api_key = secret_key
	return stripe


def get_publishable_key():
	name = _resolve_stripe_settings_name()
	return frappe.db.get_value("Stripe Settings", name, "publishable_key")


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
	"""Find the Payment Gateway record name for Stripe on this site.

	Order of attempts:
	  1. Payment Gateway whose `gateway_controller` matches the Stripe
	     Settings record we resolve (explicit link in Frappe Giving Settings,
	     or the single-record fallback).
	  2. Any Payment Gateway with `gateway_settings = "Stripe Settings"`.
	  3. Literal "Stripe" as a last resort (ensures the identifier we write
	     to Donor Payment Platform rows still uniquely tags the child row).
	"""
	try:
		stripe_settings_name = _resolve_stripe_settings_name()
	except Exception:
		stripe_settings_name = None

	if stripe_settings_name:
		name = frappe.db.get_value(
			"Payment Gateway",
			{
				"gateway_settings": "Stripe Settings",
				"gateway_controller": stripe_settings_name,
			},
			"name",
		)
		if name:
			return name

	name = frappe.db.get_value(
		"Payment Gateway", {"gateway_settings": "Stripe Settings"}, "name"
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


def _get_or_create_stripe_product(campaign_form_name, description, donation_name):
	"""Return a Stripe Product ID, caching one per Campaign Form.

	Strategy:
	  1. If the Campaign Form already has `stripe_product_id`, use it.
	     (Best effort: if the cached Product was deleted in the Stripe
	     Dashboard, the next subscription create call will fail with an
	     InvalidRequestError — at that point clear the field on the form
	     to force regeneration.)
	  2. Otherwise create a new Product and cache the ID on the Campaign
	     Form so every subsequent subscription for that form reuses it.
	  3. If no campaign_form_name is passed (shouldn't normally happen),
	     fall back to an ad-hoc Product so the flow still works.
	"""
	if campaign_form_name:
		cached = frappe.db.get_value(
			"Campaign Form", campaign_form_name, "stripe_product_id"
		)
		if cached:
			return cached

	name = campaign_form_name or description
	product = stripe.Product.create(
		name=name,
		metadata={
			"campaign_form": campaign_form_name or "",
			"source": "frappe_giving",
		},
	)

	if campaign_form_name:
		frappe.db.set_value(
			"Campaign Form",
			campaign_form_name,
			"stripe_product_id",
			product.id,
			update_modified=False,
		)

	return product.id


def create_subscription(
	amount,
	currency,
	customer_id,
	donation_name,
	frequency,
	description,
	campaign_form_name=None,
):
	get_stripe_client()
	amount_cents = int(round(float(amount) * 100))

	interval_config = _FREQUENCY_TO_INTERVAL.get(frequency)
	if not interval_config:
		frappe.throw(_("Frequency {0} is not supported for recurring.").format(frequency))

	# Stripe's Subscription API accepts `price_data.product` (an ID) but not
	# `price_data.product_data` (inline). We cache one Product per Campaign
	# Form — different forms for the same campaign (A/B tests, language
	# variants) get their own Product, enabling distinct Dashboard analytics.
	product_id = _get_or_create_stripe_product(
		campaign_form_name=campaign_form_name,
		description=description,
		donation_name=donation_name,
	)

	sub = stripe.Subscription.create(
		customer=customer_id,
		items=[
			{
				"price_data": {
					"currency": currency.lower(),
					"product": product_id,
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
