"""Donation receipt helpers.

A donation receipt is distinct from a Sales Invoice: it's the donor-facing
artifact stating the gift was tax-deductible, with no goods or services
rendered in exchange (per IRS 501c3 guidance). We generate it on-demand as
a real PDF rendered from a Frappe Print Format. Guest donors reach their
own receipt via an HMAC-signed token on the URL; logged-in donors are
authorized by matching `Donor.user == frappe.session.user`.
"""

import hashlib
import hmac
from collections import defaultdict

import frappe
from frappe import _


def _signing_key() -> bytes:
    """Return a site-local secret for HMAC.

    Prefer `encryption_key` from common_site_config (always set on
    Frappe sites since it's used for field encryption). Fall back to
    the site name as a last resort — still unique per site, just less
    secret.
    """
    key = frappe.local.conf.get("encryption_key") or ""
    if not key:
        key = frappe.local.site or "frappe-giving"
    return str(key).encode()


def get_receipt_token(donation_name: str) -> str:
    """Deterministic HMAC token for the receipt URL.

    Stable across reloads, unique per donation, unforgeable without the
    site's encryption_key.
    """
    mac = hmac.new(_signing_key(), f"receipt:{donation_name}".encode(), hashlib.sha256)
    return mac.hexdigest()[:32]  # 128 bits, hex-encoded


def validate_token(donation_name: str, token: str | None) -> bool:
    expected = get_receipt_token(donation_name)
    return hmac.compare_digest(expected, token or "")


def get_receipt_url(donation_name: str) -> str:
    """Public URL that streams the donation's receipt PDF."""
    token = get_receipt_token(donation_name)
    return (
        f"/api/method/frappe_giving.api.receipts.download_donation_receipt"
        f"?donation={donation_name}&token={token}"
    )


def _render_pdf(doctype: str, name: str, print_format: str, doc=None) -> bytes:
    """Render a PDF for an already-authorized request.

    Two paths:
      * Logged-in donor — the caller's User carries the `Donor` role plus
        a `has_permission` hook that grants read+print on their own
        records. frappe.get_print runs against the real session, no
        elevation.
      * Guest (HMAC-token) — there's no session role to lean on, so we
        render the Print Format's Jinja template ourselves and convert
        with get_pdf. Authorization came from validate_token upstream;
        doc/print-format loads bypass read perm because only this
        request path can reach the code.
    """
    if frappe.session.user == "Guest":
        from frappe.utils.pdf import get_pdf

        prev = getattr(frappe.flags, "ignore_permissions", False)
        frappe.flags.ignore_permissions = True
        try:
            if doc is None:
                doc = frappe.get_doc(doctype, name)
            pf = frappe.get_doc("Print Format", print_format)
            html = frappe.render_template(pf.html, {"doc": doc})
        finally:
            frappe.flags.ignore_permissions = prev
        return get_pdf(html)

    return frappe.get_print(
        doctype=doctype,
        name=name,
        print_format=print_format,
        as_pdf=True,
        doc=doc,
    )


@frappe.whitelist(allow_guest=True)
def download_donation_receipt(donation: str, token: str | None = None):
    """Stream a single-donation receipt PDF.

    Two auth paths:
      * `token` is a valid HMAC for this donation (email-link flow)
      * caller is logged in and their User links to this donation's Donor
    """
    if not donation:
        frappe.throw(_("Missing donation reference."), frappe.PermissionError)

    if not frappe.db.exists("Donation", donation):
        frappe.throw(_("Donation not found."), frappe.DoesNotExistError)

    if token:
        if not validate_token(donation, token):
            frappe.throw(_("Invalid or expired receipt link."), frappe.PermissionError)
    else:
        if frappe.session.user == "Guest":
            frappe.throw(_("Authentication required."), frappe.PermissionError)
        donor_name = frappe.db.get_value("Donation", donation, "donor")
        linked_user = frappe.db.get_value("Donor", donor_name, "user")
        if linked_user != frappe.session.user:
            frappe.throw(
                _("You do not have permission to access this receipt."),
                frappe.PermissionError,
            )

    status = frappe.db.get_value("Donation", donation, "status")
    if status not in ("Invoiced", "Paid"):
        frappe.throw(
            _("This donation is not yet confirmed. Please check back later."),
            frappe.ValidationError,
        )

    pdf = _render_pdf("Donation", donation, "Donation Receipt")

    frappe.local.response.filename = f"donation-receipt-{donation}.pdf"
    frappe.local.response.filecontent = pdf
    frappe.local.response.type = "download"


