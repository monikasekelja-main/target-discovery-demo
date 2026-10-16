# Deferred-decision follow-up plans

In Decision or Challenge & review, a current DEFER decision now has a **What happens next** section. Choose **Add follow-up plan**, enter required work, owner and condition for re-review, then save. Use **Update follow-up plan** to revise the plan or move it from Planned to In progress or Ready for re-review. Ready requires a progress/evidence note.

Each save appends a version bound to the exact review and assessment. Earlier versions and plans for previous decisions remain readable in Follow-up history. A newer review or assessment does not inherit the old plan as current. Concurrent changes reject stale submissions. Repeated identical submissions are deduplicated.

Saving or marking ready leaves the human DEFER decision, canonical assessment and handoff authorization unchanged. No owner notification or model call occurs. A fresh human review is still required to authorize progression. Historical, stale and bundled records are read-only.

This slice tracks follow-up work; a progress/evidence note does not import a scientific result. The reference workflow currently accepts one allowlisted synthetic outcome per run. Additional experimental evidence ingestion and creation of a new assessment from that evidence are not implemented here. Existing amendment/refresh flows create a new assessment requiring fresh review and retain the original decision and follow-up history.

Storage is additive: review_followups rows plus REVIEW_FOLLOWUP_SAVED events. Browsing does not create tables. Original workflow contracts, scientific calculations, agent reports and saved user data are not migrated or rewritten.

Validation: verify_followups covers persistence, retries, concurrent changes, required fields, ready-state semantics, read-only history, new assessment history, and Streamlit save/update/reload behavior using temporary workspaces.
