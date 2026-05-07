frappe.ui.form.on("Campaign Form", {
	refresh(frm) {
		if (frm.is_new()) return;

		frm.add_custom_button(__("View on Frontend"), () => {
			const url = `/donate/${encodeURIComponent(frm.doc.name)}`;
			window.open(url, "_blank");
		});

		frm.add_custom_button(__("Copy Embed Snippet"), () => {
			const snippet = build_full_snippet(frm.doc.name);
			copy_to_clipboard(snippet, __("Embed snippet copied to clipboard"));
		});

		frm.add_custom_button(__("Other Embed Instructions"), () => {
			open_alt_embed_dialog(frm.doc.name);
		});
	},
});

function build_full_snippet(form_name) {
	const name = form_name.replace(/"/g, "&quot;");
	return [
		`<div class="fg-donation-form" data-form-name="${name}"></div>`,
		`<link rel="stylesheet" href="/assets/frappe_giving/widget/widget.css">`,
		`<script src="/assets/frappe_giving/widget/widget.js" defer></script>`,
	].join("\n");
}

function build_mount_div(form_name) {
	const name = form_name.replace(/"/g, "&quot;");
	return `<div class="fg-donation-form" data-form-name="${name}"></div>`;
}

const PAGE_LOADER_JS = `(function () {
  if (document.querySelector('script[src$="widget/widget.js"]')) return;
  var l = document.createElement('link');
  l.rel = 'stylesheet';
  l.href = '/assets/frappe_giving/widget/widget.css';
  document.head.appendChild(l);
  var s = document.createElement('script');
  s.src = '/assets/frappe_giving/widget/widget.js';
  s.defer = true;
  document.body.appendChild(s);
})();`;

function open_alt_embed_dialog(form_name) {
	const mount_div = build_mount_div(form_name);

	const dialog = new frappe.ui.Dialog({
		title: __("Embed in a Markdown / sanitized block"),
		size: "large",
	});

	const $body = $(`
		<div class="fg-embed-instructions">
			<p>${__(
				"Use this two-part approach when the host page's editor strips <code>&lt;script&gt;</code> and <code>&lt;link&gt;</code> tags — for example, the <b>Section with Embed</b> Web Template (Markdown), or any Markdown content area."
			)}</p>

			<h5>${__("1. Paste into the embed block")}</h5>
			<p class="text-muted small">${__(
				"This goes inside the Markdown / Embed block where you want the form to appear."
			)}</p>
			<pre class="fg-embed-code" data-fg-target="div"></pre>
			<button type="button" class="btn btn-secondary btn-sm" data-fg-copy="div">
				${__("Copy mount div")}
			</button>

			<hr class="my-4"/>

			<h5>${__("2. Paste into the page's Javascript field")}</h5>
			<p class="text-muted small">${__(
				"On the Web Page record (<code>/app/web-page/&lt;your-page&gt;</code>), tick <b>Insert Code</b>, then paste this into the <b>Javascript</b> field. The script loads the widget bundle on demand and is idempotent — duplicates are safely ignored."
			)}</p>
			<pre class="fg-embed-code" data-fg-target="loader"></pre>
			<button type="button" class="btn btn-secondary btn-sm" data-fg-copy="loader">
				${__("Copy loader script")}
			</button>
		</div>
	`);

	$body.find('[data-fg-target="div"]').text(mount_div);
	$body.find('[data-fg-target="loader"]').text(PAGE_LOADER_JS);

	$body.on("click", "[data-fg-copy]", (e) => {
		const which = $(e.currentTarget).attr("data-fg-copy");
		const text = which === "div" ? mount_div : PAGE_LOADER_JS;
		const label =
			which === "div"
				? __("Mount div copied to clipboard")
				: __("Loader script copied to clipboard");
		copy_to_clipboard(text, label);
	});

	dialog.$body.append($body);
	dialog.show();
}

function copy_to_clipboard(text, success_message) {
	const fallback = () => {
		const ta = document.createElement("textarea");
		ta.value = text;
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
		frappe.show_alert({ message: success_message, indicator: "green" });

	if (navigator.clipboard?.writeText) {
		navigator.clipboard.writeText(text).then(done, () => {
			fallback();
			done();
		});
	} else {
		fallback();
		done();
	}
}
