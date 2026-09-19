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

    _sql_constraints = [
        ("token_hash_unique", "unique(token_hash)", "Login token must be unique.")
    ]

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
        record = self.sudo().create({
            "user_id": user.id,
            "token_hash": self._hash(raw),
            "expires_at": now + timedelta(minutes=ttl),
        })
        record.raw_token = raw
        return record

    @staticmethod
    def _hash(token):
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

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
        self.env.cr.execute(
            """
            UPDATE auth_email_login_token
               SET used_at = NOW()
             WHERE token_hash = %s
               AND user_id = %s
               AND used_at IS NULL
               AND expires_at > NOW()
             RETURNING id
            """,
            [self._hash(token), user_id],
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
