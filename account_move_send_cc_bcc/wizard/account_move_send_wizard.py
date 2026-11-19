# Copyright 2026 Baumgärtner Marketing GmbH
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class AccountMoveSendWizard(models.TransientModel):
    _inherit = "account.move.send.wizard"

    mail_partner_cc_ids = fields.Many2many(
        "res.partner",
        "account_move_send_wizard_res_partner_cc_rel",
        "wizard_id",
        "partner_id",
        string="Cc",
    )
    mail_partner_bcc_ids = fields.Many2many(
        "res.partner",
        "account_move_send_wizard_res_partner_bcc_rel",
        "wizard_id",
        "partner_id",
        string="Bcc",
    )

    def _get_sending_settings(self):
        send_settings = super()._get_sending_settings()
        if "mail_partner_ids" in send_settings:
            send_settings["mail_partner_cc_ids"] = self.mail_partner_cc_ids.ids
            send_settings["mail_partner_bcc_ids"] = self.mail_partner_bcc_ids.ids
        return send_settings
