import frappe

no_cache = 1


def get_context():
	context = frappe._dict()
	context.page_title = "Donate"
	return context
