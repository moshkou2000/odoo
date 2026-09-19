/** @odoo-module **/

import { registry } from "@web/core/registry";
import { RadioField, radioField } from "@web/views/fields/radio/radio_field";

export class AuthLoginMethodRadio extends RadioField {
    static template = "auth_email_link.AuthLoginMethodRadio";

    get widgetOptions() {
        return this.props.options || this.props.fieldInfo?.options || {};
    }

    get emailReady() {
        const fieldName = this.widgetOptions.email_ready_field || "auth_admin_has_valid_email";
        return Boolean(this.props.record?.data?.[fieldName]);
    }

    get oauthReady() {
        const fieldName = this.widgetOptions.oauth_ready_field || "auth_admin_has_active_oauth";
        return Boolean(this.props.record?.data?.[fieldName]);
    }

    isOptionDisabled(value) {
        if (value === "email_link" || value === "both") {
            return !this.emailReady;
        }
        if (value === "oauth_only") {
            return !this.oauthReady;
        }
        return false;
    }

    description(value) {
        return {
            password: "Keeps Odoo's standard username/login and password form unchanged.",
            email_link: "Users enter their email and receive a short-lived, single-use sign-in link.",
            both: "Users can choose standard password login or an email verification link.",
            oauth_only: "Disables local password and email-link login; users must use an enabled OAuth provider.",
        }[value] || "";
    }

    blocker(value) {
        if ((value === "email_link" || value === "both") && !this.emailReady) {
            return "Not available: The System Administrator does not have a valid email address.";
        }
        if (value === "oauth_only" && !this.oauthReady) {
            return "Not available: The System Administrator is not linked to an enabled OAuth provider.";
        }
        return "";
    }
}

export const authLoginMethodRadio = {
    ...radioField,
    component: AuthLoginMethodRadio,
};

registry.category("fields").add("auth_login_method_radio", authLoginMethodRadio);
