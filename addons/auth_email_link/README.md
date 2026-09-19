# Email Link Authentication — Odoo 19 Community

Adds a system-admin managed Authentication page under:

**Settings → Users & Companies → Authentication**

The menu is positioned immediately before Odoo's **OAuth Providers** menu.

## Login methods

- **Password** — default. Odoo's original username/login + password UI and behavior are preserved.
- **Email verification link** — passwordless email link only.
- **Both** — standard password login plus passwordless email link.
- **OAuth only** — no local authentication; enabled OAuth providers remain available.

## Safety gates

Email verification options are hidden unless `base.user_admin` is active and has a valid email address.

OAuth only is hidden unless `base.user_admin` is already linked to an OAuth provider, has an OAuth UID, and that provider is currently Allowed/enabled.

If an already-selected method later becomes unsafe because the admin email/provider is removed, the effective login page falls back to Password so the database is not locked out.

## Email-link security

- random URL-safe token
- SHA-256 token hash stored in Odoo
- configurable 1–60 minute lifetime
- atomic single-use consumption
- new token invalidates older outstanding tokens for that user
- generic request response to reduce account enumeration
- direct crafted `/web/login` email-token requests cannot bypass token validation

Configure an outgoing mail server before testing email delivery.
