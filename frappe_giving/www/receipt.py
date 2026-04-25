import frappe
from frappe import _
from frappe.utils import format_date, fmt_money

from frappe_giving.api.receipts import validate_token

no_cache = 1


def get_context(context):
	donation_name = frappe.form_dict.get("donation")
	token = frappe.form_dict.get("token")

	if not donation_name or not token:
		frappe.throw(_("Missing donation reference or token."), frappe.PermissionError)

	if not validate_token(donation_name, token):
		frappe.throw(_("Invalid or expired receipt link."), frappe.PermissionError)

	if not frappe.db.exists("Donation", donation_name):
		frappe.throw(_("Donation not found."), frappe.DoesNotExistError)

	donation = frappe.get_doc("Donation", donation_name)

	# Donations that never completed a charge shouldn't show a receipt —
	# the token is valid but the underlying donation isn't receiptable yet.
	if donation.status not in ("Invoiced", "Paid"):
		frappe.throw(
			_("This donation is not yet confirmed. Please check back later."),
			frappe.ValidationError,
		)

	donor = frappe.get_doc("Donor", donation.donor)
	company = frappe.get_doc("Company", donation.company)
	campaign_label = frappe.db.get_value(
		"Donation Campaign", donation.campaign, "campaign_name"
	) or donation.campaign

	context.no_cache = 1
	context.show_sidebar = False
	context.page_title = _("Donation Receipt")

	context.donation = donation
	context.donor = donor
	context.company = company
	context.company_address = _get_company_address(company.name)
	context.campaign_label = campaign_label
	context.formatted_amount = fmt_money(
		donation.amount, currency=donation.currency or "USD"
	)
	context.formatted_date = format_date(donation.donation_date)
	context.issued_on = format_date(frappe.utils.nowdate())

	return context


def _get_company_address(company_name):
	# Best-effort: Frappe stores addresses on the Address doctype and links
	# them via Dynamic Link. For receipt purposes we only need a printable
	# block — return None if nothing is linked and the template will hide
	# the address section.
	address_name = frappe.db.get_value(
		"Dynamic Link",
		{
			"link_doctype": "Company",
			"link_name": company_name,
			"parenttype": "Address",
		},
		"parent",
	)
	if not address_name:
		return None

	addr = frappe.db.get_value(
		"Address",
		address_name,
		[
			"address_line1",
			"address_line2",
			"city",
			"state",
			"pincode",
			"country",
		],
		as_dict=True,
	)
	return addr
