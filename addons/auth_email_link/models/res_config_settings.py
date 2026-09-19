from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import email_normalize


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    auth_login_method = fields.Selection(
        [
            ("password", "Password"),
            ("email_link", "Email verification link"),
            ("both", "Both"),
            ("oauth_only", "OAuth only"),
        ],
        string="Login method",
        default="password",
        config_parameter="auth_email_link.login_method",
        required=True,
    )
    auth_email_link_ttl = fields.Integer(
        string="Verification link validity (minutes)",
        default=10,
        config_parameter="auth_email_link.ttl_minutes",
    )
    auth_admin_has_valid_email = fields.Boolean(compute="_compute_auth_requirements")
    auth_admin_has_active_oauth = fields.Boolean(compute="_compute_auth_requirements")

    @api.model
    def _system_admin(self):
        return self.env.ref("base.user_admin", raise_if_not_found=False)

    @api.model
    def _admin_has_valid_email(self):
        admin = self._system_admin()
        return bool(admin and admin.active and admin.email and email_normalize(admin.email))

    @api.model
    def _admin_has_active_oauth(self):
        admin = self._system_admin()
        return bool(
            admin
            and admin.active
            and admin.oauth_provider_id
            and admin.oauth_provider_id.enabled
            and admin.oauth_uid
        )

    @api.depends_context("uid")
    def _compute_auth_requirements(self):
        email_ok = self._admin_has_valid_email()
        oauth_ok = self._admin_has_active_oauth()
        for rec in self:
            rec.auth_admin_has_valid_email = email_ok
            rec.auth_admin_has_active_oauth = oauth_ok

    @api.constrains("auth_email_link_ttl")
    def _check_auth_email_link_ttl(self):
        for rec in self:
            if not 1 <= rec.auth_email_link_ttl <= 60:
                raise ValidationError(
                    _("Verification link validity must be between 1 and 60 minutes.")
                )

    def set_values(self):
        self.ensure_one()
        if self.auth_login_method in ("email_link", "both") and not self._admin_has_valid_email():
            raise ValidationError(
                _("Email verification login requires a valid email on the System Administrator user.")
            )
        if self.auth_login_method == "oauth_only" and not self._admin_has_active_oauth():
            raise ValidationError(
                _("OAuth only requires the System Administrator to be linked to an enabled OAuth provider.")
            )
        return super().set_values()
