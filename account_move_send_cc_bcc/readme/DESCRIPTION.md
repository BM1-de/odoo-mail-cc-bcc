Adds the fields *Cc* and *Bcc* to the dialog that sends an invoice or a credit
note by email. The customer, the Cc recipients and the Bcc recipients get
**one single email** with the invoice attached, instead of one email per
recipient as Odoo sends them.

Nobody sees who got a blind copy. In the chatter of the invoice the message
lists all recipients for internal users.

The sending itself is done by the module *Email Cc and Bcc in One Email*
(`mail_send_cc_bcc`), which adds the same fields to the email composer used
for quotations, orders and messages. This module is installed automatically
when both it and Invoicing are installed.
