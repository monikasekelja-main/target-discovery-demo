# Read-only Evidence assistant

Open **Ask the evidence assistant**. The selected target, run and assessment remain visible, including in the sidebar. Select a suggested question or enter your own, choose your accessible model, and submit explicitly. The app reuses OPENAI_API_KEY and TARGET_REVIEW_MODEL from the Streamlit server environment.

## Three implemented slices

A. Grounded chat: one agent chooses among a small allowlist of tools. An automatic read of the exact assessment counts as the first of six permitted tool calls. At most seven model requests are possible per question. There are no automatic model retries. A literature-search tool may make one broader PubMed query after an empty result, within the same tool call. The initial read includes canonical estimates, snapshot-bound measurements, policy, provenance and available advisory reports. Evidence reads retain excluded, contradictory and unresolved records. Reports retain current/stale and live/scripted labels. Replies have three sections, verified-source excerpts and expandable tool activity.

B. Figures: effect intervals and QC comparison. Matplotlib consumes only registered, digest-bound saved data. Effect intervals preserve saved means, CIs, donor counts and the original policy threshold. QC displays paired control/perturbed absolute live-cell counts and viability, without calculating new statistical estimates. The model cannot supply arrays, paths, thresholds or code. Missing data or unsupported plot templates produce a refusal. Each ZIP download includes PNG, SVG, PDF, caption and a provenance record with every plotted value. Orange is used as an accent colour. These are publication-style figures, not journal-compliance exports.

C. External context: PubMed ESearch → ESummary → EFetch abstracts. Crossref bibliographic discovery is an explicitly labelled fallback if PubMed fails or finds nothing; DOI abstract retrieval is separate. Five search hits maximum. Discovery metadata is not scientific evidence. Only content actually retrieved can be cited; missing abstracts remain metadata-only. External findings are always labelled candidates, never incorporated into the selected assessment. DEMO-R1 queries are rejected; search methods and real biological concepts instead.

Optional search_web uses Brave Search with BRAVE_SEARCH_API_KEY. It is available only after a literature search, restricts results to configured official domains (NCBI/NLM/NIAID/FDA/EMBL-EBI), and retrieves page excerpts before synthesis. No snippets count as scientific evidence. No credentials means an explicit unavailable result; there is no silent substitute. Official-page redirects are rejected, so some pages may be inaccessible. This optional integration has not been exercised live with a Brave key.

## State and cancellation

Scientific databases are opened read-only. No assistant tool imports evidence, reviews a decision, sends a message or creates a handoff. Conversations are keyed by workspace, run, assessment and canonical SHA-256. Chat records, source captures and figure bundles live in `.assistant-state/`, separately from scientific workspaces. Changing assessment starts a separate conversation. Old messages retain their exact assessment binding.

Background work uses a cancel flag and bounded request timeouts. Cancel or navigation stops subsequent requests; an in-flight request cannot be recalled and may still incur cost. Partial model answers are not accepted. Session reruns poll the existing job and never launch another call automatically. A server restart may lose an in-progress question; completed transcripts remain saved. There is no automatic recovery or retry.

External documents are untrusted data. The dispatcher has no write tool, shell, arbitrary code execution or arbitrary URL fetch. Citation identifiers must have been read; quoted excerpts must match retrieved content exactly. This is a provenance check, not proof that the cited passage entails the claim. Human scientific review remains necessary.

## Verification and limitations

Automated tests cover five scientific states at the data/contract level, exact historical snapshots, figure values/exports, missing-data refusals, bounded tools, cancellation, unrecognised tools, read-only state, rerun idempotency, citation fabrication, fictional-target queries, external contradiction separation and retrieval errors. Agent tests use explicit test doubles. They do not measure live scientific reasoning quality.

A real public PubMed smoke test returned five records and successfully retrieved an abstract on 15 October 2026. Effect and QC PNGs were visually inspected at presentation size. No paid model calls were made during implementation. Full-text retrieval, general arbitrary web browsing, paired-donor effect templates, separate prediction templates and cross-scenario composite figures are not included in the first two-template slice. Select each scenario separately for its figures; alternative outcomes must not be pooled or described as independent experiments.

Before the demonstration, rehearse with the live model and inspect its claims:

