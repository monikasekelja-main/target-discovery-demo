# Public-copy verification — 16 October 2026

- Full offline suite: **173 tests passed** under Python 3.12 with the installed pinned dependencies.
- Saved replay: **nine runs across three workspaces, four views each** rendered in Streamlit AppTest. Model, retrieval and socket connections were blocked. Saved file hashes were unchanged by navigation.
- Main case: current input bindings, simulated approval, two follow-up records, offline report binding and simulated NEEDS_INFORMATION handoff verified.
- All six main assessment payloads match their source cases apart from version/binding metadata. Numerical policy, calculation and compiler code, agent prompts, initial target evidence and all eight experiment files are unchanged. Neutral policy wording requires new bindings; these are new public records.
- Privacy checks covered filenames, text, raw SQLite bytes and logical database records: no company/recruitment wording, known personal names, personal email addresses, home-directory paths or recognised credential patterns remain. No original databases, slides, screenshots, conversation captures, live-provider logs, Git metadata, secrets or environments are distributed. Public citation authors are retained.
- All three databases pass SQLite integrity and foreign-key checks.
- Browser inspection at **1366 × 768**: supportive Decision chart, recommendation and simulated review; Challenge & review offline disclosure; Specialist handoff receipt and needs-information reply. No record submissions or API calls were made.
- Original private bundle files still match their original manifest.
- ZIP extracted into a different directory: the same nine-run, four-view replay check passed with no provider/network calls or record changes.

Re-run the offline suite from this folder:

```sh
python -m unittest verify verify_contracts verify_workflow verify_agents verify_advanced_probes verify_ui verify_reviews verify_advisor verify_followups verify_evidence_assistant verify_evidence_relevance
python verify_public_replay.py
```

Limits: tested on macOS with an existing Python environment, not on Windows/Linux or through a fresh dependency installation. Credential-pattern scanning cannot recognise every possible secret format. Scripted reports do not evaluate live AI reasoning. Optional live AI features were not exercised and are not necessary for replay.
