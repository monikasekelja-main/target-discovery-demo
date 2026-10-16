# Replay the synthetic target-discovery demo

Use Python 3.12. From this folder:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-ui.txt
python -m streamlit run streamlit_app.py
```

On Windows use `py -3.12 -m venv .venv` and `.venv\Scripts\Activate.ps1`. Open the localhost URL printed by Streamlit. Installing dependencies needs internet access. Reading the bundled cases does not need a key or network access.

Select **My saved runs**, **demo**, **demo-A002**. If your shell sets `TARGET_DEMO_WORKSPACE`, select My saved runs explicitly. All target-specific data and predictions are fictional.

1. **Evidence & prediction**: select E07 under Inspect a source. The earlier secretion reduction was confounded by cell loss.
2. **Decision**: show 32% and 29% reductions and their intervals above the provisional threshold. Both methods share the same eight donors. The recommendation is replication and specificity work, not validation.
3. **Challenge & review**: select **offline-public-01**. This is a scripted plumbing demonstration, not a live model evaluation. Read the saved evidence limitations and explicit offline warning. The original private live captures are not distributed.
4. **Decision**: show the scripted approval. It follows a scripted deferral and scope-clarification follow-up. No new experimental work is claimed. Approval covers only the next action, and is explicitly simulated.
5. **Specialist handoff**: show the request asking whether antibody blockade can reproduce expression reduction and the simulated **NEEDS_INFORMATION** reply. No email, chat message or experiment order is sent.

The other five runs show initial, contrary, cell-loss, disagreement and imprecise outcomes. The two bundled reference workspaces also contain fresh scripted examples.

For a read-only replay, use navigation and expanders only. Review, follow-up, handoff and import controls deliberately write local records when submitted. Optional AI features require your own credentials and can incur costs; they are not needed for this route. Never commit keys or `.streamlit/secrets.toml`.

To create another fresh offline replay without overwriting the supplied records:

```sh
python seed_public_demo.py --output public-replay-new --bundled-reference
```

Choose **Other local directory** in the UI and enter `public-replay-new/demo-runs`. Timestamps and generated follow-up identifiers differ; scientific calculations are the same. No model or retrieval calls are made by this command.
