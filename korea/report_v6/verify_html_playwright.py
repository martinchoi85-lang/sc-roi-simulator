"""Playwright verification script for LG_SC_Korea_ROI_Report.html.

Verifies:
1. Desktop Light (Collapsed)
2. Desktop Dark (Collapsed)
3. Desktop Light (Expanded all details)
4. Mobile Light (375px width, checks horizontal overflow)
"""

import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

def verify_html(report_html_path: Path, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    html_url = f"file:///{report_html_path.resolve().as_posix()}"

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # 1. Desktop Light Collapsed
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(html_url)
        page.wait_for_timeout(1000)
        shot1 = output_dir / "snap_desktop_light_collapsed.png"
        page.screenshot(path=str(shot1), full_page=False)
        print(f"Captured: {shot1}")

        # Check horizontal overflow on desktop
        scroll_w = page.evaluate("() => document.documentElement.scrollWidth")
        client_w = page.evaluate("() => document.documentElement.clientWidth")
        print(f"Desktop: scrollWidth={scroll_w}, clientWidth={client_w}")
        assert scroll_w <= client_w + 1, f"Desktop horizontal overflow detected! {scroll_w} > {client_w}"

        # 2. Desktop Dark Collapsed
        page.click("#themeToggleBtn")
        page.wait_for_timeout(500)
        shot2 = output_dir / "snap_desktop_dark_collapsed.png"
        page.screenshot(path=str(shot2), full_page=False)
        print(f"Captured: {shot2}")

        # 3. Desktop Dark Expanded
        page.evaluate("() => document.querySelectorAll('details').forEach(d => d.open = true)")
        page.wait_for_timeout(1000)
        shot3 = output_dir / "snap_desktop_dark_expanded.png"
        page.screenshot(path=str(shot3), full_page=True)
        print(f"Captured: {shot3}")

        # 4. Mobile Light (375px)
        mobile_page = browser.new_page(viewport={"width": 375, "height": 812})
        mobile_page.goto(html_url)
        mobile_page.wait_for_timeout(1000)
        m_scroll_w = mobile_page.evaluate("() => document.documentElement.scrollWidth")
        m_client_w = mobile_page.evaluate("() => document.documentElement.clientWidth")
        print(f"Mobile: scrollWidth={m_scroll_w}, clientWidth={m_client_w}")
        shot4 = output_dir / "snap_mobile_light.png"
        mobile_page.screenshot(path=str(shot4), full_page=False)
        print(f"Captured: {shot4}")
        assert m_scroll_w <= m_client_w + 1, f"Mobile horizontal overflow detected! {m_scroll_w} > {m_client_w}"

        browser.close()
        print("[SUCCESS] All Playwright HTML visual verifications passed!")


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent.parent
    report_html = project_root / "korea" / "report" / "LG_SC_Korea_ROI_Report.html"
    snap_dir = project_root / "korea" / "report" / "snapshots"
    verify_html(report_html, snap_dir)

