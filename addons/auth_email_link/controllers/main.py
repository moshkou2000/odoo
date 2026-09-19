import logging

import werkzeug.urls

from odoo import http, _
from odoo.exceptions import AccessDenied
from odoo.http import request
from odoo.addons.auth_oauth.controllers.main import OAuthLogin

_logger = logging.getLogger(__name__)


def _configured_mode():
    return request.env["ir.config_parameter"].sudo().get_param(
        "auth_email_link.login_method", "password"
    )


def _admin_has_valid_email():
    settings = request.env["auth.authentication.settings"].sudo()
    return settings._admin_has_valid_email()

def _outbound_email_ready():
    settings = request.env["auth.authentication.settings"].sudo()
    return settings._outbound_email_ready()


def _admin_has_active_oauth():
    settings = request.env["auth.authentication.settings"].sudo()
    return settings._admin_has_active_oauth()


def _effective_mode():
    mode = _configured_mode()
    if mode in ("email_link", "both") and (not _admin_has_valid_email() or not _outbound_email_ready()):
        return "password"
    if mode == "oauth_only" and not _admin_has_active_oauth():
        return "password"
    return mode if mode in ("password", "email_link", "both", "oauth_only") else "password"


class EmailAuthLogin(OAuthLogin):

    @http.route()
    def web_login(self, *args, **kw):
        mode = _effective_mode()

        if request.httprequest.method == "POST":
            # Intercept the dedicated email-link form before Odoo's normal web_login
            # builds a password credential. The clicked submit button is not a safe
            # discriminator in every browser/submission path; email_login is.
            if "email_login" in request.params:
                return self._email_link_request(kw.get("redirect"))

            requested_type = request.params.get("type") or "password"

            if requested_type == "password" and mode not in ("password", "both"):
                # Do not only hide local password auth in the UI: reject crafted POSTs too.
                response = super().web_login(*args, **kw)
                if response.is_qweb:
                    response.qcontext["error"] = _("Password login is disabled by the system administrator.")
                    self._add_auth_context(response, mode)
                return response

        response = super().web_login(*args, **kw)
        if response.is_qweb:
            self._add_auth_context(response, mode)
        return response

    def _add_auth_context(self, response, mode):
        response.qcontext["auth_email_login_mode"] = mode
        response.qcontext["auth_email_admin_ready"] = _outbound_email_ready()
        response.qcontext["auth_oauth_admin_ready"] = _admin_has_active_oauth()


    @http.route("/auth/email-link/user-email", type="jsonrpc", auth="none", methods=["POST"])
    def user_email(self, login=None, **kwargs):
        mode = _effective_mode()
        if mode not in ("email_link", "both") or not login:
            return {"email": ""}
        user = request.env["res.users"].sudo().search(
            [("active", "=", True), ("login", "=", login)],
            limit=1,
        )
        return {"email": user.email or "" if user else ""}

    def _email_link_request(self, redirect=None):
        mode = _effective_mode()
        if mode not in ("email_link", "both") or not _admin_has_valid_email() or not _outbound_email_ready():
            return request.redirect("/web/login", 303)

        email = (request.params.get("email_login") or "").strip()
        if email:
            users = request.env["res.users"].sudo().search(
                [("active", "=", True), ("email", "=ilike", email)],
                limit=2,
            )
            if len(users) == 1 and users.email:
                raw_token = request.env["auth.email.login.token"].sudo().create_for_user(users)
                base_url = request.env["ir.config_parameter"].sudo().get_param("web.base.url")
                query = {"token": raw_token}
                if redirect:
                    query["redirect"] = redirect
                login_url = "%s/auth/email-login?%s" % (
                    base_url.rstrip("/"),
                    werkzeug.urls.url_encode(query),
                )
                template = request.env.ref(
                    "auth_email_link.mail_template_email_login",
                    raise_if_not_found=False,
                )
                if template:
                    admin = request.env.ref("base.user_admin").sudo()
                    mail_id = template.sudo().with_context(login_url=login_url).send_mail(
                        users.id,
                        force_send=True,
                        raise_exception=True,
                        email_values={
                            "email_to": users.email,
                            "email_from": admin.email_formatted,
                        },
                    )
                    _logger.info(
                        "Email login link mail %s sent to user %s via Odoo mail",
                        mail_id,
                        users.id,
                    )
                else:
                    _logger.error("Email login template is missing")

        query = {
            "message": _("If an account exists for that email, a login link has been sent.")
        }
        if redirect:
            query["redirect"] = redirect
        return request.redirect("/web/login?%s" % werkzeug.urls.url_encode(query), 303)


class EmailLoginController(http.Controller):

    @http.route(
        "/auth/email-login",
        type="http",
        auth="none",
        methods=["GET"],
        readonly=False,
    )
    def email_login(self, token=None, redirect=None, **kwargs):
        if not request.db or not token:
            return request.redirect("/web/login", 303)

        try:
            mode = _effective_mode()
            if mode not in ("email_link", "both"):
                raise AccessDenied()

            user = request.env["auth.email.login.token"].sudo().get_user(token)
            if not user:
                raise AccessDenied()

            auth_info = request.session.authenticate(
                request.env,
                {"login": user.login, "token": token, "type": "email_link"},
            )
            # Authentication succeeded; Odoo 19 has no res.users._login_redirect().
            target = redirect or "/odoo"
            return request.redirect(target, 303)
        except AccessDenied:
            _logger.info("Invalid or expired email login token")
            return request.redirect(
                "/web/login?%s" % werkzeug.urls.url_encode({
                    "error": _("This login link is invalid or has expired.")
                }),
                303,
            )
