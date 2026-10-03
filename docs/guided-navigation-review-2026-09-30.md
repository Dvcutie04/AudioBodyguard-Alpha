# Guided navigation and responsiveness review — 2026-09-30

The user reported jitter, hard-to-find pictures and too many ambiguous choices. The supplied TCL photo shows Roku Settings with a left menu and right submenu, not Google TV. It does not expose a model number or firmware version.

## Changes

- TCL now asks Roku / Google-Android / Fire TV before listing relevant tasks. The two new Roku tasks find Network > About and System > About in five pictures each. The catalog now has 37 guides and 326 steps. Settings illustrations use the photographed menu geometry; unknown About values remain labeled diagrams, with no invented IP address or model.
- Every instruction explicitly refers to the numbered highlight and explains that the user acts on the TV or official app before tapping Next here. Platform choices and onboarding entry cards include visible pictograms.
- Both native guides retain an unfinished step locally and offer Resume, restart and a shortcut for users already in Settings. Completion clears the saved position. Saved position is not connection evidence.
- Android choice changes now update existing buttons and the footer instead of replacing the whole reading view. Returning to the app retains the existing tutorial tree rather than rebuilding it again. This removes two unnecessary redraw and scroll-reset paths.

## Evidence and limits

The missing Roku path regression was observed failing, then passed after the catalog change. Native walkthroughs exercise platform choice, the matched Network/About pictures, close/reopen/resume and truthful completion. The review adds a simulator navigation timing trace and Android frame statistics for diagnosis. XCTest timings include automation overhead, and emulator graphics statistics do not establish latency on installed phones or a physical protection path below 200 ms.

Official paths: [TCL System information](https://support.tcl.com/en_US/62989-tcl-roku-tv/where-to-find-the-system-information-of-your-tcl-roku-tv), [TCL model lookup](https://support.tcl.com/en_US/common-questions-TVs/model-number-on-your-tcl-tv), [Roku TV manual, Network settings](https://image.roku.com/c3VwcG9ydC1B/Roku-TV-User-Guide-12-0en-US.pdf), printed page 114 / PDF page 122.

Existing TV/provider illustrations remain simplified where no exact model/firmware screenshot is available. The catalog's documented model examples do not establish pixel-identical artwork across firmware, countries and languages. To qualify exact artwork for the user's television, the next evidence needed is its System > About model/software screen. No personal room photograph is committed to the public repository.

Build, walkthrough, screenshot and package evidence is recorded in PR #32 after validation. Production control and handoff barriers remain closed.
