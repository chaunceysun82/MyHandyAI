# Model and RAG review — September 5, 2026

## Recommendation and scope

Use GPT-5.6 Terra for routine intake and project assistance, GPT-5.6 Sol for tools/materials and repair-step planning, and GPT-5.6 Luna for bounded classification and search-query tasks. Benchmark GPT-6 Astra as an escalation for difficult or conflicting evidence before enabling it. If a single text model is required, start with Sol for a quality-focused release.

These are workload recommendations, not measured improvements on MyHandyAI. This review traced the checked-out FastAPI routes, Lambda worker, agent services, ingestion scripts, and official documentation. No inference calls, database queries, deployments, or runtime code changes were made. Only `.env.example` was present in Backend; deployed environment overrides, installed dependency versions, API model access, corpus coverage, latency, and real costs remain unverified.

## Current model inventory

Paths below are repository-relative; line numbers identify the inspected implementation.

| Workload | Current implementation | Recommended candidate |
| --- | --- | --- |
| Information gathering | `gpt-5-mini`, low reasoning; `Backend/config/settings.py:64`, `Backend/agents/information_gathering_agent/agent/information_gathering_agent.py:23` | `gpt-5.6-terra`, low; Sol for complex diagnosis |
| Project assistant, including image input | `gpt-5-mini`, low; settings line 61 and assistant constructor | `gpt-5.6-terra`, low; Sol when evidence conflicts |
| Tools/materials planner | `gpt-5-mini`; Responses API with strict JSON schema; no explicit reasoning effort; `Backend/agents/solution_generation_multi_agent/planner.py:101` | `gpt-5.6-sol`, medium |
| Active step planner | `gpt-5-mini`, low; LangChain/Pydantic structured output; `Backend/agents/solution_generation_multi_agent/steps_generation_agent/steps_generation_agent.py:14` | `gpt-5.6-sol`, medium |
| Estimation complexity label | `gpt-5-mini`, low; `planner.py:865`; cost/time aggregation is primarily code | Luna, low, or deterministic classification after validation |
| YouTube query and candidate selection | Two `gpt-5-mini` calls; `Backend/worker/worker_lambda.py:725` and `:782` | Luna, low; validate selected ID against supplied candidates |
| Image planning prompts | `gpt-4o-mini`; `Backend/agents/solution_generation_multi_agent/services/image_generation_agent_service.py:61` | Terra initially; compare visual consistency and prompt cost |
| KB classification/extraction | `gpt-5-nano`; scraper config and `fetch_tools_materials.py:31` | Luna for labels; Terra for extraction of procedural details and warnings |
| Step image generation | `gemini-3-pro-image-preview`; image agent line 14 | Separate image evaluation; text-model upgrades do not replace this |
| Project preview image | `gpt-image-2`; `Backend/services/project_preview_image.py:18` | Keep for this text/RAG migration |
| Embeddings | `text-embedding-3-small`, KB dimensions hardcoded to 1536 | Keep initially; evaluate large only after retrieval repairs |
| Completion note route | `text-davinci-003` through `openai.Completion.create`; `Backend/routes/feedback.py:79` | Use the existing deterministic message; obsolete SDK call is caught and falls back |

The active worker uses `StepsGenerationAgent`, not `StepsAgentJSON`/`ContentPlanner` in the same planner file. Additional GPT-4.x/GPT-5 identifiers under `legacy_modules` and `Test` should not be mistaken for the primary production route. The `ContentPlanner` metadata value `model_used: gpt-5` is hardcoded, not reliable runtime evidence. `GOOGLE_IMAGE_MODEL=imagen-4` in settings also does not control the active step image agent: its constructor ignores the supplied model argument.

## Model economics and migration requirements

Standard short-context text prices per million tokens, as documented on the review date:

| Model | Input | Output |
| --- | ---: | ---: |
| Current GPT-5 Mini | $0.25 | $2 |
| GPT-5.6 Luna | $0.20 | $1.20 |
| GPT-5.6 Terra | $2 | $12 |
| GPT-5.6 Sol | $4 | $20 |
| GPT-6 Astra | $10 | $50 |

