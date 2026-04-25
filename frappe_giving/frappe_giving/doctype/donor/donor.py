import frappe
from frappe import _
from frappe.model.document import Document


class Donor(Document):
	def after_insert(self):
		self._create_user()
		self._create_customer_and_contact()

	def _create_user(self):
		if self.user:
			return

		if frappe.db.exists("User", self.email):
			user = frappe.get_doc("User", self.email)
		else:
			user = frappe.get_doc(
				{
					"doctype": "User",
					"email": self.email,
					"first_name": self.donor_name,
					"send_welcome_email": 0,
					"user_type": "Website User",
				}
			)
			user.insert(ignore_permissions=True)

		self.db_set("user", user.name, update_modified=False)
		frappe.msgprint(
			_("User {0} linked to Donor").format(user.name), alert=True
		)

	def _create_customer_and_contact(self):
		customer = self._create_customer()
		self._create_contact(customer.name)

	def _create_customer(self):
		if self.customer:
			return frappe.get_doc("Customer", self.customer)

		customer_group = frappe.db.get_single_value(
			"Selling Settings", "customer_group"
		)

		customer = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": self.donor_name,
				"customer_group": customer_group,
				"customer_type": "Individual"
				if self.donor_type == "Individual"
				else "Company",
			}
		)
		customer.insert(ignore_permissions=True)

		self.db_set("customer", customer.name, update_modified=False)
		frappe.msgprint(
			_("Customer {0} created and linked to Donor").format(customer.name),
			alert=True,
		)
		return customer

	def _create_contact(self, customer_name):
		if self.contact:
			return frappe.get_doc("Contact", self.contact)

		contact = frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": self.donor_name,
				"email_ids": [{"email_id": self.email, "is_primary": 1}],
				"links": [
					{
						"link_doctype": "Customer",
						"link_name": customer_name,
					}
				],
			}
		)
		contact.insert(ignore_permissions=True)

		self.db_set("contact", contact.name, update_modified=False)
		frappe.msgprint(
			_("Contact {0} created and linked to Donor and Customer").format(
				contact.name
			),
			alert=True,
		)
		return contact
