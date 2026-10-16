# Replay the synthetic target-discovery demo

Use Python 3.12. From this folder:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-ui.txt
python -m streamlit run streamlit_app.py
```

On Windows use `py -3.12 -m venv .venv` and `.venv\Scripts\Activate.ps1`. Open the localhost URL printed by Streamlit. Installing dependencies needs internet access. Reading the bundled cases does not need a key or network access.

## Follow the guided case

The app opens **Guided demo** on the saved `demo / demo-A002` case. No workspace or assessment selection is needed.

1. **Why investigate?** The target hypothesis and the earlier E07 cell-loss concern explain why another test was needed.
2. **What did we learn?** The saved chart shows the two effect estimates and provisional threshold. Shared donors and unresolved specificity limit the conclusion to a next experimental step.
3. **What was decided?** Read the Who does what? panel beside the saved decision and rationale. Inspect the saved agent report in its separate expander to see the interpretation, citations and challenger findings. The report is explicitly scripted, not live reasoning.
4. **What happens next?** Read the antibody-specific request, simulated needs-information reply and next owner.

Use **Next**, **Back**, or the step names. **Start again** returns to the first step. Supporting detail stays collapsed until you choose to inspect it. Navigation is read-only and does not generate reports or make model calls.

If the saved case is missing, changed or stale, the guide explains the problem instead of recreating records or presenting a current approval. The three-minute label is an approximate route length, not a verified speaking time.

## Explore the full workbench

Choose **Explore the workbench** at the top. It retains all original views: Decision, Evidence & prediction, Challenge & review, Specialist handoff, and Ask the evidence assistant. The main `demo` run is preselected when available. Workspace selectors, alternative outcomes, source records, review/follow-up controls, exports and full report provenance remain available.

The six main cases and two bundled reference workspaces are unchanged. Reports are explicitly scripted offline tests, not live-model evaluations. Reviews and handoffs are simulated; no experiment has been ordered and no message has been sent.

For a read-only replay, use navigation and expanders only. Full-workbench review, follow-up, handoff and import controls deliberately write local records when submitted. Optional AI features require your own credentials and may incur costs. Never commit keys or `.streamlit/secrets.toml`.

If `TARGET_DEMO_WORKSPACE` is set, the app opens the full workbench on that explicit workspace. Selecting Guided demo always shows the bundled saved case, not the custom workspace.

To create another fresh offline replay without overwriting the supplied records:

```sh
python -m scripts.seed_public_demo --output public-replay-new --bundled-reference
```

Choose **Other local directory** in the UI and enter `public-replay-new/demo-runs`. Timestamps and generated follow-up identifiers differ; scientific calculations are the same. No model or retrieval calls are made by this command.
