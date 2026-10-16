# Numerical reference: synthetic decision cases

This package specifies the scientific behaviour of the synthetic target-discovery demo. **All target-specific measurements, predictions, evidence records and experiment outcomes are invented.** DEMO-R1 is fictional. These are donor-level means and QC summaries, not raw instrument files. No synthetic source ID denotes a publication.

The criteria are proposed, reviewable assumptions for one example. They are not organisational standards, validated biological cutoffs, or probabilities of drug success. No real assay, predictive model or LLM agent has been validated here.

## Scientific question

Does partial reduction of DEMO-R1 expression lower the fraction of live CD4 T cells that are IL-17A positive by at least 20%, while preserving viable-cell recovery, in a stimulated, Th17-enriched culture representing one inflammatory skin disease-like context?

This intentionally narrows the original broad inflammatory phenotype to one measurable functional readout. It does not claim restoration of healthy cell function or patient benefit. The 72-hour assay label is a fixture identifier, not a recommended laboratory protocol. Actual assay timing, controls and perturbation feasibility need a biology team's review.

KD-A is the primary RNA knockdown method; KD-B is corroborating CRISPRi expression reduction in the **same eight donors**. Each has its own matched non-targeting control (NTC). Matching numbers across these invented controls simplify the demonstration. The second method addresses method-related explanations; it is not independent cohort replication. Rescue, new donors and a different batch remain follow-up work. Neither method establishes equivalence to receptor blockade, antagonism or degradation.

## Files and information boundaries

| Path | Purpose |
|---|---|
| `runtime/initial_evidence.json` | Sixteen synthetic evidence, limitation and challenge records; not sixteen independent studies. |
| `runtime/policy.json` | Scientist-authored criteria, exact hypothesis context and measurement definitions. These criteria are visible to agents. |
| `runtime/experiments/X*.json` | Neutral experiment IDs, measured values and QC metadata. The runtime receives the selected experiment only. |
| `evaluate.py` | Fixed arithmetic and transparent action-eligibility checks; standard-library Python only. |
| `evaluation/expected.json` | Reference actions and required scientific qualifications; NEVER include in agent prompts, search tools or retrieval indices. |
| `evaluation/calculated_summaries.json` | Computed reference metrics for development and audit; do not use as a runtime answer source. |
| `verify.py` | Numerical, branching and boundary regression checks. Run offline during development. |

Do not let the runtime enumerate all alternative experiment fixtures. A demo controller selects an outcome and exposes only that record. Filenames and IDs are for provenance, not decision labels. For a stronger evaluation later, change IDs and reserve unseen measurement variants.

## Numerical contract

Eight independent donor pairs per method; three technical wells per condition are averaged before analysis. Cells and wells do not increase biological n. Donor means are equally weighted. Do not pool the two correlated methods or the alternative outcomes as additional donors.

For donor i:

`reduction_i = 100 * (1 - KD_IL17A_positive_fraction_i / NTC_IL17A_positive_fraction_i)`

The effect is a **relative percent reduction**, not a percentage-point difference. For D01 in X101, 20.0% positive cells in NTC and 13.6% in KD-A give a 32% relative reduction and a 6.4 percentage-point difference.

Mean and two-sided 95% confidence interval:

`mean(reduction) +/- 2.3646242510102993 * sample_SD(reduction) / sqrt(8)`

The t approximation assumes independent donor sampling and an appropriate distribution of donor effects. It does not quantify uncertainty from model bias, assay validity or clinical translation. The two method-specific intervals are not a joint probability. Eight donors is chosen for a compact demonstration; a real sample size must be planned using a meaningful effect and pilot variance. No outcome-driven donor exclusions or optional repeated significance checks are allowed. A missing donor makes this fixed demo assessment unresolved until a documented plan is agreed.

Gates, applied before the functional decision:

1. Exact context, endpoint and version match; complete numeric inputs; eight unique paired donors per method; technical triplicates; at least 5,000 live CD4 events per well.
2. Each donor/method: NTC viable fraction >=90%; stimulated/unstimulated IL-17A-positive fraction ratio >=3; positive assay-control reduction >=40%, viable fraction >=85% and live-cell recovery >=90%; maximum technical CV <=15%.
3. Target surface-protein MFI falls 40-70% inclusive in each donor and method.
4. Each donor/method: viable fraction >=85% and live-cell recovery >=85% of NTC. Each method's lower 95% confidence bound for mean recovery is >=90% of NTC. Viable fraction and absolute live-cell recovery are distinct: a high fraction can conceal fewer cells.

If prerequisites pass, **both** methods must have lower 95% bounds >=20% to propose advancement to independent replication. If both upper bounds are <20%, propose deprioritizing the useful-expression-reduction hypothesis in this tested context. Otherwise the result is inconclusive. Equality at an upper bound of 20% does not exclude a 20% benefit. Compare unrounded values, allowing only 1e-9 absolute units for floating-point noise.

