"""Donor email notifications fired by successful charges.

Two templates govern per-charge emails:

  - `frappe_giving_first_donation`: sent the first time we observe a
    Succeeded Donation Payment for a donor (welcome + portal access +
    receipt link).
  - `frappe_giving_thank_you`: sent for every subsequent successful
    charge (short thank-you + receipt link).

Idempotence is per-donor via `Donor.welcome_email_sent_at`; if that
field is already set, we never resend the welcome variant.

All DB access uses `frappe.db.get_value` / `frappe.db.set_value` rather
than `frappe.get_doc` to keep the donation transaction short — these
helpers run inline inside the Stripe webhook / sync-confirm handler,
which already holds a FOR UPDATE lock on the Donation row, and any
extra reads here lengthen the window where a racing handler can trip
MariaDB error 1020 on its own FOR UPDATE.
"""

import frappe
from frappe import _
from frappe.utils import get_url, now_datetime
from frappe.utils.data import sha256_hash

from frappe_giving.api.receipts import get_receipt_url


def send_donation_receipt_email(donation_payment_name: str) -> None:
    """Send the donor an email for a freshly-succeeded charge.

    No-ops if any required data is missing — receipt emails should never
    gate the charge pipeline. Failures are logged.
    """
    try:
        dp = frappe.db.get_value(
            "Donation Payment",
            donation_payment_name,
            ["donation", "amount", "currency", "date"],
            as_dict=True,
        )
        if not dp or not dp.donation:
            return

        donation = frappe.db.get_value(
            "Donation",
            dp.donation,
            [
                "donor",
                "campaign",
                "campaign_form",
                "company",
                "currency",
                "donation_date",
            ],
            as_dict=True,
        )
        if not donation or not donation.donor:
            return

        donor = frappe.db.get_value(
            "Donor",
            donation.donor,
            ["name", "donor_name", "email", "user", "welcome_email_sent_at"],
            as_dict=True,
        )
        if not donor or not donor.email:
            return

        is_first = not donor.welcome_email_sent_at
        template_name = _resolve_template_name(donation.campaign_form, is_first)
        if not template_name:
            frappe.log_error(
                title="Donation receipt email skipped: no usable Email Template",
                message=f"Donation Payment: {donation_payment_name}",
            )
            return

        context = _build_context(
            donor,
            donation,
            dp,
            donation_name=dp.donation,
            include_account_link=is_first,
        )

        template = frappe.db.get_value(
            "Email Template", template_name, ["subject", "response"], as_dict=True
        )
        subject = frappe.render_template(template.subject, context)
        message = frappe.render_template(template.response, context)

        frappe.sendmail(
            recipients=[donor.email],
            subject=subject,
            message=message,
        )

        if is_first:
            frappe.db.set_value(
                "Donor",
                donor.name,
                "welcome_email_sent_at",
                now_datetime(),
                update_modified=False,
            )
    except Exception:
        frappe.log_error(
            title=f"Donation receipt email failed for {donation_payment_name}",
            message=frappe.get_traceback(),
        )


def _resolve_template_name(campaign_form_name, is_first: bool) -> str | None:
    """Pick the Email Template for this charge.

    Priority:
      1. The Campaign Form's `email_template_first` / `email_template_recurring`
         (lets each form ship its own donor copy).
      2. The global `frappe_giving_first_donation` / `frappe_giving_thank_you`
         fixtures, kept as a safety net so a Campaign Form without templates
         still produces an email.

    Returns `None` if neither resolves to an existing Email Template — the
    caller logs and skips the send.
    """
    fieldname = "email_template_first" if is_first else "email_template_recurring"
    fallback = "frappe_giving_first_donation" if is_first else "frappe_giving_thank_you"

    if campaign_form_name:
        per_form = frappe.db.get_value("Campaign Form", campaign_form_name, fieldname)
        if per_form and frappe.db.exists("Email Template", per_form):
            return per_form

    if frappe.db.exists("Email Template", fallback):
        return fallback

    return None


def _build_context(
    donor, donation, dp, donation_name, include_account_link: bool
) -> dict:
    campaign_title = (
        frappe.db.get_value("Donation Campaign", donation.campaign, "campaign_name")
        or donation.campaign
    )
    company_name = donation.company or _("our organisation")

    context = {
        "donor_name": donor.donor_name or _("friend"),
        "donor_email": donor.email,
        "donation_name": donation_name,
        "donation_amount": dp.amount,
        "donation_currency": dp.currency or donation.currency,
        "donation_date": dp.date or donation.donation_date,
        "campaign_name": campaign_title,
        "company_name": company_name,
        "receipt_url": get_receipt_url(donation_name),
        "portal_url": get_url("/donate/donorportal"),
        "account_setup_url": "",
        "login_email": donor.email,
    }

    if include_account_link and donor.user:
        context["account_setup_url"] = _account_setup_url(donor.user)

    return context


def _account_setup_url(user_name: str) -> str:
    """Mint a fresh reset key for the donor's User and return the absolute
    `/update-password` URL. Existing passwords are not affected — only
    the temporary `reset_password_key` field changes.

    Replicates `User.reset_password(send_email=False)` without loading the
    full User document, so we don't add a tabUser SELECT inside the donation
    transaction. Stores `sha256_hash(key)` in the DB and embeds the raw
    `key` in the URL — same scheme as Frappe's built-in flow, otherwise
    `/update-password` rejects the link as "expired or used".
    """
    try:
        key = frappe.generate_hash()
        frappe.db.set_value(
            "User",
            user_name,
            {
                "reset_password_key": sha256_hash(key),
                "last_reset_password_key_generated_on": now_datetime(),
            },
            update_modified=False,
        )
        return get_url(f"/update-password?key={key}", allow_header_override=False)
    except Exception:
        frappe.log_error(
            title=f"Account setup URL failed for user {user_name}",
            message=frappe.get_traceback(),
        )
        return ""
