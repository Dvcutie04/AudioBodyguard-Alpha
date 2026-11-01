# Offline picture-row bounds

October 28, 2026. This phone-independent continuation repairs the offline
picture companion. Android's latest delivered app remains 0.38/build 41;
iPhone/iPad source remains 0.38.0/build 1. Neither native renderer is changed.

## Reproduced picture defect

Fire TV setup picture 2 put `2 → Home — hold about 10` on the first line of a
184-unit remote-button target. With its two 12-unit side insets, the target has
160 units for text. The declared 16-unit Arial-compatible measurement was
198.5 units. The rendered first line visibly extended beyond the white target.

The shared offline row renderer now wraps the number, arrow and label together.
Its narrow remote targets use a shorter line than Roku menu rows. The Fire TV
label retains the complete `Home — hold about 10 seconds` action across two
lines. A row requiring more than two lines raises a generation error rather
than silently dropping the end of the label. Source instructions, choices,
chronology, model qualifications and native catalogs retain their existing data.

Two regression cases first failed on tests-only source
`e79e86bfec79a48b4d53f68269b22a20e73057a6`: the actual Fire TV target overflow
and silent truncation of an overlong target. The Python job in
[run 40714991458](https://github.com/Dvcutie04/AudioBodyguard-Alpha/actions/runs/40714991458)
reported both failures alongside 2,123 passing tests and 19 passing subtests.

## Scope of verification

The repaired catalog generates all 51 routes and 436 pictures. All 22 focused
setup-guide checks pass locally, including the two new regressions. A separate
geometry pass inspected all 666 drawn rows and every SVG text element against
the canvas, using Liberation Sans Regular as the Arial-compatible measurement.
No row or canvas overflow remained in that pass. Before/after Fire TV renders
were inspected. Font substitution and actual phone viewing still require the
owner's review; these measurements are not a universal firmware or font claim.

The PDF companion is a review copy of the same catalog, with one numbered
picture per page, an index and the catalog's official source links. It is not
an iPhone app or a signed installation. Its page/contents and rendered layouts
are checked separately before saving. Exact final CI, PDF identity and the
draft PR belong to the delivery receipt.

This is a presentation repair using already reviewed content. No new backend
research, OS API, permission, audio work, hardware observation or production
authority is added. Physical TV pairing, N2b–N5 and signed iPhone distribution
remain pending.
