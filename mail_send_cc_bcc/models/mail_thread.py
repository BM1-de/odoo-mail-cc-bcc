# Copyright 2026 Baumgärtner Marketing GmbH
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, fields, models
from odoo.tools.misc import is_list_of

# Messages to customers: several recipients in To get one common email. For
# other messages (notifications of users) this needs a Cc or Bcc recipient.
SINGLE_EMAIL_MESSAGE_TYPES = ("comment", "auto_comment", "email_outgoing")
CONTEXT_KEY = "mail_send_cc_bcc_single"


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    # ------------------------------------------------------------
    # Cc and Bcc recipients of a message
    # ------------------------------------------------------------

    @api.model
    def _mail_send_cc_bcc_clean(self, partner_ids, partner_cc_ids, partner_bcc_ids):
        """Return the To, Cc and Bcc partner IDs of a message as three lists
        in which a partner appears once: To wins over Cc, Cc over Bcc."""
        for name, value in (
            ("partner_cc_ids", partner_cc_ids),
            ("partner_bcc_ids", partner_bcc_ids),
        ):
            if value and not is_list_of(value, int):
                raise ValueError(
                    self.env._(
                        "Posting a message should receive %(name)s as a list of IDs "
                        "(received %(value)s)",
                        name=name,
                        value=repr(value),
                    )
                )
        to_ids = partner_ids
        if to_ids and is_list_of(to_ids, int):
            to_ids = list(dict.fromkeys(to_ids))
        seen = set(to_ids) if to_ids and is_list_of(to_ids, int) else set()
        cc_ids = [pid for pid in dict.fromkeys(partner_cc_ids or []) if pid not in seen]
        seen.update(cc_ids)
        bcc_ids = [
            pid for pid in dict.fromkeys(partner_bcc_ids or []) if pid not in seen
        ]
        return to_ids, cc_ids, bcc_ids

    def message_post(
        self, *, partner_ids=None, partner_cc_ids=None, partner_bcc_ids=None, **kwargs
    ):
        """Accept ``partner_cc_ids`` and ``partner_bcc_ids``, lists of partner
        IDs like ``partner_ids``: the recipients in Cc and Bcc."""
        partner_ids, cc_ids, bcc_ids = self._mail_send_cc_bcc_clean(
            partner_ids, partner_cc_ids, partner_bcc_ids
        )
        if cc_ids:
            kwargs["partner_cc_ids"] = cc_ids
        if bcc_ids:
            kwargs["partner_bcc_ids"] = bcc_ids
        return super().message_post(partner_ids=partner_ids, **kwargs)

    def message_notify(
        self, *, partner_ids=False, partner_cc_ids=None, partner_bcc_ids=None, **kwargs
    ):
        partner_ids, cc_ids, bcc_ids = self._mail_send_cc_bcc_clean(
            partner_ids, partner_cc_ids, partner_bcc_ids
        )
        if cc_ids:
            kwargs["partner_cc_ids"] = cc_ids
        if bcc_ids:
            kwargs["partner_bcc_ids"] = bcc_ids
        return super().message_notify(partner_ids=partner_ids, **kwargs)

    def _get_message_create_valid_field_names(self):
        return super()._get_message_create_valid_field_names() | {
            "partner_cc_ids",
            "partner_bcc_ids",
        }

    def _message_create(self, values_list):
        # like 'partner_ids': lists of IDs become commands
        values_list = [dict(values) for values in values_list]
        for values in values_list:
            for fname in ("partner_cc_ids", "partner_bcc_ids"):
                if values.get(fname) and is_list_of(values[fname], int):
                    values[fname] = [fields.Command.link(pid) for pid in values[fname]]
        return super()._message_create(values_list)

    def _notify_get_recipients(self, message, msg_vals=False, **kwargs):
        msg_sudo = message.sudo()
        cc_ids = msg_sudo.partner_cc_ids.ids
        bcc_ids = msg_sudo.partner_bcc_ids.ids
        if not cc_ids and not bcc_ids:
            return super()._notify_get_recipients(message, msg_vals=msg_vals, **kwargs)
        msg_vals = dict(msg_vals or {})
        to_ids = (
            msg_vals["partner_ids"]
            if "partner_ids" in msg_vals
            else msg_sudo.partner_ids.ids
        )
        msg_vals["partner_ids"] = list(dict.fromkeys([*to_ids, *cc_ids, *bcc_ids]))
        # who puts himself in Cc or Bcc wants this copy; Odoo does not notify
        # the author of a message otherwise
        author_id = msg_vals.get("author_id") or msg_sudo.author_id.id
        if self._message_compute_real_author(author_id).id in (*cc_ids, *bcc_ids):
            kwargs["notify_author_mention"] = True
        recipients_data = super()._notify_get_recipients(
            message, msg_vals=msg_vals, **kwargs
        )
        for data in recipients_data:
            data["is_bcc"] = data["id"] in bcc_ids
            data["is_cc"] = data["id"] in cc_ids and not data["is_bcc"]
            # a copy is a copy of the email, also for users who read their
            # notifications in Odoo
            if (data["is_cc"] or data["is_bcc"]) and data.get("notif") == "inbox":
                data["notif"] = "email"
        return recipients_data

    # ------------------------------------------------------------
    # One email for the To, Cc and Bcc recipients
    # ------------------------------------------------------------

    def _mail_send_cc_bcc_single_plan(self, message, recipients_data):
        """Tell which recipients of the message get one common email.

        These are the customers and other external partners the message is
        addressed to (To) and every partner in Cc and Bcc. Followers and
        internal users in To keep their own notification with the buttons of
        their group.

        :return: dict with the partner IDs ``to``, ``cc``, ``bcc`` (sets), the
          ID ``primary`` of the partner whose group gives the layout, and
          ``lang``; ``None`` if Odoo shall send its emails as usual
        """
        if self._name == "discuss.channel":
            return None
        msg_sudo = message.sudo()
        direct_ids = set(msg_sudo.partner_ids.ids)
        to_ids, cc_ids, bcc_ids = [], [], []
        by_id = {}
        for data in recipients_data:
            pid = data.get("id")
            if not pid or data.get("notif") != "email":
                continue
            by_id[pid] = data
            if data.get("is_bcc"):
                bcc_ids.append(pid)
            elif data.get("is_cc"):
                cc_ids.append(pid)
            elif pid in direct_ids and data.get("share"):
                to_ids.append(pid)
        if not cc_ids and not bcc_ids:
            # Without copies only messages to customers are merged, and not
            # from the number of recipients on from which Odoo does not show
            # them to each other anymore. With copies the email is always a
            # common one: the emails of Odoo would show who got a blind copy.
            if (
                len(to_ids) < 2
                or len(to_ids) >= self._CUSTOMER_HEADERS_LIMIT_COUNT
                or msg_sudo.message_type not in SINGLE_EMAIL_MESSAGE_TYPES
            ):
                return None
        ordered = to_ids + cc_ids + bcc_ids
        # the layout of the customer if there is one, never the one with the
        # buttons of internal users for an external recipient
        primary = next((pid for pid in ordered if by_id[pid].get("share")), ordered[0])
        return {
            "to": set(to_ids),
            "cc": set(cc_ids),
            "bcc": set(bcc_ids),
            "primary": primary,
            "lang": by_id[primary].get("lang"),
        }

    def _notify_thread_by_email(self, message, recipients_data, **kwargs):
        plan = self._mail_send_cc_bcc_single_plan(message, recipients_data)
        if not plan:
            return super()._notify_thread_by_email(message, recipients_data, **kwargs)
        single_ids = plan["to"] | plan["cc"] | plan["bcc"]
        others = [data for data in recipients_data if data.get("id") not in single_ids]
        # one language for the common email: the one of its main recipient
        single = [
            dict(data, lang=plan["lang"])
            for data in recipients_data
            if data.get("id") in single_ids
        ]
        res = True
        if others:
            res = super()._notify_thread_by_email(message, others, **kwargs)
        super(
            MailThread, self.with_context(**{CONTEXT_KEY: plan})
        )._notify_thread_by_email(message, single, **kwargs)
        return res

    def _notify_get_recipients_classify(
        self, message, recipients_data, *args, **kwargs
    ):
        groups = super()._notify_get_recipients_classify(
            message, recipients_data, *args, **kwargs
        )
        plan = self.env.context.get(CONTEXT_KEY)
        if not plan or len(groups) < 2:
            return groups
        # Odoo makes one email per group of recipients (customer, portal user,
        # ...): put everybody into the group of the main recipient
        target = next(
            (
                group
                for group in groups
                if plan["primary"]
                in group["recipients_ids"] + group.get("recipients_cc_ids", [])
            ),
            groups[0],
        )
        for group in groups:
            if group is target:
                continue
            for key in (
                "recipients_data",
                "recipients_ids",
                "recipients_cc_ids",
                "recipients_emails",
            ):
                if group.get(key):
                    target[key] = target.get(key, []) + group[key]
        return [target]

    def _notify_by_email_get_final_mail_values(
        self, recipient_ids, mail_values, *args, **kwargs
    ):
        values = super()._notify_by_email_get_final_mail_values(
            recipient_ids, mail_values, *args, **kwargs
        )
        plan = self.env.context.get(CONTEXT_KEY)
        if not plan:
            return values
        partner_ids = list(
            dict.fromkeys(
                command[1]
                for fname in ("recipient_ids", "recipient_cc_ids")
                for command in values.get(fname) or []
            )
        )
        if not partner_ids:
            return values
        link = fields.Command.link
        values.update(
            is_single_email=True,
            recipient_ids=[link(pid) for pid in partner_ids],
            recipient_cc_ids=[link(pid) for pid in partner_ids if pid in plan["cc"]],
            recipient_bcc_ids=[link(pid) for pid in partner_ids if pid in plan["bcc"]],
        )
        return values
