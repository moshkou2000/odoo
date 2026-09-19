import hashlib
import secrets
from datetime import timedelta

from odoo import api, fields, models


class EmailLoginToken(models.Model):
    _name = "auth.email.login.token"
    _description = "Email Login Token"
    _order = "id desc"

    user_id = fields.Many2one("res.users", required=True, ondelete="cascade", index=True)
    token_hash = fields.Char(required=True, index=True, copy=False)
    expires_at = fields.Datetime(required=True, index=True)
    used_at = fields.Datetime(index=True, copy=False)

    _token_hash_unique = models.Constraint(
        "UNIQUE(token_hash)",
        "Login token must be unique.",
    )

    @api.model
    def create_for_user(self, user):
        now = fields.Datetime.now()
        ttl = int(self.env["ir.config_parameter"].sudo().get_param(
            "auth_email_link.ttl_minutes", 10
        ))
        ttl = max(1, min(ttl, 60))

        self.sudo().search([
            ("user_id", "=", user.id),
            ("used_at", "=", False),
        ]).write({"used_at": now})

        raw = secrets.token_urlsafe(48)
        self.sudo().create({
            "user_id": user.id,
            "token_hash": self._hash(raw),
            "expires_at": now + timedelta(minutes=ttl),
        })
        # Return the raw token only to the caller. It is never stored on the ORM
        # record or in the database; only its SHA-256 hash is persisted.
        return raw

    @staticmethod
    def _hash(token):
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @api.model
    def get_user(self, token):
        if not token:
            return self.env["res.users"]
        record = self.sudo().search([
            ("token_hash", "=", self._hash(token)),
            ("used_at", "=", False),
            ("expires_at", ">", fields.Datetime.now()),
            ("user_id.active", "=", True),
        ], limit=1)
        return record.user_id if record else self.env["res.users"]

    @api.model
    def get_login(self, token):
        record = self.sudo().search([
            ("token_hash", "=", self._hash(token)),
            ("used_at", "=", False),
            ("expires_at", ">", fields.Datetime.now()),
            ("user_id.active", "=", True),
        ], limit=1)
        return record.user_id.login if record else False

    @api.model
    def consume_for_user(self, token, user_id):
        if not token or not user_id:
            return False

        token_hash = self._hash(token)
        now = fields.Datetime.now()

        # Resolve the token with ORM first so Odoo handles datetime conversion and
        # record rules consistently. The SQL UPDATE remains the atomic single-use gate.
        record = self.sudo().search([
            ("token_hash", "=", token_hash),
            ("user_id", "=", user_id),
            ("used_at", "=", False),
            ("expires_at", ">", now),
            ("user_id.active", "=", True),
        ], limit=1)
        if not record:
            return False

        self.env.cr.execute(
            """
            UPDATE auth_email_login_token
               SET used_at = %s
             WHERE id = %s
               AND used_at IS NULL
             RETURNING id
            """,
            [now, record.id],
        )
        return bool(self.env.cr.fetchone())

    @api.autovacuum
    def _gc_expired_tokens(self):
        self.env.cr.execute(
            """
            DELETE FROM auth_email_login_token
             WHERE expires_at < NOW() OR used_at IS NOT NULL
            """
        )
