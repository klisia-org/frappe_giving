"""Donation receipt helpers.

A donation receipt is distinct from a Sales Invoice: it's the donor-facing
artifact stating the gift was tax-deductible, with no goods or services
rendered in exchange (per IRS 501c3 guidance). We generate it on-demand as
a public HTML page and protect it with an HMAC-signed token so donors —
who are Guest users — can still reach their own receipt without auth.
"""

import hashlib
import hmac

import frappe


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
	token = get_receipt_token(donation_name)
	return f"/receipt?donation={donation_name}&token={token}"
