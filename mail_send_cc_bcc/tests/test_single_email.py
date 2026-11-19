# Copyright 2026 Baumgärtner Marketing GmbH
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests import tagged
from odoo.tools import email_normalize, mute_logger

from odoo.addons.mail.tests.common import MailCommon


@tagged("post_install", "-at_install")
class TestSingleEmail(MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Partner = cls.env["res.partner"]
        # the document the messages are posted on
        cls.document = Partner.create({"name": "Musterfirma Beispiel GmbH"})
        cls.customer = Partner.create(
            {"name": "Anna Beispiel", "email": "anna.beispiel@example.com"}
        )
        cls.customer_2 = Partner.create(
            {"name": "Bernd Muster", "email": "bernd.muster@example.com"}
        )
        cls.copy = Partner.create(
            {"name": "Clara Kopie", "email": "clara.kopie@example.com"}
        )
        cls.blind = Partner.create(
            {"name": "Dora Verdeckt", "email": "dora.verdeckt@example.com"}
        )
        cls.no_email = Partner.create({"name": "Emil Ohneadresse"})

    def _post(self, record=None, **kwargs):
        record = record or self.document
        kwargs.setdefault("body", "Guten Tag")
        kwargs.setdefault("message_type", "comment")
        kwargs.setdefault("subtype_xmlid", "mail.mt_comment")
        with self.mock_mail_gateway():
            message = record.with_user(self.user_employee).message_post(**kwargs)
        return message

    def _addresses(self, header):
        return sorted(email_normalize(part) for part in (header or "").split(","))

    def _notification_status(self, message):
        return {
            notification.res_partner_id: notification.notification_status
            for notification in message.sudo().notification_ids
        }

    # ------------------------------------------------------------
    # one email for To, Cc and Bcc
    # ------------------------------------------------------------

    def test_to_cc_bcc_are_one_email(self):
        message = self._post(
            partner_ids=self.customer.ids,
            partner_cc_ids=self.copy.ids,
            partner_bcc_ids=self.blind.ids,
        )
        msg_sudo = message.sudo()
        self.assertEqual(msg_sudo.partner_ids, self.customer)
        self.assertEqual(msg_sudo.partner_cc_ids, self.copy)
        self.assertEqual(msg_sudo.partner_bcc_ids, self.blind)

        mail = self._new_mails
        self.assertEqual(len(mail), 1)
        self.assertTrue(mail.is_single_email)
        self.assertEqual(mail.recipient_ids, self.customer + self.copy + self.blind)
        self.assertEqual(mail.recipient_cc_ids, self.copy)
        self.assertEqual(mail.recipient_bcc_ids, self.blind)

        # one email left the server, addressed to all three
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
        self.assertEqual(
            self._addresses(email["msg_to"]), ["anna.beispiel@example.com"]
        )
        self.assertEqual(self._addresses(email["msg_cc"]), ["clara.kopie@example.com"])
        # nobody reads who got the blind copy
        self.assertNotIn("dora.verdeckt", email["message"])
        self.assertNotIn("Bcc", email["message"])
        self.assertNotIn("X-Msg-To-Add", email["message"])

        self.assertEqual(
            self._notification_status(message),
            {self.customer: "sent", self.copy: "sent", self.blind: "sent"},
        )

    def test_two_recipients_in_to_are_one_email(self):
        message = self._post(partner_ids=(self.customer + self.customer_2).ids)
        self.assertEqual(len(self._new_mails), 1)
        self.assertTrue(self._new_mails.is_single_email)
        self.assertEqual(len(self.emails), 1)
        self.assertEqual(
            self._addresses(self.emails[0]["msg_to"]),
            ["anna.beispiel@example.com", "bernd.muster@example.com"],
        )
        self.assertFalse(self.emails[0]["msg_cc"])
        self.assertEqual(
            self._notification_status(message),
            {self.customer: "sent", self.customer_2: "sent"},
        )

    def test_one_recipient_is_left_to_odoo(self):
        self._post(partner_ids=self.customer.ids)
        self.assertEqual(len(self._new_mails), 1)
        self.assertFalse(self._new_mails.is_single_email)
        self.assertEqual(len(self.emails), 1)

    def test_notification_to_several_partners_is_left_to_odoo(self):
        """Only messages to customers are merged without Cc or Bcc."""
        self._post(
            partner_ids=(self.customer + self.customer_2).ids,
            message_type="notification",
        )
        self.assertFalse(any(self._new_mails.mapped("is_single_email")))
        self.assertEqual(len(self.emails), 2)

    def test_only_copies(self):
        """Cc and Bcc without To: still one email."""
        self._post(partner_cc_ids=self.copy.ids, partner_bcc_ids=self.blind.ids)
        self.assertEqual(len(self.emails), 1)
        email = self.emails[0]
        self.assertFalse(email["msg_to"])
        self.assertEqual(self._addresses(email["msg_cc"]), ["clara.kopie@example.com"])
        self.assertEqual(
            sorted(email["smtp_to_list"]),
            ["clara.kopie@example.com", "dora.verdeckt@example.com"],
        )

    def test_a_partner_is_addressed_once(self):
        """To wins over Cc, Cc over Bcc."""
        message = self._post(
            partner_ids=self.customer.ids,
            partner_cc_ids=(self.customer + self.copy).ids,
            partner_bcc_ids=(self.copy + self.blind + self.blind).ids,
        )
        msg_sudo = message.sudo()
        self.assertEqual(msg_sudo.partner_ids, self.customer)
        self.assertEqual(msg_sudo.partner_cc_ids, self.copy)
        self.assertEqual(msg_sudo.partner_bcc_ids, self.blind)
        self.assertEqual(len(self.emails), 1)
        self.assertEqual(len(self.emails[0]["smtp_to_list"]), 3)

    def test_invalid_parameters(self):
        with self.assertRaises(ValueError):
            self.document.message_post(body="x", partner_cc_ids=[(4, self.copy.id)])
        with self.assertRaises(ValueError):
            self.document.message_post(body="x", partner_bcc_ids=["7"])

    # ------------------------------------------------------------
    # followers and users
    # ------------------------------------------------------------

    def test_followers_keep_their_own_email(self):
        """An internal follower gets the notification of Odoo, with the
        buttons of users; the customer and the copies get the common email."""
        self.user_admin.notification_type = "email"
        self.document.message_subscribe(partner_ids=self.partner_admin.ids)
        message = self._post(
            partner_ids=self.customer.ids, partner_cc_ids=self.copy.ids
        )
        self.assertEqual(len(self._new_mails), 2)
        single = self._new_mails.filtered("is_single_email")
        self.assertEqual(single.recipient_ids, self.customer + self.copy)
        self.assertEqual((self._new_mails - single).recipient_ids, self.partner_admin)
        self.assertEqual(len(self.emails), 2)
        for email in self.emails:
            if email["smtp_to_list"] == [self.partner_admin.email_normalized]:
                # the follower's own email names no copy
                self.assertFalse(email["msg_cc"])
            else:
                self.assertEqual(
                    sorted(email["smtp_to_list"]),
                    ["anna.beispiel@example.com", "clara.kopie@example.com"],
                )
        self.assertEqual(
            self._notification_status(message),
            {self.customer: "sent", self.copy: "sent", self.partner_admin: "sent"},
        )

    def test_user_in_cc_gets_the_email(self):
        """A copy is a copy of the email, also for a user who reads his
        notifications in Odoo."""
        self.user_admin.notification_type = "inbox"
        message = self._post(
            partner_ids=self.customer.ids, partner_cc_ids=self.partner_admin.ids
        )
        self.assertEqual(len(self.emails), 1)
        self.assertEqual(
            sorted(self.emails[0]["smtp_to_list"]),
            sorted(["anna.beispiel@example.com", self.partner_admin.email_normalized]),
        )
        notification = message.sudo().notification_ids.filtered(
            lambda n: n.res_partner_id == self.partner_admin
        )
        self.assertEqual(notification.notification_type, "email")

    def test_author_in_bcc_gets_the_email(self):
        message = self._post(
            partner_ids=self.customer.ids,
            partner_bcc_ids=self.partner_employee.ids,
        )
        self.assertEqual(len(self.emails), 1)
        self.assertIn(
            self.partner_employee.email_normalized, self.emails[0]["smtp_to_list"]
        )
        self.assertFalse(self.emails[0]["msg_cc"])
        self.assertEqual(
            self._addresses(self.emails[0]["msg_to"]), ["anna.beispiel@example.com"]
        )
        self.assertEqual(
            self._notification_status(message),
            {self.customer: "sent", self.partner_employee: "sent"},
        )

    def test_author_in_cc_gets_the_email(self):
        message = self._post(
            partner_ids=self.customer.ids,
            partner_cc_ids=self.partner_employee.ids,
        )
        self.assertEqual(len(self.emails), 1)
        self.assertIn(
            self.partner_employee.email_normalized, self.emails[0]["smtp_to_list"]
        )
        self.assertEqual(
            self._notification_status(message),
            {self.customer: "sent", self.partner_employee: "sent"},
        )

    def test_layout_of_the_customer(self):
        """The common email never carries the button of internal users."""
        self.user_admin.notification_type = "email"
        self._post(
            partner_ids=self.customer.ids,
            partner_cc_ids=self.partner_admin.ids,
        )
        self.assertEqual(len(self.emails), 1)
        self.assertNotIn("/mail/view", self._new_mails.body_html)

    # ------------------------------------------------------------
    # partners without address, many recipients
    # ------------------------------------------------------------

    @mute_logger("odoo.addons.mail.models.mail_mail")
    def test_partner_without_email(self):
        """The others get the email, the notification tells who did not."""
        message = self._post(
            partner_ids=self.customer.ids, partner_cc_ids=self.no_email.ids
        )
        self.assertEqual(len(self.emails), 1)
        self.assertEqual(self.emails[0]["smtp_to_list"], ["anna.beispiel@example.com"])
        self.assertFalse(self.emails[0]["msg_cc"])
        notifications = {
            notification.res_partner_id: notification
            for notification in message.sudo().notification_ids
        }
        self.assertEqual(notifications[self.customer].notification_status, "sent")
        self.assertEqual(notifications[self.no_email].notification_status, "exception")
        self.assertEqual(
            notifications[self.no_email].failure_type, "mail_email_missing"
        )

    def test_many_recipients_in_to_are_left_to_odoo(self):
        """Odoo does not show the recipients of a message to each other from
        a certain number on; neither does this module."""
        limit = self.env["mail.thread"]._CUSTOMER_HEADERS_LIMIT_COUNT
        partners = self.env["res.partner"].create(
            [
                {"name": f"Kunde {number}", "email": f"kunde{number}@example.com"}
                for number in range(limit + 1)
            ]
        )
        self._post(partner_ids=partners.ids)
        self.assertFalse(any(self._new_mails.mapped("is_single_email")))
        self.assertEqual(len(self.emails), limit + 1)

    def test_many_recipients_with_bcc_stay_hidden(self):
        """With a blind copy the emails are always common ones: the header
        of the emails of Odoo would show who got it."""
        self.env["ir.config_parameter"].sudo().set_int("mail.batch_size", 2)
        self._post(
            partner_ids=(self.customer + self.customer_2).ids,
            partner_cc_ids=self.copy.ids,
            partner_bcc_ids=self.blind.ids,
        )
        self.assertEqual(len(self._new_mails), 2)
        self.assertTrue(all(self._new_mails.mapped("is_single_email")))
        self.assertEqual(len(self.emails), 2)
        self.assertEqual(
            sorted(
                address for email in self.emails for address in email["smtp_to_list"]
            ),
            [
                "anna.beispiel@example.com",
                "bernd.muster@example.com",
                "clara.kopie@example.com",
                "dora.verdeckt@example.com",
            ],
        )
        for email in self.emails:
            self.assertNotIn("dora.verdeckt", email["message"])

    def test_user_in_to_keeps_the_notification_of_odoo(self):
        """An internal user in To is notified as Odoo does it, here in Odoo
        itself; the email goes to the customer and the copy."""
        self.user_admin.notification_type = "inbox"
        message = self._post(
            partner_ids=(self.customer + self.partner_admin).ids,
            partner_cc_ids=self.copy.ids,
        )
        self.assertEqual(len(self.emails), 1)
        self.assertEqual(
            sorted(self.emails[0]["smtp_to_list"]),
            ["anna.beispiel@example.com", "clara.kopie@example.com"],
        )
        notification = message.sudo().notification_ids.filtered(
            lambda n: n.res_partner_id == self.partner_admin
        )
        self.assertEqual(notification.notification_type, "inbox")

    def test_notify_without_document(self):
        """message_notify takes the copies like message_post."""
        with self.mock_mail_gateway():
            message = (
                self.env["mail.thread"]
                .with_user(self.user_employee)
                .message_notify(
                    body="Guten Tag",
                    subject="Hinweis",
                    partner_ids=self.customer.ids,
                    partner_cc_ids=self.copy.ids,
                    partner_bcc_ids=self.blind.ids,
                )
            )
        msg_sudo = message.sudo()
        self.assertEqual(msg_sudo.partner_ids, self.customer)
        self.assertEqual(msg_sudo.partner_cc_ids, self.copy)
        self.assertEqual(msg_sudo.partner_bcc_ids, self.blind)
        self.assertEqual(len(self.emails), 1)
        email = self.emails[0]
        self.assertEqual(len(email["smtp_to_list"]), 3)
        self.assertEqual(self._addresses(email["msg_cc"]), ["clara.kopie@example.com"])
        self.assertNotIn("dora.verdeckt", email["message"])

    def test_channels_are_left_to_odoo(self):
        channel = self.env["discuss.channel"].create({"name": "Allgemein"})
        message = self.env["mail.message"]
        self.assertIsNone(channel._mail_send_cc_bcc_single_plan(message, []))

    def test_email_without_partner_is_left_alone(self):
        """The values of an email to plain addresses stay as Odoo made them."""
        plan = {"to": set(), "cc": set(), "bcc": set(), "primary": False, "lang": False}
        values = self.document.with_context(
            mail_send_cc_bcc_single=plan
        )._notify_by_email_get_final_mail_values([], {"subject": "Hinweis"})
        self.assertNotIn("is_single_email", values)

    # ------------------------------------------------------------
    # the common email itself
    # ------------------------------------------------------------

    def test_addresses_without_partner_are_kept(self):
        """Plain addresses in the fields To and Cc of an email stay in To
        and Cc of the common email."""
        mail = (
            self.env["mail.mail"]
            .sudo()
            .create(
                {
                    "subject": "Hinweis",
                    "body_html": "<p>Guten Tag</p>",
                    "email_to": "frei@example.com",
                    "email_cc": "frei.kopie@example.com",
                    "recipient_ids": [(4, self.customer.id), (4, self.blind.id)],
                    "recipient_bcc_ids": [(4, self.blind.id)],
                    "is_single_email": True,
                }
            )
        )
        emails = mail._prepare_outgoing_list()
        self.assertEqual(len(emails), 1)
        email = emails[0]
        self.assertEqual(
            sorted(email_normalize(address) for address in email["email_to"]),
            ["anna.beispiel@example.com", "frei@example.com"],
        )
        self.assertEqual(email["email_cc"], ["frei.kopie@example.com"])
        self.assertIn("dora.verdeckt@example.com", email["headers"]["Bcc"])
        self.assertEqual(
            sorted(email["email_to_normalized"]),
            [
                "anna.beispiel@example.com",
                "dora.verdeckt@example.com",
                "frei.kopie@example.com",
                "frei@example.com",
            ],
        )
        self.assertFalse(email["partner_id"])

        # only a plain Cc address and a partner
        mail.write({"email_to": False})
        email = mail._prepare_outgoing_list()[0]
        self.assertEqual(
            [email_normalize(address) for address in email["email_to"]],
            ["anna.beispiel@example.com"],
        )
        self.assertEqual(email["email_cc"], ["frei.kopie@example.com"])

    def test_email_of_odoo_is_not_merged(self):
        mail = (
            self.env["mail.mail"]
            .sudo()
            .create(
                {
                    "subject": "Hinweis",
                    "body_html": "<p>Guten Tag</p>",
                    "recipient_ids": [(4, self.customer.id), (4, self.copy.id)],
                }
            )
        )
        self.assertEqual(len(mail._prepare_outgoing_list()), 2)

    # ------------------------------------------------------------
    # who may see the blind copies
    # ------------------------------------------------------------

    def test_bcc_is_hidden_from_portal_users(self):
        user_portal = self._create_portal_user()
        Message = self.env["mail.message"]
        self.assertIn(
            "partner_bcc_ids", Message.with_user(self.user_employee).fields_get()
        )
        self.assertNotIn("partner_bcc_ids", Message.with_user(user_portal).fields_get())
        self.assertIn("partner_cc_ids", Message.with_user(user_portal).fields_get())
