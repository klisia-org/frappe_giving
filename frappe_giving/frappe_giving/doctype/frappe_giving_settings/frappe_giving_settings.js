// Copyright (c) 2026, Klisia and contributors
// For license information, please see license.txt

frappe.ui.form.on("Frappe Giving Settings", {
	refresh(frm) {
		frm.set_query("account_fee_recovery", () => ({
			filters: {
				root_type: "Income",
				is_group: 0,
			},
		}));
	},
});
