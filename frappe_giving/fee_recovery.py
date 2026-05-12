from decimal import ROUND_HALF_UP, Decimal

import frappe


def compute_fee_recovery(amount, percentage, fixed) -> Decimal:
	"""Gross-up surcharge so the charity nets `amount` after the processor fee.

	fee = (amount * pct + fixed) / (1 - pct)
	"""
	a = Decimal(str(amount or 0))
	p = Decimal(str(percentage or 0)) / Decimal(100)
	f = Decimal(str(fixed or 0))
	if a <= 0 or p >= 1 or p < 0:
		return Decimal(0)
	raw = (a * p + f) / (Decimal(1) - p)
	return raw.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def get_fee_recovery_for_donation(amount) -> Decimal:
	"""Read the global fee formula from Frappe Giving Settings and compute."""
	settings = frappe.get_cached_doc("Frappe Giving Settings")
	return compute_fee_recovery(amount, settings.fee_percentage, settings.fee_fixed)
