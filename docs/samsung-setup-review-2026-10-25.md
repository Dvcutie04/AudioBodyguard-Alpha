# Samsung setup review — October 25, 2026

The owner checked 0.31 and reported that Samsung setup was confusing. This
revision continues the existing 0.32 code as 0.32.1 (Android build 33) so the
updated installer can be distinguished. No specific Samsung model or failing
screen was supplied; this review fixes observable guide problems and retains
model/region differences.

The former Samsung entry asked users to choose an OK or PIN guide before the
TV had displayed its request. Samsung now opens one neutral SmartThings guide.
At the actual approval picture, TV shows a PIN switches directly to the PIN
picture. Back returns to the same OK picture. The TV code is read on the TV
and entered in SmartThings on the phone. No sample PIN or code length is
implied. The existing route IDs, prefix and step indices remain compatible
with old bookmarks; the active pairing variant replaces its sibling bookmark.

The phone part now opens a five-picture check of the TV already added in
SmartThings, instead of leading with generic phone Wi-Fi menus. TV is missing
opens the pairing guide, and Back returns to the phone check. Optional
phone-specific Wi-Fi help remains available. A phone-only completion cannot
advance the TV part. Completing either guide still changes local learning
progress only; Home remains Connection not verified.

The shared catalog generates identical guidance for Android, iPhone and the
offline companion. The companion now depicts Samsung approval/PIN on a TV;
the phone PIN-entry picture remains separate. The repeated TV selection in
SmartThings is clarified: first choose the device type, then Samsung's TV
category. Existing Google Home and Alexa paths remain separate.

## Evidence and scope

The existing Samsung sources were checked again on October 25:

- [Samsung SmartThings TV setup](https://www.samsung.com/us/support/answer/ANS10005262/)
  supports the same-network/account prerequisites, category/discovery order,
  and model-dependent TV approval or PIN. This is manufacturer guidance,
  not a measurement or universal model-compatibility result.
- [Samsung assistant linking](https://www.samsung.com/us/support/answer/ANS10006871/)
  keeps Google and Alexa authorization separate from TV pairing.
- [Samsung model lookup](https://www.samsung.com/ca/support/home-appliances/find-the-model-and-serial-numbers-for-your-samsung-device/)
  is regional guidance; exact model menus still require comparison.

The three local regressions first failed for the two-entry selector, missing
Samsung phone companion and phone-shaped offline TV approval pictures. They
pass after repair. Core tests add a phone-part-only completion case on each
native platform. Focused native walkthroughs cover OK/PIN navigation, Back,
PIN resume, Android rotation, phone checking and help, and large text on iPhone.
Exact source-bound results and APK identity belong to this revision's draft PR.
The earlier output inventory and existing input tools remain in the candidate.
No TV-control integration, permission, calibrated output or protection authority
is added. Signed iPhone installation and N2b–N5 remain pending.
