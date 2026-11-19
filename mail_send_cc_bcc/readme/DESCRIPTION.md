Adds the fields *Cc* and *Bcc* to the email composer and sends a message as
**one single email** to all its recipients.

Out of the box Odoo 19 has no Cc or Bcc when you send a quotation, an order or
any other message to a customer, and it sends one email per recipient: a
message to two people leaves the server as two emails, each addressed to one
of them. With this module

- the composer has a line *Cc* and a line *Bcc* below *To*,
- the recipients in To, Cc and Bcc get the same single email, with the To and
  Cc recipients in its header, as any mail program would send it,
- nobody sees who got a blind copy: not the other recipients, and not portal
  users who look at the messages of their document,
- two or more customers in *To* also get one common email instead of one each.

Sending invoices has its own dialog in Odoo; the module *Invoice Email Cc and
Bcc* (`account_move_send_cc_bcc`), installed automatically with Invoicing, adds
both lines there.

Followers of the document and internal users in *To* keep the notification of
Odoo with the buttons of their group; nothing changes for them.

The fields use the names of Odoo 20, which brings Cc in its composer: after an
upgrade the Cc recipients of old messages are kept.
