{
    "name": "Email Link Authentication",
    "version": "19.0.1.43.0",
    "category": "Authentication",
    "summary": "Configurable password, email-link and OAuth-only authentication",
    "license": "LGPL-3",
    "author": "Custom Development",
    "depends": ["web", "mail", "base_setup", "auth_oauth"],
    "data": [
        "security/ir.model.access.csv",
        "data/mail_template.xml",
        "data/authentication_settings.xml",
        "views/res_config_settings_views.xml",
        "views/web_login_templates.xml"
    ],
    "assets": {
        "web.assets_frontend_minimal": [
            "auth_email_link/static/src/js/user_switch_email_link.js",
        ],
        "web.assets_backend": [
            "auth_email_link/static/src/js/auth_login_method_radio.js",
            "auth_email_link/static/src/xml/auth_login_method_radio.xml"
        ],
    },
    "installable": True,
    "application": False
}
