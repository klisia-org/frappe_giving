frappe.provide("frappe.dashboards.chart_sources");

frappe.dashboards.chart_sources["Donor Base by Donation Type"] = {
	method: "frappe_giving.frappe_giving.dashboard_chart_source.donor_base_by_donation_type.donor_base_by_donation_type.get",
	filters: [],
};
