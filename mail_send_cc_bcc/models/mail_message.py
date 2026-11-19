# Copyright 2026 Baumgärtner Marketing GmbH
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class MailMessage(models.Model):
    _inherit = "mail.message"

    # Same name and relation table as the field of Odoo 20: after an upgrade
    # the field of Odoo takes over the recipients stored here.
    partner_cc_ids = fields.Many2many(
        "res.partner",
        relation="mail_message_res_partner_cc_rel",
        string="Recipients (Cc)",
        context={"active_test": False},
    )
    # Blind copies are shown to internal users only: portal users may read the
    # messages of their documents, they must not learn who got a blind copy.
    partner_bcc_ids = fields.Many2many(
        "res.partner",
        relation="mail_message_res_partner_bcc_rel",
        string="Recipients (Bcc)",
        context={"active_test": False},
        groups="base.group_user",
    )
