# OP-041/042 ingredient identity and evidence-linked goal priors

## Outcome

Extend the existing WellnessBox `/api/tips` and R&D recommendation paths with one versioned cross-repository ingredient-identifier contract, and replace unreferenced goal-alignment constants with a validated evidence-linked prior registry.

OP-041 may claim `INTEGRATED` only after the service route consumes the mapping, both repositories carry byte-equivalent contracts, and a cross-repository smoke proves mapped and unmapped behavior. OP-042 may claim `IMPLEMENTED` after the runtime knowledge builder validates the prior records and the existing candidate scorer consumes them.

## Boundaries

- Reuse `data/catalog/ingredients.json`, `IngredientCatalogItem`, `score_candidate`, the reference-ingestion pipeline, runtime knowledge DB, `/v1/interim/recommendations`, and WellnessBox `POST /api/tips`.
- Do not create a second ingredient catalog, recommendation API, candidate generator, or safety engine.
- Preserve R&D canonical keys in R&D responses. Add a separate service identifier field at the service boundary.
- Treat broader or narrower identifiers as directional mappings. Do not claim round-trip equivalence for `magnesium_glycinate`/`ING:MAGNESIUM`, `vitamin_d3`/`ING:VITAMIN_D`, or `calcium_citrate`/`ING:CALCIUM`.
- Fail closed when R&D returns a recommendation key that has no approved R&D-to-service mapping.
- Keep `general_wellness` priors low and nutritional-policy scoped. Do not represent it as a clinical outcome.
- Encode mixed, limited, or null evidence explicitly. A prior is a candidate-ordering input, not proof of efficacy or a treatment recommendation.
- Do not deploy either repository in this loop.

## Contract design

Create byte-equivalent JSON contracts at:

- `wellnessbox/contracts/wb-rnd/ingredient-identifier-map-v1.json`
- `wellnessbox-rnd/data/contracts/wellnessbox_ingredient_identifier_map_v1.json`

The contract records:

- schema and mapping versions;
- both identifier namespaces;
- active mappings with allowed direction and semantic relationship;
- every unmapped service candidate identifier with a reason;
- every unmapped R&D catalog key with a reason.

Validation must prove:

- unique service and R&D identifiers;
- complete coverage of the service proxy model ingredient list and R&D catalog;
- no unknown identifiers;
- only approved relationship and direction values;
- every active mapping supports `rnd_to_service`;
- the two repository copies are byte-equivalent.

## Runtime mapping

Add a server-only mapping module in WellnessBox. `enforceWbRndInterimSafetyAuthority` will enrich every valid recommendation with `service_ingredient_id` and attach the mapping version to the response. Any unmapped R&D recommendation will produce the existing service-owned fail-closed response with zero recommendations and a stable reason code.

QA must exercise the actual `POST /api/tips` export with:

1. a valid READY R&D fixture containing a mapped key;
2. a valid BLOCKED R&D fixture with no recommendations;
3. a valid-looking READY R&D fixture containing an unmapped key;
4. the existing malformed upstream fixture.

## Evidence-linked goal-prior registry

Create `data/knowledge/goal_ingredient_priors_v1.json`. Each record contains:

- R&D ingredient key and `RecommendationGoal` value;
- versioned candidate-ordering points (`35` for a specific goal and `18` for `general_wellness`), preserving the existing deterministic policy scale;
- evidence strength and direction;
- limitations that prevent efficacy overstatement;
- non-empty reference and claim IDs.

Use official NIH ODS, NCCIH, CDC, and narrowly scoped PubMed trial records. Paraphrased repository evidence notes must preserve source limitations. The initial registry covers all nine current goal values with at least one prior, but it need not assign a positive prior to every legacy `supported_goals` pair.

Extend the runtime knowledge DB with goal-prior records. Validation must reject:

- unknown ingredient or goal keys;
- duplicate ingredient-goal pairs;
- scores outside the versioned candidate-ordering policy;
- empty IDs;
- missing references or claims;
- claims owned by a different reference;
- claims whose ingredient or domain scope does not cover the prior;
- a current goal with no registered prior.

Update `score_candidate` so `goal_alignment` is calculated only from validated goal priors. Existing symptom, lifestyle, budget, safety, conservative, and learned-effect terms remain unchanged.

## Implementation sequence

1. Add mapping contracts, R&D validator tests, and service mapping QA.
2. Integrate mapping enrichment and unmapped fail-closed behavior into `/api/tips`.
3. Add source notes for each goal-prior claim and regenerate parsed/reference/runtime knowledge artifacts.
4. Add goal-prior models, loader, validation, and scorer use.
5. Add a deterministic OP-041/042 smoke covering mapping parity, mapped output, unmapped fail-closed output, runtime priors, and score reconstruction.
6. Run focused tests, both service QAs, TypeScript, encoding audit, full Ruff, exact CI selection, full pytest baseline comparison, runtime stored/fresh equality, and the official 256-case frozen evaluation.
7. Obtain independent review with zero Critical and Important findings.
8. Update manifest and generated completion reports: OP-041 `INTEGRATED`, OP-042 `IMPLEMENTED` only if the evidence supports those stages.
9. Update progress and handoff documents, stage only loop-owned files, commit and push service first, pin its commit in R&D CI, then commit and push R&D and wait for both CI workflows.

## Expected stage boundary

- OP-041 required and claimed stage: `INTEGRATED` after cross-repository contract parity and actual service-route use.
- OP-042 required and claimed stage: `IMPLEMENTED` after runtime validation and scorer consumption.
- No `OPERATED` claim, deployment claim, production environment claim, or production two-process claim.
