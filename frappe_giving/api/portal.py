"""Donor-facing portal API.

Endpoints consumed by the Vue donor portal at /donate/portal. Every method
resolves the caller's Donor record server-side from `frappe.session.user`
— the client never supplies a donor identifier, so cross-donor access is
impossible by construction.
"""

from collections import defaultdict

import frappe
from frappe import _

from frappe_giving.api.receipts import email_yearly_statement, get_receipt_url


def _resolve_donor() -> str:
    if frappe.session.user == "Guest":
        frappe.throw(_("Authentication required."), frappe.PermissionError)
    donor = frappe.db.get_value("Donor", {"user": frappe.session.user}, "name")
    if not donor:
        frappe.throw(
            _("No donor record is linked to your account."),
            frappe.PermissionError,
        )
    return donor


@frappe.whitelist()
def get_donor_profile() -> dict | None:
    # `None` is a graceful signal to the portal UI that the current user
    # is logged in but not a donor (so we can show a "contact support"
    # message instead of looping them back through /login). The other
    # portal endpoints still raise PermissionError in the same situation
    # since they should never be reachable for a non-donor anyway.
    if frappe.session.user == "Guest":
        frappe.throw(_("Authentication required."), frappe.PermissionError)
    donor = frappe.db.get_value("Donor", {"user": frappe.session.user}, "name")
    if not donor:
        return None
    return frappe.db.get_value(
        "Donor",
        donor,
        ["name", "donor_name", "email", "donor_since", "status"],
        as_dict=True,
    )


@frappe.whitelist()
def email_yearly_statement_to_self(year) -> dict:
    """Donor-triggered re-send of their own yearly statement PDF.

    Sends to whatever email is on file for the donor. Used by the
    'Email this to me' button in the portal — gives donors an off-ramp
    when they don't want to download the PDF in-browser (e.g., they're
    on a kiosk or want it in their inbox for tax-time reference).
    """
    donor = _resolve_donor()
    donor_email = frappe.db.get_value("Donor", donor, "email")

    try:
        year = int(year)
    except (TypeError, ValueError):
        frappe.throw(_("Invalid year."))

    sent = email_yearly_statement(donor, year)
    if not sent:
        frappe.throw(
            _("No confirmed donations found for {0}.").format(year),
            frappe.DoesNotExistError,
        )
    return {"sent_to": donor_email}


@frappe.whitelist()
def get_portal_donate_form() -> dict:
    """Pick the best donation form for the logged-in donor.

    Priority:
      1. Active form attached to the campaign of the donor's most recent
         submitted donation — meets returning donors where they've already
         shown intent.
      2. The site-wide default form (same logic as `get_default_form_name`),
         so first-time portal visitors still land on a curated default.

    Returns the resolved form name plus the donor's prefillable identity,
    so the CampaignForm can render with name+email already known. If no
    active form exists anywhere, `form_name` is `None` and the UI shows
    a graceful empty state instead of routing to a 404.
    """
    donor = _resolve_donor()

    donor_profile = (
        frappe.db.get_value("Donor", donor, ["donor_name", "email"], as_dict=True) or {}
    )

    form_name = None
    last_campaign = frappe.db.get_value(
        "Donation",
        filters={"donor": donor, "docstatus": 1},
        fieldname="campaign",
        order_by="donation_date desc, name desc",
    )
    if last_campaign:
        form_name = frappe.db.get_value(
            "Campaign Form",
            {"campaign": last_campaign, "status": "Active"},
            "name",
        )

    if not form_name:
        from frappe_giving.api.donate import get_default_form_name

        form_name = get_default_form_name()

    return {
        "form_name": form_name,
        "donor": {
            "full_name": donor_profile.get("donor_name") or "",
            "email": donor_profile.get("email") or "",
        },
    }


@frappe.whitelist()
def get_active_recurring_donations() -> list[dict]:
    """Active subscriptions, newest first, enriched with last-charge date."""
    donor = _resolve_donor()
    donations = frappe.get_all(
        "Donation",
        filters={
            "donor": donor,
            "frequency": ["!=", "One-Time"],
            "subscription_status": "Active",
            "docstatus": 1,
        },
        fields=[
            "name",
            "amount",
            "currency",
            "frequency",
            "campaign",
            "donation_date",
            "gate_subscription_id",
        ],
        order_by="donation_date desc",
    )
    if not donations:
        return []

    names = [d.name for d in donations]
    last_by_donation = {
        row.donation: row.last_date
        for row in frappe.db.sql(
            """
			SELECT donation, MAX(date) AS last_date
			FROM `tabDonation Payment`
			WHERE donation IN %(names)s AND status = 'Succeeded'
			GROUP BY donation
			""",
            {"names": tuple(names)},
            as_dict=True,
        )
    }

    campaign_labels = _campaign_labels([d.campaign for d in donations])
    for d in donations:
        d.campaign_label = campaign_labels.get(d.campaign, d.campaign)
        d.last_payment_date = last_by_donation.get(d.name)
    return donations


