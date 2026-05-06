import './index.css';
import '@seminary/portal-shell/style.css';
import { createApp } from "vue";
import App from "./App.vue";

import router from './router';
import call from '@/utils/call';
import { configurePortals } from '@seminary/portal-shell';

configurePortals({
	brand: {
		name: 'Seminary Giving',
		color: '#0D3049',
		logoUrl: '/assets/seminary/images/klisia_icon.png',
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
