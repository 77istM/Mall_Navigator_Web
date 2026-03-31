# Phase 4 QA Playbook

## Integration tests
- Run: `pytest tests/test_integration_flow.py`
- Verifies flow: select start -> route -> generate directions.

## E2E tests (Playwright)
- Install browsers: `playwright install`
- Run app: `streamlit run app.py`
- Run tests:
  - `set E2E_BASE_URL=http://localhost:8501`
  - `pytest tests/e2e/test_streamlit_journey.py`

## Load testing (k6)
- Run app: `streamlit run app.py`
- Run load script:
  - `set LOAD_BASE_URL=http://localhost:8501`
  - `k6 run tests/load/streamlit_smoke.js`

## Accessibility audit checklist (WCAG 2.1 AA)
- Keyboard-only navigation across all controls.
- Focus indicator visible for buttons, inputs, and map interactions.
- Non-color cues for state messaging (success/warning/info).
- Verify text alternatives for map markers and route instructions.
- Test with NVDA and JAWS on key flows.

## Browser compatibility matrix
- Chrome latest: core navigation + map click + product save
- Edge latest: core navigation + live mode panel
- Firefox latest: search, directions, outdoor map
- Safari latest: search and path rendering (manual verification)
