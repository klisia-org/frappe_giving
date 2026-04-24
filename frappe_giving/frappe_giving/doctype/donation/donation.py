import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, nowdate


class Donation(Document):
	def validate(self):
		self._compute_amount_usd()

	def on_submit(self):
		si = self._create_sales_invoice()
		if self.donation_via == "Portal":
			self._create_donation_payment(si.name, si.posting_date)
		self._set_status("Invoiced")

	def _compute_amount_usd(self):
		if self.amount and self.exchange_rate:
			self.amount_usd = self.amount * self.exchange_rate

	def _create_sales_invoice(self, amount=None, posting_date=None, persist_link=True):
		"""Create and submit a Sales Invoice for this donation.

		Defaults to the donation's own amount and date; subscription
		renewals override them via `_create_cycle_invoice_and_payment`.
		"""
		donor = frappe.get_doc("Donor", self.donor)
		if not donor.customer:
			frappe.throw(
				_(
					"Donor {0} has no linked Customer. "
					"Please save the Donor record first to auto-create one."
				).format(self.donor)
			)

		amount = amount if amount is not None else self.amount
		posting_date = posting_date or self.donation_date or nowdate()

		campaign = frappe.get_doc("Donation Campaign", self.campaign)

		si_dict = {
			"doctype": "Sales Invoice",
			"customer": donor.customer,
			"company": self.company,
			"cost_center": campaign.cost_center,
			"posting_date": posting_date,
			"due_date": posting_date,
			"currency": self.currency or "USD",
			"conversion_rate": self.exchange_rate or 1,
			"items": [
				{
					"item_code": campaign.erp_item,
					"qty": 1,
					"rate": amount,
					"cost_center": campaign.cost_center,
					"description": _("Donation {0} – Campaign: {1}").format(
						self.name, self.campaign
					),
				}
			],
		}

		if campaign.payment_term:
			si_dict["payment_terms_template"] = None
			payment_term = frappe.get_doc("Payment Term", campaign.payment_term)
			due_date = add_days(posting_date, payment_term.credit_days or 0)
			si_dict["due_date"] = due_date
			si_dict["payment_schedule"] = [
				{
					"payment_term": payment_term.name,
					"due_date_based_on": payment_term.due_date_based_on,
					"invoice_portion": 100,
					"payment_amount": amount,
					"credit_days_based_on": payment_term.due_date_based_on,
					"credit_days": payment_term.credit_days or 0,
					"due_date": due_date,
				}
			]

		si = frappe.get_doc(si_dict)
		si.insert(ignore_permissions=True)
		si.submit()

		if persist_link:
			frappe.db.set_value("Donation", self.name, "sales_invoice", si.name)
			self.sales_invoice = si.name

		frappe.msgprint(
			_("Sales Invoice {0} created").format(si.name), alert=True
		)
		return si

	def _create_donation_payment(
		self, si_name, invoice_date, amount=None, status="Waiting", stripe_pi_id=None
	):
		amount = amount if amount is not None else self.amount
		dp = frappe.get_doc(
			{
				"doctype": "Donation Payment",
				"donation": self.name,
				"sales_invoice": si_name,
				"invoice_date": invoice_date,
				"amount": amount,
				"currency": self.currency or "USD",
				"exchange_rate": self.exchange_rate or 1,
				"status": status,
				"stripe_payment_intent_id": stripe_pi_id or "",
				"date": nowdate() if status != "Waiting" else None,
			}
		)
		dp.insert(ignore_permissions=True)

		frappe.msgprint(
			_("Donation Payment {0} created").format(dp.name), alert=True
		)
		return dp

	def _create_cycle_invoice_and_payment(self, amount, date, stripe_pi_id):
		"""Create a new SI + Donation Payment for a subscription renewal cycle.

		Called by the Stripe webhook when `invoice.payment_succeeded` fires
		for a billing cycle after the first one. Does not touch
		`donation.sales_invoice` (that points at the first SI).
		"""
		si = self._create_sales_invoice(
			amount=amount, posting_date=date, persist_link=False
		)
		return self._create_donation_payment(
			si_name=si.name,
			invoice_date=si.posting_date,
			amount=amount,
			status="Succeeded",
			stripe_pi_id=stripe_pi_id,
		)

	def _set_status(self, status):
		frappe.db.set_value("Donation", self.name, "status", status)
		self.status = status
