"""Donor email notifications fired by successful charges.

Two templates govern per-charge emails:

  - `frappe_giving_first_donation`: sent the first time we observe a
    Succeeded Donation Payment for a donor (welcome + portal access +
    receipt link).
  - `frappe_giving_thank_you`: sent for every subsequent successful
    charge (short thank-you + receipt link).

Idempotence is per-donor via `Donor.welcome_email_sent_at`; if that
field is already set, we never resend the welcome variant.
"""

import frappe
from frappe import _
from frappe.utils import get_url, now_datetime

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

        donation = frappe.get_doc("Donation", dp.donation)
        donor = frappe.get_doc("Donor", donation.donor)
        if not donor.email:
            return

        is_first = not donor.welcome_email_sent_at
        template_name = (
            "frappe_giving_first_donation" if is_first else "frappe_giving_thank_you"
        )
        if not frappe.db.exists("Email Template", template_name):
            frappe.log_error(
                title=f"Donation receipt email skipped: missing Email Template {template_name}",
                message=f"Donation Payment: {donation_payment_name}",
            )
            return

        context = _build_context(donor, donation, dp, include_password_link=is_first)

        template = frappe.get_doc("Email Template", template_name)
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


def _build_context(donor, donation, dp, include_password_link: bool) -> dict:
    campaign_title = (
        frappe.db.get_value("Donation Campaign", donation.campaign, "campaign_name")
        or donation.campaign
    )
    company_name = donation.company or _("our organisation")

    context = {
        "donor_name": donor.donor_name or _("friend"),
        "donor_email": donor.email,
        "donation_name": donation.name,
        "donation_amount": dp.amount,
        "donation_currency": dp.currency or donation.currency,
        "donation_date": dp.date or donation.donation_date,
        "campaign_name": campaign_title,
        "company_name": company_name,
        "receipt_url": get_receipt_url(donation.name),
        "portal_url": get_url("/donate/donorportal"),
        "account_setup_url": "",
        "login_email": donor.email,
    }

    if include_password_link and donor.user:
        context["account_setup_url"] = _account_setup_url(donor.user)

    return context


def _account_setup_url(user_name: str) -> str:
    """Mint a fresh reset key for the donor's User and return the absolute
    `/update-password` URL. Existing passwords are not affected — only
    the temporary `reset_password_key` field changes.
    """
    try:
        user = frappe.get_doc("User", user_name)
        return user.reset_password(send_email=False)
    except Exception:
        frappe.log_error(
            title=f"Password setup URL failed for user {user_name}",
            message=frappe.get_traceback(),
        )
        return ""
