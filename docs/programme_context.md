# Programme context v1

The Decision view now introduces **Plaque psoriasis | DEMO-R1** with a compact hypothesis caption and a collapsed **Programme hypothesis and scope** expander. The expander distinguishes published disease background, synthetic target-specific evidence/frozen predictions, and untested mechanism/differentiation hypotheses. It includes the competing explanations, original assay/donor limits and questions for antibody, oligonucleotide and small-molecule specialists.

Copy lives once in `ui_assets/programme_context_v1.json`; `target_discovery/ui/ui_programme_context.py` renders it only for the selected brief's DEMO-R1 target. A different or missing context identifier produces an explicit applicability warning. Unrelated targets receive no programme card. The asset is presentation metadata, outside runtime evidence, policy snapshots, assessment fingerprints and approval bindings. It is not supplied to agents, chat or retrieval and does not retrospectively become part of a reviewed assessment.

The recommendation, numerical chart and threshold still come from the selected saved assessment and its recorded policy. Detailed human review and follow-up sections now follow the scientific summary on Decision, while the current human-review status remains alongside the recommendation. Challenge & review retains its existing ordering and controls. There are no new controls, dependencies, migrations or provider calls.

Disease background links supplied by the brief:

- [Langley et al., NEJM 2014](https://doi.org/10.1056/NEJMoa1314258): IL-17A therapeutic relevance in plaque psoriasis; no evidence for DEMO-R1, expression-reduction equivalence or the provisional useful-effect criterion.
- [Fries et al., Nature Communications 2023](https://doi.org/10.1038/s41467-023-39484-4): tissue-dependent T-cell states and epithelial interactions; no validation of DEMO-R1 or the mock culture as a psoriasis model.

These explanatory links are not ingested evidence. No psoriasis-patient or skin-tissue provenance, target validation, modality feasibility or therapeutic advantage is implied.

