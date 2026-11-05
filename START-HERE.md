# LDSAMRA dashboard - start here

Public call-out statistics and map for the Lake District Search & Mountain
Rescue Association, updated nightly from the LDSAMRA call-out log.
Repository: https://github.com/wasdale-mrt/LDSAMRA-Dashboard (public).
Website: https://wasdale-mrt.github.io/LDSAMRA-Dashboard/ (once switched on).

Set up 1 November 2026 by Lee Tunstall with Claude. Same pattern as
`wasdale-mrt/Wasdale-Stats`, but the source is the LDSAMRA workbook, not D4H.

## How it works

1. The statistics officer fills in `LDSAMRA_Call_out_log.xlsx` in the shared
   OneDrive folder `LDSAMRA - Statistics` (Lee's personal OneDrive for now).
   That is the only job. Nobody needs GitHub for this.
2. Each night a GitHub Actions job fetches the workbook with the OneDrive key,
   works out the figures, and publishes the dashboard.
3. No laptop needs to be on.

The workbook is downloaded into the job's temporary folder, read, and deleted.
It is never committed, never uploaded and never published. Only totals and
the map points go on the website.

## What the dashboard reads from the workbook

It finds sheets and columns by **name**, not position. Moving sheets or
columns around needs no change here. Renaming any of these does:

| Sheet | Columns used |
|---|---|
| `Export – totals` | Year, MonthNo, Team, Metric, Value |
| `Export – detail` | Year, MonthNo, Dimension, Category, Value |
| `Callouts` | ID, Date, Time, Year, Month no, Location, Grid ref, Root cause, Activity |
| `Deployments` | Callout ID, Team |

The workbook's own formulas are a different matter: inserting or moving
columns inside the workbook can break its Summary and Export sheets. See the
handover notes in the private `ldsamra-stats` repository before rearranging.

## Decisions (1 Nov 2026)

- **All breakdowns are public and live**, including injury, medical, age band
  and sex (Lee's decision). They are counts only.
- **Air outcome and Team role are not shown.**
- **Headline is 999 calls** (819 for Jan-Oct 2026). The North Wales drone job
  on 29 June 2026 (Source = Other) is not a 999 call, so it is left out of
  that figure, as in the workbook. It still shows under "Who made the 999 call".
- **Time of day** is worked out from the Callouts sheet's Time column (C).
  The workbook's own export counts Jan-Aug 2026 twice; this avoids that.
- **Injured vs Avoidable**: Injured = Injured, Medical Emergency, Ambulance
  Assist, Body Recovery. Every other root cause is Avoidable (same as the old
  master workbook).
- **Map popups** show ID, month and year, place, cause, activity and teams.
  No exact date or time, no notes, no police references, nothing about the
  casualty.
- **Grey dots** on the 2026 map are call-outs from before September 2026,
  brought across from the old records, which kept root causes only as
  monthly totals. The page explains this.
- **Kirkby Stephen, January 2026, 4,495 team hours** is correct (a large
  search). Not a typo.
- Older years: main figures from 2019, team hours from 2024, breakdowns from
  2025, map from 2026.

## Highest recorded year box (added 5 Nov 2026)

A box beside the other big numbers, and a dotted line on the running total
chart. Same idea as the Wasdale MRT stats page.

- **What it shows:** the full year before this one with the most 999 calls,
  that year's total, and "At this point in YEAR: X. This year: Y." Once this
  year is higher than that year's total, it says "This year (Y) has now gone
  past YEAR." instead.
- **Worked out each night** in `tools/build_stats.py` (`highest_year`), never
  typed in. A tie goes to the later year. A year only counts once December
  has figures.
- **For LDSAMRA as a whole only**, on 999 calls. Not per team (Lee, 5 Nov 2026).
- **"At this point" means to the end of the same month** as this year's latest
  figures (for example Jan-Oct in both years). Years before 2026 are stored as
  monthly totals, so a day-by-day comparison is not possible. This matches
  the other boxes.
- **Data starts in 2019.** No earlier year was busier (Lee, 5 Nov 2026).
- **The dotted line** is black (white in dark mode). It is not drawn when the
  highest year is last year, because last year's grey line is already there.
  The dashed red line is still the projection. The legend and the note under
  the chart name both.
- **No full years yet:** the box and the line are hidden.
- The box and line show only for the latest year, not when an older year is
  picked.

**Wording rules.** We want fewer call-outs, not more, so this must never read
like a goal. Never call it a "record", a "target" or something to "beat". No
progress bar and no "X more to go". Keep it neutral and factual. Anyone
changing the wording on the page should keep to this.

## A new year

The workbook's export sheets follow the yellow year cell on the Summary sheet
(B4). Each January:

1. Finish December's entries and team hours, and build the annual report.
2. Change B4 to the new year. Until then, the new year's call-outs are not
   counted on the dashboard, and the page says the new figures will appear
   shortly (the nightly log also warns).

Nothing is lost when B4 moves on. Every finished year is saved by the nightly
job in `archive/<year>.json` (totals and map dots only, the same as the
website shows) and used whenever the workbook no longer has it. While the
workbook still has a year, the workbook wins and the saved copy is updated,
so late corrections are kept. To correct a year after B4 has moved on, set
B4 back to that year for one night, or edit its archive file.

## Files

| Path | What it is |
|---|---|
| `site/index.html` | The dashboard. Reads `data/stats.json` and `data/callouts.json`. Same look as the Wasdale stats page. |
| `tools/build_stats.py` | The nightly script. Reads the workbook and writes the two JSON files. Prints counts only. |
| `tools/osgrid.py` | Turns OS grid references into map positions. Works offline. |
| `.github/workflows/nightly.yml` | The nightly job, about 02:23 each night. Also runs by hand, or when files change. |
| `archive/` | Finished years, saved by the nightly job. Totals and map dots only. |

Test without OneDrive, from the workbook's CSV exports:

```
python tools/build_stats.py --totals Totals.csv --details Details.csv
```

## The OneDrive key

The job reads OneDrive with **rclone**. Its settings file (with the key in it)
is saved as a GitHub secret called `RCLONE_CONFIG`. The remote inside it must
be called `onedrive`.

The key can read the whole of Lee's OneDrive, not just the one folder. It is
only ever used to fetch the workbook. Move to an LDSAMRA account when their
IT is sorted: make a new key, replace the secret, and update the `WORKBOOK`
path at the top of the workflow if the folder name changes.

### Renewing the key

Microsoft refresh tokens last 90 days, and the job does not save the
refreshed one, so the key lapses about 90 days after it was last made.
**Renew it every 2 months.** Made 1 Nov 2026, so first renewal by about
20 Dec 2026, then about every 2 months after each renewal. If it does lapse,
the nightly job fails and GitHub emails Lee. On the laptop:

1. Open the rclone folder, click the address bar, type `cmd`, press Enter.
2. Type `rclone config reconnect onedrive:` and press Enter. Sign in when the
   browser opens.
3. Type `rclone config file` and press Enter. Open that file in Notepad and
   copy everything.
4. GitHub > LDSAMRA-Dashboard > Settings > Secrets and variables > Actions >
   `RCLONE_CONFIG` > Update. Paste, then Update secret.
5. Actions tab > Nightly stats > Run workflow.

## Visitor numbers

The page counts visits with GoatCounter (free, no cookies, no personal data).
See them at https://ldsamra.goatcounter.com (Lee's login). Visits from
browsers with ad blockers may not be counted.

## Rules

- Never put the key, or any secret, in a file here.
- Never commit the workbook or any CSV export. `.gitignore` blocks `.xlsx`.
- No names, notes, police references or per-person casualty details anywhere
  in this repository or on the website.
- The Actions log is public: print counts only.

## Working with Lee (for a new Claude chat)

- Lee is dyslexic: plain words, short steps, British English.
- Spell instructions out in full every time.
- New to GitHub: every change ends with GitHub Desktop - a **Summary** line
  and a short **Description**, then **Commit**, then **Push origin**.
- Lee keeps to-dos in Google Tasks. When a job is agreed for later, end the
  reply with one line: "Add to Google Tasks: [short task name]".
