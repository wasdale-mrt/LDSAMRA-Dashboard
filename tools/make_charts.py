"""
LDSAMRA report charts - saves the dashboard's charts as pictures for the annual report.

Runs in the nightly job, after build_stats.py. It opens the dashboard in a hidden
browser in report mode (index.html?report=YEAR), shows each chart named in
site/report-charts.js one at a time, and saves it as a PNG. The report builder
fetches them from the website for the year it is building.

Which years:
  - The latest year (the one in the yellow cell B4 on the workbook's Summary
    sheet) is drawn again every night, so late figures from the teams are
    picked up. Saved in site/charts/<year>/ only (not kept in the repository).
  - Finished years, from 2025 (when the breakdowns start), are drawn once and
    kept in charts/<year>/ in the repository, so the report stays a fixed
    record. To draw a finished year again, delete its folder in charts/, or run
    with --redraw <year>.

Only totals are drawn, the same as the website shows.

    python tools/make_charts.py                  # the nightly job
    python tools/make_charts.py --redraw 2025    # draw 2025 again
"""

import argparse
import datetime as dt
import functools
import http.server
import json
import shutil
import socketserver
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
KEPT = ROOT / "charts"          # finished years, kept in the repository
FIRST_YEAR = 2025               # breakdowns start in 2025, so report charts do too
WIDTH = 760                     # page width in CSS pixels; pictures are twice this


def serve(folder):
    """A small local web server for the site folder (the page needs http, not file://)."""
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    srv = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(folder)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def draw_year(page, port, year, out, fixed):
    """Save every chart for one year into the folder 'out'. Returns the manifest, or None."""
    page.goto(f"http://127.0.0.1:{port}/?report={year}", wait_until="domcontentloaded")
    page.wait_for_function("window.REPORT_READY || window.REPORT_ERROR", timeout=60000)
    err = page.evaluate("window.REPORT_ERROR || null")
    if err:
        print(f"{year}: no charts ({err})")
        return None
    info = page.evaluate("window.REPORT_INFO")
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    charts, skipped = [], []
    for name in info["charts"]:
        r = page.evaluate("n => reportChart(n)", name)
        if not r.get("ok"):
            skipped.append({"name": name, "why": r.get("why", "")})
            continue
        file = f"{len(charts) + 1:02d}_{name}.png"
        page.locator(".card.shot").screenshot(path=str(out / file))
        charts.append({"file": file, "name": name, "caption": r["caption"]})
    m = info["months"]
    manifest = {
        "year": year,
        "months": m,                                   # last month with figures, 12 = whole year
        "complete": all(m.get(k) == 12 for k in ("calls", "deployments", "hours")),
        "fixed": fixed,                                # True once the year is no longer the latest
        "made": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d"),
        "figuresUpdated": info.get("updated"),
        "charts": charts,
        "skipped": skipped,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    note = f", skipped: {', '.join(s['name'] for s in skipped)}" if skipped else ""
    print(f"{year}: {len(charts)} charts, figures to month {m['calls']}{' (fixed)' if fixed else ''}{note}")
    return manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--redraw", type=int, action="append", default=[], help="draw this finished year again")
    a = ap.parse_args()

    stats = json.loads((SITE / "data" / "stats.json").read_text(encoding="utf-8"))
    latest = int(stats["latest"]["year"])
    years = [int(y) for y in stats["years"] if FIRST_YEAR <= int(y) <= latest]
    to_draw = []                                      # (year, folder, fixed)
    for y in years:
        if y == latest:
            to_draw.append((y, SITE / "charts" / str(y), False))
        elif y in a.redraw or not (KEPT / str(y) / "manifest.json").exists():
            to_draw.append((y, KEPT / str(y), True))

    if to_draw:
        from playwright.sync_api import sync_playwright
        srv = serve(SITE)
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={"width": WIDTH, "height": 900},
                                        device_scale_factor=2, color_scheme="light")
                for y, out, fixed in to_draw:
                    draw_year(page, srv.server_address[1], y, out, fixed)
                browser.close()
        finally:
            srv.shutdown()

    # Put the kept (finished) years on the website too.
    done = []
    for y in years:
        src = KEPT / str(y)
        if y != latest and (src / "manifest.json").exists():
            dst = SITE / "charts" / str(y)
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
        if (SITE / "charts" / str(y) / "manifest.json").exists():
            done.append(y)
    (SITE / "charts").mkdir(exist_ok=True)
    (SITE / "charts" / "index.json").write_text(json.dumps({"years": done, "latest": latest}), encoding="utf-8")
    print("Report charts on the website for: " + (", ".join(map(str, done)) or "none"))


if __name__ == "__main__":
    sys.exit(main())
