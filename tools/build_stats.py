"""
LDSAMRA nightly stats - READ ONLY.

Reads the LDSAMRA call-out log and writes two public files:
  site/data/stats.json     - the figures for the dashboard (site/index.html)
  site/data/callouts.json  - one dot per call-out for the map

Rules (see START-HERE.md):
  - The workbook is only read. It is never changed and never published.
  - Only totals go into stats.json. The map file holds, per call-out: ID,
    month and year, place, position, root cause, activity and teams.
    No notes, no police references, no exact dates or times, and nothing
    about the casualty.
  - The GitHub Actions log is public, so the log prints counts only.

Normal use (the nightly job):
    python tools/build_stats.py --xlsx LDSAMRA_Call_out_log.xlsx

For a test from exported files:
    python tools/build_stats.py --totals Totals.csv --details Details.csv --points map-points.json
"""

import argparse
import collections
import csv
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import osgrid  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site" / "data"

ALL = "LDSAMRA (all)"
TEAM_ORDER = [
    "Cockermouth", "COMRU", "Coniston", "Duddon & Furness", "Kendal", "Keswick",
    "Kirkby Stephen", "Langdale & Ambleside", "Patterdale", "Penrith", "Wasdale",
    "LDSAMRA Dogs", "LDSAMRA Drones",
]
# Root causes counted as "Injured" in the Injured vs Avoidable split.
# Everything else is "Avoidable". Same grouping as the old master workbook.
INJURED_GROUP = {"Injured", "Medical Emergency", "Ambulance Assist", "Body Recovery"}
# Cells in the export that are placeholders, not categories.
JUNK = {"", "0", "—", "-", "None recorded"}
# Breakdowns only recorded from this year and month (shown as a note on the page).
RECORDED_FROM = {"Outcome": (2026, 9), "Handover": (2026, 9)}
# Days with a call-out: each date counts once, however many call-outs or teams
# (the old report's Day of the week chart). Worked out from the Callouts sheet's
# Date column, so it starts in 2026. Lee, 8 Nov 2026.
DAYS = "Days with a call-out"
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
# Breakdowns in the export that the dashboard does not show (Lee, 1 Nov 2026).
NOT_SHOWN = {"Air outcome", "Team role"}


# ---------------------------------------------------------------- reading

def rows_from_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.reader(f))


def rows_from_sheet(wb, name):
    ws = wb[name]
    return [["" if v is None else v for v in r] for r in ws.iter_rows(values_only=True)]


def table(rows):
    """Skip the title lines above the 'Year' header row; return dicts."""
    for i, r in enumerate(rows):
        if r and str(r[0]).strip() == "Year":
            head = [str(h).strip() for h in r]
            out = []
            for r2 in rows[i + 1:]:
                if not r2 or str(r2[0]).strip() == "":
                    continue
                out.append(dict(zip(head, r2)))
            return out
    raise SystemExit("Could not find the 'Year' header row in an export sheet.")


def num(v):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def find_sheet(wb, *starts):
    for name in wb.sheetnames:
        low = name.lower().replace("–", "-")
        if any(low.startswith(s) for s in starts):
            return name
    raise SystemExit(f"No sheet starting {starts} in the workbook.")


# ---------------------------------------------------------------- figures

def build_totals(rows):
    calls = collections.defaultdict(lambda: [0] * 12)
    deps = collections.defaultdict(lambda: collections.defaultdict(lambda: [0] * 12))
    hours = collections.defaultdict(lambda: collections.defaultdict(lambda: [0] * 12))
    for r in table(rows):
        y, m = int(num(r["Year"])), int(num(r["MonthNo"]))
        if not (1 <= m <= 12):
            continue
        team, metric, v = str(r["Team"]).strip(), str(r["Metric"]).strip(), num(r["Value"])
        if metric == "999 calls" and team == ALL:
            calls[y][m - 1] += v
        elif metric == "Deployments" and team != ALL:
            deps[y][team][m - 1] += v
        elif metric == "Team hours" and team != ALL:
            hours[y][team][m - 1] += v
    return calls, deps, hours