Sources: [GPT-5 Mini](https://developers.openai.com/api/docs/models/gpt-5-mini), [Luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna), [model comparison](https://developers.openai.com/api/docs/models/compare). These exclude cache pricing, long-context premiums, images, and tools. Reasoning tokens affect billed output. Terra is 8x input/6x output relative to current Mini; Sol is 16x/10x. Routing matters. Total task cost depends on actual token consumption and retries.

1. Centralize model IDs, reasoning, output limits, timeouts, and fallback policy for every active role. Changing only the two existing agent settings misses most worker calls. Log requested and returned model IDs.
2. Review pinned `langchain==1.0.7` and `langchain-openai==1.0.3` compatibility. Verify tool calls, image inputs, persisted conversations, and structured output with the new model names; do not assume schema strategy detection works automatically.
3. Prefer Responses for reasoning, tools, and multi-turn workflows per [GPT-5.6 guidance](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-5.6). Explicitly configure effort to avoid an unintended latency increase.
4. Astra tool calling requires Responses, has no `none` effort, and requires removing temperature/top-p/logprob parameters per [Astra migration guidance](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-6-astra). The image prompt helper currently uses `max_tokens` and temperature; migrate request shapes, not just names.
5. Update `Backend/database/llm_consumption.py:15`: new models currently receive no cost estimate. Track cached/reasoning usage and all model turns. Several worker/service calls omit project/user identifiers, preventing accurate per-project attribution.

## Current RAG flow

The system combines three dense-vector lookups backed by MongoDB:

1. Intake stores a project summary, optionally with hypotheses, in Qdrant `project_summaries`.
2. Worker finds the best previous project. Score >=0.95 copies tools, steps, and estimates; 0.70–0.95 supplies the previous plan for adaptation; lower scores generate afresh.
3. Unless the score selects copying, worker retrieves one item from `kb_summaries`. At >=0.70, its summary, tools, materials, warnings, and URL are added to planning prompts.
4. Generated tool names query `tools`; matches >=0.80 reuse image/product links after a retrieval threshold of 0.75.

The project assistant loads the current project's full steps and tool context from MongoDB on each turn. It has no KB retrieval tool. Current RAG is concentrated in initial generation.

## Findings in priority order

### P1 — Similarity alone authorizes copying a complete repair plan

`Backend/worker/worker_lambda.py:423` copies prior output and exits. It bypasses newly built user context and KB evidence. Similar descriptions can differ in dimensions, materials, appliance model, location, user capability, or hazard conditions. Search has no ownership/sharing, approval, category, or completion filter (`Backend/worker/helper.py:299`). This permits reuse across projects regardless of those boundaries; actual cross-user exposure was not tested.

Use previous plans as references that must be adapted and validated. Reserve exact reuse for a canonical, approved template with matching constraints and versions. Filter by ownership or explicit sharing and eligibility before search. Preserve provenance and recalculate quantities/estimates. More capable generation models cannot fix a branch that bypasses generation.

### P1 — Cold-start summary indexing can fail before collection creation

`Backend/agents/information_gathering_agent/agent/tools.py:272` performs a diagnostic similarity search before embedding/upsert, in the same try block. The search raises on a missing collection; collection creation lives in the subsequently skipped embedding function. Decouple optional lookup from indexing, handle missing collections explicitly, and make indexing retryable with a recorded status.

### P1 — Retrieval discards the actual repair procedure

`Backend/worker/helper.py:144` returns only the first hit, even if top_k increases. MongoDB stores `extracted.sections`, but retrieval returns summary/tools/materials/warnings only. `worker_lambda.py:285` never formats article instructions. Index section/step content with document title and section context; retain summary vectors for document discovery. Return multiple relevant passages with stable source IDs.

### P2 — Retrieval misses candidates and hides failures

There is no hybrid keyword retrieval, reranking, or metadata filtering in the worker path. KB errors and no hits both become None. An orphan top project can prevent consideration of valid runners-up. If a >=0.95 project lacks generated outputs, copying falls back to generation after KB search was already skipped.

Introduce a shared retrieval result with status (`ok`, `no_match`, `unavailable`), candidates, provenance, timings, and model/index version. Select only eligible candidates; run KB retrieval whenever generation will occur. Reuse the query embedding across compatible collections instead of embedding the same summary repeatedly.

### P2 — Ingestion and embedding configuration can drift

Scraper discovery uses `DB_NAME` defaulting to `myhandyai_kb`; enrichment uses `MONGODB_DATABASE`; backend defaults to `MyHandyAI`. `mongo_fill_documents.py:248` stops after 15 records without a progress cursor. Repeated runs can revisit the same subset. These are configuration risks; actual corpus population is unknown.

Unify configuration and add resumable, content-version-aware enrichment with counts for fetched, extracted, indexed, failed, and stale documents. Propagate existing revision/hash/date/category metadata into Qdrant and use it during retrieval.

Intake and KB indexing hardcode the small embedding model while worker queries use settings. Project chunk size is 500,000 characters (`embeddings_generation.py:170`), with no token guard. The embedding models have an 8,192-token input limit; small and large default to 1536 and 3072 dimensions respectively. [Official embeddings guide](https://developers.openai.com/api/docs/guides/embeddings)

Use token-aware chunks and a single embedding configuration. Changing embeddings requires reindexing all corpus vectors, even if dimensions are made equal. Build a versioned collection and switch atomically; do not mix embedding spaces. Validate dimensions/model version on startup and remove stale chunks when a document shrinks.

### P2 — Evidence is not preserved through generation

The step schema has no citations and `worker_lambda.py:649` saves `referenceLinks: []`. The prompt labels retrieved content “verified” (`steps_generation_agent_service.py:90`) without checking a review status; ingestion assigns medium authority and a fixed reliability weight.

Pass retrieved passages as clearly delimited evidence, never executable instructions. Record source ID, URL, section, revision, and retrieval time; require source IDs on supported procedural claims and verify them against supplied passages. Keep private project examples separate from reviewed reference material. Add manufacturer-specific sources where applicable. Missing or contradictory evidence should trigger clarification or a bounded escalation, not an unsupported confident plan.

## Proposed retrieval and rollout

Keep Qdrant. Start with section-aware chunks around 400–800 tokens and 50–100 overlap, preserving complete steps and associated warnings where possible. These are initial parameters to evaluate.

Retrieve dense semantic and sparse keyword candidates (initially 20 each), fuse rankings, then rerank and select roughly 4–8 passages within a context budget. Keywords help with exact product models, sizes, and part identifiers. Qdrant supports both [hybrid fusion](https://qdrant.tech/documentation/search/hybrid-queries/) and [multi-stage reranking](https://qdrant.tech/documentation/tutorials-basics/reranking-hybrid-search/). Evaluate this against dense-only retrieval; gains are not guaranteed. Do not carry cosine thresholds of 0.70/0.95 over to fusion or reranker scores.

Provide the project assistant with scoped retrieval using the latest question plus current step and constraints. Keep the current step and relevant warnings in context; summarize the rest of the plan instead of resending every instruction indefinitely.

Roll out in this order:

1. Establish representative evaluation cases and baseline metrics; fix cold-start indexing, copy eligibility, fallback retrieval, and model/cost configuration.
2. Build a versioned section index, resumable ingestion, source-bearing results, and multiple-candidate retrieval. Test dense-only versus hybrid/reranking separately.
3. Compare Mini versus Terra/Sol with retrieval held fixed, then compare retrieval changes with the model held fixed. Test Astra only on difficult cases. Confirm API access and adapter compatibility before switching defaults.
4. Canary winning configurations behind role-specific flags; retain old model settings and index for rollback.

Start with 50–100 representative cases, including near-identical summaries with different materials/dimensions, missing KB, stale/orphan records, contradictory sources, prompt injection in retrieved text, and private-project access boundaries. Measure evidence recall@k, citation support, plan correctness, warning omissions, inappropriate reuse, schema/tool failures, p50/p95 latency, and full cost per project. Preserve existing summary-confirmation behavior. Set release thresholds after measuring the baseline; do not promote a model based solely on a generic benchmark or self-reported confidence.
