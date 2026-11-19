Adds the field *Bcc* to the email composer and sends a message as **one
single email** to all its recipients.

Odoo 20 has *Cc* in its composer, but no Bcc, and it still sends one email per
recipient: a message to two people leaves the server as two emails. With this
module

- the composer has a line *Bcc* below *Cc*,
- the recipients in To, Cc and Bcc get the same single email, with the To and
  Cc recipients in its header, as any mail program would send it,
- nobody sees who got a blind copy: not the other recipients, and not portal
  users who look at the messages of their document,
- two or more customers in *To* also get one common email instead of one each.

Sending invoices has its own dialog in Odoo, without Cc; the module *Invoice
Email Cc and Bcc* (`account_move_send_cc_bcc`), installed automatically with
Invoicing, adds *Cc* and *Bcc* there.

Followers of the document and internal users in *To* keep the notification of
Odoo with the buttons of their group; nothing changes for them.

The version for Odoo 19 of this module adds Cc as well, with the field names
of Odoo 20: after an upgrade the Cc recipients of old messages are kept.