def build_detail(rows):
    det = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(lambda: [0] * 12)))
    order = collections.defaultdict(list)
    for r in table(rows):
        y, m = int(num(r["Year"])), int(num(r["MonthNo"]))
        dim, cat, v = str(r["Dimension"]).strip(), str(r["Category"]).strip(), num(r["Value"])
        if cat in JUNK or dim in NOT_SHOWN or not (1 <= m <= 12):
            continue
        if cat not in order[dim]:
            order[dim].append(cat)
        det[dim][y][cat][m - 1] += v
    return det, order


def last_month(series12):
    """1-12: the last month with anything in it, or 0 if the year is empty."""
    for i in range(11, -1, -1):
        if series12[i]:
            return i + 1
    return 0


def plain(d):
    """defaultdicts -> plain dicts, years as strings, whole numbers as int."""
    if isinstance(d, dict):
        return {str(k): plain(v) for k, v in d.items()}
    if isinstance(d, list):
        return [plain(v) for v in d]
    if isinstance(d, float) and d.is_integer():
        return int(d)
    if isinstance(d, float):
        return round(d, 1)
    return d


def highest_year(calls, this_year, this_month):
    """The busiest full year before this_year, by 999 calls. A tie goes to the later year.

    Neutral wording only on the page: never "record", "target" or "beat"
    (see START-HERE.md). Old years are monthly totals, so "at this point"
    means up to the end of the same month as this year's latest figures.
    Returns None if there is no full year yet.
    """
    full = [y for y in calls if y < this_year and last_month(calls[y]) == 12]
    if not full:
        return None
    best = max(full, key=lambda y: (sum(calls[y]), y))
    running, t = [], 0
    for v in calls[best]:
        t += v
        running.append(t)
    so_far = sum(calls[this_year][:this_month])
    return {
        "year": best,
        "thisYear": this_year,
        "month": this_month,
        "total": running[-1],
        "atThisPoint": running[this_month - 1] if this_month else 0,
        "thisYearSoFar": so_far,
        "gonePast": so_far > running[-1],
        "running": running,
    }


def assemble(calls, deps, hours, det, order, hour_override=None):
    years = sorted(y for y in calls if sum(calls[y]) > 0)
    latest = years[-1]
    latest_month = last_month(calls[latest])

    teams = [t for t in TEAM_ORDER if any(t in deps[y] or t in hours[y] for y in years)]
    teams += sorted({t for y in years for t in list(deps[y]) + list(hours[y])} - set(teams))

    def keep_years(d):
        return {y: d[y] for y in years if y in d}

    lm = {
        "calls": {y: last_month(calls[y]) for y in years},
        "deployments": {y: last_month([sum(v[i] for v in deps[y].values()) for i in range(12)]) for y in years if y in deps},
        "hours": {y: last_month([sum(v[i] for v in hours[y].values()) for i in range(12)]) for y in years if y in hours},
    }
    lm["hours"] = {y: m for y, m in lm["hours"].items() if m}

    if hour_override:
        for y, cats in hour_override.items():
            det["Hour of call"][y] = cats

    # Drop categories that are empty in every year, and empty years.
    detail, dorder = {}, {}
    for dim, by_year in det.items():
        yrs = {y: {c: v for c, v in cats.items() if sum(v)} for y, cats in by_year.items() if y in years}
        yrs = {y: c for y, c in yrs.items() if c}
        if not yrs:
            continue
        detail[dim] = yrs
        used = {c for cats in yrs.values() for c in cats}
        dorder[dim] = [c for c in order[dim] if c in used] + sorted(used - set(order[dim]))

    # Injured vs Avoidable, worked out from Root cause.
    if "Root cause" in detail:
        split = {}
        for y, cats in detail["Root cause"].items():
            inj, avo = [0] * 12, [0] * 12
            for c, v in cats.items():
                tgt = inj if c in INJURED_GROUP else avo
                for i in range(12):
                    tgt[i] += v[i]
            split[y] = {"Injured": inj, "Avoidable": avo}
        detail["Injured vs Avoidable"] = split
        dorder["Injured vs Avoidable"] = ["Injured", "Avoidable"]

    return {
        "updated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d"),
        "latest": {"year": latest, "month": latest_month},
        "years": years,
        "teams": teams,
        "calls": keep_years(calls),
        "deployments": keep_years(deps),
        "hours": {y: hours[y] for y in years if y in lm["hours"]},
        "lastMonth": lm,
        "detail": detail,
        "detailOrder": dorder,
        "recordedFrom": {k: {"year": v[0], "month": v[1]} for k, v in RECORDED_FROM.items()},
        "highest": highest_year(calls, latest, latest_month),
    }


