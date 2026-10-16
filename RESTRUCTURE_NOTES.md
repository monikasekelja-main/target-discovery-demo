# Repository restructure — review before GitHub update

GitHub has not been updated. The previous public-copy directory and its saved records remain untouched.

## What changed

- Reduced the root from 44 Python files to one four-line Streamlit launcher.
- Moved application code into `target_discovery/`, grouped into workflow, agents, evidence, review, UI and CLI packages. A conventional repository-root package keeps source-checkout use simple without import-path hacks.
- Moved 11 test modules into `tests/` with standard unittest discovery; maintenance and replay tools live in `scripts/`.
- Added `pyproject.toml` for package metadata, dependencies and optional editable-install entry points. Existing pinned requirements and the Streamlit launch command remain available.
- Replaced implicit sibling imports with explicit package imports. Centralised asset location in `target_discovery/paths.py` and fingerprinted that resolver.
- Updated CLI examples, test commands, architecture documentation and the README.

## Saved demo and provenance

Moving source files changes implementation hashes. Old approvals and advisory reports were not silently relabelled as current. The public replay was rebuilt using the existing offline seeder and its explicitly simulated reviews. It keeps the same nine runs, scenario choices, assessment/review IDs, scientific findings, review wording, follow-up sequence and simulated handoffs. Timestamps, follow-up UUIDs, implementation hashes, the derived reference implementation version and dependent record digests are new.

Compared all **16 saved assessments** across three workspaces: scientific content and runtime input hashes are identical; only implementation bindings and the derived reference version differ. Review content is identical except for its corresponding assessment digest. All runtime fixtures, evaluation material, schemas, programme-context assets and agent prompt text are byte-identical to the previous public copy.

No original human review or live-provider report was regenerated. The bundle contains only the already disclosed scripted public replay. Stale-record detection remains enabled.

## Verification

- **173 offline regression tests passed**, including CLI subprocess, rerun, stale-binding, review, follow-up and handoff checks.
- Contract validation passed: 35 typed JSON files, 16 schemas, 16 evidence records, eight experiment cases and four reference briefs.
- Replay check passed: nine runs across three workspaces, four views each. Provider, retrieval and network calls blocked; saved files unchanged by navigation.
- Extracted ZIP replay passed in a different directory: all nine runs and four views, with network and provider calls blocked.
- All databases pass integrity and foreign-key checks. Privacy and credential-pattern scans passed; the original public-copy manifest still matches.
- Browser inspection at **1366 × 768** confirms the supportive chart, current simulated approval and saved needs-information handoff render correctly.

No paid API calls were made. Windows/Linux, a fresh dependency download and optional editable installation were not tested. The supported distribution remains a complete source checkout or ZIP with its data assets; an asset-free wheel is not supported.

## File moves

| Previous root file | New location |
|---|---|
| `agent_contracts.py` | `target_discovery/agents/agent_contracts.py` |
| `agent_demo.py` | `target_discovery/cli/agent_demo.py` |
| `agent_layer.py` | `target_discovery/agents/agent_layer.py` |
| `agent_offline.py` | `target_discovery/agents/agent_offline.py` |
| `agent_prompts.py` | `target_discovery/agents/agent_prompts.py` |
| `agent_provider.py` | `target_discovery/agents/agent_provider.py` |
| `build_contract_fixtures.py` | `scripts/build_contract_fixtures.py` |
| `challenger_probe.py` | `target_discovery/agents/challenger_probe.py` |
| `contracts.py` | `target_discovery/workflow/contracts.py` |
| `decision_compiler.py` | `target_discovery/workflow/decision_compiler.py` |
| `demo.py` | `target_discovery/cli/demo.py` |
| `evaluate.py` | `target_discovery/workflow/evaluate.py` |
| `evidence_assistant.py` | `target_discovery/evidence/evidence_assistant.py` |
| `evidence_context.py` | `target_discovery/evidence/evidence_context.py` |
| `evidence_figures.py` | `target_discovery/evidence/evidence_figures.py` |
| `evidence_relevance.py` | `target_discovery/evidence/evidence_relevance.py` |
| `evidence_search.py` | `target_discovery/evidence/evidence_search.py` |
| `followup_service.py` | `target_discovery/review/followup_service.py` |
| `local_tools.py` | `target_discovery/workflow/local_tools.py` |
| `rationale_advisor.py` | `target_discovery/review/rationale_advisor.py` |
| `review_service.py` | `target_discovery/review/review_service.py` |
| `seed_public_demo.py` | `scripts/seed_public_demo.py` |
| `streamlit_app.py` | `target_discovery/ui/app.py` |
| `ui_charts.py` | `target_discovery/ui/ui_charts.py` |
| `ui_evidence_assistant.py` | `target_discovery/ui/ui_evidence_assistant.py` |
| `ui_followups.py` | `target_discovery/ui/ui_followups.py` |
| `ui_programme_context.py` | `target_discovery/ui/ui_programme_context.py` |
| `ui_reviews.py` | `target_discovery/ui/ui_reviews.py` |
| `ui_service.py` | `target_discovery/ui/ui_service.py` |
| `validate_contracts.py` | `scripts/validate_contracts.py` |
| `verify.py` | `tests/test_numerics.py` |
| `verify_advanced_probes.py` | `tests/test_advanced_probes.py` |
| `verify_advisor.py` | `tests/test_advisor.py` |
| `verify_agents.py` | `tests/test_agents.py` |
| `verify_contracts.py` | `tests/test_contracts.py` |
| `verify_evidence_assistant.py` | `tests/test_evidence_assistant.py` |
| `verify_evidence_relevance.py` | `tests/test_evidence_relevance.py` |
| `verify_followups.py` | `tests/test_followups.py` |
| `verify_public_replay.py` | `scripts/verify_public_replay.py` |
| `verify_reviews.py` | `tests/test_reviews.py` |
| `verify_ui.py` | `tests/test_ui.py` |
| `verify_workflow.py` | `tests/test_workflow.py` |
| `workflow.py` | `target_discovery/workflow/workflow.py` |
| `workflow_store.py` | `target_discovery/workflow/workflow_store.py` |

`streamlit_app.py` remains at the root as a new thin launcher.