1. On demo-A002: ask why the target cannot advance beyond replication. Expect scoped support and unresolved independence, specificity and modality equivalence.
2. Request effect intervals and then QC comparison. Inspect exported units, sample sizes and threshold against saved records.
3. Ask for methods to distinguish selective cell depletion from reduced cytokine production. Require read abstracts, relevant citations, applicability caveats, no systemic-safety inference, and the external-candidate label.
4. Repeat on initial, contrary, imprecise and cell-loss runs. Require unmeasured, scoped negative, inconclusive and diagnostic-only interpretations respectively. These semantic checks remain a live rehearsal requirement, not a claimed benchmark pass.
5. Try a fictional-target publication request and a failed retrieval. Expect explicit limitations, no fabricated sources or scripted fallback.

## Provider references checked during implementation

- [NCBI usage guidelines](https://eutilities.github.io/site/API_Key/usageandkey/): requests are serialised and spaced at least 0.4 seconds apart within this app process. Multiple server processes share an IP quota; coordinate them for larger use. NCBI_EMAIL can identify the maintainer. The UI displays the NCBI disclaimer link.
- [Crossref REST API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/): public metadata access, with abstract copyright caveats.
- [Brave Web Search reference](https://api-dashboard.search.brave.com/api-reference/web/search/get): optional subscription-token integration; requires the user's own applicable API plan.
- [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses): existing Responses transport reused with a strict action/answer schema and server-side validation. No change to existing analyst/challenger provider or prompts.


## Search and proposal-label refinement (15 October 2026)

Literature queries now accept one to three short plain concept groups separated by `|`, with the most important concept first. The agent supplies publication start/end years separately. PubMed receives `datetype=pdat`, `mindate` and `maxdate`; Crossref receives matching publication-date filters. Year lists and long keyword chains are rejected before any network request. For unspecified “recent” requests, the agent is instructed to disclose a window from the current year minus five through the current year.

After zero PubMed hits, the service makes at most one broader query, dropping the final concept and retaining the dates. It never broadens the date range silently. Queries, filters, result counts and fallback notices are retained in source records and displayed in tool activity. The six logical-tool limit is unchanged; a literature tool can perform multiple bounded HTTP requests without additional model calls.

Next-step suggestions carry a persistent UI label: proposals for specialist discussion, not validated protocols. The agent is instructed to distinguish supporting knowledge gaps from evidence that a suggested experiment works, defer feasibility/controls/priorities to specialists, and avoid irrelevant generic QC warnings. Existing transcripts are retained.

Verification: all 167 tests passed, including 21 assistant tests. A live public PubMed search for `cytokine secretion | live cell | flow cytometry`, filtered to 2021–2026, returned five records and retrieved one abstract. This verifies retrieval and date-filter execution, not comprehensive coverage or scientific relevance of every hit. No paid model calls were made; revised live synthesis still needs rehearsal.


## Literature relevance screening

The assistant now records candidate/relevant/reject decisions with question-specific reasons in tool activity. Reading a publication requires a candidate decision based on discovery metadata. Citing it requires a later relevant decision supported by an exact excerpt from content actually read. Rejected sources cannot be cited, even if their abstracts were retrieved. These are model relevance judgments backed by provenance checks, not an independently validated relevance classifier.

If one completed literature search yields no accepted source and tool budget remains, an attempted final answer is redirected to a second focused methods search. Web fallback requires two distinct completed literature queries in the same date window; the automatic zero-hit broadening does not count as the second query. Repeated identical queries and silent date-window changes are rejected. Search failure is reported without inventing results. Screening decisions are carried on normal agent steps and consume no extra tool calls; the six-tool and seven-model-request limits remain.

For depletion-versus-production questions, the prompt prioritises viable cytokine-producer recovery, live secretion measurement and longitudinal survival/secretion methods, separating method discovery from transfer to CD4/IL-17A. Generic population profiling is insufficient. A lack of relevant findings must be reported rather than filled with weakly related citations.

Validation: 171 tests passed, including a simulated irrelevant-hit → second focused search → relevant abstract flow, rejection of early web fallback, unchanged scientific records and relevance citation gates. No paid model calls were made for this change. Repeat the methods question to test live relevance judgments; prior transcripts remain unchanged.