# ---------------------------------------------------------------- map

def map_points(records):
    """records: dicts with id, year, month, place, grid, cause, activity, teams."""
    out, unread = [], 0
    for r in records:
        if not r.get("grid"):
            continue
        p = osgrid.parse_point(r["grid"])
        if not p or not (53.9 <= p[0] <= 55.2 and -3.9 <= p[1] <= -2.0):
            unread += 1
            continue
        out.append({
            "id": r["id"], "y": int(r["year"]), "m": int(r["month"]),
            "lat": p[0], "lon": p[1],
            "place": str(r.get("place") or "").strip(),
            "cause": str(r.get("cause") or "").strip(),
            "activity": str(r.get("activity") or "").strip(),
            "teams": r.get("teams") or [],
        })
    return out, unread


def hour_of(t):
    """The Time column (C) -> hour 0-23, or None if blank."""
    if isinstance(t, (dt.time, dt.datetime)):
        return t.hour
    if isinstance(t, (int, float)):
        return int(t * 24) % 24
    return None


def hours_from_file(path):
    """Test only: {"2026-1": [24 counts], ...} -> hour-of-call breakdown."""
    raw = json.load(open(path, encoding="utf-8"))
    out = collections.defaultdict(lambda: collections.defaultdict(lambda: [0] * 12))
    for ym, counts in raw.items():
        y, m = (int(v) for v in ym.split("-"))
        for h, c in enumerate(counts):
            if c:
                out[y][f"{h:02d}:00"][m - 1] += c
    return {y: dict(sorted(c.items())) for y, c in out.items()}


def date_of(v):
    """The Date column -> a date, or None. Excel dates, or text as dd/mm/yyyy."""
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    if isinstance(v, str):
        for f in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y"):
            try:
                return dt.datetime.strptime(v.strip(), f).date()
            except ValueError:
                pass
    return None


def days_from_dates(dates):
    """{year: set of dates} -> {year: {weekday: [12 monthly counts]}}, each date once."""
    out = {}
    for y, ds in dates.items():
        cats = {d: [0] * 12 for d in WEEKDAYS}
        for d in ds:
            cats[WEEKDAYS[d.weekday()]][d.month - 1] += 1
        out[y] = cats
    return out


def records_from_workbook(wb):
    """Callouts + Deployments sheets -> map records, hour-of-call counts and call-out dates."""
    dep = collections.defaultdict(set)
    head = None
    for r in wb["Deployments"].iter_rows(values_only=True):
        if head is None:
            if r and "Callout ID" in r:
                head = list(r)
            continue
        d = dict(zip(head, r))
        if d.get("Callout ID") and d.get("Team"):
            dep[str(d["Callout ID"]).strip()].add(str(d["Team"]).strip())

    recs, hours = [], collections.defaultdict(lambda: collections.defaultdict(lambda: [0] * 12))
    dates = collections.defaultdict(set)
    head = None
    for r in wb["Callouts"].iter_rows(values_only=True):
        if head is None:
            if r and r[0] == "ID":
                head = [str(h).strip() if h else "" for h in r]
            continue
        d = dict(zip(head, r))
        if not d.get("ID") or not d.get("Date") or not d.get("Year"):
            continue
        y, m = int(d["Year"]), int(d["Month no"])
        day = date_of(d.get("Date"))
        if day and day.year == y:
            dates[y].add(day)
        hr = hour_of(d.get("Time"))
        if hr is not None:
            hours[y][f"{hr:02d}:00"][m - 1] += 1
        recs.append({
            "id": str(d["ID"]), "year": y, "month": m,
            "place": d.get("Location"), "grid": d.get("Grid ref"),
            "cause": d.get("Root cause"), "activity": d.get("Activity"),
            "teams": sorted(dep.get(str(d["ID"]).strip(), [])),
        })
    # Hour of call straight from the Callouts sheet's Time column (C), in hour order.
    hours = {y: dict(sorted(c.items())) for y, c in hours.items()}
    return recs, hours, days_from_dates(dates)


