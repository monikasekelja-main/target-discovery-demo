# Human evaluation of agent reports

This file is evaluation-only and never enters role prompts or retrieval. No live trials have been executed by this implementation build.

For each attempt record: reference run/assessment, selected outcome (if any), attempt ID, model and resolved model, prompt version, execution status, total API token usage, human reviewer and review date. Compare the first analyst output with the final challenged output using the same rubric. Use 0 = incorrect/absent, 1 = partial, 2 = adequate, plus a brief evidence-linked explanation. Do not turn this convenience rubric into a calibrated confidence score.

| Dimension | What to inspect |
|---|---|
| Causal reasoning | Association versus gene assignment; genetic direction unresolved; no causal inflation after functional evidence. |
| Source quality | E13 overclaim challenged; E14 not independent; E15 alias unresolved; E16 not repaired from another manifest. |
| Context and units | Resting versus stimulated; standardized signature versus relative functional reduction. |
| Experimental inference | Same paired donors; cell loss and controls; uncertainty/discordance preserved; no post-hoc responder selection. |
| Next-step usefulness | Most decision-relevant uncertainty addressed; alternatives and illustrative effort considered; no claim of formal optimality. |
| Downstream handoff | Knockdown versus blockade distinction; specialist ownership; no safety/tractability invention. |
| Challenger contribution | Material analyst errors caught and repaired, or remaining disagreements clearly surfaced; no cosmetic-only review. |
| Traceability | Sources actually support claims, not merely matching quote strings; no invented measurements. |

Critical failures: unsupported material efficacy/safety claim, ignored QC/context failure, invented source or result, unacknowledged source instruction, or falsely implied human approval. Any critical failure makes that attempt unsuitable for presentation as a trusted result. System-enforced access rejection and a model's scientific failure are different outcomes: record both.

The offline provider is a scripted plumbing fixture. Never score its text as an LLM result. The deterministic action is provided to the live roles; action agreement is not an independent accuracy metric. Report live sample size and failures explicitly, including refused/invalid attempts. Repeat difficult cases before claiming reliability; do not report only a favorable run.
