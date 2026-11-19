# Copyright 2026 Baumgärtner Marketing GmbH
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from unittest.mock import patch

from odoo.tests import Form, tagged

from odoo.addons.account.models.account_move_send import (
    AccountMoveSend as AccountMoveSendOdoo,
)
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.mail.tests.common import MailCommon


@tagged("post_install", "-at_install")
class TestInvoiceSend(AccountTestInvoicingCommon, MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Partner = cls.env["res.partner"]
        cls.customer = Partner.create(
            {
                "name": "Musterfirma Beispiel GmbH",
                "email": "rechnung@musterfirma.example.com",
                "invoice_sending_method": "email",
            }
        )
        cls.copy = Partner.create(
            {"name": "Clara Kopie", "email": "clara.kopie@example.com"}
        )
        cls.blind = Partner.create(
            {"name": "Dora Verdeckt", "email": "dora.verdeckt@example.com"}
        )
        cls.invoice = cls.init_invoice(
            "out_invoice", partner=cls.customer, amounts=[100.0], post=True
        )
        cls.all_addresses = [
            "clara.kopie@example.com",
            "dora.verdeckt@example.com",
            "rechnung@musterfirma.example.com",
        ]

    def _wizard_form(self):
        return Form(
            self.env["account.move.send.wizard"].with_context(
                active_model="account.move", active_ids=self.invoice.ids
            )
        )

    def _sent_message(self):
        return self.invoice.message_ids.filtered(
            lambda message: message.message_type == "comment"
        )[:1].sudo()

    def _assert_one_email_to_all(self):
        self.assertEqual(len(self.emails), 1)
        email = self.emails[0]
        self.assertEqual(sorted(email["smtp_to_list"]), self.all_addresses)
        self.assertIn("rechnung@musterfirma.example.com", email["msg_to"])
        self.assertNotIn("clara.kopie", email["msg_to"])
        self.assertIn("clara.kopie@example.com", email["msg_cc"])
        self.assertNotIn("dora.verdeckt", email["message"])

    def test_wizard_sends_one_email(self):
        form = self._wizard_form()
        self.assertEqual(form.mail_partner_ids[:], self.customer)
        form.mail_partner_cc_ids.add(self.copy)
        form.mail_partner_bcc_ids.add(self.blind)
        wizard = form.save()
        with self.mock_mail_gateway():
            wizard.action_send_and_print()

        message = self._sent_message()
        self.assertEqual(message.partner_ids, self.customer)
        self.assertEqual(message.partner_cc_ids, self.copy)
        self.assertEqual(message.partner_bcc_ids, self.blind)
        self._assert_one_email_to_all()
        # the invoice is attached to the one email
        self.assertIn(".pdf", self.emails[0]["message"])
        self.assertTrue(self.invoice.is_move_sent)

    def test_wizard_without_copies_is_unchanged(self):
        wizard = self._wizard_form().save()
        with self.mock_mail_gateway():
            wizard.action_send_and_print()
        message = self._sent_message()
        self.assertEqual(message.partner_ids, self.customer)
        self.assertFalse(message.partner_cc_ids)
        self.assertFalse(message.partner_bcc_ids)
        self.assertEqual(len(self.emails), 1)
        self.assertEqual(
            self.emails[0]["smtp_to_list"], ["rechnung@musterfirma.example.com"]
        )
        self.assertFalse(self._new_mails.is_single_email)

    def test_wizard_without_email_passes_no_copies(self):
        form = self._wizard_form()
        form.mail_partner_cc_ids.add(self.copy)
        wizard = form.save()
        wizard.sending_methods = []
        self.assertNotIn("mail_partner_cc_ids", wizard._get_sending_settings())

    def test_settings_of_the_sending(self):
        """Copies given to the sending itself, as other modules may do."""
        with self.mock_mail_gateway():
            self.env["account.move.send"]._generate_and_send_invoices(
                self.invoice,
                sending_methods=["email"],
                mail_partner_cc_ids=self.copy.ids,
                mail_partner_bcc_ids=self.blind.ids,
            )
        self._assert_one_email_to_all()

    def test_sending_in_the_background(self):
        """The scheduled action reads the settings stored on the invoice."""
        self.invoice.sending_data = {
            "author_user_id": self.env.user.id,
            "author_partner_id": self.env.user.partner_id.id,
            "sending_methods": ["email"],
            "mail_partner_cc_ids": self.copy.ids,
            "mail_partner_bcc_ids": self.blind.ids,
        }
        with self.mock_mail_gateway():
            self.env["account.move.send"]._generate_and_send_invoices(
                self.invoice, from_cron=True
            )
        self._assert_one_email_to_all()

    def test_default_settings_have_no_copies(self):
        settings = self.env["account.move.send"]._get_default_sending_settings(
            self.invoice
        )
        self.assertEqual(settings["mail_partner_cc_ids"], [])
        self.assertEqual(settings["mail_partner_bcc_ids"], [])

    def test_sending_without_email_has_no_copies(self):
        settings = self.env["account.move.send"]._get_default_sending_settings(
            self.invoice, sending_methods=[], mail_partner_cc_ids=self.copy.ids
        )
        self.assertNotIn("mail_partner_cc_ids", settings)
        self.assertNotIn("mail_partner_bcc_ids", settings)

    def test_no_email_to_send(self):
        """Odoo or another module may decide that there is no email."""
        with patch.object(
            AccountMoveSendOdoo, "_get_mail_params", autospec=True, return_value={}
        ):
            params = self.env["account.move.send"]._get_mail_params(
                self.invoice, {"mail_partner_cc_ids": self.copy.ids}
            )
        self.assertEqual(params, {})