@frappe.whitelist()
def get_donation_history(
    year: int | None = None, limit: int = 50, offset: int = 0
) -> dict:
    """Paginated history for the logged-in donor, newest first. Each row
    carries a ready-to-open `receipt_pdf_url` so the UI doesn't need to
    round-trip for token generation."""
    donor = _resolve_donor()
    try:
        limit = max(1, min(int(limit), 200))
        offset = max(0, int(offset))
    except (TypeError, ValueError):
        frappe.throw(_("Invalid pagination parameters."))

    filters = {"donor": donor, "docstatus": 1}
    if year:
        try:
            year = int(year)
        except (TypeError, ValueError):
            frappe.throw(_("Invalid year."))
        filters["donation_date"] = ["between", [f"{year}-01-01", f"{year}-12-31"]]

    rows = frappe.get_all(
        "Donation",
        filters=filters,
        fields=[
            "name",
            "amount",
            "currency",
            "frequency",
            "donation_date",
            "status",
            "campaign",
        ],
        order_by="donation_date desc, name desc",
        limit_start=offset,
        limit_page_length=limit + 1,  # fetch one extra to detect has_more
    )
    has_more = len(rows) > limit
    rows = rows[:limit]

    campaign_labels = _campaign_labels([r.campaign for r in rows])
    for r in rows:
        r.campaign_label = campaign_labels.get(r.campaign, r.campaign)
        # Only receiptable donations get a URL; the UI hides the link otherwise.
        if r.status in ("Invoiced", "Paid"):
            r.receipt_pdf_url = get_receipt_url(r.name)
        else:
            r.receipt_pdf_url = None

    return {"rows": rows, "has_more": has_more}


@frappe.whitelist()
def get_available_years() -> list[int]:
    """Calendar years with at least one confirmed donation, descending."""
    donor = _resolve_donor()
    rows = frappe.db.sql(
        """
		SELECT DISTINCT YEAR(donation_date) AS y
		FROM `tabDonation`
		WHERE donor = %s
		  AND status IN ('Invoiced', 'Paid')
		  AND docstatus = 1
		ORDER BY y DESC
		""",
        (donor,),
    )
    return [int(r[0]) for r in rows if r[0]]


@frappe.whitelist()
def get_yearly_summary(year: int) -> dict:
    """Consolidated totals + line items for a calendar year. Same filters
    and shape the yearly-statement PDF uses, so the on-screen summary
    and the downloaded PDF stay in sync."""
    donor = _resolve_donor()
    try:
        year = int(year)
    except (TypeError, ValueError):
        frappe.throw(_("Invalid year."))

    lines = frappe.db.sql(
        """
		SELECT name, donation_date AS date, amount, currency, amount_usd,
		       campaign, frequency
		FROM `tabDonation`
		WHERE donor = %s
		  AND YEAR(donation_date) = %s
		  AND status IN ('Invoiced', 'Paid')
		  AND docstatus = 1
		ORDER BY donation_date
		""",
        (donor, year),
        as_dict=True,
    )

    campaign_labels = _campaign_labels([l.campaign for l in lines])
    totals_by_currency: dict[str, float] = defaultdict(float)
    total_usd = 0.0
    for l in lines:
        l.campaign_label = campaign_labels.get(l.campaign, l.campaign)
        totals_by_currency[l.currency or "USD"] += float(l.amount or 0)
        total_usd += float(l.amount_usd or 0)

    return {
        "year": year,
        "donation_count": len(lines),
        "line_items": lines,
        "currency_breakdown": [
            {"currency": c, "total": round(t, 2)}
            for c, t in sorted(totals_by_currency.items())
        ],
        "total_usd": round(total_usd, 2),
    }


def _campaign_labels(campaign_names: list[str]) -> dict[str, str]:
    unique = {c for c in campaign_names if c}
    if not unique:
        return {}
    rows = frappe.get_all(
        "Donation Campaign",
        filters={"name": ["in", list(unique)]},
        fields=["name", "campaign_name"],
    )
    return {r.name: r.campaign_name or r.name for r in rows}
