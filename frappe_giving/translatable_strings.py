"""Register strings that Frappe's extractors miss into the POT.

Frappe ships gettext extractors for workspace, doctype, report, and a handful
of other fixture types — but not for Dashboard, Dashboard Chart, or Number
Card. Strings inside those fixtures never make it into `main.pot` and so
never make it into Crowdin, never compile into `.mo`, and never translate
on the desk.

This module is never imported. Its sole purpose is to hold `_()` calls
that the `**.py` Babel extractor will pick up and add to the POT. Once
strings land in the POT they follow the normal Crowdin → PO → MO pipeline
and the frontend's client-side `__()` calls translate them automatically.

Drop new fixture-only strings here as you add dashboards / number cards
/ dashboard charts. Remove an entry only when the underlying fixture is
deleted from the app.
"""

from frappe import _

# Dashboard Chart names (see frappe_giving/dashboard_chart/*/<chart>.json)
_("Donor Base")

# Number Card labels (see frappe_giving/number_card/*/<card>.json)
_("Donations per Month")
