from odoo.tests.common import TransactionCase


class TestEmailAuthSettings(TransactionCase):

    def test_password_is_always_available_and_default(self):
        settings = self.env["res.config.settings"].create({})
        self.assertEqual(settings.auth_login_method, "password")
        self.assertIn("password", dict(settings._selection_auth_login_method()))

    def test_oauth_only_requires_admin_link(self):
        settings = self.env["res.config.settings"]
        admin = self.env.ref("base.user_admin")
        admin.write({"oauth_provider_id": False, "oauth_uid": False})
        self.assertNotIn("oauth_only", dict(settings._selection_auth_login_method()))
