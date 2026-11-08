// Charts for the LDSAMRA annual report, in the order they appear.
//
// The nightly job saves each one as a picture (charts/<year>/01_..., 02_...),
// and the report builder fetches them for the year it is building.
//
// To drop a chart: delete its line.
// To change the order: move the lines up or down.
// To bring one back: copy its name from the list at the bottom.
// Keep the quote marks and the comma at the end of each line.

window.REPORT_CHARTS = [
  "calls_running",          // 999 calls through the year, last 3 years
  "deployments_running",    // Team deployments through the year, last 3 years
  "calls_by_month",         // 999 calls each month, this year and last
  "every_year",             // 999 calls and team deployments, every year
  "call_source",            // Who made the 999 call
  "deployments_by_team",    // Deployments by team
  "team_hours",             // Team hours
  "root_cause",             // Root cause
  "injured_avoidable",      // Injured or avoidable
  "activity",               // Activity
  "injury",                 // Injury
  "medical",                // Medical
  "age_band",               // Age band
  "sex",                    // Sex
  "air_support",            // Air support
  "fatalities",             // Fatalities
  "hour_of_call",           // Time of day the call came in
  "day_of_week",            // Call-outs by day of the week (each call-out once)
  "days_with_callout",      // Days with a call-out (each day once; from 2026)
];

// Also available, not used at the moment: "outcome", "handover"
