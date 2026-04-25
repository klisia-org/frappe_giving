"""Payment Entry doc_events hooks for frappe_giving.

When staff records a Payment Entry against a Sales Invoice that belongs to
a subscription-generated Donation Payment (currently in 'Waiting'), flip
that Donation Payment to 'Succeeded' so the donor's history reflects the
collection.
"""

import frappe


def on_submit(doc, method=None):
	for ref in doc.references or []:
		if ref.reference_doctype != "Sales Invoice":
			continue

		dp_name = frappe.db.get_value(
			"Donation Payment",
			{
				"sales_invoice": ref.reference_name,
				"status": "Waiting",
			},
			"name",
		)
		if not dp_name:
			continue

		frappe.db.set_value(
			"Donation Payment",
			dp_name,
			{
				"status": "Succeeded",
				"date": doc.posting_date,
			},
		)
