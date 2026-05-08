"""Install hooks for frappe_giving.

Right now this only handles wiring `allowed_referrers` so the embed widget
works for logged-in users on a fresh site. See ADR 0004 for the why.
"""

import frappe
from frappe.installer import update_site_config
from frappe.utils import get_url


def after_install():
    _ensure_allowed_referrer()


def _ensure_allowed_referrer():
    """Append the site's URL to `allowed_referrers` in site_config.json.

    Frappe v16's CSRF check (`frappe.auth.HTTPRequest.validate_csrf_token`)
    rejects logged-in POSTs that don't carry an `X-Frappe-CSRF-Token`
    header. The embed widget runs on host pages whose templates don't
    expose `window.csrf_token`, so its POSTs would fail. Adding the site
    origin to `allowed_referrers` lets `is_allowed_referrer()` short-circuit
    the check for same-origin requests, which is the only configuration
    the widget supports anyway.

    Idempotent — re-running on a site that already has the URL is a noop.
    Sites behind a reverse proxy whose `host_name` was set after install
    should verify `site_config.json` manually; we use whatever
    `frappe.utils.get_url()` returns at install time.
    """
    site_url = (get_url() or "").rstrip("/")
    if not site_url:
        return

    existing = frappe.conf.get("allowed_referrers") or []
    if not isinstance(existing, list):
        # Don't clobber a non-list value an operator set deliberately.
        return

    if site_url in existing:
        return

    update_site_config("allowed_referrers", list(existing) + [site_url])