# ---------------------------------------------------------------- finished years
#
# The workbook's export sheets only carry the year set in the yellow cell on
# Summary (B4), plus 2019-2025 from the History sheets. When B4 moves on to a
# new year, last year would drop out. So once a year is finished, its figures
# are saved in archive/<year>.json in this repository, and used whenever the
# workbook no longer has them. While the workbook still has a year, the
# workbook wins and the saved copy is refreshed, so late corrections are kept.

ARCHIVE = ROOT / "archive"


def nonzero(series):
    return any(series or [])


def year_snapshot(y, calls, deps, hours, det, order, hour_override, points):
    detail = {}
    for dim, by_year in det.items():
        cats = {c: v for c, v in by_year.get(y, {}).items() if nonzero(v)}
        if cats:
            detail[dim] = cats
    if hour_override and y in hour_override:
        detail["Hour of call"] = {c: v for c, v in hour_override[y].items() if nonzero(v)}
    return plain({
        "year": y,
        "calls": calls[y],
        "deployments": {t: v for t, v in deps.get(y, {}).items() if nonzero(v)},
        "hours": {t: v for t, v in hours.get(y, {}).items() if nonzero(v)},
        "detail": detail,
        "order": {dim: [c for c in order.get(dim, []) if c in cats] for dim, cats in detail.items()},
        "points": [p for p in points if p["y"] == y],
    })


