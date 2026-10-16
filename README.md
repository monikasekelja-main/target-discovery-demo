# Target Discovery Workbench

A runnable scientific decision-workflow demonstration: inspect evidence, challenge a hypothesis, record a scoped review and prepare a specialist handoff.

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

The app opens directly into a **four-step guided demo**: why investigate, what we learned, what was decided and what happens next. Use **Next** to follow the saved case; **View supporting detail** reveals evidence and provenance. Choose **Explore the workbench** for all scenarios, review controls and the optional evidence assistant. See the [saved replay guide](REPLAY_DEMO.md). Optional AI features require your own credentials and may incur costs.

## Repository layout

```text
streamlit_app.py          Thin Streamlit launcher
target_discovery/        Application package
   workflow/             Deterministic calculations, contracts and persistence
   agents/               Bounded analyst/challenger roles and providers
   evidence/             Read-only evidence assistant, retrieval and figures
   review/               Human reviews, rationale checks and follow-ups
   ui/                   Streamlit views and presentation helpers
   cli/                  Workflow and agent command-line entry points
tests/                  Offline regression tests
scripts/                Fixture generation, validation and replay setup
docs/                   Architecture, scientific assumptions and usage guides
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
