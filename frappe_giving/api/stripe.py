"""Stripe-facing endpoints: donor-initiated payment setup + inbound webhook."""

import frappe
from frappe import _
from frappe.utils import cint

from frappe_giving import stripe_helpers
from frappe_giving.api.donate import (
	_default_company,
	_find_or_create_donor,
)
from frappe_giving.api.notifications import send_donation_receipt_email
from frappe_giving.fee_recovery import compute_fee_recovery


# Guest-accessible: anonymous donors are the primary user. Amount + fee
# recomputed server-side; Stripe customer/PaymentIntent scoped to posted email.
# nosemgrep: guest-whitelisted-method
@frappe.whitelist(allow_guest=True, methods=["POST"])
def initiate_stripe_payment(
	form_name: str,
	amount: float | str,
	frequency: str,
	donor_data: dict | str,
	cover_fees: int | str = 0,
):
	"""Create the Donor (if new), a Draft Donation, and a Stripe charge.

	Returns the client_secret the frontend needs to confirm payment.
	The Donation remains in Draft status until the webhook confirms the charge.
	"""
	if not frappe.db.exists("Campaign Form", form_name):
		frappe.throw(_("Form not found."), frappe.DoesNotExistError)

	form = frappe.get_doc("Campaign Form", form_name)
	if form.status != "Active":
		frappe.throw(_("This donation form is not active."))

	if isinstance(donor_data, str):
		donor_data = frappe.parse_json(donor_data)

	amount = float(amount)
	if amount <= 0:
		frappe.throw(_("Donation amount must be greater than zero."))

	email = (donor_data.get("email") or "").strip().lower()
	full_name = (donor_data.get("full_name") or "").strip()
	if not email or not full_name:
		frappe.throw(_("Name and email are required."))

	campaign = frappe.get_doc("Donation Campaign", form.campaign)
	currency = campaign.currency or "USD"

	# Recompute fee server-side from Settings; the client only signals intent.
	cover_fees = bool(cint(cover_fees)) and bool(form.fee_recovery_display)
	fee_recovered = 0.0
	if cover_fees:
		settings = frappe.get_cached_doc("Frappe Giving Settings")
		fee_recovered = float(compute_fee_recovery(amount, settings.fee_percentage, settings.fee_fixed))
	charge_amount = amount + fee_recovered

	donor = _find_or_create_donor(email, full_name, donor_data)

	donation = frappe.get_doc(
		{
			"doctype": "Donation",
			"donor": donor.name,
			"campaign": form.campaign,
			"campaign_form": form.name,
			"company": _default_company(),
			"currency": currency,
			"amount": amount,
			"cover_fees": 1 if cover_fees else 0,
			"fee_recovered": fee_recovered,
			"exchange_rate": 1,
			"frequency": frequency,
			"donor_note": donor_data.get("donor_note"),
			"is_anonymous": 1 if donor_data.get("is_anonymous") else 0,
		}
	)
	donation.insert(ignore_permissions=True)

	customer_id = stripe_helpers.get_or_create_stripe_customer(donor, email, full_name)

	description = _("Donation {0} – {1}").format(donation.name, form.campaign)

	if frequency == "One-Time":
		pi = stripe_helpers.create_payment_intent(
			amount=charge_amount,
			currency=currency,
			customer_id=customer_id,
			donation_name=donation.name,
			description=description,
		)
		return {
			"donation": donation.name,
			"mode": "payment",
			"client_secret": pi.client_secret,
			"publishable_key": stripe_helpers.get_publishable_key(),
		}

	# Recurring — apply gross-up to every cycle so the cause nets `amount` each time.
	sub = stripe_helpers.create_subscription(
		amount=charge_amount,
		currency=currency,
		customer_id=customer_id,
		donation_name=donation.name,
		frequency=frequency,
		description=description,
		campaign_form_name=form.name,
	)

	frappe.db.set_value(
		"Donation",
		donation.name,
		{
			"gate_subscription_id": sub.id,
			"subscription_status": "Incomplete",
		},
	)

	invoice = sub.latest_invoice
	payment_intent = getattr(invoice, "payment_intent", None)
	if not payment_intent:
		frappe.throw(_("Stripe did not return a payment intent for the subscription."))

	return {
		"donation": donation.name,
		"mode": "subscription",
		"subscription_id": sub.id,
		"client_secret": payment_intent.client_secret,
		"publishable_key": stripe_helpers.get_publishable_key(),
	}


