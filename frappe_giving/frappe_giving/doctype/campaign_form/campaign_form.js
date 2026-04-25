frappe.ui.form.on("Campaign Form", {
	refresh(frm) {
		if (frm.is_new()) return;

		frm.add_custom_button(__("View on Frontend"), () => {
			const url = `/donate/${encodeURIComponent(frm.doc.name)}`;
			window.open(url, "_blank");
		});

		frm.add_custom_button(__("Copy Embed Snippet"), () => {
			const name = frm.doc.name.replace(/"/g, "&quot;");
			const snippet = [
				`<div class="fg-donation-form" data-form-name="${name}"></div>`,
				`<link rel="stylesheet" href="/assets/frappe_giving/widget/widget.css">`,
				`<script src="/assets/frappe_giving/widget/widget.js" defer></script>`,
			].join("\n");

			const fallbackCopy = () => {
				const ta = document.createElement("textarea");
				ta.value = snippet;
				ta.style.position = "fixed";
				ta.style.opacity = "0";
				document.body.appendChild(ta);
				ta.select();
				try {
					document.execCommand("copy");
				} finally {
					document.body.removeChild(ta);
				}
			};

			const done = () =>
				frappe.show_alert({
					message: __("Embed snippet copied to clipboard"),
					indicator: "green",
				});

			if (navigator.clipboard?.writeText) {
				navigator.clipboard.writeText(snippet).then(done, fallbackCopy);
			} else {
				fallbackCopy();
				done();
			}
		});
	},
});
