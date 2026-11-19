# Copyright 2026 Baumgärtner Marketing GmbH
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models, tools


class MailMail(models.Model):
    _inherit = "mail.mail"

    # Same name and relation table as the field of Odoo 20.
    recipient_cc_ids = fields.Many2many(
        "res.partner",
        relation="mail_mail_res_partner_cc_rel",
        string="Cc (Partners)",
        context={"active_test": False},
    )
    recipient_bcc_ids = fields.Many2many(
        "res.partner",
        relation="mail_mail_res_partner_bcc_rel",
        string="Bcc (Partners)",
        context={"active_test": False},
    )
    is_single_email = fields.Boolean(
        "One Email for All Recipients",
        help="The partners of this email get one common email with the To, Cc "
        "and Bcc recipients in its header instead of one email each. In "
        "that case 'To (Partners)' lists every partner, the fields 'Cc "
        "(Partners)' and 'Bcc (Partners)' tell who of them gets a copy.",
    )

    def _personalize_outgoing_body(self, body, partner=False, doc_to_followers=None):
        # one email for everybody: nothing in it may belong to one recipient
        if self.is_single_email:
            partner = False
        return super()._personalize_outgoing_body(
            body, partner=partner, doc_to_followers=doc_to_followers
        )

    def _prepare_outgoing_list(self, mail_server=False, doc_to_followers=None):
        email_list = super()._prepare_outgoing_list(
            mail_server=mail_server, doc_to_followers=doc_to_followers
        )
        if not self.is_single_email or not email_list:
            return email_list
        return [self._mail_send_cc_bcc_merge_outgoing(email_list)]

    def _mail_send_cc_bcc_merge_outgoing(self, email_list):
        """Merge the emails Odoo prepared, one per partner, into one email.

        The To, Cc and Bcc partners become the To, Cc and Bcc header of that
        email. Odoo sends an email to every address of the three headers and
        removes the Bcc header before the email leaves, see
        ``ir.mail_server``. Partners without a valid address are left out, see
        ``_postprocess_sent_message``.
        """
        self.ensure_one()
        cc_partners = self.recipient_cc_ids
        bcc_partners = self.recipient_bcc_ids - cc_partners
        email_to, email_cc, email_bcc, normalized, raw = [], [], [], [], []
        for values in email_list:
            partner = values.get("partner_id")
            valid = values.get("email_to_normalized") or []
            if partner:
                if not valid:
                    continue
                addresses = (values.get("email_to") or []) + (
                    values.get("email_cc") or []
                )
                if partner in bcc_partners:
                    email_bcc += addresses
                elif partner in cc_partners:
                    email_cc += addresses
                else:
                    email_to += addresses
            else:
                # addresses without partner (fields 'To' and 'Cc' of the email)
                email_to += values.get("email_to") or []
                email_cc += values.get("email_cc") or []
            normalized += valid
            if values.get("email_to_raw"):
                raw.append(values["email_to_raw"])
        merged = dict(email_list[0])
        headers = dict(merged.get("headers") or {})
        # Odoo adds the other recipients to the header of each single email
        # with these two; the common email names them itself
        headers.pop("X-Msg-To-Add", None)
        headers.pop("X-Msg-Cc-Add", None)
        if email_bcc:
            headers["Bcc"] = ", ".join(dict.fromkeys(email_bcc))
        merged.update(
            email_to=list(dict.fromkeys(email_to)),
            email_cc=list(dict.fromkeys(email_cc)),
            email_to_normalized=list(dict.fromkeys(normalized)),
            email_to_raw=", ".join(raw),
            headers=headers,
            partner_id=False,
        )
        return merged

    def _postprocess_sent_message(
        self, success_pids, success_emails, failure_reason=False, failure_type=None
    ):
        # A common email that was sent marks the notification of every partner
        # as sent. Partners without a valid address were left out of it: their
        # notification has to tell so.
        left_out = self.env["mail.notification"]
        single_mails = self.filtered("is_single_email")
        if single_mails and not failure_type:
            without_email = single_mails.recipient_ids.filtered(
                lambda partner: not tools.mail.email_normalize_all(partner.email)
            )
            if without_email:
                left_out = (
                    self.env["mail.notification"]
                    .sudo()
                    .search(
                        [
                            ("notification_type", "=", "email"),
                            ("mail_mail_id", "in", single_mails.ids),
                            ("res_partner_id", "in", without_email.ids),
                            ("notification_status", "not in", ("sent", "canceled")),
                        ]
                    )
                )
        res = super()._postprocess_sent_message(
            success_pids,
            success_emails,
            failure_reason=failure_reason,
            failure_type=failure_type,
        )
        left_out = left_out.exists()
        if left_out:
            left_out.write(
                {
                    "notification_status": "exception",
                    "failure_type": "mail_email_missing",
                    "failure_reason": self.env._("Missing email address"),
                }
            )
            messages = left_out.mail_message_id.filtered(
                lambda message: message._is_thread_message()
            )
            messages._notify_message_notification_update()
        return res
