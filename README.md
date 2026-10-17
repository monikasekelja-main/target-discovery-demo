# Target Discovery Workbench

An offline demonstration of a proposed workflow: patient single-cell data → in-silico perturbation → intervention and cell-state nomination → biological test. The patient study has not been run.

**DEMO-R1 and all target-specific data are fictional.** Bundled reviews and follow-ups are scripted; bundled agent reports use an offline test provider. This demonstrates workflow behaviour, not biological validation or live AI quality.

## Run the saved demo

Use Python 3.12 and run these commands from the repository root:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-ui.txt
python -m streamlit run streamlit_app.py
```

On Windows, use `py -3.12 -m venv .venv` and `.venv\Scripts\Activate.ps1`.
Installing dependencies requires internet access; replaying the saved cases needs no API key.

The app opens into **Patient-study demo**, a four-step offline rehearsal: define the study, test the prediction, review the experiment and agree the next action. Expand **Explore a different scenario or route** to try nine illustrative scenarios and both sequential and parallel biology routes. No patient data or foundation model is used, and no API key is needed.

Human review in this new path is **session-only rehearsal**: it never changes saved assessments or authorizes execution. Review approval is bound to the study, scenario and route. See [the patient-study guide](PREDICTIVE_DEMO.md).

The original **Optional assay example** remains available as an optional, independent synthetic assay example; its 32%/29% results are not outputs of the proposed patient study. **Explore the workbench** retains the original technical functionality, persistent reviews and optional AI features. Those optional features require your credentials and may incur costs. See the [original saved replay guide](REPLAY_DEMO.md).

## Repository layout

```text
streamlit_app.py          Thin Streamlit launcher
target_discovery/        Application package
   predictive/           Versioned study contracts and pure offline scenario replay
   workflow/             Deterministic calculations, contracts and persistence
   agents/               Bounded analyst/challenger roles and providers
   evidence/             Read-only evidence assistant, retrieval and figures
   review/               Human reviews, rationale checks and follow-ups
   ui/                   Streamlit views and presentation helpers
   cli/                  Workflow and agent command-line entry points
tests/                  Offline regression tests
scripts/                Fixture generation, validation and replay setup
docs/                   Architecture, scientific assumptions and usage guides
predictive_examples/    Illustrative patient-study manifest and nine scenarios
runtime/                Synthetic evidence, policy and frozen predictions
demo-runs/              Six saved public replay cases
recorded_examples/      Additional scripted reference workspaces
```

`schemas/`, `agent_schemas/`, `examples/` and `evaluation/` contain contracts and validation material. They are kept separate from runtime evidence. `ui_assets/` contains display-only programme context.

## Verify locally

```sh
python -m unittest discover -s tests -t .
python -m scripts.validate_contracts
python -m scripts.verify_public_replay
```

These checks use local fixtures and fake providers. No paid model calls are needed.

## Command-line workflow

```sh
python -m target_discovery.cli.demo --help
python -m target_discovery.cli.agent_demo --help
python -m scripts.seed_public_demo --output public-replay-new --bundled-reference
```

The seed command refuses to overwrite an existing directory. Run from a complete source checkout; a standalone wheel without the accompanying assets is not a supported distribution. `pyproject.toml` defines package metadata and optional editable-install CLI entry points; requirements files retain the pinned setup used for the demo.

## Read more

- [Architecture and source bindings](docs/architecture.md)
- [Scientific reference workflow](docs/reference_workflow.md)
- [Scientific assumptions and numerical rules](docs/numerical_reference.md)
- [Programme context and evidence boundaries](docs/programme_context.md)
- [Public-copy provenance](PUBLIC_RELEASE.md)
- [Guided demo changes and verification](GUIDED_DEMO_NOTES.md)
- [Earlier restructure changes](RESTRUCTURE_NOTES.md)

The handoff is a local simulation: no message is sent and no experiment is ordered. Shared-donor method agreement does not establish independent replication or antibody blockade equivalence.

### Optional live proposal questions

Open **Ask about this proposal → Live assistant (API)**. Offline examples remain the default. For live answers, set `OPENAI_API_KEY` in your local server environment, set `TARGET_PROPOSAL_MODEL` to a model available to your API account, and restart Streamlit. Do not paste or commit credentials.

Only clicking **Send to live assistant** makes a paid request. The assistant explains the current proposal and cannot change records, approve work or run experiments. See [proposal-chat boundaries](PREDICTIVE_DEMO.md#optional-live-proposal-chat) for context, limits and checks.
