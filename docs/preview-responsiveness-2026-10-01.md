# Preview responsiveness — October 1, 2026

The user's new lag report follows the iOS Appetize preview built from `8a58426726928b5510e8986601f5cb3deff93359`. This increment removes verified avoidable work in guide navigation and changes the browser preview to an optimized Release build. It does not assign every reported delay to the app or claim an installed-device latency improvement.

## Findings and changes

| Finding in the supplied preview | Change | Verification |
|---|---|---|
| Both iOS tutorials and illustrated guides placed a changing `.id` on the entire ScrollView. Each Next, Back and help transition replaced that scrolling subtree. | Preserve the scrolling view and its state. Explicitly return to the content's top anchor without an animation when the step changes. Focus the current heading using the new step key. | UI regressions compare a guide-lifetime identifier across TV/route selection, Next, Back and mismatch help, and assert that the next heading is visible at the top after scrolling the previous step. |
| iOS `resumeIndex` decoded the entire saved JSON during view construction, sometimes repeatedly for the introduction and footer. Saving through `@AppStorage` also invalidated the view after navigation had already changed it. | Decode once per presented guide into a cached store. Resume reads a dictionary. Persist only changed, valid bookmarks; persistence does not publish a second view update. Keep the existing storage key and format. | Unit regressions exercise round trips, finishing one guide without erasing another, unchanged writes, invalid indices, voice exclusion and malformed/oversized storage. Existing native resume/finish walkthrough remains required. |
| The iOS tutorial added its Next button only after a selection, changing the footer layout while the user was interacting. | Keep Next present and disabled until the required choice is made. Use one instruction/selection label in the footer. | UI regression checks that the selected TV button retains its position, Next remains gated, and a Back transition retains the prior choice. |
| The Appetize artifact was compiled in Debug with Swift `-Onone`. | Run the iOS UI walkthrough and package the ARM simulator app in Release, with explicit `-O` and whole-module compilation. | Successful Release UI tests and ARM build are required before delivery. Archive CRC, bundle metadata and architecture are checked afterward. |
| Android illustrated setup rebuilt its header, progress bar and navigation controls for every picture. Posted focus/scroll callbacks did not check whether their step was still current. | Retain those controls; update their text, visibility and progress. Discard scroll/focus callbacks for an older render or a closing Activity. Changed picture content still updates normally. | Existing Android walkthrough covers Next, local resume, finish, rotation, largest font, voice help and account-approval diagrams. Before/after frame evidence remains collected. |

The iOS Next action also rejects a callback captured for a different route or step. No artificial sleep, click debounce delay, new network operation, discovery or account request is added to guide navigation.

## Evidence boundaries

The optional `--aqss-trace-navigation` launch argument exposes only an ephemeral guide-lifetime UUID as the scroll view's accessibility value. It collects no user content, stores no telemetry and grants no additional capability. The regression checks establish that the guide subtree stays alive; they are not touch-to-photon measurements.

Appetize streams a remotely running simulator. This task has no trace from the user's specific Appetize session, so network/video-stream delay remains unmeasured. The prior hosted Android timing samples were small, and some included corrupt completion fields; they cannot establish this iOS report's cause. Preserve raw adverse evidence and withhold unqualified summaries as described in `latency-follow-up-2026-09-30.md`.

Under the research charter, UI rendering, instruction completion, device authorization, control execution and independently verified physical response remain separate events. This app remains a read-only simulation. Local guide completion neither proves a TV connection nor opens the production actuation boundary. Installed-device latency, energy and physical-response qualification remain separate work.

Final native CI results, exact delivered revision and archive hash are recorded in draft PR #32. Relevant implementation guidance: [Apple: SwiftUI performance](https://developer.apple.com/documentation/Xcode/understanding-and-improving-swiftui-performance), [Apple: view identity](https://developer.apple.com/documentation/swiftui/view/id(_:)), [Appetize: configuration and server location](https://docs.appetize.io/javascript-sdk/configuration).
