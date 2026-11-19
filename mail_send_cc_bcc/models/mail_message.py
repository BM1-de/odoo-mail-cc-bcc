# Copyright 2026 Baumgärtner Marketing GmbH
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class MailMessage(models.Model):
    _inherit = "mail.message"

    # Blind copies are shown to internal users only: portal users may read the
    # messages of their documents, they must not learn who got a blind copy.
    partner_bcc_ids = fields.Many2many(
        "res.partner",
        relation="mail_message_res_partner_bcc_rel",
        string="Recipients (Bcc)",
        context={"active_test": False},
        groups="base.group_user",
    )
