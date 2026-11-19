# Copyright 2026 Baumgärtner Marketing GmbH
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests import Form, tagged

from odoo.addons.mail.tests.common import MailCommon


@tagged("post_install", "-at_install")
class TestComposer(MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Partner = cls.env["res.partner"]
        cls.document = Partner.create({"name": "Musterfirma Beispiel GmbH"})
        cls.customer = Partner.create(
            {"name": "Anna Beispiel", "email": "anna.beispiel@example.com"}
        )
        cls.copy = Partner.create(
            {"name": "Clara Kopie", "email": "clara.kopie@example.com"}
        )
        cls.blind = Partner.create(
            {"name": "Dora Verdeckt", "email": "dora.verdeckt@example.com"}
        )

    def _composer_form(self, **context):
        return Form(
            self.env["mail.compose.message"]
            .with_user(self.user_employee)
            .with_context(
                default_model=self.document._name,
                default_res_ids=self.document.ids,
                default_composition_mode="comment",
                **context,
            )
        )

    def test_send_with_cc_and_bcc(self):
        form = self._composer_form()
        form.partner_ids.add(self.customer)
        # the button "Cc" of Odoo shows the lines Cc and Bcc
        form.partner_cc_allowed = True
        form.partner_cc_ids.add(self.copy)
        form.partner_bcc_ids.add(self.blind)
        form.subject = "Angebot"
        form.body = "<p>Guten Tag</p>"
        composer = form.save()
        with self.mock_mail_gateway():
            composer._action_send_mail()

        message = self.document.message_ids[0].sudo()
        self.assertEqual(message.partner_ids, self.customer)
        self.assertEqual(message.partner_cc_ids, self.copy)
        self.assertEqual(message.partner_bcc_ids, self.blind)
        self.assertEqual(len(self.emails), 1)
        email = self.emails[0]
        self.assertEqual(
            sorted(email["smtp_to_list"]),
            [
                "anna.beispiel@example.com",
                "clara.kopie@example.com",
                "dora.verdeckt@example.com",
            ],
        )
        self.assertIn("anna.beispiel@example.com", email["msg_to"])
        self.assertIn("clara.kopie@example.com", email["msg_cc"])
        self.assertNotIn("dora.verdeckt", email["message"])

    def test_send_without_copies_is_unchanged(self):
        form = self._composer_form()
        form.partner_ids.add(self.customer)
        form.subject = "Angebot"
        form.body = "<p>Guten Tag</p>"
        composer = form.save()
        with self.mock_mail_gateway():
            composer._action_send_mail()
        self.assertEqual(len(self.emails), 1)
        self.assertFalse(self._new_mails.is_single_email)
        message = self.document.message_ids[0].sudo()
        self.assertFalse(message.partner_cc_ids)
        self.assertFalse(message.partner_bcc_ids)

    def test_reply_takes_over_cc_but_not_bcc(self):
        with self.mock_mail_gateway():
            parent = self.document.with_user(self.user_employee).message_post(
                body="Guten Tag",
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
                partner_ids=self.customer.ids,
                partner_cc_ids=self.copy.ids,
                partner_bcc_ids=self.blind.ids,
            )
        form = self._composer_form(default_parent_id=parent.id)
        self.assertEqual(form.partner_ids[:], self.customer)
        self.assertEqual(form.partner_cc_ids[:], self.copy)
        self.assertFalse(form.partner_bcc_ids[:])

    def test_mass_mail_ignores_blind_copies(self):
        """Bcc belongs to the mode with one document."""
        composer = (
            self.env["mail.compose.message"]
            .with_user(self.user_employee)
            .with_context(
                default_model=self.customer._name,
                default_res_ids=self.customer.ids,
                default_composition_mode="mass_mail",
            )
            .create(
                {
                    "subject": "Rundschreiben",
                    "body": "<p>Guten Tag</p>",
                    "partner_bcc_ids": [(4, self.blind.id)],
                }
            )
        )
        with self.mock_mail_gateway():
            composer._action_send_mail()
        self.assertEqual(len(self.emails), 1)
        self.assertEqual(self.emails[0]["smtp_to_list"], ["anna.beispiel@example.com"])

    def test_scheduled_message_keeps_the_copies(self):
        form = self._composer_form()
        form.partner_ids.add(self.customer)
        form.partner_cc_allowed = True
        form.partner_cc_ids.add(self.copy)
        form.partner_bcc_ids.add(self.blind)
        form.subject = "Angebot"
        form.body = "<p>Guten Tag</p>"
        composer = form.save()
        composer.scheduled_date = "2099-01-01 08:00:00"
        scheduled = composer._action_schedule_message()
        self.assertEqual(len(scheduled), 1)
        with self.mock_mail_gateway():
            scheduled._post_message()

        message = self.document.message_ids[0].sudo()
        self.assertEqual(message.partner_ids, self.customer)
        self.assertEqual(message.partner_cc_ids, self.copy)
        self.assertEqual(message.partner_bcc_ids, self.blind)
        self.assertEqual(len(self.emails), 1)
        self.assertEqual(len(self.emails[0]["smtp_to_list"]), 3)
        self.assertNotIn("dora.verdeckt", self.emails[0]["message"])
