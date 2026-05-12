"""Scheduled background tasks for Frappe Giving.

Currently only `send_annual_statements`, fired by the `scheduler_events`
cron in hooks.py on Jan 5, 08:00 site-local. Safe to run manually any
time after Dec 31 — the per-donor `last_statement_emailed_year` field
makes the batch idempotent.
"""

import frappe
from frappe.utils import today

from frappe_giving.api.receipts import email_yearly_statement


@frappe.whitelist()
def send_annual_statements():
	"""Email last-year donation statements to opted-in donors.

	For each Donor with `send_annual_statement = 1` and at least one
	confirmed donation in the target year, generate the consolidated
	statement PDF and email it. Skips donors already emailed for that
	year (via `last_statement_emailed_year`). Per-donor errors are
	logged and the batch continues — one bad email shouldn't gate the
	rest.

	For sites with thousands of donors this should be split into
	background jobs via `frappe.enqueue` to avoid one long-running
	transaction. For typical org volumes (<500 donors) inline is fine
	and gives clearer logs.
	"""
	target_year = int(today().split("-")[0]) - 1

	donors = frappe.get_all(
		"Donor",
		filters={
			"send_annual_statement": 1,
			"status": ["in", ["Active", "Lapsed"]],  # not Inactive
		},
		pluck="name",
	)

	sent = 0
	skipped_no_donations = 0
	skipped_already_emailed = 0
	failed = 0

	for donor_name in donors:
		# Idempotence: skip if we already mailed this donor for this year.
		if frappe.db.get_value("Donor", donor_name, "last_statement_emailed_year") == target_year:
			skipped_already_emailed += 1
			continue

		# Cheap filter before the expensive PDF render: did they donate?
		has_donations = frappe.db.exists(
			"Donation",
			{
				"donor": donor_name,
				"docstatus": 1,
				"status": ["in", ["Invoiced", "Paid"]],
				"donation_date": [
					"between",
					[f"{target_year}-01-01", f"{target_year}-12-31"],
				],
			},
		)
		if not has_donations:
			skipped_no_donations += 1
			continue

		try:
			ok = email_yearly_statement(donor_name, target_year)
			if ok:
				sent += 1
				# Commit per-donor so a later failure doesn't unwind earlier
				# successes — annual emails should never re-send accidentally.
				frappe.db.commit()
			else:
				skipped_no_donations += 1
		except Exception:
			failed += 1
			frappe.log_error(
				title=f"Annual statement email failed for {donor_name} ({target_year})",
				message=frappe.get_traceback(),
			)

	frappe.logger().info(
		f"send_annual_statements({target_year}): "
		f"sent={sent} skipped_already={skipped_already_emailed} "
		f"skipped_no_donations={skipped_no_donations} failed={failed}"
	)
	return {
		"target_year": target_year,
		"sent": sent,
		"skipped_already_emailed": skipped_already_emailed,
		"skipped_no_donations": skipped_no_donations,
		"failed": failed,
	}
