"""
IWM Figma Export Tool
Generates full-page PNG screenshots of all screens
and combines them into a single importable PDF for Figma.

Usage: python generate_figma_export.py
Output: C:\GitRepo\ml\Figma\export\
"""

import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
from fpdf import FPDF
from PIL import Image

# ── Config ──────────────────────────────────────────────
BASE_DIR    = Path(r"C:\GitRepo\ml\Figma")
SCREENS_DIR = BASE_DIR / "screens"
EXPORT_DIR  = BASE_DIR / "export"
PNG_DIR     = EXPORT_DIR / "png"
PDF_PATH    = EXPORT_DIR / "IWM_Figma_AllScreens.pdf"
VIEWPORT_W  = 1440

# ── Screen definitions ─────────────────────────────────
SCREENS = [
    ("01_Login",              "01_login.html"),
    ("02_ForgotPassword",     "02_forgot_password.html"),
    ("03_Dashboard",          "03_dashboard.html"),
    ("04_Products_List",      "04_products.html"),
    ("05_Add_Product",        "05_add_product.html"),
    ("07_Categories",         "07_categories.html"),
    ("08_Orders_List",        "08_orders.html"),
    ("09_Order_Detail",       "09_order_detail.html"),
    ("10_Generate_Bill",      "10_generate_bill.html"),
    ("11_Prescriptions",      "11_prescriptions.html"),
    ("14_User_Management",    "14_users.html"),
    ("15_System_Settings",    "15_settings.html"),
    ("16_Reports",            "16_reports.html"),
]

def capture_screens():
    """Take full-page screenshots of all screens."""
    PNG_DIR.mkdir(parents=True, exist_ok=True)
    png_files = []

    print("\n📸 Capturing screens...\n")

    with sync_playwright() as p:
        browser = p.chromium.launch()

        for name, filename in SCREENS:
            html_path = SCREENS_DIR / filename
            if not html_path.exists():
                print(f"  ⚠️  Skipped (not found): {filename}")
                continue

            file_url = html_path.as_uri()
            out_path  = PNG_DIR / f"{name}.png"

            try:
                page = browser.new_page(viewport={"width": VIEWPORT_W, "height": 900})
                page.goto(file_url, wait_until="networkidle", timeout=15000)

                # Wait for fonts / layout
                page.wait_for_timeout(800)

                # Full page screenshot
                page.screenshot(path=str(out_path), full_page=True)
                print(f"  ✅  {name:<35} → {out_path.name}")
                png_files.append((name, out_path))

            except Exception as e:
                print(f"  ❌  {name}: {e}")

        browser.close()

    return png_files


def build_pdf(png_files):
    """Combine all PNGs into one importable PDF."""
    print(f"\n📄 Building PDF: {PDF_PATH.name}\n")

    pdf = FPDF(unit="pt")
    pdf.set_auto_page_break(False)

    for name, png_path in png_files:
        if not png_path.exists():
            continue

        img = Image.open(png_path)
        img_w, img_h = img.size

        # Scale to fit A4 landscape-ish width (1440pt → 842pt)
        scale   = 842 / img_w
        page_w  = 842
        page_h  = max(int(img_h * scale), 100)

        pdf.add_page(format=(page_w, page_h))

        pdf.image(str(png_path), x=0, y=0, w=page_w)
        print(f"  ✅  Added: {name}")

    pdf.output(str(PDF_PATH))
    print(f"\n✅ PDF saved → {PDF_PATH}")


def print_summary(png_files):
    print("\n" + "="*60)
    print("  IWM FIGMA EXPORT — COMPLETE")
    print("="*60)
    print(f"\n  📁 Export folder : {EXPORT_DIR}")
    print(f"  🖼️  PNG screens   : {len(png_files)} files  →  {PNG_DIR}")
    print(f"  📄 PDF (all-in-1): {PDF_PATH.name}")
    print(f"\n  ─── HOW TO IMPORT INTO FIGMA ──────────────────────────")
    print(f"  Option A (PDF):")
    print(f"    1. Open Figma → Shridhar App project")
    print(f"    2. Click + → Import")
    print(f"    3. Select: {PDF_PATH.name}")
    print(f"    4. Each page = one Figma frame ✅")
    print(f"")
    print(f"  Option B (Individual PNGs):")
    print(f"    1. Open Figma design file")
    print(f"    2. Drag & drop any PNG from: {PNG_DIR}")
    print(f"    3. Each PNG placed as a frame ✅")
    print("="*60 + "\n")


if __name__ == "__main__":
    print("="*60)
    print("  IWM — Inventory & Warehouse Management")
    print("  Figma Export Generator | SG Softech")
    print("="*60)

    png_files = capture_screens()

    if png_files:
        build_pdf(png_files)
        print_summary(png_files)
    else:
        print("\n❌ No screens captured. Check HTML files exist.")
        sys.exit(1)
