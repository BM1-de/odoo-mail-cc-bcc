# Copyright 2026 Baumgärtner Marketing GmbH
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Invoice Email Cc and Bcc",
    "summary": "Cc and Bcc recipients when sending an invoice by email, sent as "
    "one single email to all recipients",
    "version": "19.0.1.0.0",
    "category": "Accounting/Accounting",
    "website": "https://github.com/BM1-de/odoo-mail-cc-bcc",
    "author": "Baumgärtner Marketing GmbH",
    "maintainers": ["bm1-phillip"],
    "license": "AGPL-3",
    "development_status": "Alpha",
    "depends": ["account", "mail_send_cc_bcc"],
    "data": ["wizard/account_move_send_wizard_views.xml"],
    "images": ["static/description/banner.png"],
    "installable": True,
    "auto_install": True,
}
