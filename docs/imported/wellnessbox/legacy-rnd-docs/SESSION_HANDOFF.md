# R&D ?몄뀡 ?몃뱶?ㅽ봽 (Codex ?댁뼱諛쏄린??

## 1) 臾몄꽌 紐⑹쟻
- ???몄뀡?먯꽌 ?댁쟾 ?묒뾽 留λ씫??鍮좊Ⅴ寃?蹂듭썝?섍퀬 利됱떆 ?댁뼱??援ы쁽/寃利앺븯湲??꾪븳 ?댁쁺 臾몄꽌.
- 湲곗? 臾몄꽌??`C:/dev/wellnessbox-rnd/docs/imported/wellnessbox/legacy-rnd-docs/01_kpi_and_evaluation.md`?대ŉ, 蹂?臾몄꽌???꾩옱 援ы쁽 ?곹깭? ?ㅽ뻾 諛⑸쾿???붿빟?쒕떎.

## 2) ?꾩옱 湲곗? ?쒖젏
- ?묒꽦/寃利?湲곗??? 2026-03-06
- 湲곗? 紐낅졊:
  - `npm run rnd:train:all`
  - `npm run lint`
  - `npm run build`
  - `npm run audit:encoding`

## 3) ?꾩옱 援ы쁽 ?곹깭 ?붿빟

### 怨듯넻
- R&D 援ы쁽? 湲곗〈 二쇰Ц/沅뚰븳/愿由ъ옄 ?몄쬆 肄붿뼱瑜?嫄대뱶由ъ? ?딅뒗 蹂꾨룄 寃쎈줈(`lib/rnd`, `scripts/rnd`)濡?援ъ꽦??
- ?듯빀 ?숈뒿/?됯?/?쒖텧 踰덈뱾???⑥씪 紐낅졊?쇰줈 ?ы쁽 媛??

### ?듭떖 ?꾨즺 ??ぉ
- ?⑥씪 紐낅졊 ?듯빀 ?숈뒿: `npm run rnd:train:all`
- ?щ씪?대뱶 25~26 KPI ?섏떇 湲곕컲 ?됯? 寃뚯씠???곸슜
- ?곗씠??理쒖냼 議곌굔(?섑뵆 ?? ?덈룄??而ㅻ쾭由ъ?, ?뚯뒪 而ㅻ쾭由ъ?) ?먮룞 ?먯젙
- 援ы쁽 而ㅻ쾭由ъ?(?щ씪?대뱶 13~26) ?먮룞 ?먯젙 由ы룷???앹꽦
- ?쒖텧 踰덈뱾 + 泥댄겕??寃利?由ы룷???먮룞 ?앹꽦
- ??⑸웾 ?곗텧臾?Git/Vercel ?낅줈???쒖쇅 ?ㅼ젙 ?곸슜
- ?щ씪?대뱶 24 蹂닿컯:
  - `genetic-adjustment-samples.jsonl` 異붽?
  - ?좎쟾???뚮씪誘명꽣 -> ?덉쟾 ?쒖빟/理쒖쟻??媛以묒튂 議곗젙 trace
  - `geneticAdjustmentTraceCoveragePercent`, `geneticRuleCatalogCoveragePercent` 吏??異붽?

## 4) 理쒓렐 寃利?寃곌낵 (?붿빟)

### 理쒓렐 ?깃났 ?ㅽ뻾
- runId: `rnd-ai-2026-03-06T07-57-02-131Z-standard-scale-1_2`
- 寃곌낵:
  - `allTargetsSatisfied: true`
  - `allDataRequirementsSatisfied: true`
  - `implementationCoverageSatisfied: true`
  - `slideEvidenceSatisfied: true`
  - `weightedPassScorePercent: 100`
  - `weightedObjectiveScore: 125.971`

