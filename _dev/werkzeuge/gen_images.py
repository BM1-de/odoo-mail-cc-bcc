# Copyright 2026 Baumgärtner Marketing GmbH
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Banner and icon of the module (static/description).

In English, as the Odoo Apps Store requires, and in the style of the other BM1
modules. Runs inside the Odoo container, which has Pillow and the DejaVu
fonts::

    docker compose run --rm --no-deps -T --entrypoint python3 odoo - \
        < _dev/werkzeuge/gen_images.py
"""

# pylint: disable=print-used

from PIL import Image, ImageDraw, ImageFont

BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
DARK, LIGHT, ACCENT, WHITE = (
    (31, 58, 96),
    (233, 239, 247),
    (52, 120, 184),
    (255, 255, 255),
)


def fitted(draw, text, path, size, width):
    """Font of at most ``size`` points whose ``text`` fits into ``width``."""
    while size > 10:
        font = ImageFont.truetype(path, size)
        if draw.textlength(text, font=font) <= width:
            return font
        size -= 1
    return ImageFont.truetype(path, size)


def label(draw, text, box, color):
    """``text`` centred in the horizontal range of ``box`` at its top."""
    left, top, right = box
    font = fitted(draw, text, BOLD, 44, right - left)
    width = draw.textlength(text, font=font)
    draw.text((left + (right - left - width) / 2, top), text, font=font, fill=color)


def save_icon(img, out):
    img.resize((128, 128), Image.LANCZOS).save(out + "icon.png", optimize=True)


def banner(out, rows):
    width, height = 1120, 560
    margin = 80
    img = Image.new("RGB", (width, height), DARK)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, height - 120, width, height), fill=ACCENT)
    title, first, second, footer = rows
    for text, path, size, color, top in (
        (title, BOLD, 84, WHITE, 100),
        (first, REGULAR, 38, LIGHT, 240),
        (second, REGULAR, 38, LIGHT, 300),
        (footer, REGULAR, 30, WHITE, height - 82),
    ):
        font = fitted(draw, text, path, size, width - 2 * margin)
        draw.text((margin, top), text, font=font, fill=color)
    img.save(out + "banner.png", optimize=True)


def icon(out):
    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=40, fill=DARK)
    # one envelope, three recipients
    draw.rounded_rectangle((36, 40, 220, 150), radius=12, fill=WHITE)
    draw.line((40, 46, 128, 108, 216, 46), fill=DARK, width=8, joint="curve")
    for index, color in enumerate((ACCENT, LIGHT, (160, 172, 190))):
        left = 44 + index * 60
        draw.ellipse((left + 12, 166, left + 36, 190), fill=color)
        draw.rounded_rectangle((left, 196, left + 48, 220), radius=12, fill=color)
    save_icon(img, out)


for addon, rows in (
    (
        "mail_send_cc_bcc",
        (
            "Email Cc and Bcc in One Email",
            "Cc and Bcc in the email composer, and one single email",
            "to all recipients instead of one email per recipient",
            "Odoo 19 · quotations, orders, messages to customers",
        ),
    ),
    (
        "account_move_send_cc_bcc",
        (
            "Invoice Email Cc and Bcc",
            "Cc and Bcc when sending an invoice by email, and one",
            "single email with the invoice to all recipients",
            "Odoo 19 · invoices and credit notes",
        ),
    ),
):
    OUT = f"/mnt/extra-addons/{addon}/static/description/"
    icon(OUT)
    banner(OUT, rows)
print("ok")
