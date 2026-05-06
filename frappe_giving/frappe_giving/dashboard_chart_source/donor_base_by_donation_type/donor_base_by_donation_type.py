"""Dashboard chart source: split the active donor base by donation type.

Two mutually exclusive categories so the slices sum to the active donor
base:

  - Subscribers: donors with at least one submitted Donation whose
    frequency is anything other than One-Time.
  - One-Time: donors who only have submitted One-Time Donations.

A donor with both kinds counts as a Subscriber (recurring relationship
trumps a side one-off gift). Donors without any submitted Donation are
not counted — they're prospects, not part of the active base.
"""

import frappe
from frappe.utils import cint


@frappe.whitelist()
def get(
    chart_name=None,
    chart=None,
    no_cache=None,
    filters=None,
    from_date=None,
    to_date=None,
    timespan=None,
    time_interval=None,
    heatmap_year=None,
    refresh=None,
):
    # Cache by hand instead of using `@cache_source`. The stock decorator
    # also writes `last_synced_on` back to the Dashboard Chart row — under
    # contention that UPDATE can hit a lock-wait timeout (1205) on
    # `tabDashboard Chart`. We don't need that timestamp for anything;
    # skipping the write avoids the issue entirely.
    cache_key = f"chart-data:{chart_name or 'donor-base-by-donation-type'}"
    if not cint(refresh):
        cached = frappe.cache.get_value(cache_key)
        if cached:
            return frappe.parse_json(frappe.safe_decode(cached))

    result = _compute()
    frappe.cache.set_value(cache_key, frappe.as_json(result))
    return result


def _compute():
    subscribers = (
        frappe.db.sql(
            """
            SELECT COUNT(DISTINCT donor)
            FROM `tabDonation`
            WHERE docstatus = 1
              AND frequency != 'One-Time'
            """
        )[0][0]
        or 0
    )

    one_time_only = (
        frappe.db.sql(
            """
            SELECT COUNT(DISTINCT d.donor)
            FROM `tabDonation` d
            WHERE d.docstatus = 1
              AND d.frequency = 'One-Time'
              AND NOT EXISTS (
                  SELECT 1
                  FROM `tabDonation` d2
                  WHERE d2.donor = d.donor
                    AND d2.docstatus = 1
                    AND d2.frequency != 'One-Time'
              )
            """
        )[0][0]
        or 0
    )

    return {
        "labels": ["One-Time", "Subscribers"],
        "datasets": [{"name": "Donors", "values": [one_time_only, subscribers]}],
    }