The 20%, 40-70%, viability, precision and QC cutoffs are demo assumptions to agree with scientists before the experiment. No cited paper supplies these exact values. A real assay would use benchmarks, assay variability, disease biology and intended action to justify or change them. Policy changes require a new version and a new review.

## Expected brief updates (evaluation only)

| Case | KD-A mean reduction (95% CI) | KD-B mean reduction (95% CI) | Expected proposal |
|---|---|---|---|
| Initial | No qualifying experiment | No qualifying experiment | Resolve application metadata, inspect the eligible mock signature response, then propose the relevant-context functional experiment. Genetic direction and cell-loss concerns remain. |
| X101 | 32.0% (29.5-34.5) | 29.0% (27.0-31.0) | Advance to new-donor/batch replication and target-specificity work; initiate specialist feasibility discussion. |
| X102 | 3.0% (0.8-5.2) | 2.0% (0.1-3.9) | Deprioritize the useful-benefit hypothesis at achieved expression reduction in this assay/context. Small effects may remain. |
| X103 | 23.0% (5.2-40.8) | 24.0% (8.1-39.9) | Hold: intervals include effects above and below the useful threshold. Investigate donor variability; plan a prospective follow-up. |

The initial evidence contains a synthetic disease-locus association (OR 1.16, reported 95% CI 1.10-1.22), uncertain gene assignment, and a coloc PP.H4 of 0.86 in resting cells with risk-allele direction unresolved. These are not target-success probabilities. Genetics records share an evidence family and must not be counted as independent. The historical -0.65 standardized-unit mock transcriptomic prediction remains specific to resting cells. Version 3 adds a separate eligible-context response (-0.50, 0 and +0.20 standardized signature units for -50%, 0% and +50% expression changes). Neither output predicts the functional IL-17A percentage reduction. Earlier bulk IL-17A fell 40% while live-cell counts also fell 40%; that result does not establish a beneficial functional effect.

Proposed evidence categories: causal support stays 1/3 in all branches because the genetic mapping/direction limitations remain. Intervention support is 1/3 initially, 2/3 after X101, 0/3 after X102 for this useful-benefit hypothesis, and 1/3 after X103 with uncertainty explicit. These are human-reviewed ordinal labels, not calibrated probabilities, and are not calculated by the eligibility code. No branch reaches 3/3. Preserve adverse or contradictory findings instead of hiding them inside a score.

## Additional safeguards represented in data

- X104: same apparently favourable effects as X101, but viable fraction 60-68% and live-cell recovery 58-66%; investigate cell loss and on-target/off-target/delivery explanations. No benefit claim from surviving cells alone.
- X105: small target effect but the positive control reduces the endpoint only 10%; the assay cannot support the intended negative conclusion.
- X106: small effect with only 18% protein reduction; the intended perturbation was not achieved.
- X107: primary method supportive, corroborating method not; resolve the disagreement rather than averaging the methods.
- X108: supportive values from a different cell context; do not import them as direct support for this hypothesis.

## Agent, review and platform contract

The evidence analyst identifies sources, asks the tools for measurements and assembles a proposed brief. The challenger checks context, independence, unsupported causal claims, contradictions and missing evidence. Fixed code calculates the intervals and eligibility gates. Passing those gates is necessary for the proposed demo action, but scientists may still defer because of other credible evidence or limitations. Agents cannot silently override a failed gate or change thresholds. Human review is required for every proposal.

Store evidence IDs/version, policy version, model/prompt versions, measured effect with interval, failed gates, caveats, proposed action, reviewer and approval status. Imported evidence invalidates earlier approval. The illustrative calculator does not implement application persistence, approval handling, general schema security or LLM evaluation; persistence and CLI review handling now live in workflow.py/workflow_store.py; LLM evaluation remains later work.

Handoffs stay specific: antibody specialists evaluate access and whether binding gives the desired functional consequence; small-molecule specialists evaluate tractability, functional equivalence and exposure; oligonucleotide specialists evaluate relevant-cell delivery, isoforms and tolerability. Preserved cell viability does not establish systemic safety. A positive result authorizes a recommendation for replication and feasibility work, not programme advancement or molecule design.

## Run the checks

From the package root, with Python 3.10 or later:

```bash
python verify.py
python evaluate.py runtime/experiments/X101.json
```

Checks establish arithmetic and rule consistency only. They do not establish biological validity, agent accuracy or confidence calibration.

## Methodological grounding

- Wagner MR, Kleiner M. *How thoughtful experimental design can empower biologists in the omics era*. Nature Communications (2025). https://doi.org/10.1038/s41467-025-62616-x . Supports planning replication, controls, analysis and mock data before measurement.
- Morgan JL. *Alternative to the statistical mass confusion of testing for “no effect”*. Journal of Cell Biology (2025). https://doi.org/10.1083/jcb.202403034 . Supports centring effect size and precision in biological interpretation; it does not prescribe this demo's cutoffs.

The real literature above concerns methodology. It is not evidence for the fictional target.
