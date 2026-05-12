"""Create the `Donor` role and assign it to every existing Donor's User.

New donors pick up the role in `Donor._create_user()` (see donor.py), but
prior to that hook existing donor Users have no role, so they can't read
their own records via the portal or download receipts. This patch
backfills them.
"""

import frappe


def execute():
	if not frappe.db.exists("Role", "Donor"):
		frappe.get_doc(
			{
				"doctype": "Role",
				"role_name": "Donor",
				"desk_access": 0,
				"disabled": 0,
			}
		).insert(ignore_permissions=True)

	donor_users = frappe.db.sql_list("SELECT user FROM `tabDonor` WHERE user IS NOT NULL AND user != ''")
	for user_name in donor_users:
		if not frappe.db.exists("User", user_name):
			continue
		user = frappe.get_doc("User", user_name)
		existing = {r.role for r in (user.roles or [])}
		if "Donor" in existing:
			continue
		user.append("roles", {"role": "Donor"})
		user.save(ignore_permissions=True)