def generate_yearly_statement(donor_name: str, year: int) -> tuple[str, bytes]:
    """Build the consolidated yearly statement PDF for a specific donor.

    Single source of truth for the statement renderer, used by:
      * `download_yearly_statement` — streams the PDF to the browser
      * `email_yearly_statement` — attaches the PDF to an outbound email
      * `tasks.send_annual_statements` — bulk year-end batch

    Returns `(filename, pdf_bytes)`. Raises `DoesNotExistError` if the
    donor has no Invoiced/Paid donations in the given year — callers
    should handle that as "skip, not an error".
    """
    try:
        year = int(year)
    except (TypeError, ValueError):
        frappe.throw(_("Invalid year."))

    lines = frappe.db.sql(
        """
		SELECT name, donation_date as date, amount, currency, amount_usd,
		       campaign, frequency, company
		FROM `tabDonation`
		WHERE donor = %s
		  AND YEAR(donation_date) = %s
		  AND status IN ('Invoiced', 'Paid')
		  AND docstatus = 1
		ORDER BY donation_date
		""",
        (donor_name, year),
        as_dict=True,
    )

    if not lines:
        frappe.throw(
            _("No confirmed donations found for {0}.").format(year),
            frappe.DoesNotExistError,
        )

    campaign_labels: dict[str, str] = {}
    company_counts: dict[str, int] = defaultdict(int)
    totals_by_currency: dict[str, float] = defaultdict(float)
    total_usd = 0.0

    for line in lines:
        if line.campaign and line.campaign not in campaign_labels:
            campaign_labels[line.campaign] = (
                frappe.db.get_value("Donation Campaign", line.campaign, "campaign_name")
                or line.campaign
            )
        line.campaign_label = campaign_labels.get(line.campaign, line.campaign)
        totals_by_currency[line.currency or "USD"] += float(line.amount or 0)
        total_usd += float(line.amount_usd or 0)
        if line.company:
            company_counts[line.company] += 1

    # Use the company with the most donations as the letterhead; most
    # donors give to a single entity so this is just a safe default for
    # multi-company edge cases.
    primary_company = (
        max(company_counts.items(), key=lambda kv: kv[1])[0] if company_counts else None
    )

    prev = getattr(frappe.flags, "ignore_permissions", False)
    frappe.flags.ignore_permissions = True
    try:
        donor_doc = frappe.get_doc("Donor", donor_name)
    finally:
        frappe.flags.ignore_permissions = prev

    donor_doc.statement_year = year
    donor_doc.statement_company = primary_company
    donor_doc.statement_line_items = lines
    donor_doc.statement_currency_breakdown = [
        frappe._dict(currency=c, total=round(t, 2))
        for c, t in sorted(totals_by_currency.items())
    ]
    # Only show a USD grand total when there's more than one currency —
    # for single-currency donors the breakdown row already is the total.
    donor_doc.statement_total_usd = (
        round(total_usd, 2) if len(totals_by_currency) > 1 else 0
    )

    pdf = _render_pdf("Donor", donor_name, "Donation Yearly Statement", doc=donor_doc)
    filename = f"donation-statement-{year}-{donor_name}.pdf"
    return filename, pdf


def email_yearly_statement(donor_name: str, year: int) -> bool:
    """Generate the yearly statement and email it to the donor.

    Returns True on a successful send, False if the donor has no
    confirmed donations in `year` (no email is sent — there's nothing
    to attest). All other failures (missing email, bad PDF render, SMTP
    rejection) propagate so the batch caller can log and continue.

    On success, stamps `Donor.last_statement_emailed_year` with the
    year — that's the idempotence key for the annual batch.
    """
    donor = frappe.get_doc("Donor", donor_name)
    if not donor.email:
        frappe.throw(
            _("Donor {0} has no email on file.").format(donor_name),
            frappe.ValidationError,
        )

    try:
        filename, pdf = generate_yearly_statement(donor_name, year)
    except frappe.DoesNotExistError:
        return False

    # Look up a company display name for subject/body. `generate_yearly_statement`
    # already picked the primary company internally; recompute the cheap
    # version here rather than restructure the helper to expose it.
    company_name = frappe.db.get_value(
        "Donation",
        {
            "donor": donor_name,
            "docstatus": 1,
            "status": ["in", ["Invoiced", "Paid"]],
            "donation_date": ["between", [f"{year}-01-01", f"{year}-12-31"]],
        },
        "company",
        order_by="donation_date desc",
    ) or _("our organisation")

    subject = _("Your {0} donation statement from {1}").format(year, company_name)
    message = _(
        "Hi {0},\n\n"
        "Thank you for your support of {1} in {2}. Your consolidated "
        "donation statement for the year is attached as a PDF — please "
        "keep it for your tax records.\n\n"
        "You can also access this and previous years' statements anytime "
        "through your donor portal."
    ).format(donor.donor_name or _("friend"), company_name, year)

    frappe.sendmail(
        recipients=[donor.email],
        subject=subject,
        message=message,
        attachments=[{"fname": filename, "fcontent": pdf}],
    )

    frappe.db.set_value(
        "Donor",
        donor_name,
        "last_statement_emailed_year",
        year,
        update_modified=False,
    )
    return True


@frappe.whitelist()
def download_yearly_statement(year: int):
    """Stream a consolidated per-year donation statement PDF for the
    logged-in donor."""
    donor_name = frappe.db.get_value("Donor", {"user": frappe.session.user}, "name")
    if not donor_name:
        frappe.throw(
            _("No donor record linked to your account."), frappe.PermissionError
        )

    filename, pdf = generate_yearly_statement(donor_name, year)

    frappe.local.response.filename = filename
    frappe.local.response.filecontent = pdf
    frappe.local.response.type = "download"
