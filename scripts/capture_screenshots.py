"""Capture landing-page screenshots (docs/images/*.jpg, 1600x1000) and catalog cards (docs/catalog/*.jpg,
960x600, under 100 KB) from the hosted example on Sample data.

  python3 -m http.server 8766 --bind 127.0.0.1 --directory docs &
  python scripts/capture_screenshots.py [base_url]
"""
import io
import pathlib
import sys

from PIL import Image
from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8766/try/"
ROOT = pathlib.Path(__file__).resolve().parents[1]
IMG, CARD = ROOT / "docs/images", ROOT / "docs/catalog"
IMG.mkdir(parents=True, exist_ok=True)
CARD.mkdir(parents=True, exist_ok=True)


def save(page, name, card=None):
    im = Image.open(io.BytesIO(page.screenshot())).convert("RGB")
    im.resize((1600, 1000), Image.LANCZOS).save(IMG / f"{name}.jpg", quality=84, optimize=True)
    if card:
        c = im.resize((960, 600), Image.LANCZOS)
        for q in (82, 76, 70, 64, 58):
            buf = io.BytesIO()
            c.save(buf, "JPEG", quality=q, optimize=True)
            if buf.tell() < 100_000:
                break
        (CARD / f"verified-bank-research-{card}.jpg").write_bytes(buf.getvalue())


with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=2, reduced_motion="reduce")
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)

    page.goto(BASE + "#desk")
    page.wait_for_selector("#cov tbody tr")
    page.wait_for_timeout(600)
    save(page, "01-desk", 1)

    page.locator("[data-bank]", has_text="Kestrova Bank").first.click()
    page.wait_for_selector(".drawer")
    page.wait_for_timeout(400)
    save(page, "07-bank", 6)
    page.keyboard.press("Escape")

    page.goto(BASE + "#compose")
    page.wait_for_selector("#c-run")
    page.select_option("#c-s", "Ombrel National Bank")
    page.click("#c-run")
    page.wait_for_selector(".hallmark", timeout=20000)
    page.wait_for_timeout(500)
    save(page, "02-compose", 2)
    page.evaluate("window.scrollTo(0, document.querySelector('#c-out').getBoundingClientRect().top + scrollY - 76)")
    page.wait_for_timeout(200)
    save(page, "03-note-verified", 3)

    page.goto(BASE + "#compose")
    page.wait_for_selector("#c-run")
    page.select_option("#c-s", "Ombrel National Bank")
    page.check("#c-i")
    page.click("#c-run")
    page.wait_for_selector(".hallmark", timeout=20000)
    page.wait_for_timeout(500)
    page.evaluate("window.scrollTo(0, document.querySelector('#c-out').getBoundingClientRect().top + scrollY - 76)")
    page.wait_for_timeout(200)
    save(page, "04-note-review", 4)

    page.goto(BASE + "#notes")
    page.wait_for_selector("#nt tbody tr")
    page.wait_for_timeout(300)
    save(page, "05-notes", 5)

    page.goto(BASE + "#ask")
    page.wait_for_selector("[data-q]")
    page.click("[data-q='0']")
    page.wait_for_selector(".msg.bot .ans", timeout=20000)
    page.wait_for_timeout(800)
    save(page, "06-ask", 7)

    b.close()
    print("console errors:", errors or "none")