### 二쇱슂 KPI 媛?- 異붿쿇 ?뺥솗?? `91.69%`
- ?④낵 媛쒖꽑??SCGI): `15.9099pp`
- Closed-loop ?≪뀡 ?뺥솗?? `93.22%`
- LLM ?듬? ?뺥솗?? `100%`
- ?덊띁?곗뒪 ?뺥솗?? `98.7%`
- ?쎈Ъ?댁긽諛섏쓳 嫄댁닔: `4嫄?year`
- ?쎈Ъ?댁긽諛섏쓳 ?덈룄??而ㅻ쾭由ъ?: `365??
- ?곕룞?? `93.89%`

### ?щ씪?대뱶 24 愿??吏??- `geneticAdjustmentSampleCount: 1800`
- `geneticAdjustmentTraceCoveragePercent: 100`
- `geneticRuleCatalogCoveragePercent: 100`

### ?щ씪?대뱶 13~26 援ы쁽 而ㅻ쾭由ъ? ?ш?利?- PDF ?뚮뜑留??뺤씤:
  - `tmp/pdf_render_13_24/tips-13.png` ~ `tips-24.png`
  - `tmp/pdf_render/tips-25.png`
  - `tmp/pdf_render/tips-26.png`
- 援ы쁽 而ㅻ쾭由ъ? 寃곌낵:
  - `one_stop_workflow`: pass
  - `data_lake_engine`: pass
  - `safety_validation_engine`: pass
  - `two_tower_reranker`: pass
  - `ite_quantification_model`: pass
  - `optimization_constraints`: pass
  - `closed_loop_node_orchestration`: pass
  - `crag_grounding_quality`: pass
  - `closed_loop_schedule_automation`: pass
  - `closed_loop_online_finetune`: pass
  - `biosensor_genetic_integration`: pass
  - `genetic_parameter_adjustment`: pass
  - `kpi_eval_gate`: pass

### ?щ씪?대뱶 利앸튃 ?꾪떚?⑺듃
- `tips-slide-evidence-map.json` ?앹꽦
- ?щ씪?대뱶 13~26 媛곴컖?????
  - ?곌껐??援ы쁽 泥댄겕 ID
  - ?곌껐???곗씠??議곌굔 ID
  - ?곌껐??KPI ID
  - 愿???곗텧臾?寃쎈줈
  瑜????뚯씪?먯꽌 ?뺤씤 媛??
### 理쒖떊 ?덉쭏 寃利?- `npm run lint`: ?깃났
- `npm run build`: ?깃났
- `npm run audit:encoding`: ?깃났

### ?몄퐫??媛???댁쁺 硫붾え
- `data/b2b/backups/`???댁쁺 諛깆뾽 ?ㅻ깄???붾젆?곕━濡?媛꾩＜??`audit:encoding` ?ㅼ틪?먯꽌 ?쒖쇅??- ?댁쑀:
  - ?섏빟???먮Ц ?곗씠?곗뿉 ?쒖옄+?쒓? ?쇱슜 ?쒗쁽???ы븿?섏뼱 ?몄퐫??源⑥쭚???꾨땶 ?뺤긽 ?곗씠?곌? ?ㅽ깘?????덉쓬
  - ?뚯뒪/臾몄꽌/?ㅼ젙 ?뚯씪 ?몄퐫??寃?щ뒗 洹몃?濡??좎?

## 5) 諛섎뱶??癒쇱? ?쎌쓣 ?뚯씪
1. `AGENTS.md`
2. `C:/dev/wellnessbox-rnd/docs/imported/wellnessbox/legacy-rnd-docs/01_kpi_and_evaluation.md`
3. `C:/dev/wellnessbox-rnd/docs/imported/wellnessbox/legacy-rnd-docs/RND_DOCS_INDEX.md`
4. ?꾩옱 ?묒뾽 ???紐⑤뱢 臾몄꽌 1媛?(`C:/dev/wellnessbox-rnd/docs/imported/wellnessbox/legacy-rnd-docs/02~07`)
5. ?꾩슂 ???대떦 援ы쁽 ?명듃 1媛?(`C:/dev/wellnessbox-rnd/docs/imported/wellnessbox/legacy-rnd-impl/02~07`)

## 6) 二쇱슂 肄붾뱶 ?꾩튂

### ?듯빀 ?뚯씠?꾨씪??- `lib/rnd/ai-training/pipeline.ts`
- `scripts/rnd/train-all-ai.ts`
- `scripts/rnd/train-all-ai.reporting.ts`
- `scripts/rnd/train-all-ai.cjs`

### KPI ?됯? ?⑥닔
- `lib/rnd/module02-data-lake/evaluation.ts` (KPI #5 ?쇰?)
- `lib/rnd/module03-personal-safety/evaluation.ts` (KPI #5 ?쇰? + KPI #6)
- `lib/rnd/module04-efficacy-quantification/evaluation.ts` (KPI #2)
- `lib/rnd/module05-optimization/evaluation.ts` (KPI #1)
- `lib/rnd/module06-closed-loop-ai/evaluation.ts` (KPI #3/#4)
- `lib/rnd/module07-biosensor-genetic-integration/evaluation.ts` (KPI #7 + KPI #5 ?쇰?)

## 7) ?ㅽ뻾 紐낅졊 (?ы쁽 ?덉감)

```bash
npm run audit:encoding
npm run rnd:train:all
npm run lint
npm run build
```

## 8) ?곗텧臾??뺤씤 泥댄겕由ъ뒪??
### ?곗씠???곗텧臾?(`tmp/rnd/ai-training-data/<runId>/`)
- ?꾩닔 ?섑뵆:
  - `kpi01-samples.jsonl`
  - `kpi02-samples.jsonl`
  - `kpi03-samples.jsonl`
  - `kpi04-samples.jsonl`
  - `kpi05-module02-samples.jsonl`
  - `kpi05-module03-samples.jsonl`
  - `kpi05-module07-samples.jsonl`
  - `kpi06-samples.jsonl`
  - `kpi07-samples.jsonl`
- 援ы쁽/而ㅻ쾭由ъ? ?섑뵆:
  - `workflow-samples.jsonl`
  - `closed-loop-schedule-samples.jsonl`
  - `closed-loop-node-trace-samples.jsonl`
  - `crag-grounding-samples.jsonl`
  - `optimization-constraint-samples.jsonl`
  - `ite-feedback-samples.jsonl`
  - `genetic-adjustment-samples.jsonl`

### 紐⑤뜽/由ы룷???곗텧臾?(`tmp/rnd/ai-model-artifacts/<runId>/`)
- `train-report.json`
- `attempt-selection-report.json`
- `tips-kpi-evaluation-summary.json`
- `tips-implementation-coverage.json`
- `tips-slide-evidence-map.json`
- `tips-evaluation-submission-bundle.json`
- `tips-evaluation-submission-verify.json`

## 9) 諛고룷 愿??二쇱쓽?ы빆
- ??⑸웾 R&D ?곗텧臾쇱? ??μ냼/諛고룷 踰덈뱾???ы븿?섎㈃ ????
  - `.gitignore`: `tmp/` (?섏쐞 `tmp/rnd/`, `tmp/pdfs/` ?ы븿)
  - `.vercelignore`: `tmp/` (?섏쐞 `tmp/rnd/`, `tmp/pdfs/` ?ы븿)
- 諛고룷 媛?μ꽦 寃利앹? 理쒖냼 `npm run build` ?깃났??湲곗??쇰줈 ?먮떒.

## 9-1) 諛고룷 寃利?寃곌낵 (2026-02-28)
- `npm run build`: ?깃났
- Vercel CLI 濡쒖뺄 寃利?
  - 紐낅졊: `npx vercel build --yes`
  - ?곹깭: ?ㅽ뙣(?몄쬆 ?좏겙 ?댁뒋)
  - ?ㅻ쪟: `The specified token is not valid. Use vercel login to generate a new token.`
- 議곗튂:
  - 肄붾뱶/?ㅼ젙 痢〓㈃ 諛고룷 由ъ뒪?щ뒗 `tmp/` ?꾩껜 ignore濡??꾪솕
  - ?ㅼ젣 Vercel 鍮뚮뱶 寃利앹쓣 ?꾪빐 ?좏슚??Vercel ?좏겙?쇰줈 ?ъ떎???꾩슂

## 10) ???몄뀡?먯꽌 諛붾줈 ????1. `git status`濡??묒뾽 ?몃━ ?곹깭 ?뺤씤
2. `npm run audit:encoding` ?ㅽ뻾
3. `C:/dev/wellnessbox-rnd/docs/imported/wellnessbox/legacy-rnd-docs/PROGRESS.md` 理쒖떊 ??ぉ ?뺤씤
4. `tmp/rnd/latest-train-all-run.json`媛 媛由ы궎??理쒖떊 run怨?`tips-kpi-evaluation-summary.json` / `tips-implementation-coverage.json` / `tips-slide-evidence-map.json`瑜?癒쇱? ?뺤씤
5. ?꾩슂 ??`npm run rnd:train:all` ?ъ떎?됲빐 理쒖떊 由ы룷???앹꽦
6. ?꾩슂 蹂寃??곸슜 ??`lint/build` ?ш?利?7. 蹂寃??댁슜??`C:/dev/wellnessbox-rnd/docs/imported/wellnessbox/legacy-rnd-docs/PROGRESS.md`? 蹂?臾몄꽌???숆린??