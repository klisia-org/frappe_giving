import frappe
from frappe.model.document import Document


class FrappeGivingSettings(Document):
	pass


def get_settings():
	return frappe.get_cached_doc("Frappe Giving Settings")
