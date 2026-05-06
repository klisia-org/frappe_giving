app_name = "frappe_giving"
app_title = "Frappe Giving"
app_publisher = "Klisia"
app_description = "Donation management for Frappe/ERPNext"
app_icon = "frappe_giving.png"
app_logo_url = "/assets/frappe_giving/images/frappe_giving.png"
app_email = "support@klisia.org"
app_license = "mit"

# Apps
# ------------------

required_apps = ["erpnext"]

# Each item in the list will be shown as an app in the apps page
add_to_apps_screen = [
    {
        "name": "frappe_giving",
        "logo": "/assets/frappe_giving/images/frappe_giving.svg",
        "title": "Frappe Giving",
        "route": "/app/frappe-giving",
    }
]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/frappe_giving/css/frappe_giving.css"
# app_include_js = "/assets/frappe_giving/js/frappe_giving.js"

# include js, css files in header of web template
# web_include_css = "/assets/frappe_giving/css/frappe_giving.css"
# web_include_js = "/assets/frappe_giving/js/frappe_giving.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "frappe_giving/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "frappe_giving/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "frappe_giving.utils.jinja_methods",
# 	"filters": "frappe_giving.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "frappe_giving.install.before_install"
# after_install = "frappe_giving.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "frappe_giving.uninstall.before_uninstall"
# after_uninstall = "frappe_giving.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "frappe_giving.utils.before_app_install"
# after_app_install = "frappe_giving.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "frappe_giving.utils.before_app_uninstall"
# after_app_uninstall = "frappe_giving.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "frappe_giving.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# Row-level restriction for donors: Users with the `Donor` role (and no
# bypass role) can only see their own Donor record, their Donations, and
# the Donation Payments attached to those Donations.
permission_query_conditions = {
    "Donor": "frappe_giving.donor_permissions.donor_query_conditions",
    "Donation": "frappe_giving.donor_permissions.donation_query_conditions",
    "Donation Payment": "frappe_giving.donor_permissions.donation_payment_query_conditions",
}
has_permission = {
    "Donor": "frappe_giving.donor_permissions.donor_has_permission",
    "Donation": "frappe_giving.donor_permissions.donation_has_permission",
    "Donation Payment": "frappe_giving.donor_permissions.donation_payment_has_permission",
}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    "Sales Invoice": {
        "on_submit": "frappe_giving.signals.sales_invoice.on_submit",
    },
    "Payment Entry": {
        "on_submit": "frappe_giving.signals.payment_entry.on_submit",
    },
}

# Scheduled Tasks
# ---------------

scheduler_events = {
    "cron": {
        # Jan 5, 08:00 site-local. The 5-day buffer past Dec 31 lets late
        # Stripe renewals and webhook backfills settle before the batch
        # snapshots the year. Idempotent — `last_statement_emailed_year`
        # on Donor prevents accidental re-sends if the cron also fires
        # manually.
        "0 8 5 1 *": [
            "frappe_giving.tasks.send_annual_statements",
        ],
    },
}

# Fixtures
# --------
# Bootstrap editable Email Templates so admins can tweak subject/body without
# code changes. Filtered by name prefix so we only ever export our own.

fixtures = [
    {
        "doctype": "Email Template",
        "filters": [["name", "like", "frappe_giving_%"]],
    },
]

# Testing
# -------

# before_tests = "frappe_giving.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "frappe_giving.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "frappe_giving.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "frappe_giving.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["frappe_giving.utils.before_request"]
# after_request = ["frappe_giving.utils.after_request"]

# Job Events
# ----------
# before_job = ["frappe_giving.utils.before_job"]
# after_job = ["frappe_giving.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"frappe_giving.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []


website_route_rules = [
    # The donor portal is a nested SPA route (/donate/donorportal,
    # /donate/donorportal/history, /donate/donorportal/receipts), so we
    # need a path-converter rule to hand every subpath to the same
    # donate.html entry. This specific prefix keeps the generic
    # single-segment `<form_name>` rule below untouched so Builder pages
    # under `/donate/*` still resolve through Frappe's regular routing.
    {"from_route": "/donate/donorportal", "to_route": "donate"},
    {"from_route": "/donate/donorportal/<path:subpath>", "to_route": "donate"},
    # Single-segment match for campaign forms.
    {"from_route": "/donate/<form_name>", "to_route": "donate"},
    {"from_route": "/donate", "to_route": "donate"},
]
