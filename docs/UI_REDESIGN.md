# SignGuard 3.1 interface redesign

Rebuilt all seven workspace pages with one shared design system: deep green navigation, neutral surfaces, clear typography, restrained status colours, line icons, responsive grids and visible keyboard focus. No external font requests are required.

The overview emphasises document analysis and controlled demonstrations. Document intake separates preview/settings from the outcome; result tabs distinguish findings, digital signatures, revisions and coverage. The lab uses a choose/generate/compare/analyse flow. The evidence viewer separates methods and keeps all-page and pair records available. Evaluation emphasises measured trade-offs and failures. Reports distinguish PDF summaries from structured JSON evidence. The guided presentation keeps navigation available throughout.

The verification engine and research metrics are unchanged. Public shared-audit restrictions remain in place.

Verified:

- All seven pages render and survive navigation reruns.
- Overview action buttons navigate to their destinations.
- All six lab scenarios generate, analyse and retain their expected verdicts.
- Evidence tabs render after a scenario analysis.
- Guided baseline verification works with a real signed control.
- PDF/JSON export controls render with a real analysis result.
- Three public-demo privacy/regeneration tests pass.
- Browser inspection covers the overview and document intake, including a synthetic PDF upload, completed analysis, result tabs and export controls.

Deploy through the existing `streamlit-deploy` branch using `streamlit_app.py`. Streamlit Community Cloud should redeploy on a new commit when configured to follow that branch. The public service cannot be inspected from this workspace because the destination is blocked by its network policy.
