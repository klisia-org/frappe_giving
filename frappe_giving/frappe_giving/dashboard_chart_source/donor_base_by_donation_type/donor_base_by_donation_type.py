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
from frappe.utils.dashboard import cache_source


@frappe.whitelist()
@cache_source
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
):
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
