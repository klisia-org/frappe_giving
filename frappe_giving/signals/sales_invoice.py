"""Sales Invoice doc_events hooks for frappe_giving.

When the ERPNext Subscription scheduler generates (and auto-submits) a
Sales Invoice for a Donation-owned Subscription, mirror it as a Donation
Payment row in status 'Waiting'. The payment_entry hook flips it to
'Succeeded' once staff records the incoming check/transfer.
"""

import frappe


def on_submit(doc, method=None):
	if not getattr(doc, "subscription", None):
		return

	donation_name = frappe.db.get_value("Donation", {"erpnext_subscription": doc.subscription}, "name")
	if not donation_name:
		return

	if frappe.db.exists("Donation Payment", {"sales_invoice": doc.name}):
		return

	frappe.get_doc(
		{
			"doctype": "Donation Payment",
			"donation": donation_name,
			"sales_invoice": doc.name,
			"invoice_date": doc.posting_date,
			"amount": doc.grand_total,
			"currency": doc.currency,
			"exchange_rate": doc.conversion_rate or 1,
			"status": "Waiting",
		}
	).insert(ignore_permissions=True)
