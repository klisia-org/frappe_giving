"""Ensure the Donor role has desk_access disabled.

`create_donor_role` only sets `desk_access=0` when it inserts the role.
On sites where the Donor role was created earlier (manually, by an
older patch, or by a previous app install) it may have desk_access=1,
which lets donor users into Desk and breaks the portal-only flow.

Idempotent — re-running just confirms the field stays at 0.
"""

import frappe


def execute():
	if not frappe.db.exists("Role", "Donor"):
		return
	if frappe.db.get_value("Role", "Donor", "desk_access") != 0:
		frappe.db.set_value("Role", "Donor", "desk_access", 0, update_modified=False)
