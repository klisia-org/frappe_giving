// proxyOptions is only consumed by `vite dev` so the backend can be reached
// at the bench's webserver_port. In CI / non-bench checkouts the sibling
// `sites/` directory doesn't exist, so we fall back to an empty proxy —
// `vite build` doesn't touch this anyway.
let common_site_config = {};
try {
	common_site_config = require('../../../sites/common_site_config.json');
} catch (e) {
	// Not running inside a bench — no proxy needed.
}
const { webserver_port } = common_site_config;

export default webserver_port
	? {
			'^/(app|api|assets|files|private)': {
				target: `http://127.0.0.1:${webserver_port}`,
				ws: true,
				router: function (req) {
					const site_name = req.headers.host.split(':')[0];
					return `http://${site_name}:${webserver_port}`;
				},
			},
		}
	: {};
