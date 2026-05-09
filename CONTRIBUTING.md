# Contributing to Frappe Giving

Thanks for considering a contribution. This guide covers what you need to get a working dev setup, the branching/PR workflow, and the standards we expect on PRs. If anything here is unclear or wrong, please open an issue — the doc itself is fair game for a PR.

## What's in this app

Frappe Giving is a donation-management app for Frappe/ERPNext. The high-level pieces:

- **Doctypes** under [frappe_giving/frappe_giving/doctype/](frappe_giving/frappe_giving/doctype/) — `Donation`, `Donor`, `Donation Campaign`, `Campaign Form`, `Donation Payment`, plus singles like `Frappe Giving Settings`.
- **API** under [frappe_giving/api/](frappe_giving/api/) — whitelisted endpoints for the donor portal, embeddable widget, Stripe webhooks, receipts, and notifications.
- **Frontend** under [frontend/](frontend/) — a Vue 3 SPA that powers `/donate/donorportal` and `/donate/<form>`, plus an embeddable `widget` bundle that hosts can drop onto their own pages.
- **Architecture decisions** under [.docs/adr/](.docs/adr/) — read these first if you're touching anything non-trivial; they explain *why* the code is shaped the way it is.

## Local setup

This app runs inside a Frappe bench. If you don't have one yet, follow the [official bench install guide](https://github.com/frappe/bench).

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/<your-fork>/frappe_giving.git
bench --site <your-dev-site> install-app frappe_giving
```

Frontend dependencies:

```bash
cd apps/frappe_giving/frontend
yarn install
yarn build         # full build (SPA + widget)
yarn dev           # vite dev server during frontend work
```

Pre-commit (Python formatting, lint, secrets, translation stability):

```bash
cd apps/frappe_giving
pre-commit install
```

Once installed, `pre-commit` runs automatically on `git commit`. To run it on the whole tree manually:

```bash
pre-commit run --all-files
```

## Branching and PRs

We use trunk-based development:

1. **Fork** the repo and create a feature branch off `main` in your fork. Name it after the change, e.g. `feat/donor-portal-search` or `fix/stripe-webhook-idempotence`.
2. **Commit** in small, reviewable steps. Conventional commit prefixes (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`) are appreciated but not enforced.
3. **Push** and open a PR against `main`. Link any related issue.
4. **CI / local checks** must pass: `pre-commit run --all-files` and the test suite (see below).
5. A maintainer reviews. Address feedback by pushing follow-up commits — please don't force-push during review.

There is no `develop` branch and no release branches. `main` is always the integration target.

## Tests

Backend tests live alongside each doctype as `test_<doctype>.py`. Run the full app suite from your bench:

```bash
bench --site <your-dev-site> run-tests --app frappe_giving
```

To target a specific module:

```bash
bench --site <your-dev-site> run-tests --app frappe_giving --module frappe_giving.frappe_giving.doctype.donation.test_donation
```

If your change touches Stripe flows, please cover both the happy path and at least one failure path (idempotence, signature mismatch, etc.) — the existing `test_donation.py` and Stripe webhook tests are reasonable templates.

For frontend changes, exercise the affected flow in a real browser session against your dev site (the SPA at `/donate/donorportal`, the form at `/donate/<form_name>`, and an embed-context page for widget changes). We don't have automated UI tests yet; if you'd like to add some, that's a welcome contribution on its own.

## Working on the frontend

Two build targets share the same source:

- **SPA** (`yarn build:app`) — owns the `/donate/donorportal` page and `/donate/<form>` standalone donation pages. Includes Tailwind preflight; safe because it owns the page.
- **Widget** (`yarn build:widget`) — embedded into host pages (Frappe Builder, Web Page, etc.). Built from `frontend/src/widget.css` which deliberately omits Tailwind preflight so it doesn't reset the host's typography. See [ADR 0004](.docs/adr/0004-embed-integration-on-frappe-pages.md) for the why.

`yarn build` builds both. After a frontend change, run the build and `bench build --app frappe_giving` so the served bundle picks it up; hard-refresh the browser (Ctrl+Shift+R / Cmd+Shift+R) to bypass cached assets.

## Translations

User-facing strings should go through `frappe._()` (Python) or i18n primitives (frontend). The repo includes a `stabilize-pot.py` pre-commit hook that prevents spurious POT-file churn. If you add translatable strings, run `bench generate-pot-file --app frappe_giving` before committing so the POT update lands in your PR.

## Architecture decisions (ADRs)

Non-trivial design choices are recorded under [.docs/adr/](.docs/adr/). If your PR introduces a notable architectural change (a new payment integration, a substantially different data flow, a security-sensitive choice), please add an ADR alongside the code change. Use the existing files as a template — the typical sections are Context, Decision, Consequences, Alternatives, and Follow-ons.

Smaller changes don't need an ADR. Use judgment; if in doubt, ask in the PR.

## Reporting issues and asking questions

- **Bugs**: open a GitHub issue with steps to reproduce, expected vs. actual behavior, your Frappe/ERPNext version, and any relevant log excerpts (please scrub secrets).
- **Feature ideas**: open an issue to discuss before opening a large PR. Small, self-contained PRs are fine without prior discussion.
- **Security issues**: please email support@klisia.org rather than filing a public issue.

## Code conventions worth knowing

- **Server vs. client trust boundary** — the server is authoritative on amounts, fees, identifiers, and donor data. Treat anything from the browser (including the embed widget) as untrusted; recompute server-side from saved configuration. See [ADR 0005](.docs/adr/0005-donor-covered-transaction-fees.md) for an example.
- **Idempotence in webhooks** — Stripe webhooks can deliver duplicates. Existing handlers use the `stripe_payment_intent_id` lookup as the idempotence key; new handlers should follow the same pattern.
- **Permission bypasses are scoped** — `frappe.flags.ignore_permissions = True` is acceptable for guest-reachable paths but should be applied around the smallest possible block, not globally. See [ADR 0002](.docs/adr/0002-recurring-donation-subscriptions.md).
- **One change per PR** — refactors, bug fixes, and feature work are easier to review separately. If you find yourself fixing something tangential while working, prefer a follow-up PR.

Thanks for helping make giving better.
