# Dashboard audit — 26 November 2026

## Reproduced issue

Presentation step 4 displayed only a raw absolute pixel difference. Scenarios A and B produced an all-black image because their rendered pages were identical; scenario C changed about 0.0131% of the representative page, making its full-page raw difference hard to see. Scenarios D, E and F had no signed baseline. These are distinct evidence states, not interchangeable image failures.

## Fixes

- Shared revision evidence in Presentation, Document analysis and Evidence viewer now shows signed/current pages, a red change overlay and a zoomed region when detected boxes exist. Raw difference and threshold images remain available for changed pages. Measurements and exported evidence are unchanged.
- Unchanged pages, missing signed baselines, unavailable comparisons and reconstruction errors receive explicit explanations.
- Step 4 provides a post-signing revision example (Scenario C) and keeps the selected scenario label consistent.
- Changing a presentation scenario invalidates its previous result and label. Loading the signed demo updates document identity and clears prior results.
- Unavailable signature-region and ELA evidence receives an explanation rather than an empty presentation tab. The evidence viewer avoids an empty ELA quality selector.
- Unavailable static inspection is no longer described as a clean inventory.
- The signed baseline scenario description distinguishes passing signature mathematics from its untrusted self-signed test certificate.

## Verification scope

The regression tests use the actual Streamlit entry point and page renderers through AppTest. All nine pages are exercised empty and with all six scenario results. Additional checks operate the guided walkthrough, generate/analyse all six lab scenarios, inspect image elements and the changed-region crop, invalidate stale results, compare samples, save reviews, export/verify packages, change source-inclusion options and clear session state. Failed processing and missing optional evidence are also exercised.

AppTest has no native file-upload action. Upload boundaries are injected with byte streams while actual parsing, workers, result rendering and retry/settings controls execute. Exports are checked through emitted controls, package verification and the existing report-format tests. This does not claim verification of every browser file-picker or download-manager behavior.

The production Streamlit URL returned an HTTP 403 CONNECT-tunnel denial from the workspace network. Live production rendering, Cloud redeployment, mobile layout and production media delivery could not be verified. A passing local test suite is not proof that the hosted deployment is current.

## Final result

Full regression suite: **143 passed**, zero failures, 152.94 seconds. This includes 24 new dashboard/display regression cases and the existing 119 tests.
