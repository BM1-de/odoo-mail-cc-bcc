# Copyright 2026 Baumgärtner Marketing GmbH
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, models

CC_BCC_SETTINGS = {
    # setting of the invoice sending: parameter of message_post
    "mail_partner_cc_ids": "partner_cc_ids",
    "mail_partner_bcc_ids": "partner_bcc_ids",
}


class AccountMoveSend(models.AbstractModel):
    _inherit = "account.move.send"

    @api.model
    def _get_default_sending_settings(self, move, from_cron=False, **custom_settings):
        vals = super()._get_default_sending_settings(
            move, from_cron=from_cron, **custom_settings
        )
        if "email" in vals["sending_methods"]:
            for key in CC_BCC_SETTINGS:
                if key in custom_settings:
                    value = custom_settings[key]
                elif from_cron:
                    value = (move.sending_data or {}).get(key)
                else:
                    value = None
                vals[key] = list(value or [])
        return vals

    @api.model
    def _get_mail_params(self, move, move_data):
        params = super()._get_mail_params(move, move_data)
        if params:
            for key, parameter in CC_BCC_SETTINGS.items():
                if move_data.get(key):
                    params[parameter] = list(move_data[key])
        return params
