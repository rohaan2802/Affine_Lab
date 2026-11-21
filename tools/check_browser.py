"""Real browser checks. Install dev extras and `playwright install chromium`.

Windows uses installed Edge when present; other systems use Playwright Chromium.
The test starts only local servers and never requests Gemini.
"""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import tempfile
import threading
from playwright.sync_api import sync_playwright
from affine_lab.crypto import Key, decrypt, encrypt
from affine_lab.analysis import rank_keys
from affine_lab.providers import ReplayProvider
from affine_lab.web import Dashboard

ROOT = Path(__file__).resolve().parents[1]


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def copyfile(self, source, outputfile):
        try:
            super().copyfile(source, outputfile)
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass


def main():
    http = ThreadingHTTPServer(("127.0.0.1", 0), partial(Quiet, directory=str(ROOT)))
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    temp = tempfile.TemporaryDirectory()
    app = Dashboard(ReplayProvider(), http_port=0, tcp_port=0, output=Path(temp.name))
    app.backend.__enter__()
    dash = threading.Thread(target=app.http.serve_forever, daemon=True)
    dash.start()
    checks = []
    errors = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                channel="msedge" if sys.platform == "win32" else None, headless=True
            )
            page = browser.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            base = f"http://127.0.0.1:{http.server_port}"
            for width, columns in [(1440, 3), (820, 2), (390, 1), (320, 1)]:
                for theme in ["light", "dark"]:
                    page.set_viewport_size({"width": width, "height": 900})
                    page.goto(base)
                    page.locator(".figure-card").first.wait_for()
                    if page.locator("html").get_attribute("data-theme") != theme:
                        page.locator("#theme").click()
                    assert page.evaluate(
                        "document.documentElement.scrollWidth<=innerWidth"
                    ), f"Overflow at {width}/{theme}"
                    assert page.locator(".figure-card").count() == 24
                    assert (
                        page.locator("#gallery").evaluate(
                            "e=>getComputedStyle(e).gridTemplateColumns.split(' ').length"
                        )
                        == columns
                    )
                    if width <= 1180:
                        page.locator("#menu").click()
                        assert page.locator("#nav").is_visible()
                        assert page.locator("#close-menu").is_visible()
                        page.locator('#nav a[href="#evidence"]').click()
                        assert not page.locator("#nav").is_visible()
                    page.locator(".figure-open").first.click()
                    assert page.locator("#viewer").is_visible()
                    page.keyboard.press("ArrowRight")
                    assert page.locator("#viewer-title").inner_text().startswith("02")
                    page.keyboard.press("ArrowLeft")
                    assert page.locator("#viewer-title").inner_text().startswith("01")
                    page.locator("#zoom").click()
                    assert "zoomed" in page.locator("#stage").get_attribute("class")
                    page.locator("#zoom").click()
                    page.locator("#next").click()
                    page.locator("#previous").click()
                    page.locator("#stage").evaluate(
                        "e=>{for(const [name,x] of [['touchstart',250],['touchend',100]]){const event=new Event(name);Object.defineProperty(event,'changedTouches',{value:[{clientX:x}]});e.dispatchEvent(event);}}"
                    )
                    assert page.locator("#viewer-title").inner_text().startswith("02")
                    page.keyboard.press("Escape")
                    assert not page.locator("#viewer").is_visible()
                    assert page.locator(".figure-open").first.evaluate(
                        "e=>e===document.activeElement"
                    )
                    page.locator("#search").fill("PCAP")
                    assert 0 < page.locator(".figure-card").count() < 24
                    page.locator("#search").fill("nothing-matches-xyz")
                    assert page.locator("#empty").is_visible()
                    page.locator("#search").fill("")
                    page.get_by_role("button", name="Source", exact=True).click()
                    assert page.locator(".figure-card").count() == 2
                    page.get_by_role("button", name="All", exact=True).click()
                    page.locator("#cipher-form button[type=submit]").click()
                    assert "a=7, b=6" in page.locator("#cipher-output").inner_text()
                    assert page.locator("#candidate-rows tr").count() == 5
                    assert page.locator("#frequency-chart rect").count() == 52
                    with page.expect_download() as download:
                        page.locator("#download-result").click()
                    exported = json.loads(
                        Path(download.value.path()).read_text(encoding="utf-8")
                    )
                    assert (
                        exported["key"]["a"] == 7
                        and len(exported["top_candidates"]) == 5
                    )
                    page.locator("#copy-result").click()
                    page.locator("#export-status").filter(has_text="Result").wait_for()
                    page.locator('[data-tab="ubuntu"]').click()
                    assert page.locator("#ubuntu").is_visible()
                    page.locator("#reference-purpose").scroll_into_view_if_needed()
                    page.wait_for_timeout(100)
                    page.wait_for_function(
                        "document.querySelector('#nav a[href=\"#reference\"]').classList.contains('active')"
                    )
                    assert page.locator("#backtop").is_visible()
                    if width <= 1180:
                        page.locator("#menu").click()
                    page.locator('#nav a[href="#author"]').click()
                    page.wait_for_function(
                        "document.querySelector('#nav a[href=\"#author\"]').getAttribute('aria-current') === 'location'"
                    )
                    assert page.locator('#nav a.active').count() == 1
                    page.locator("#backtop").click()
                    page.wait_for_function("scrollY<50", timeout=5000)
                    page.wait_for_function(
                        "document.querySelector('#nav a[href=\"#overview\"]').classList.contains('active')"
                    )
                    if width in [1440, 390]:
                        (ROOT / "runs").mkdir(exist_ok=True)
                        page.screenshot(
                            path=str(ROOT / f"runs/site-{width}-{theme}.png")
                        )
                    checks.append(
                        {
                            "viewport": width,
                            "theme": theme,
                            "columns": columns,
                            "passed": True,
                        }
                    )
            # Compare browser arithmetic against Python for every valid key.
            vectors = []
            for a in [1, 3, 5, 7, 9, 11, 15, 17, 19, 21, 23, 25]:
                for b in range(26):
                    vectors.append([a, b, encrypt("Affine Lab 123 — AaZz!", Key(a, b))])
            assert page.evaluate(
                "rows=>rows.every(([a,b,c])=>AffinePlayground.transform('Affine Lab 123 — AaZz!',a,b)===c && AffinePlayground.transform(c,a,b,true)==='Affine Lab 123 — AaZz!')",
                vectors,
            )
            sample = page.locator("#cipher-input").input_value()
            py = rank_keys(sample)
            js = page.evaluate("text=>AffinePlayground.recover(text)", sample)
            assert all(
                (a.a, a.b) == (b["a"], b["b"]) and abs(a.score - b["score"]) < 1e-7
                for a, b in zip(py, js)
            )
            # file:// compatibility for the portable static presentation.
            page.goto((ROOT / "index.html").as_uri())
            page.locator(".figure-card").first.wait_for()
            assert page.locator(".figure-card").count() == 24
            # Actual local dashboard, with strict CSP left enabled.
            for width in [1440, 820, 390, 320]:
                for theme in ["light", "dark"]:
                    page.set_viewport_size({"width": width, "height": 900})
                    page.goto(f"http://127.0.0.1:{app.http.server_port}")
                    page.locator(".result").first.wait_for()
                    assert page.locator(".result").count() == 5
                    if page.locator("html").get_attribute("data-theme") != theme:
                        page.locator("#theme").click()
                    assert page.evaluate(
                        "document.documentElement.scrollWidth<=innerWidth"
                    ), f"Dashboard overflow {width}/{theme}"
            page.set_viewport_size({"width": 1440, "height": 900})
            page.goto(f"http://127.0.0.1:{app.http.server_port}")
            page.locator("#all").click()
            page.locator("#message").filter(has_text="PASS").wait_for(timeout=10000)
            assert page.locator(".history-row").count() == 1
            (ROOT / "runs").mkdir(exist_ok=True)
            page.screenshot(path=str(ROOT / "runs/dashboard-capture.png"))
            page.locator(".result").first.screenshot(
                path=str(ROOT / "runs/dashboard-result.png")
            )
            assert not errors, errors
            browser.close()
        report = {
            "static_layouts": checks,
            "dashboard_layouts": 8,
            "arithmetic_keys": 312,
            "candidate_score_parity": True,
            "gallery_controls": True,
            "file_uri": True,
            "dashboard_tcp_run": True,
            "javascript_errors": errors,
        }
        (ROOT / "reports/browser_checks.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
        print(
            "PASS: 16 layout/theme combinations, gallery controls, 312-key JS/Python parity, file://, dashboard TCP run"
        )
    finally:
        http.shutdown()
        http.server_close()
        thread.join()
        app.close()
        dash.join()
        app.backend.__exit__()
        temp.cleanup()


if __name__ == "__main__":
    main()
