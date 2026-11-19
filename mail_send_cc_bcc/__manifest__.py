# Copyright 2026 Baumgärtner Marketing GmbH
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Email Cc and Bcc in One Email",
    "summary": "Bcc recipients in the email composer, and one single email to "
    "the To, Cc and Bcc recipients instead of one email per recipient",
    "version": "20.0.1.0.0",
    "category": "Productivity/Discuss",
    "website": "https://github.com/BM1-de/odoo-mail-cc-bcc",
    "author": "Baumgärtner Marketing GmbH",
    "maintainers": ["bm1-phillip"],
    "license": "AGPL-3",
    "development_status": "Alpha",
    "depends": ["mail"],
    "data": [
        "views/mail_mail_views.xml",
        "views/mail_message_views.xml",
        "wizard/mail_compose_message_views.xml",
    ],
    "images": ["static/description/banner.png"],
    "installable": True,
}
