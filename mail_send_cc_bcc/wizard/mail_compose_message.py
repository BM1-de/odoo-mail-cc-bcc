# Copyright 2026 Baumgärtner Marketing GmbH
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

    # Same name and relation table as the field of Odoo 20.
    partner_cc_ids = fields.Many2many(
        "res.partner",
        "mail_compose_message_res_partner_cc_rel",
        "wizard_id",
        "partner_id",
        string="Additional Cc contacts",
        compute="_compute_partner_cc_ids",
        readonly=False,
        store=True,
    )
    partner_bcc_ids = fields.Many2many(
        "res.partner",
        "mail_compose_message_res_partner_bcc_rel",
        "wizard_id",
        "partner_id",
        string="Additional Bcc contacts",
    )

    @api.depends("composition_mode", "parent_id")
    def _compute_partner_cc_ids(self):
        """A reply goes to the Cc recipients of the message it answers, like
        it goes to its To recipients. Blind copies are not taken over."""
        for composer in self:
            if composer.composition_mode == "comment" and composer.parent_id:
                composer.partner_cc_ids = composer.parent_id.partner_cc_ids
            else:
                composer.partner_cc_ids = composer.partner_cc_ids

    def _prepare_mail_values(self, res_ids):
        mail_values_all = super()._prepare_mail_values(res_ids)
        if self.composition_mode != "comment":
            return mail_values_all
        cc_ids, bcc_ids = self.partner_cc_ids.ids, self.partner_bcc_ids.ids
        for mail_values in mail_values_all.values():
            if cc_ids:
                mail_values["partner_cc_ids"] = list(cc_ids)
            if bcc_ids:
                mail_values["partner_bcc_ids"] = list(bcc_ids)
        return mail_values_all
