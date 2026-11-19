# Copyright 2026 Baumgärtner Marketing GmbH
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import models


class MailScheduledMessage(models.Model):
    _inherit = "mail.scheduled.message"

    def _notification_parameters_whitelist(self):
        # A message scheduled in the composer keeps its Cc and Bcc recipients in
        # these parameters; without them here it would be sent without copies.
        return super()._notification_parameters_whitelist() | {
            "partner_cc_ids",
            "partner_bcc_ids",
        }
