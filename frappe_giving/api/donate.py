import frappe
from frappe import _


@frappe.whitelist(allow_guest=True)
def get_campaign_form(form_name):
	if not frappe.db.exists("Campaign Form", form_name):
		frappe.throw(_("Form not found."), frappe.DoesNotExistError)

	form = frappe.get_doc("Campaign Form", form_name)

	if form.status != "Active":
		frappe.throw(_("This donation form is not active."))

	campaign = frappe.get_doc("Donation Campaign", form.campaign)

	return {
		"form_title": form.form_title,
		"campaign": form.campaign,
		"hero_title": form.hero_title,
		"subtitle": form.subtitle,
		"description": form.description,
		"image": form.image,
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
	}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def create_draft_donation(form_name, amount, frequency, donor_data):
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
