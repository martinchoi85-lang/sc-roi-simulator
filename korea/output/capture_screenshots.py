import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

def main():
    html_path = Path("korea/report/LG_SC_Korea_ROI_Report.html").resolve()
    url = f"file:///{html_path.as_posix()}"
    out_dir = Path("korea/output")
    out_dir.mkdir(parents=True, exist_ok=True)
    brain_dir = Path(r"C:\Users\marti\.gemini\antigravity\brain\9f1371e6-d2c2-4ac9-be60-cc73f1f9dfd2")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 1400})
        page.goto(url)
        page.wait_for_timeout(1500)

        # 1. Appendix A: Core 72 3 occupants AWHP, winter weekday
        page.evaluate("""() => {
            S.hp = 'c72_3';
            S.heat = 'awhp';
            S.dayKind = 'winter_weekday';
            renderAll();
        }""")
        page.wait_for_timeout(1000)

        page.click('#a-day-tabs button[data-k="winter_weekday"]')
        page.wait_for_timeout(1000)

        # Wrap Appendix A target elements for screenshot
        page.evaluate("""() => {
            const h3 = document.querySelector('#sec-a h3');
            const tabs = document.querySelector('#a-day-tabs');
            const sub = document.querySelector('#a-day-sub');
            const chart = document.querySelector('#c-day');
            const wrap = document.createElement('div');
            wrap.id = 'wrap-appendix-a';
            wrap.style.background = '#ffffff';
            wrap.style.padding = '20px';
            wrap.style.borderRadius = '8px';
            h3.parentNode.insertBefore(wrap, h3);
            wrap.appendChild(h3);
            wrap.appendChild(tabs);
            wrap.appendChild(sub);
            wrap.appendChild(chart);
        }""")
        page.wait_for_timeout(500)

        shot_a = out_dir / "appendix_a_winter_weekday_c72_3p_awhp.png"
        el_a = page.query_selector('#wrap-appendix-a')
        el_a.screenshot(path=str(shot_a))
        print(f"Captured Appendix A: {shot_a}")

        if brain_dir.exists():
            (brain_dir / shot_a.name).write_bytes(shot_a.read_bytes())

        # 2. Appendix B: ESS lowest 7 days
        page.evaluate("""() => {
            document.querySelector('#sec-b').scrollIntoView();
        }""")
        page.wait_for_timeout(1000)

        page.evaluate("""() => {
            const h3 = Array.from(document.querySelectorAll('#sec-b h3')).find(el => el.textContent.includes('ESS 충전 상태'));
            const sub = document.querySelector('#b-soc-sub');
            const chart = document.querySelector('#c-b-soc');
            const wrap = document.createElement('div');
            wrap.id = 'wrap-appendix-b';
            wrap.style.background = '#ffffff';
            wrap.style.padding = '20px';
            wrap.style.borderRadius = '8px';
            h3.parentNode.insertBefore(wrap, h3);
            wrap.appendChild(h3);
            wrap.appendChild(sub);
            wrap.appendChild(chart);
        }""")
        page.wait_for_timeout(500)

        shot_b = out_dir / "appendix_b_soc7_lowest.png"
        el_b = page.query_selector('#wrap-appendix-b')
        el_b.screenshot(path=str(shot_b))
        print(f"Captured Appendix B: {shot_b}")

        if brain_dir.exists():
            (brain_dir / shot_b.name).write_bytes(shot_b.read_bytes())

        browser.close()

if __name__ == "__main__":
    main()
