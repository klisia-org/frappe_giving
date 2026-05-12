import frappe
from frappe import _


# Guest-accessible: public branding (logo only), no PII.
@frappe.whitelist(allow_guest=True)  # nosemgrep: guest-whitelisted-method
def get_branding():
    return {
        "giving_logo": frappe.db.get_single_value(
            "Frappe Giving Settings", "giving_logo"
        )
        or "",
    }


# Guest-accessible: donate landing pages render before login; reads public
# Campaign Form fields only and throws on inactive forms.
@frappe.whitelist(allow_guest=True)  # nosemgrep: guest-whitelisted-method
def get_campaign_form(form_name: str):
    if not frappe.db.exists("Campaign Form", form_name):
        frappe.throw(_("Form not found."), frappe.DoesNotExistError)

    form = frappe.get_doc("Campaign Form", form_name)

    if form.status != "Active":
        frappe.throw(_("This donation form is not active."))

    campaign = frappe.get_doc("Donation Campaign", form.campaign)
    settings = frappe.get_cached_doc("Frappe Giving Settings")

    return {
        "form_title": form.form_title,
        "campaign": form.campaign,
        "hero_title": form.hero_title,
        "subtitle": form.subtitle,
        "description": form.description,
        "image": form.image,
        "background": form.background,
        "button_color": form.button_color,
        "cta_label": form.cta_label,
        "thank_you_message": form.thank_you_message,
        "show_full_name": form.show_full_name,
        "show_email": form.show_email,
        "show_phone": form.show_phone,
        "show_address": form.show_address,
        "show_donor_note": form.show_donor_note,
        "allow_anonymous": form.allow_anonymous,
        "allow_custom_amount": form.allow_custom_amount,
        "currency": campaign.currency or "USD",
        "giving_levels": [
            {
                "amount": level.amount,
                "label": level.label,
                "is_default": level.is_default,
            }
            for level in (form.giving_levels or [])
        ],
        "fee_recovery_display": form.fee_recovery_display or "",
        "fee_recovery_default": form.fee_recovery_default or "Opt-in",
        "fee_percentage": float(settings.fee_percentage or 0),
        "fee_fixed": float(settings.fee_fixed or 0),
        "fee_recovery_message_template": settings.fee_recovery_message_template or "",
    }


@frappe.whitelist()
def get_default_form_name() -> str | None:
    """Name of a usable Campaign Form for generic "Give now" links.

    Prefers a form attached to a campaign flagged `default=1`, falls back
    to any Active form. Returns `None` if no active form exists so the
    frontend can hide the CTA rather than link to /donate and 404.
    """
    default_campaign = frappe.db.get_value(
        "Donation Campaign", {"default": 1, "status": "Active"}, "name"
    )
    if default_campaign:
        form = frappe.db.get_value(
            "Campaign Form",
            {"campaign": default_campaign, "status": "Active"},
            "name",
        )
        if form:
            return form
    return frappe.db.get_value("Campaign Form", {"status": "Active"}, "name")


# Guest-accessible: anonymous donors must reach the non-Stripe donation entry
# point. Donor identity captured from posted form; amount and form validated
# server-side.
# nosemgrep: guest-whitelisted-method
@frappe.whitelist(allow_guest=True, methods=["POST"])
def create_draft_donation(
    form_name: str,
    amount: float | str,
    frequency: str,
    donor_data: dict | str,
):
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

    donor = _find_or_create_donor(email, full_name, donor_data)

    donation = frappe.get_doc(
        {
            "doctype": "Donation",
            "donor": donor.name,
            "campaign": form.campaign,
            "campaign_form": form.name,
            "company": _default_company(),
            "currency": campaign.currency or "USD",
            "amount": amount,
            "exchange_rate": 1,
            "frequency": frequency,
            "donor_note": donor_data.get("donor_note"),
            "is_anonymous": 1 if donor_data.get("is_anonymous") else 0,
        }
    )
    donation.insert(ignore_permissions=True)

    return {"donation": donation.name, "donor": donor.name}


def _find_or_create_donor(email, full_name, donor_data):
    existing = frappe.db.get_value("Donor", {"email": email}, "name")
    if existing:
        return frappe.get_doc("Donor", existing)

    donor = frappe.get_doc(
        {
            "doctype": "Donor",
            "donor_name": full_name,
            "email": email,
            "donor_type": "Individual",
            "status": "Active",
            "donor_since": frappe.utils.nowdate(),
            "is_anonymous": 1 if donor_data.get("is_anonymous") else 0,
        }
    )
    donor.insert(ignore_permissions=True)
    return donor


def _default_company():
    company = frappe.defaults.get_global_default("company")
    if company:
        return company
    company = frappe.db.get_value("Company", {}, "name")
    if not company:
        frappe.throw(_("No Company configured in ERPNext."))
    return company
