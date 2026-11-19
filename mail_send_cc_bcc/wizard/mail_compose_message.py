# Copyright 2026 Baumgärtner Marketing GmbH
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

    partner_bcc_ids = fields.Many2many(
        "res.partner",
        "mail_compose_message_res_partner_bcc_rel",
        "wizard_id",
        "partner_id",
        string="Additional Bcc contacts",
    )

    def _prepare_mail_values(self, res_ids):
        mail_values_all = super()._prepare_mail_values(res_ids)
        bcc_ids = self.partner_bcc_ids.ids
        if self.composition_mode != "comment" or not bcc_ids:
            return mail_values_all
        for mail_values in mail_values_all.values():
            mail_values["partner_bcc_ids"] = list(bcc_ids)
        return mail_values_all