# Guest-accessible: post-payment confirm callback. PaymentIntent is retrieved
# from Stripe and its metadata.donation_name must match `donation_name` before
# any DB write.
# nosemgrep: guest-whitelisted-method
@frappe.whitelist(allow_guest=True, methods=["POST"])
def confirm_donation_payment(donation_name: str, payment_intent_id: str):
	"""Synchronous confirmation after the donor's browser completes payment.

	The frontend calls this immediately after `stripe.confirmPayment` resolves
	successfully. We retrieve the PaymentIntent from Stripe to verify it
	really succeeded (never trust the client) and that its metadata matches
	the Donation, then submit the Donation. This keeps the happy path fast
	and independent of webhook delivery. The webhook handler remains as a
	safety net (idempotent via `stripe_payment_intent_id` lookup) and is
	required for subscription renewals and Dashboard-initiated refunds.

	NOTE: we deliberately DON'T do an upfront `frappe.db.exists("Donation",
	...)` check here — that would snapshot the Donation row into the
	transaction before the handler's FOR UPDATE lock fires, causing
	InnoDB error 1020 under concurrent webhook + sync-confirm runs. The
	handler's `frappe.get_doc(..., for_update=True)` raises
	DoesNotExistError naturally if the donation is missing.
	"""
	client = stripe_helpers.get_stripe_client()
	pi = client.PaymentIntent.retrieve(payment_intent_id)

	metadata_donation = (pi.get("metadata") or {}).get("donation_name")
	if metadata_donation != donation_name:
		frappe.throw(
			_("Payment Intent does not belong to this donation."),
			frappe.PermissionError,
		)

	if pi["status"] != "succeeded":
		frappe.throw(_("Payment has not yet succeeded. Stripe status: {0}").format(pi["status"]))

	# Trusted: PI belongs to this donation and Stripe confirms success.
	# Permission bypass is applied at the specific-doc level inside the
	# handler (not globally) — narrower grant, honest audit trail (Guest,
	# not Administrator), no other Administrator privileges granted.
	_handle_payment_intent_succeeded(pi)

	from frappe_giving.api.receipts import get_receipt_url

	return {
		"donation": donation_name,
		"status": frappe.db.get_value("Donation", donation_name, "status"),
		"receipt_url": get_receipt_url(donation_name),
	}


# Guest-accessible: Stripe webhook endpoint. Payload is verified via
# Stripe-Signature HMAC against the signing secret before any handler runs.
# nosemgrep: guest-whitelisted-method
@frappe.whitelist(allow_guest=True, methods=["POST"])
def webhook():
	"""Entry point for Stripe webhooks.

	Stripe posts JSON with a Stripe-Signature header; we verify using the
	signing secret from Frappe Giving Settings.
	"""
	payload = frappe.request.data
	sig_header = frappe.request.headers.get("Stripe-Signature")
	if not sig_header:
		frappe.throw(_("Missing Stripe-Signature header."), frappe.PermissionError)

	try:
		event = stripe_helpers.construct_webhook_event(payload, sig_header)
	except ValueError:
		frappe.throw(_("Invalid Stripe webhook payload."), frappe.PermissionError)
	except Exception as exc:
		frappe.log_error(
			title="Stripe webhook signature verification failed",
			message=str(exc),
		)
		frappe.throw(
			_("Stripe webhook signature verification failed."),
			frappe.PermissionError,
		)

	handler = _EVENT_HANDLERS.get(event["type"])
	if not handler:
		# Unhandled but valid event — acknowledge so Stripe stops retrying.
		return {"ok": True, "ignored": event["type"]}

	# Signature is verified. Permission bypass is applied per-doc inside
	# the individual handlers, not globally — narrower grant, audit trail
	# stays honest (Guest, not Administrator).
	try:
		handler(event["data"]["object"])
	except Exception:
		frappe.log_error(
			title=f"Stripe webhook handler failed: {event['type']}",
			message=frappe.get_traceback(),
		)
		raise

	return {"ok": True, "type": event["type"]}


# ------------------------------------------------------------------
# Event handlers
# ------------------------------------------------------------------


