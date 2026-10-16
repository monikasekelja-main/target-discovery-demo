# Architecture

The application package is organised by responsibility. `workflow` owns deterministic calculations, typed contracts, versioned source snapshots and SQLite state. `agents` adds bounded advisory reports without granting approval. `evidence` provides read-only retrieval and explanation. `review` records explicit local decisions and follow-ups. `ui` renders the workbench; `cli` exposes command-line operations.

The root Streamlit launcher executes the UI module on each rerun. This keeps Streamlit lifecycle behaviour intact. Imports use explicit package names; no path injection or compatibility aliases are required. `target_discovery.paths.PROJECT_ROOT` locates the accompanying fixtures independently of the working directory.

## Saved-record bindings

Scientific briefs retain input-content hashes. Workflow freshness also compares the actual source files listed in `IMPLEMENTATION_FILES`; advisory reports additionally bind `AGENT_FILES` and prompt version. Paths in those lists now point to relocated files. The shared `paths.py` resolver is also fingerprinted because it determines which source assets are read.

The layout change deliberately invalidates old implementation bindings. No old hashes are silently rewritten, and stale-record detection is retained. The bundled public cases were rebuilt through the existing offline seeder after restructuring. These remain explicitly scripted demonstrations; review IDs and scientific assessments are preserved, while execution timestamps, follow-up UUIDs and implementation bindings are newly generated. Original copies are retained outside this distribution.

Real operator reviews or live reports from an older checkout must not be rebased automatically. Keep the matching old source to replay them, or use the normal explicit refresh and review workflow with the new implementation.

## Development

Run commands from the repository root using `python -m ...`. Tests use standard-library unittest discovery; fixture/setup utilities live in `scripts`. Runtime assets and saved replays remain repository-level data, so the supported distribution is a full checkout or ZIP, not an asset-free wheel.
