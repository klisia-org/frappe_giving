// Embeddable Campaign Form widget.
//
// Usage on any Frappe-hosted page (typically a Builder Embed block):
//
//   <div class="fg-donation-form" data-form-name="MyCampaignForm"></div>
//   <link rel="stylesheet" href="/assets/frappe_giving/widget/widget.css">
//   <script src="/assets/frappe_giving/widget/widget.js" defer></script>
//
// The script scans the host page for every `.fg-donation-form` element
// with a non-empty `data-form-name` and mounts an independent Vue
// instance on each. Safe to include the <script>/<link> multiple times
// per page — both are idempotent.

// Widget-specific CSS: same as index.css without Tailwind preflight, so
// the bundle doesn't reset the host page's typography. See widget.css.
import './widget.css';
import { createApp } from 'vue';
import CampaignForm from './views/CampaignForm.vue';

const MOUNT_SELECTOR = '.fg-donation-form';
const MOUNTED_FLAG = 'fgMounted';

// Inline minimal Frappe-method caller. We deliberately do NOT import
// doppio's `call` controller because it transitively imports the SPA's
// router, and `createWebHistory("/donate")` runs at module load — that
// rewrites window.history and prepends `/donate` to the host page's URL.
// Embedded widgets must not touch the host page's history.
async function call(method, args) {
	const headers = {
		Accept: 'application/json',
		'Content-Type': 'application/json; charset=utf-8',
		'X-Frappe-Site-Name': window.location.hostname,
	};
	if (window.csrf_token && window.csrf_token !== '{{ csrf_token }}') {
		headers['X-Frappe-CSRF-Token'] = window.csrf_token;
	}

	const res = await fetch(`/api/method/${method}`, {
		method: 'POST',
		headers,
		body: JSON.stringify(args || {}),
	});

	if (res.ok) {
		const data = await res.json();
		return data.message ?? data;
	}

	let body = await res.text();
	let parsed = null;
	try {
		parsed = JSON.parse(body);
	} catch (_) {}

	let message = parsed?._error_message;
	if (!message && parsed?._server_messages) {
		try {
			const messages = JSON.parse(parsed._server_messages).map((m) => {
				try { return JSON.parse(m).message; } catch (_) { return m; }
			});
			message = messages.filter(Boolean).join('\n');
		} catch (_) {}
	}
	const err = new Error(message || `Request failed (${res.status})`);
	err.exc_type = parsed?.exc_type;
	throw err;
}

function mount(el) {
	if (el.dataset[MOUNTED_FLAG]) return;
	const formName = el.dataset.formName;
	if (!formName) {
		console.warn('[frappe-giving] missing data-form-name on', el);
		return;
	}
	el.dataset[MOUNTED_FLAG] = '1';

	const app = createApp(CampaignForm, { formName });
	app.provide('$call', call);
	app.mount(el);
}

function scan(root = document) {
	root.querySelectorAll(MOUNT_SELECTOR).forEach(mount);
}

if (document.readyState === 'loading') {
	document.addEventListener('DOMContentLoaded', () => scan());
} else {
	scan();
}

// Builder's in-editor preview and SPA-navigated hosts may inject new
// mount points after the initial load. Observe and re-scan.
const observer = new MutationObserver(() => scan());
observer.observe(document.body || document.documentElement, {
	childList: true,
	subtree: true,
});

window.FrappeGiving = { mount, scan };
