"""Stamp welcome_email_sent_at for donors who already have a successful charge.

Without this, deploying the new per-charge notification flow would surprise
existing donors with a "first donation" welcome email on their next renewal.
We mark every donor who already has at least one Succeeded Donation Payment
as having received their welcome (using their donor_since date as a
plausible timestamp). Future charges for these donors will route through
the shorter thank-you template.

Idempotent: only updates rows where welcome_email_sent_at IS NULL.
"""

import frappe


def execute():
    rows = frappe.db.sql(
        """
        SELECT DISTINCT d.name, d.donor_since
        FROM `tabDonor` d
        JOIN `tabDonation` dn ON dn.donor = d.name
        JOIN `tabDonation Payment` dp ON dp.donation = dn.name
        WHERE dp.status = 'Succeeded'
          AND (d.welcome_email_sent_at IS NULL OR d.welcome_email_sent_at = '')
        """,
        as_dict=True,
    )

    for row in rows:
        # donor_since is a Date; cast to a Datetime by appending midnight.
        stamp = f"{row.donor_since} 00:00:00" if row.donor_since else frappe.utils.now()
        frappe.db.set_value(
            "Donor",
            row.name,
            "welcome_email_sent_at",
            stamp,
            update_modified=False,
        )

    frappe.db.commit()