def _handle_payment_intent_succeeded(pi):
	donation_name = (pi.get("metadata") or {}).get("donation_name")
	if not donation_name:
		return

	pi_id = pi["id"]

	# CRITICAL: reset the transaction snapshot before the FOR UPDATE.
	#
	# Both callers (sync-confirm and the webhook) have already done
	# read-only DB work — `stripe_helpers.get_stripe_client()` reads
	# Stripe Settings + Frappe Giving Settings, which under MariaDB's
	# REPEATABLE READ isolation establishes the transaction snapshot.
	# When the racing transaction has already modified `tabDonation`,
	# our FOR UPDATE then raises error 1020 ("Record has changed since
	# last read") instead of blocking on the lock.
	#
	# Committing here ends the read-only transaction; the next query
	# starts a fresh transaction whose snapshot includes the racing
	# transaction's commits. The FOR UPDATE then either acquires the
	# lock cleanly, or — if the racing transaction is still in progress
	# — blocks until it commits. Either way, the idempotence check
	# below catches the duplicate.
	# Reset REPEATABLE READ snapshot before FOR UPDATE — see comment above
	# for the MariaDB error 1020 rationale.
	frappe.db.commit()  # nosemgrep: frappe-manual-commit

	try:
		donation = frappe.get_doc("Donation", donation_name, for_update=True)
	except frappe.DoesNotExistError:
		return

	# Idempotence: check AFTER acquiring the lock so we see the winning
	# transaction's writes.
	if frappe.db.exists("Donation Payment", {"stripe_payment_intent_id": pi_id}):
		return

	if donation.docstatus == 0:
		# First successful charge — submit the donation.
		# donation.on_submit creates a Sales Invoice and, for Portal donations,
		# an initial Donation Payment row. We bypass the whitelisted `.submit()`
		# wrapper by flipping docstatus and saving with `ignore_permissions=True`
		# directly — this is what the webhook and sync-confirm Guest paths need,
		# since `.submit()` doesn't accept an `ignore_permissions` kwarg and
		# setting `self.flags.ignore_permissions` alone has proven unreliable
		# across the whitelist-wrapped call chain in this Frappe build.
		donation.docstatus = 1
		donation.save(ignore_permissions=True)

	# Find or create the Donation Payment for this PI.
	dp_name = frappe.db.get_value(
		"Donation Payment",
		{"donation": donation_name, "stripe_payment_intent_id": ("in", ["", None])},
		"name",
		order_by="creation desc",
	)
	if dp_name:
		dp = frappe.get_doc("Donation Payment", dp_name)
		dp.stripe_payment_intent_id = pi_id
		dp.status = "Succeeded"
		dp.date = frappe.utils.nowdate()
		dp.save(ignore_permissions=True)

		# Reconcile the SI so it's not stuck Unpaid.
		donation.reload()
		donation._reconcile_sales_invoice(
			si_name=dp.sales_invoice,
			amount=float(pi["amount"]) / 100,
			stripe_pi_id=pi_id,
		)
		notify_dp_name = dp.name
	else:
		# Subscription renewal: no pre-existing DP row, create one.
		donation.reload()
		new_dp = donation._create_cycle_invoice_and_payment(
			amount=float(pi["amount"]) / 100,
			date=frappe.utils.nowdate(),
			stripe_pi_id=pi_id,
		)
		notify_dp_name = new_dp.name

	frappe.db.set_value("Donation", donation_name, "status", "Paid")

	send_donation_receipt_email(notify_dp_name)


def _handle_payment_intent_failed(pi):
	donation_name = (pi.get("metadata") or {}).get("donation_name")
	if not donation_name or not frappe.db.exists("Donation", donation_name):
		return
	frappe.db.set_value("Donation", donation_name, "status", "Failed")


def _handle_invoice_payment_succeeded(invoice):
	"""Subscription billing cycles dispatch here.

	First cycle of a subscription fires both `payment_intent.succeeded` and
	`invoice.payment_succeeded`. We route the bookkeeping through the PI
	handler (which has the metadata) and treat this event as a no-op when
	the PI has already been processed.
	"""
	payment_intent_id = invoice.get("payment_intent")
	if payment_intent_id and frappe.db.exists(
		"Donation Payment", {"stripe_payment_intent_id": payment_intent_id}
	):
		return

	subscription_id = invoice.get("subscription")
	if not subscription_id:
		return

	donation_name = frappe.db.get_value("Donation", {"gate_subscription_id": subscription_id}, "name")
	if not donation_name:
		return

	donation = frappe.get_doc("Donation", donation_name)
	donation._create_cycle_invoice_and_payment(
		amount=float(invoice["amount_paid"]) / 100,
		date=frappe.utils.nowdate(),
		stripe_pi_id=payment_intent_id or "",
	)


def _handle_subscription_updated(sub):
	donation_name = frappe.db.get_value("Donation", {"gate_subscription_id": sub["id"]}, "name")
	if not donation_name:
		return

	status_map = {
		"active": "Active",
		"trialing": "Active",
		"past_due": "Active",
		"paused": "Paused",
		"canceled": "Cancelled",
		"incomplete": "Incomplete",
		"incomplete_expired": "Cancelled",
		"unpaid": "Paused",
	}
	mapped = status_map.get(sub.get("status"))
	if mapped:
		frappe.db.set_value("Donation", donation_name, "subscription_status", mapped)


def _handle_subscription_deleted(sub):
	donation_name = frappe.db.get_value("Donation", {"gate_subscription_id": sub["id"]}, "name")
	if donation_name:
		frappe.db.set_value("Donation", donation_name, "subscription_status", "Cancelled")


def _handle_charge_refunded(charge):
	pi_id = charge.get("payment_intent")
	if not pi_id:
		return
	dp_name = frappe.db.get_value("Donation Payment", {"stripe_payment_intent_id": pi_id}, "name")
	if dp_name:
		frappe.db.set_value("Donation Payment", dp_name, "status", "Refunded")
		donation_name = frappe.db.get_value("Donation Payment", dp_name, "donation")
		if donation_name:
			frappe.db.set_value("Donation", donation_name, "status", "Refunded")


_EVENT_HANDLERS = {
	"payment_intent.succeeded": _handle_payment_intent_succeeded,
	"payment_intent.payment_failed": _handle_payment_intent_failed,
	"invoice.payment_succeeded": _handle_invoice_payment_succeeded,
	"customer.subscription.updated": _handle_subscription_updated,
	"customer.subscription.deleted": _handle_subscription_deleted,
	"charge.refunded": _handle_charge_refunded,
}
