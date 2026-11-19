# Copyright 2026 Baumgärtner Marketing GmbH
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Screenshots of the two dialogs with Cc and Bcc filled in.

Runs against a local development database with invented data (a customer with
the contacts named below, a posted invoice and a quotation) and uses the
installed Google Chrome in a throw-away profile::

    uv run --with playwright python _dev/werkzeuge/screenshots.py \\
        --url http://localhost:8077 --lang en_US \\
        --invoice 2 --order 1 --out build/screenshots/en

Writes ``invoice_send.png`` and ``composer.png`` into the output directory.
The login is the one of a fresh local Odoo database; never point this script
at a database with real data.
"""

# pylint: disable=print-used

import argparse
import pathlib

from playwright.sync_api import sync_playwright

CC_NAME = "Clara Kopie"
BCC_NAME = "Archiv Buchhaltung"


def add_tag(dialog, field, name):
    """Type ``name`` into the many2many tags ``field`` and take the proposal."""
    box = dialog.locator(f"[name='{field}'] input").first
    box.click()
    box.type(name[:5], delay=40)
    dialog.page.locator(".o-autocomplete--dropdown-item", has_text=name).first.click()
    dialog.locator(f"[name='{field}'] .o_tag", has_text=name).wait_for()
    # Odoo drops a tag, also of its own field "To", if the next click comes
    # within milliseconds of the selection
    dialog.page.wait_for_timeout(500)


def open_dialog(page, url, button):
    page.goto(url)
    page.locator(f"button[name='{button}']:visible").first.click()
    # a fresh database asks for the document layout first
    for _attempt in range(40):
        if page.locator(".modal [name$='partner_ids']").count():
            break
        layout = page.locator(".modal button[name='document_layout_save']:visible")
        if layout.count():
            layout.first.click()
        page.wait_for_timeout(250)
    dialog = page.locator(".modal .modal-content").last
    dialog.locator("[name$='partner_ids']:visible").first.wait_for()
    return dialog


def call(page, url, model, method, call_args):
    response = page.request.post(
        f"{url}/web/dataset/call_kw/{model}/{method}",
        data={
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": model,
                "method": method,
                "args": call_args,
                "kwargs": {},
            },
        },
    )
    result = response.json()
    if result.get("error"):
        raise SystemExit(f"{model}.{method}: {result['error']['data']['message']}")
    return result["result"]


def customer_ids(page, args):
    invoice = call(
        page, args.url, "account.move", "read", [[args.invoice], ["partner_id"]]
    )
    order = call(page, args.url, "sale.order", "read", [[args.order], ["partner_id"]])
    return sorted({invoice[0]["partner_id"][0], order[0]["partner_id"][0]})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8077")
    parser.add_argument("--login", default="admin")
    parser.add_argument("--password", default="admin")
    parser.add_argument("--lang", default="en_US")
    parser.add_argument("--invoice", type=int, required=True)
    parser.add_argument("--order", type=int, required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context(
            viewport={"width": 1400, "height": 900},
            device_scale_factor=2,
            locale=args.lang.replace("_", "-"),
        )
        page = context.new_page()
        page.goto(f"{args.url}/web/login")
        page.fill("input[name='login']", args.login)
        page.fill("input[name='password']", args.password)
        page.click("button[type='submit']")
        page.wait_for_url("**/odoo**")
        # the user and the customer of the documents speak the language of
        # the screenshot, the user signs the emails
        for model, method, call_args in (
            ("res.users", "write", [[2], {"lang": args.lang}]),
            (
                "res.partner",
                "write",
                [customer_ids(page, args), {"lang": args.lang}],
            ),
            ("account.move", "write", [[args.invoice], {"invoice_user_id": 2}]),
            ("sale.order", "write", [[args.order], {"user_id": 2}]),
        ):
            call(page, args.url, model, method, call_args)

        # invoice: the Send dialog
        dialog = open_dialog(
            page, f"{args.url}/odoo/account.move/{args.invoice}", "action_invoice_sent"
        )
        add_tag(dialog, "mail_partner_cc_ids", CC_NAME)
        add_tag(dialog, "mail_partner_bcc_ids", BCC_NAME)
        page.mouse.click(5, 5)
        page.wait_for_timeout(600)
        for field in ("mail_partner_cc_ids", "mail_partner_bcc_ids"):
            if not dialog.locator(f"[name='{field}'] .o_tag").count():
                raise SystemExit(f"{field} is empty in the invoice dialog")
        dialog.screenshot(path=str(out / "invoice_send.png"))
        print("invoice_send.png")

        # quotation: the email composer
        dialog = open_dialog(
            page, f"{args.url}/odoo/sale.order/{args.order}", "action_quotation_send"
        )
        # Odoo 20 shows Cc and Bcc of the composer after a click on "Cc"
        if not dialog.locator("[name='partner_cc_ids']:visible").count():
            dialog.locator("[name='partner_cc_allowed']").first.click()
            dialog.locator("[name='partner_cc_ids']:visible").first.wait_for()
        add_tag(dialog, "partner_cc_ids", CC_NAME)
        add_tag(dialog, "partner_bcc_ids", BCC_NAME)
        page.mouse.click(5, 5)
        page.wait_for_timeout(600)
        for field in ("partner_cc_ids", "partner_bcc_ids"):
            if not dialog.locator(f"[name='{field}'] .o_tag").count():
                raise SystemExit(f"{field} is empty in the composer")
        dialog.screenshot(path=str(out / "composer.png"))
        print("composer.png")
        browser.close()


if __name__ == "__main__":
    main()
