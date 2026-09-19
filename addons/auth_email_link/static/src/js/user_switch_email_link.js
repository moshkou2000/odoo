/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { UserSwitch } from "@web/core/user_switch/user_switch";
import { rpc } from "@web/core/network/rpc";

patch(UserSwitch.prototype, {
    async fillForm(login = "") {
        const loginInput = this.form?.querySelector("input#login");
        const passwordInput = this.form?.querySelector("input#password");
        const emailInput = this.form?.querySelector("input#email_login");

        if (loginInput) {
            loginInput.value = login;
        }
        if (passwordInput) {
            passwordInput.value = "";
        }
        if (emailInput) {
            emailInput.value = "";
            if (login) {
                const result = await rpc("/auth/email-link/user-email", { login });
                emailInput.value = result?.email || "";
            }
        }

        this.toggleFormDisplay();
    },
});
