# Streamlit slice 1: read-only workbench

Historical slice. See [slice 2](streamlit_slice2.md) for the current explicit review and local handoff controls.

Implemented 15 October 2026. Python 3.12 recommended. Tested with Streamlit 1.66.0,
Plotly 7.1.0 and the existing pinned Pydantic dependency.

## Launch

From the package's `decision-fixtures` directory, with your virtual environment active:

```bash
python -m pip install -r requirements-ui.txt
python -m streamlit run streamlit_app.py
```

Open the local URL printed by Streamlit. No API key is needed. This slice does not
call an LLM, perform a review, import an outcome, modify a run or create a handoff.

## Updating your existing project

Copy `streamlit_app.py`, `target_discovery/ui/ui_service.py`, `target_discovery/ui/ui_charts.py`, `requirements-ui.txt`,
`tests/test_ui.py` and the packaged `.streamlit/config.toml` into your existing project.
Keep your existing `demo-runs/` and virtual environment. Baseline workflow, agent
files and runtime fixtures are unchanged by this release. The theme config is
included in the ZIP; if not copied, Streamlit still runs with its default theme.

Alternatively, extract into a separate directory and use the workspace selector's
**Other local directory** option to point to your existing project's `demo-runs`
directory. That avoids copying or moving your saved runs. Select the directory
containing `workflow.sqlite3`, not the database file or an exported report directory.

## What to inspect

The default workspace is your local `demo-runs` if it exists. Otherwise the app
opens the bundled initial/supportive examples. A second bundled workspace contains
the reviewed antibody handoff. Bundled agent responses are explicitly scripted
offline captures, not live model reasoning.

1. **Decision:** hypothesis question, current evidence, fixed-code next action,
   saved review status, method-specific effect intervals and remaining uncertainty.
2. **Evidence & prediction:** source ledger, source/alias provenance, application
   manifest and separate frozen-signature plot. Unsupported source claims are visible
   as original source content, not endorsed conclusions.
3. **Challenge & review:** saved agent report for the selected assessment, live-versus-
   scripted origin, challenger findings and actual call/revision history. Nothing is
   generated when a report is absent. Old schema reports remain inspectable and stale
   bindings are prominently labelled.
4. **Specialist handoff:** an existing saved response if present; otherwise an honest
   empty state. Platform question summaries are illustrative, not specialist verdicts.

Select `test-cell-loss` in your own workspace to inspect the diagnostic-only result;
select `demo` to inspect the supportive result/handoff. Each is a separate saved run.
This slice supports manual run selection, not the planned side-by-side comparison
or guided four-minute replay.

The assessment selector includes history. The selected brief and its chart threshold
use their original policy snapshot. The Evidence view explicitly shows the run's latest
captured context, not a reconstructed historical context. Full original version
references remain in each selected brief. Historical assessments never show current
approval as effective.

“Report ready for review” does not mean target approval. Existing reviews apply to the
canonical reference brief, not to newly displayed agent prose. No new review receipt
or agent adoption is implemented in this read-only slice.

## Verification

```bash
python -m unittest discover -s tests -t .
```

100 tests passed: 84 existing tests and 16 UI tests. The UI tests exercise real Streamlit
AppTest navigation with temporary saved runs, including initial/metadata states,
cell-loss warning, saved handoff, missing/legacy/stale agent reports, historical policy
binding, and read-only database behavior. Navigation preserves database/report bytes
and does not invoke the model provider. Startup and HTTP response were checked.

Local browser QA completed on 15 October 2026 at a 1366 × 768 laptop viewport.
The existing local Streamlit server on port 8501 was reachable in the Codex browser;
a second launch using `.venv` confirmed that port was already occupied. All four
views were inspected in rendered screenshots, then checked again after layout edits.

The header, headings and spacing are compact; the supportive decision now shows
the question, next action and complete functional chart in the first screen. The
saved rationale remains directly below the chart. The threshold annotation was
moved above the plotting area after visual inspection found it overlapping KD-A.
The evidence context is summarized as text, with the full manifest still available
in its existing expander. Challenger checks wrap as bounded claim statements;
PASS is explicitly not proof of replication or modality equivalence.

Initial and supportive states used bundled agent runs; the specialist response
used the bundled reviewed handoff. No cell-loss saved run exists in this checkout,
so X104 was loaded through the existing workflow into an isolated temporary QA
database with a simulated setup review. No project saved run or approval changed.
The cell-loss warning and diagnostic chart were visually checked. Missing-handoff
and missing-workspace states were also checked in the browser.

At the initial QA pass, no saved live-model report was available. Its origin banner was checked with an
in-memory mocked report projection in AppTest, not claimed as live-model visual
verification. No model calls were made. The tests also cover scripted reports,
legacy/stale bindings and database/report byte preservation. A before/after hash
audit confirmed scientific code, fixtures, prompts and saved records were unchanged.

Selected screenshots: [supportive decision](visual-qa/supportive.png),
[cell-loss decision](visual-qa/cell-loss.png), and
[challenger boundaries](visual-qa/challenge.png). Long ledgers and detailed reports
still require scrolling; source claims remain fully inspectable through the existing
source selector. Mobile layouts and other browser engines were not signed off.

## Deliberately left for later slices

Review/amend/defer controls; agent-assisted review receipts; live model job launch;
guided recorded playback; side-by-side alternative-outcome comparison; complete
live correction-cycle verification; screen-share layout polish. The app already
shows saved records for these concepts without pretending to execute them.


## Workspace reconciliation (15 October 2026, follow-up)

The authoritative code and running server directory is
`<project-directory>`.
The original `demo-runs` directory is now available at that location and is the
selected UI data workspace (**My saved runs**). The existing default logic already
selects it when its database exists; no code/configuration change was needed.
All six expected runs are present: `demo`, `test-initial`, `test-contrary`,
`test-cell-loss`, `test-disagreement`, and `test-imprecise`.

Visually inspected `demo` / `demo-A002` / `live-02` at 1366 × 768. The UI shows
“Captured live LLM output — no call is running”, the stale-binding warning, and
the legacy-schema warning. Challenger cautions preserve same-donor limits and
exclude therapeutic blockade equivalence, modality feasibility and systemic safety.
The assessment content digest still matches. The binding differs in agent code
(`target_discovery/agents/agent_prompts.py`, `target_discovery/agents/agent_offline.py`, `target_discovery/agents/agent_layer.py`, `target_discovery/agents/agent_contracts.py`) and
prompt version (`bounded-evidence-roles-v1` versus installed v2).

Six saved live reports are available across five runs; all currently evaluate as
stale. `test-imprecise` has no saved agent report. None was regenerated. A recursive
before/after SHA-256 comparison confirmed every file in `demo-runs` unchanged.
No API calls, record moves, record recreation or UI controls were added.
Screenshots: [live origin and warnings](visual-qa/live-report-origin.png) and
[live challenger findings](visual-qa/live-report-findings.png).
