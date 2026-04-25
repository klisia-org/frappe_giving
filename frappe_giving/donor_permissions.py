"""Row-level permissions for the donor-facing doctypes.

A User with the `Donor` role may read and print their own Donor record,
their Donations, and the Donation Payments attached to those Donations.
Users with a staff role (System Manager, Accounts Manager, Accounts User)
are never restricted — they always see everything.

These hooks are registered in hooks.py under `has_permission` and
`permission_query_conditions` for each of the three doctypes.
"""

import frappe

# Staff roles that always bypass the donor restriction. A User carrying
# any of these sees all records, even if they're also linked to a Donor.
BYPASS_ROLES = {"System Manager", "Accounts Manager", "Accounts User"}


def _current_donor(user: str) -> str | None:
    return frappe.db.get_value("Donor", {"user": user}, "name")


def _should_restrict(user: str) -> bool:
    if not user or user == "Administrator":
        return False
    roles = set(frappe.get_roles(user))
    if roles & BYPASS_ROLES:
        return False
    return bool(_current_donor(user))


# ---------------------------------------------------------------------------
# Donation
# ---------------------------------------------------------------------------
def donation_has_permission(doc, ptype, user):
    if not user:
        user = frappe.session.user
    if not _should_restrict(user):
        return True
    return getattr(doc, "donor", None) == _current_donor(user)


def donation_query_conditions(user):
    if not user:
        user = frappe.session.user
    if not _should_restrict(user):
        return ""
    donor = _current_donor(user)
    if not donor:
        return "1=0"
    return f"(`tabDonation`.donor = {frappe.db.escape(donor)})"


# ---------------------------------------------------------------------------
# Donor
# ---------------------------------------------------------------------------
def donor_has_permission(doc, ptype, user):
    if not user:
        user = frappe.session.user
    if not _should_restrict(user):
        return True
    return getattr(doc, "name", None) == _current_donor(user)


def donor_query_conditions(user):
    if not user:
        user = frappe.session.user
    if not _should_restrict(user):
        return ""
    donor = _current_donor(user)
    if not donor:
        return "1=0"
    return f"(`tabDonor`.name = {frappe.db.escape(donor)})"


# ---------------------------------------------------------------------------
# Donation Payment (child of Donation, filter by parent.donor)
# ---------------------------------------------------------------------------
def donation_payment_has_permission(doc, ptype, user):
    if not user:
        user = frappe.session.user
    if not _should_restrict(user):
        return True
    donor = _current_donor(user)
    parent_donor = frappe.db.get_value("Donation", doc.donation, "donor")
    return parent_donor == donor


def donation_payment_query_conditions(user):
    if not user:
        user = frappe.session.user
    if not _should_restrict(user):
        return ""
    donor = _current_donor(user)
    if not donor:
        return "1=0"
    return (
        f"(`tabDonation Payment`.donation IN ("
        f"SELECT name FROM `tabDonation` "
        f"WHERE donor = {frappe.db.escape(donor)}"
        f"))"
    )
