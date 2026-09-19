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
        ],
        string="Login method",
        required=True,
        default="password",
    )
    auth_email_link_ttl = fields.Integer(
        string="Verification link validity (minutes)",
        default=10,
    )
    auth_admin_has_valid_email = fields.Boolean(compute="_compute_requirements")
    auth_outbound_email_ready = fields.Boolean(compute="_compute_requirements")
    auth_admin_has_active_oauth = fields.Boolean(compute="_compute_requirements")

    @api.model
    def _system_admin(self):
        return self.env.ref("base.user_admin", raise_if_not_found=False)

    @api.model
    def _admin_has_valid_email(self):
        admin = self._system_admin()
        return bool(
            admin
            and admin.active
            and admin.email
            and email_normalize(admin.email)
        )

    @api.model
    def _outbound_email_ready(self):
        return bool(self.env["ir.mail_server"].sudo().search_count([
            ("active", "=", True),
        ]))

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
        admin_email_ok = self._admin_has_valid_email()
        outbound_email_ok = self._outbound_email_ready()
        oauth_ok = self._admin_has_active_oauth()
        for record in self:
            record.auth_admin_has_valid_email = admin_email_ok
            record.auth_outbound_email_ready = outbound_email_ok
            record.auth_admin_has_active_oauth = oauth_ok

    @api.constrains("auth_email_link_ttl")
    def _check_ttl(self):
        for record in self:
            if record.auth_email_link_ttl and not 1 <= record.auth_email_link_ttl <= 60:
                raise ValidationError(
                    _("Verification link validity must be between 1 and 60 minutes.")
                )

    def _validate_authentication_settings(self):
        for record in self:
            if record.auth_login_method in ("email_link", "both"):
                blockers = []
                if not record._admin_has_valid_email():
                    blockers.append(_("a valid email address on the System Administrator"))
                if not record._outbound_email_ready():
                    blockers.append(_("an active outgoing mail server"))
                if blockers:
                    raise ValidationError(
                        _("Email verification login requires %s.") % _(" and ").join(blockers)
                    )

    def _sync_authentication_parameters(self):
        self.ensure_one()
        params = self.env["ir.config_parameter"].sudo()
        params.set_param("auth_email_link.login_method", self.auth_login_method)
        params.set_param("auth_email_link.ttl_minutes", self.auth_email_link_ttl or 10)

    def write(self, vals):
        result = super().write(vals)
        for record in self:
            record._validate_authentication_settings()
            record._sync_authentication_parameters()
        return result

    def action_save(self):
        self.ensure_one()
        if not self.auth_email_link_ttl:
            self.auth_email_link_ttl = 10
        self._validate_authentication_settings()
        self._sync_authentication_parameters()
        return {"type": "ir.actions.client", "tag": "reload"}
