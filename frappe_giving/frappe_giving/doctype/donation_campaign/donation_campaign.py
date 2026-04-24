import frappe
from frappe import _
from frappe.model.document import Document


class DonationCampaign(Document):
	def validate(self):
		self._validate_single_default()

	def _validate_single_default(self):
		if not self.default:
			return

		existing_default = frappe.db.get_value(
			"Donation Campaign",
			{"default": 1, "name": ("!=", self.name)},
			"name",
		)

		if existing_default:
			frappe.throw(
				_(
					"Campaign {0} is already set as the default. "
					"Please uncheck it first before setting a new default."
				).format(existing_default)
			)
