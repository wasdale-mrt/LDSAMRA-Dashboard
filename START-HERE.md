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

## Files

| Path | What it is |
|---|---|
| `site/index.html` | The dashboard. Reads `data/stats.json` and `data/callouts.json`. Same look as the Wasdale stats page. |
| `tools/build_stats.py` | The nightly script. Reads the workbook and writes the two JSON files. Prints counts only. |
| `tools/osgrid.py` | Turns OS grid references into map positions. Works offline. |
| `.github/workflows/nightly.yml` | The nightly job, about 02:23 each night. Also runs by hand, or when files change. |

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

Microsoft keys for personal accounts expire. If the nightly job fails with a
token or sign-in error (GitHub emails Lee), on the laptop:

1. Open the rclone folder, click the address bar, type `cmd`, press Enter.
2. Type `rclone config reconnect onedrive:` and press Enter. Sign in when the
   browser opens.
3. Type `rclone config file` and press Enter. Open that file in Notepad and
   copy everything.
4. GitHub > LDSAMRA-Dashboard > Settings > Secrets and variables > Actions >
   `RCLONE_CONFIG` > Update. Paste, then Update secret.
5. Actions tab > Nightly stats > Run workflow.

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
