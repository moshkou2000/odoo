from odoo import models
from odoo.exceptions import AccessDenied


class ResUsers(models.Model):
    _inherit = "res.users"

    def _check_credentials(self, credential, env):
        if credential.get("type") == "email_link":
            mode = self.env["ir.config_parameter"].sudo().get_param(
                "auth_email_link.login_method", "password"
            )
            if mode not in ("email_link", "both"):
                raise AccessDenied()

            self.ensure_one()
            token = credential.get("token")
            if not token or not self.env["auth.email.login.token"].sudo().consume_for_user(
                token, self.id
            ):
                raise AccessDenied()

            return {
                "uid": self.id,
                "auth_method": "email_link",
                "mfa": "default",
            }

        return super()._check_credentials(credential, env)
