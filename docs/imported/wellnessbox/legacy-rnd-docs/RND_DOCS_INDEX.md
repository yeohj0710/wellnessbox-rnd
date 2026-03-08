# R&D 臾몄꽌/肄붾뱶 ?몃뜳??
## 紐⑹쟻
- TIPS R&D 愿??臾몄꽌媛 遺꾩궛?섏뼱 ?덉뼱?? ???몄뀡?먯꽌 諛붾줈 ?댁뼱???묒뾽?????덇쾶 ?꾩튂瑜?怨좎젙?쒕떎.
- 臾몄꽌(?붽뎄?ы빆/李멸퀬/?댁쁺)? 肄붾뱶(紐⑤뱢/?ㅽ겕由쏀듃/?곗텧臾????곌껐 愿怨꾨? ??踰덉뿉 蹂댁뿬以??

## 1) 臾몄꽌 怨꾩링

### ?꾩닔 ?붽뎄?ы빆 怨꾩링 (`C:/dev/wellnessbox-rnd/docs/imported/wellnessbox/legacy-rnd-docs/`)
- `00_readme_how_to_use.md`: 臾몄꽌 ?곗꽑?쒖쐞? 濡쒕뵫 洹쒖튃
- `01_kpi_and_evaluation.md`: ?щ씪?대뱶 25~26 ?됯? 湲곗?(理쒖긽??
- `02~07_*.md`: 紐⑤뱢蹂??붽뎄?ы빆
- `ai_training_pipeline.md`: ?⑥씪 紐낅졊 ?숈뒿 ?ㅽ뻾/?곗텧臾?媛?대뱶
- `PROGRESS.md`: ?꾩쟻 ?묒뾽 ?대젰
- `SESSION_HANDOFF.md`: ???몄뀡 ?댁뼱諛쏄린 臾몄꽌

### ?좏깮 李멸퀬 怨꾩링 (`C:/dev/wellnessbox-rnd/docs/imported/wellnessbox/legacy-rnd-impl/`)
- `02~07_*_impl_notes.md`: 援ы쁽 ?뚰듃 臾몄꽌
- 異⑸룎 ??`C:/dev/wellnessbox-rnd/docs/imported/wellnessbox/legacy-rnd-docs/*` 湲곗? ?곗꽑

## 2) R&D 肄붾뱶 ?꾩튂

### 紐⑤뱢 援ы쁽
- `lib/rnd/module02-data-lake/*`
- `lib/rnd/module03-personal-safety/*`
- `lib/rnd/module04-efficacy-quantification/*`
- `lib/rnd/module05-optimization/*`
- `lib/rnd/module06-closed-loop-ai/*`
- `lib/rnd/module07-biosensor-genetic-integration/*`

### ?듯빀 ?숈뒿/?됯? ?뚯씠?꾨씪??- `lib/rnd/ai-training/pipeline.ts`
- `scripts/rnd/train-all-ai.ts`
- `scripts/rnd/train-all-ai.reporting.ts`
- `scripts/rnd/train-all-ai.cjs`
- `package.json` ?ㅽ겕由쏀듃: `rnd:train:all`

### 紐⑤뱢蹂??ㅽ뻾 ?ㅽ겕由쏀듃
- `scripts/rnd/module02/*`
- `scripts/rnd/module03/*`
- `scripts/rnd/module04/*`
- `scripts/rnd/module05/*`
- `scripts/rnd/module06/*`
- `scripts/rnd/module07/*`

## 3) ?곗텧臾??꾩튂

### ?숈뒿 ?곗씠??紐⑤뜽 ?곗텧臾?- ?숈뒿 ?곗씠?? `tmp/rnd/ai-training-data/<runId>/`
- 紐⑤뜽/由ы룷?? `tmp/rnd/ai-model-artifacts/<runId>/`
- 理쒖떊 ?ъ씤?? `tmp/rnd/latest-train-all-run.json`

### ?듭떖 由ы룷???뚯씪
- `train-report.json`
- `attempt-selection-report.json`
- `tips-kpi-evaluation-summary.json`
- `tips-implementation-coverage.json`
- `tips-slide-evidence-map.json`
- `tips-evaluation-submission-bundle.json`
- `tips-evaluation-submission-verify.json`

## 4) ?щ씪?대뱶-援ы쁽 留ㅽ븨 (?듭떖)

- ?щ씪?대뱶 13~15: One-Stop ?뚰겕?뚮줈??  - `workflow-samples.jsonl`
- ?щ씪?대뱶 16: Data Lake
  - `data-lake-softmax.json`, `data-lake-samples.jsonl`
- ?щ씪?대뱶 17: 媛쒖씤???덉쟾 寃利??붿쭊
  - `safety-softmax.json`, `safety-samples.jsonl`
- ?щ씪?대뱶 18~19: Two-Tower+Reranker, ITE ?섏튂??  - `recommender-two-tower.json`, `recommender-reranker-gbdt.json`, `ite-linear-regression.json`
- ?щ씪?대뱶 20: ?쒖빟 湲곕컲 理쒖쟻??  - `optimization-constraint-samples.jsonl`
- ?щ씪?대뱶 21~22: Closed-loop ?몃뱶/CRAG/?ㅼ?以??먮룞??  - `closed-loop-node-trace-samples.jsonl`, `crag-grounding-samples.jsonl`, `closed-loop-schedule-samples.jsonl`
- ?щ씪?대뱶 23: ITE ?⑤씪??蹂댁젙
  - `ite-feedback-samples.jsonl`, `ite-finetune-summary.json`
- ?щ씪?대뱶 24: 諛붿씠?ㅼ꽱???좎쟾???곕룞
  - `integration-samples.jsonl`, `genetic-adjustment-samples.jsonl`
- ?щ씪?대뱶 25~26: KPI ?됯? 湲곗?/?곗씠??議곌굔
  - `tips-kpi-evaluation-summary.json`??KPI 諛?`dataRequirements`
  - `tips-slide-evidence-map.json`???щ씪?대뱶蹂?援ы쁽/?곗텧臾?洹쇨굅

## 5) 鍮좊Ⅸ ?먭? 紐낅졊

```bash
npm run audit:encoding
npm run rnd:train:all
npm run lint
npm run build
```

## 6) 諛고룷 ?덉쟾??愿???뚯씪
- `.gitignore`: `tmp/rnd/`, `tmp/pdfs/` ?쒖쇅
- `.vercelignore`: `tmp/rnd/`, `tmp/pdfs/` ?낅줈???쒖쇅

## 7) ?꾨씫 ?먭? 諛⑸쾿
- 臾몄꽌 ?꾨씫 ?먭?:
  - `Get-ChildItem -Path docs -Recurse -File`
- R&D 肄붾뱶 ?꾨씫 ?먭?:
  - `Get-ChildItem -Path lib/rnd -Recurse -File`
  - `Get-ChildItem -Path scripts/rnd -Recurse -File`