def save_finished_years(this_year, calls, deps, hours, det, order, hour_override, points):
    """Save every finished year the workbook still holds. Returns years saved or changed."""
    ARCHIVE.mkdir(exist_ok=True)
    changed = []
    for y in sorted(calls):
        if y >= this_year or last_month(calls[y]) != 12:
            continue
        snap = year_snapshot(y, calls, deps, hours, det, order, hour_override, points)
        path = ARCHIVE / f"{y}.json"
        text = json.dumps(snap, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            path.write_text(text, encoding="utf-8")
            changed.append(y)
    return changed


def fill_from_archive(calls, deps, hours, det, order, hour_override, points):
    """Use saved years for anything the workbook no longer has. Returns years used."""
    used = []
    if not ARCHIVE.exists():
        return used
    for path in sorted(ARCHIVE.glob("*.json")):
        snap = json.loads(path.read_text(encoding="utf-8"))
        y, took = int(snap["year"]), False
        if not nonzero(calls.get(y)):
            calls[y] = list(snap["calls"]); took = True
        if not any(nonzero(v) for v in deps.get(y, {}).values()) and snap["deployments"]:
            deps[y] = collections.defaultdict(lambda: [0] * 12, snap["deployments"]); took = True
        if not any(nonzero(v) for v in hours.get(y, {}).values()) and snap["hours"]:
            hours[y] = collections.defaultdict(lambda: [0] * 12, snap["hours"]); took = True
        for dim, cats in snap["detail"].items():
            if dim == "Hour of call" and hour_override and y in hour_override:
                continue  # the Callouts sheet still has this year
            if not any(nonzero(v) for v in det[dim].get(y, {}).values()):
                det[dim][y] = collections.defaultdict(lambda: [0] * 12, cats); took = True
                for c in snap["order"].get(dim, cats):
                    if c not in order[dim]:
                        order[dim].append(c)
        if not any(p["y"] == y for p in points) and snap["points"]:
            points.extend(snap["points"]); took = True
        if took:
            used.append(y)
    return used


def waiting_year(this_year, calls, recs):
    """Call-outs logged for this year that the export does not count yet (B4 not moved on)."""
    n = sum(1 for r in recs if int(r["year"]) == this_year)
    if n and not nonzero(calls.get(this_year)):
        return {"year": this_year, "count": n}
    return None


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx")
    ap.add_argument("--totals")
    ap.add_argument("--details")
    ap.add_argument("--points")
    ap.add_argument("--hours", help="test only: hour counts per month")
    ap.add_argument("--today", help="test only: pretend today is this date (YYYY-MM-DD)")
    a = ap.parse_args()
    today = dt.date.fromisoformat(a.today) if a.today else dt.datetime.now(dt.timezone.utc).date()

    hour_override, days = None, {}
    if a.xlsx:
        import openpyxl
        wb = openpyxl.load_workbook(a.xlsx, data_only=True, read_only=True)
        trows = rows_from_sheet(wb, find_sheet(wb, "export - totals", "export – totals"))
        drows = rows_from_sheet(wb, find_sheet(wb, "export - detail", "export – detail"))
        recs, hour_override, days = records_from_workbook(wb)
    elif a.totals and a.details:
        trows, drows = rows_from_csv(a.totals), rows_from_csv(a.details)
        recs = json.load(open(a.points, encoding="utf-8")) if a.points else []
        hour_override = hours_from_file(a.hours) if a.hours else None
    else:
        ap.error("give --xlsx, or --totals and --details")

    calls, deps, hours = build_totals(trows)
    det, order = build_detail(drows)
    for y, cats in days.items():          # days with a call-out, from the Callouts sheet
        det[DAYS][y] = collections.defaultdict(lambda: [0] * 12, cats)
    if days:
        order[DAYS] = list(WEEKDAYS)
    points, unread = map_points(recs)
    if hour_override is not None:
        hour_override = dict(hour_override)

    saved = save_finished_years(today.year, calls, deps, hours, det, order, hour_override, points)
    from_archive = fill_from_archive(calls, deps, hours, det, order, hour_override, points)
    waiting = waiting_year(today.year, calls, recs)

    stats = assemble(calls, deps, hours, det, order, hour_override)
    stats["waiting"] = waiting

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "stats.json").write_text(json.dumps(plain(stats), separators=(",", ":")), encoding="utf-8")
    (OUT / "callouts.json").write_text(json.dumps(points, separators=(",", ":")), encoding="utf-8")

    # Counts only: the Actions log is public.
    L = stats["latest"]
    print(f"Years {stats['years'][0]}-{stats['years'][-1]}, latest data {L['month']:02d}/{L['year']}")
    print(f"{L['year']} 999 calls so far: {int(sum(stats['calls'][L['year']]))}")
    print(f"Breakdowns: {len(stats['detail'])}. Map dots: {len(points)} of {len(recs)} call-outs"
          f" ({unread} grid refs could not be read)")
    hi = stats["highest"]
    if hi:
        print(f"Highest recorded year: {hi['year']} ({int(hi['total'])}); at this point {int(hi['atThisPoint'])}, "
              f"{hi['thisYear']} so far {int(hi['thisYearSoFar'])}")
    else:
        print("Highest recorded year: none yet (no full years)")
    if hour_override:
        print("Hour of call worked out from the Callouts sheet's Time column.")
    if days:
        print("Days with a call-out: " + ", ".join(f"{y} {sum(sum(v) for v in c.values())} days" for y, c in sorted(days.items())))
    if saved:
        print("Finished years saved or updated in archive/: " + ", ".join(map(str, saved)))
    if from_archive:
        print("Taken from archive/ (no longer in the workbook): " + ", ".join(map(str, from_archive)))
    if waiting:
        print(f"::warning::{waiting['count']} call-outs are logged for {waiting['year']}, but the export "
              f"sheets do not count {waiting['year']} yet. Change the yellow year cell on the Summary "
              f"sheet (B4) to {waiting['year']}.")


if __name__ == "__main__":
    main()
