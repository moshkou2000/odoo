from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import email_normalize


class AuthAuthenticationSettings(models.Model):
    _name = "auth.authentication.settings"
    _description = "Authentication Settings"
    _rec_name = "name"

    name = fields.Char(default="Authentication", required=True)

    @api.depends("name")
    def _compute_display_name(self):
        for record in self:
            record.display_name = record.name or _("Authentication")

    auth_login_method = fields.Selection(
        [
            ("password", "Password"),
            ("email_link", "Email verification link"),
            ("both", "Both"),
            ("oauth_only", "OAuth only"),
        ],
        string="Login method",
        required=True,
        default="password",
    )
    auth_email_link_ttl = fields.Integer(
        string="Verification link validity (minutes)",
        required=True,
        default=10,
    )
    auth_admin_has_valid_email = fields.Boolean(compute="_compute_requirements")
    auth_admin_has_active_oauth = fields.Boolean(compute="_compute_requirements")

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
    def _compute_requirements(self):
        email_ok = self._admin_has_valid_email()
        oauth_ok = self._admin_has_active_oauth()
        for record in self:
            record.auth_admin_has_valid_email = email_ok
            record.auth_admin_has_active_oauth = oauth_ok

    @api.constrains("auth_email_link_ttl")
    def _check_ttl(self):
        for record in self:
            if not 1 <= record.auth_email_link_ttl <= 60:
                raise ValidationError(
                    _("Verification link validity must be between 1 and 60 minutes.")
                )

    def action_save(self):
        self.ensure_one()
        if self.auth_login_method in ("email_link", "both") and not self._admin_has_valid_email():
            raise ValidationError(
                _("Email verification login requires a valid email on the System Administrator user.")
            )
        if self.auth_login_method == "oauth_only" and not self._admin_has_active_oauth():
            raise ValidationError(
                _("OAuth only requires the System Administrator to be linked to an enabled OAuth provider.")
            )
        params = self.env["ir.config_parameter"].sudo()
        params.set_param("auth_email_link.login_method", self.auth_login_method)
        params.set_param("auth_email_link.ttl_minutes", self.auth_email_link_ttl)
        return {"type": "ir.actions.client", "tag": "reload"}
