import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, nowdate


# `self.sales_invoice` is persisted via `frappe.db.set_value` in
# `_create_sales_invoice`; the subsequent `self.sales_invoice = si.name` only
# keeps the in-memory doc in sync.
class Donation(Document):  # nosemgrep: frappe-modifying-but-not-comitting-other-method
    def validate(self):
        self._compute_amount_usd()

    def on_submit(self):
        # Non-Stripe recurring: hand scheduling off to ERPNext Subscription.
        # No immediate SI — the subscription's scheduler owns cadence.
        if self.frequency != "One-Time" and self.donation_via == "Direct Payment":
            self._create_erpnext_subscription()
            self._set_status("Invoiced")
            return

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

        When the donor opted to cover transaction fees, the SI carries two
        item lines: the deductible donation (campaign income account) and a
        non-deductible fee-recovery surcharge (separate item + income
        account from Frappe Giving Settings). The donor-facing receipt
        breaks these apart; the GL keeps tax-deductible income clean.
        """
        donor = frappe.get_doc("Donor", self.donor)
        if not donor.customer:
            frappe.throw(
                _(
                    "Donor {0} has no linked Customer. "
                    "Please save the Donor record first to auto-create one."
                ).format(self.donor)
            )

        fee_portion = float(self.fee_recovered or 0) if self.cover_fees else 0
        if amount is None:
            amount = float(self.amount or 0) + fee_portion
        # Subscription cycles pass the gross Stripe charge as `amount`; the
        # donation portion is whatever's left after the fee surcharge that
        # was set at signup. For first-charge SIs `amount` already equals
        # self.amount + fee_portion so this is a no-op.
        donation_portion = float(amount) - fee_portion

        posting_date = posting_date or self.donation_date or nowdate()

        campaign = frappe.get_doc("Donation Campaign", self.campaign)

        donation_item = {
            "item_code": campaign.erp_item,
            "qty": 1,
            "rate": donation_portion,
            "cost_center": campaign.cost_center,
            "description": _("Donation {0} – Campaign: {1}").format(
                self.name, self.campaign
            ),
        }
        if campaign.account:
            donation_item["income_account"] = campaign.account

        items = [donation_item]

        if fee_portion > 0:
            settings = frappe.get_cached_doc("Frappe Giving Settings")
            if not settings.item_fee_recovery or not settings.account_fee_recovery:
                frappe.throw(
                    _(
                        "Fee recovery is enabled on this donation but Frappe "
                        "Giving Settings is missing 'Item for fee recovery' "
                        "and/or 'Account for Fee Recovery'. Configure both "
                        "and try again."
                    )
                )
            items.append(
                {
                    "item_code": settings.item_fee_recovery,
                    "qty": 1,
                    "rate": fee_portion,
                    "cost_center": campaign.cost_center,
                    "income_account": settings.account_fee_recovery,
                    "description": _("Transaction fee recovery"),
                }
            )

        si_dict = {
            "doctype": "Sales Invoice",
            "customer": donor.customer,
            "company": self.company,
            "cost_center": campaign.cost_center,
            "posting_date": posting_date,
            "due_date": posting_date,
            "currency": self.currency or "USD",
            "conversion_rate": self.exchange_rate or 1,
            "items": items,
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
        si.flags.ignore_permissions = True
        si.insert(ignore_permissions=True)
        si.submit()

        if persist_link:
            frappe.db.set_value("Donation", self.name, "sales_invoice", si.name)
            self.sales_invoice = si.name

        frappe.msgprint(_("Sales Invoice {0} created").format(si.name), alert=True)
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

        frappe.msgprint(_("Donation Payment {0} created").format(dp.name), alert=True)
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
        dp = self._create_donation_payment(
            si_name=si.name,
            invoice_date=si.posting_date,
            amount=amount,
            status="Succeeded",
            stripe_pi_id=stripe_pi_id,
        )
        self._reconcile_sales_invoice(si.name, amount, stripe_pi_id, date)
        return dp

    def _reconcile_sales_invoice(
        self, si_name, amount, stripe_pi_id, posting_date=None
    ):
        """Create and submit a Payment Entry that marks the SI as Paid.

        Uses the Payment Gateway Account configured for Stripe. The Payment
        Entry debits the gateway clearing account and credits AR, matching
        the Sales Invoice. Actual bank deposit (net of fees) is reconciled
        later via ERPNext's Bank Reconciliation.

        Failures write to the Error Log instead of being silently swallowed —
        this runs in webhook and sync-confirm contexts where no operator is
        watching for msgprint alerts.
        """
        from erpnext.accounts.doctype.payment_entry.payment_entry import (
            get_payment_entry,
        )

        # Find any Payment Gateway Account whose Payment Gateway uses
        # Stripe Settings. Sites often have multiple Payment Gateway records
        # pointing at the same Stripe account, and we don't want to pin on
        # one specific name — any matching PGA is the correct clearing target.
        stripe_gateways = frappe.get_all(
            "Payment Gateway",
            filters={"gateway_settings": "Stripe Settings"},
            pluck="name",
        )

        clearing_account = None
        if stripe_gateways:
            clearing_account = frappe.db.get_value(
                "Payment Gateway Account",
                {
                    "payment_gateway": ("in", stripe_gateways),
                    "company": self.company,
                },
                "payment_account",
            ) or frappe.db.get_value(
                "Payment Gateway Account",
                {"payment_gateway": ("in", stripe_gateways)},
                "payment_account",
            )

        if not clearing_account:
            frappe.log_error(
                title="Donation reconcile: no Payment Gateway Account",
                message=(
                    f"Donation: {self.name}\n"
                    f"Sales Invoice: {si_name}\n"
                    f"Company: {self.company}\n"
                    f"Stripe gateways on site: {stripe_gateways}\n"
                    "Fix: create a Payment Gateway Account at "
                    "/app/payment-gateway-account pointing at one of the "
                    "gateways above."
                ),
            )
            return None

        posting_date = posting_date or nowdate()
        pe = get_payment_entry("Sales Invoice", si_name, bank_account=clearing_account)
        pe.posting_date = posting_date
        pe.reference_no = stripe_pi_id or si_name
        pe.reference_date = posting_date
        pe.paid_amount = amount
        pe.received_amount = amount
        pe.flags.ignore_permissions = True
        pe.insert(ignore_permissions=True)
        pe.submit()

        return pe

    def _create_erpnext_subscription(self):
        """Create an ERPNext Subscription for a non-Stripe recurring donation.

        The Subscription's daily scheduler generates (and auto-submits) a
        Sales Invoice each cycle. Our Sales Invoice `on_submit` hook then
        creates the paired Donation Payment (status Waiting) and the Payment
        Entry hook flips it to Succeeded when staff reconciles the check.
        """
        donor = frappe.get_doc("Donor", self.donor)
        if not donor.customer:
            frappe.throw(
                _(
                    "Donor {0} has no linked Customer; cannot create an "
                    "ERPNext Subscription."
                ).format(self.donor)
            )

        campaign = frappe.get_doc("Donation Campaign", self.campaign)
        plan_name = self._ensure_subscription_plan(campaign)

        sub = frappe.get_doc(
            {
                "doctype": "Subscription",
                "party_type": "Customer",
                "party": donor.customer,
                "company": self.company,
                "cost_center": campaign.cost_center,
                "start_date": self.donation_date or nowdate(),
                "submit_invoice": 1,
                "generate_invoice_at": "Beginning of the current subscription period",
                "plans": [{"plan": plan_name, "qty": 1}],
            }
        )
        sub.flags.ignore_permissions = True
        sub.insert(ignore_permissions=True)
        sub.submit()

        self.db_set("erpnext_subscription", sub.name, update_modified=False)

        frappe.msgprint(
            _("ERPNext Subscription {0} created for recurring donation").format(
                sub.name
            ),
            alert=True,
        )
        return sub

    def _ensure_subscription_plan(self, campaign):
        """Return the name of the Subscription Plan for this (campaign, frequency,
        amount) combo, creating it lazily if needed.

        Plan naming is deterministic so repeat donors at the same level reuse
        a single Subscription Plan record.
        """
        plan_name = f"{self.campaign}-{self.frequency}-{self.amount:.2f}"
        if frappe.db.exists("Subscription Plan", plan_name):
            return plan_name

        interval_map = {
            "Monthly": ("Month", 1),
            "Quarterly": ("Month", 3),
            "Annual": ("Year", 1),
        }
        interval, count = interval_map.get(self.frequency, (None, None))
        if not interval:
            frappe.throw(
                _("Frequency {0} is not supported for recurring subscriptions.").format(
                    self.frequency
                )
            )

        plan = frappe.get_doc(
            {
                "doctype": "Subscription Plan",
                "plan_name": plan_name,
                "item": campaign.erp_item,
                "currency": self.currency or "USD",
                "price_determination": "Fixed Rate",
                "cost": self.amount,
                "billing_interval": interval,
                "billing_interval_count": count,
                "cost_center": campaign.cost_center,
            }
        )
        plan.insert(ignore_permissions=True)
        return plan.name

    def _set_status(self, status):
        frappe.db.set_value("Donation", self.name, "status", status)
        self.status = status
