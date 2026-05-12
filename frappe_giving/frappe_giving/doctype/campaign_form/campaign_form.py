import frappe
from frappe import _
from frappe.model.document import Document


class CampaignForm(Document):
	def validate(self):
		self._validate_single_default_giving_level()

	def _validate_single_default_giving_level(self):
		defaults = [row for row in (self.giving_levels or []) if row.is_default]
		if len(defaults) > 1:
			frappe.throw(_("Only one giving level can be marked as default."))
