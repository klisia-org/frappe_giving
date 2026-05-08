import './index.css';
import '@seminary/portal-shell/style.css';
import { createApp } from "vue";
import App from "./App.vue";

import router from './router';
import call from '@/utils/call';
import { configurePortals } from '@seminary/portal-shell';

const FALLBACK_LOGO = '/assets/seminary/images/klisia_icon.png';

async function resolveGivingLogo() {
	try {
		const res = await fetch('/api/method/frappe_giving.api.donate.get_branding', {
			headers: { Accept: 'application/json' },
		});
		if (!res.ok) return FALLBACK_LOGO;
		const data = await res.json();
		return data?.message?.giving_logo || FALLBACK_LOGO;
	} catch (e) {
		return FALLBACK_LOGO;
	}
}

resolveGivingLogo().then((logoUrl) => {
	configurePortals({
		brand: {
			name: 'Seminary Giving',
			color: '#0D3049',
			logoUrl,
		},
		portals: [
			{ id: 'student', label: 'Courses', url: '/seminary', roles: ['Student', 'Academics User', 'Instructor'] },
			{ id: 'alumni', label: 'Alumni', url: '/seminary/alumni', roles: ['Alumni'] },
			{ id: 'donor', label: 'Donate', url: '/donate/donorportal' },
		],
	});

	const app = createApp(App);
	app.use(router);
	app.provide("$call", call);
	app.mount("#app");
});
