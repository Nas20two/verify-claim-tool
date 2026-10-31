---
title: "NEBIUS BUILD RUNBOOK — Agent Claim Verification (Build B)"
tags: [nebius, build, runbook, verify-claim, ai-judge]
status: active
created: 2026-10-31
supersedes: "2026-10-30-NEBIUS-BUILD-RUNBOOK.md"
---

# NEBIUS BUILD RUNBOOK — Agent Claim Verification (Build B)

**Audience:** NaSy (logged into Nebius AI Builder, cold start)
**Build:** Agent Claim Verification (`verify-claim`, v0.1.1+)
**Deadline:** Credits expire 31/12/2026
**Repo:** `verify-claim-tool` · Branch `pain-01-verify-claim` · HEAD `f1d45b1`
**Task source:** Kai → @SATORI, 2026-10-31. 3rd dispatch (two prior went to wrong pubkey).

**Update note (31 Oct vs 30 Oct runbook):**
- HEAD moved from `bc7a616` → `f1d45b1` (README added)
- Model IDs re-verified against live catalog at `tokenfactory.nebius.com/model-catalog.md`
- Batch pricing verified at `nebius.com/solutions/inference`
- **⚠ NOV 9 DEPRECATION WARNING added** — several models disappear from Serverless in 9 days

---

## 1. PRE-BUILD CHECKLIST

Check these before touching Nebius. Nothing below costs credits.

### 1.1 Repo cloned and branch checked out
```bash
cd ~/Repos  # or wherever you keep code
git clone https://github.com/nasyhub/verify-claim-tool.git  # or buzz://clone URL
cd verify-claim-tool
git checkout pain-01-verify-claim
# Verify HEAD
git log --oneline -1
# Should show: f1d45b1 docs: add README for verify-claim-tool
#
# If it shows bc7a616 instead, run: git pull origin pain-01-verify-claim
```

### 1.2 v0.1.2 worktree fix (must apply before any Nebius work)

**Why:** The current `verify-claim.py` assumptions check `os.path.isdir(os.path.join(repo, ".git"))` which fails on git worktrees (`.git` is a file, not directory). This fix was identified in the v0.1.1 code review but not yet committed.

**Action:** Open `verify-claim.py`, find the `verify_commit` function (around line 81-86), and replace:

**Old code (v0.1.1):**
```python
git_dir = os.path.join(repo, ".git")
if not os.path.isdir(git_dir):
    log_fail(f"Not a git repository: {repo}", quiet, fmt)
```

**New code (copy-paste replacement):**
```python
git_dir = os.path.join(repo, ".git")
if not os.path.isdir(git_dir):
    # Check if it's a worktree (.git is a file with gitdir: <path>)
    if os.path.isfile(git_dir):
        with open(git_dir) as f:
            gitdir_path = f.read().strip().split(": ", 1)[-1].strip()
        # resolved — worktree is valid, continue
    else:
        log_fail(f"Not a git repository: {repo}", quiet, fmt)
        if fmt == "json":
            emit_json("FAIL", "commit", {"sha": sha, "branch": branch, "repo": repo, "error": "Not a git repository"})
        return 1
```

**Test after applying:**
```bash
./verify-claim commit --sha f1d45b1 --branch pain-01-verify-claim --repo . --format json
# Expected: {"result": "PASS", ...}
```

### 1.3 Demand post copy ready

The demand post ("My agents hallucinate at times about completing work. Does yours too?") lives at:
```
plans/2026-10-29-PAIN-01-BUILD-AND-POST.md
```
Status (as of 2026-10-31): **Locked but NOT yet posted.** NaSy should confirm the copy before posting. Timelines per §(g) of the recommendation: Nov 7–13.

Not needed for the Nebius build itself — needed for the landing page skeleton.

### 1.4 Landing page skeleton

A one-page HTML/CSS landing page (one headline + two buttons: "Download CLI" / "Hosted Dashboard Coming Soon") with Stripe checkout shell. Pure static hosting (Vercel/GitHub Pages, $0).

Status (as of 2026-10-31): **NOT YET BUILT.** NaSy: build this in a `landing/` folder or a `gh-pages` branch. Not a Nebius deliverable.

### 1.5 Check credits are visible

```bash
# Log into https://tokenfactory.nebius.com → check top-right balance
# Expected: ~$275 total (Token Factory $25 + Tavily $25 + LangSmith $100 + Toloka $100 + $1 cert + ~$24 other)
# Promo code XdRUdjnvJm7NQeci should be applied (expires 31/12/2026)
# If balance is $0: go to dev.nebius.com/builders and re-apply
```

### 1.6 ⚠ Model deprecation check (NOV 9 — only 9 days away)

On **November 9, 2026** the following Serverless models are removed. **None of our primary picks are affected** (we use `deepseek-ai/DeepSeek-V4.1-Flash-1017` which stays), but the fallback and ultra-cheap options we listed in v0.1 of the runbook ARE deprecated:

| Model | Status | Replacement used |
|-------|--------|------------------|
| `deepseek-ai/DeepSeek-V4.1-Flash` | DEPRECATED Nov 9 | Already using `-1017` variant ✅ |
| `deepseek-ai/DeepSeek-V4-Flash-0731` | DEPRECATED Nov 9 | Wasn't our pick ✅ |
| `deepseek-ai/DeepSeek-V4-Pro` | DEPRECATED Nov 9 | Not our pick ✅ |
| `Qwen/Qwen3.5-397B-A17B` | DEPRECATED Nov 9 | Not our pick ✅ |
| `Qwen/Qwen3-235B-A22B-Instruct-2507` | DEPRECATED Nov 9 | Not our pick ✅ |
| `moonshotai/Kimi-K2.6` | DEPRECATED Nov 9 | Wasn't our pick ✅ |
| `moonshotai/Kimi-K2.7-Code` | DEPRECATED Nov 9 | Wasn't our pick ✅ |
| `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` | DEPRECATED Nov 9 | **WAS our ultra-cheap fallback** ⚠ |

**Action needed:** By Nov 9, replace the ultra-cheap fallback `Nemotron-3-Nano-30B-A3B` with the recommended replacement `nvidia/Nemotron-3_5-Lightning` ($0.06/$0.03/$0.24 per 1M — same price range). Or just skip it and use Qwen3-30B as the only cheap fallback. See Step 2c below for the updated recommendation.

---

## 2. MODEL SELECTION

Verified from [tokenfactory.nebius.com/model-catalog.md](https://tokenfactory.nebius.com/model-catalog.md) (fetched 2026-10-31). All model IDs confirmed against live catalog.

### 2a. AI Claim-Judge (primary)

**Job:** Extract structured claims from agent messages, classify PASS/FAIL, flag hallucinated "done" reports.

| Property | Value |
|---|---|
| **Model ID:** | `deepseek-ai/DeepSeek-V4.1-Flash-1017` |
| **Why:** | DeepSeek V4.1 Flash built for reasoning + tool-driven workflows. 738 tok/s — fast enough. Supports JSON structured output. Excellent instruction following for extraction + classification. |
| **Input price:** | $0.30 / 1M tokens |
| **Output price:** | $1.20 / 1M tokens |
| **Cached input:** | $0.006 / 1M tokens |
| **Context:** | Multimodal (text + image input) |
| **Processing region:** | us-north1 |
| **Fast flavor:** | `deepseek-ai/DeepSeek-V4.1-Flash-1017-fast` (append `-fast` for lower latency, higher price — not needed for batch) |
| **Batch price:** | ~50% of real-time = ~$0.15/$0.60 per 1M (verified: nebius.com/solutions/inference) |
| **Deprecation:** | **NOT deprecated.** Stays past Nov 9. ✅ |

### 2b. Cheap fallback (classifier / bulk batch)

| Property | Value |
|---|---|
| **Model ID:** | `Qwen/Qwen3-30B-A3B-Instruct-2507` |
| **Why:** | 30B MoE with only 3B active params. $0.10/$0.30 per 1M = 3× cheaper than primary. 70 tok/s. Strong reasoning for its size. |
| **Input price:** | $0.10 / 1M tokens |
| **Cached input:** | $0.10 / 1M tokens (note: same as base — unusual, but from catalog) |
| **Output price:** | $0.30 / 1M tokens |
| **Context:** | Text only, 262K context |
| **Region:** | eu-north1 |
| **Deprecation:** | ⚠ **DEPRECATED Nov 9, 2026.** Replacement: this specific variant (Instruct-2507) is deprecated. Qwen general models remain. Migrate to `Qwen/Qwen3-30B-A3B` (same price) after Nov 9 if you prefer an instruct-tuned fallback. |
| **Verdict:** | Fine for MVP work between now and Nov 9. After Nov 9 use the base Qwen3-30B-A3B (non-instruct) or switch to the judge model directly. |

### 2c. Ultra-cheap batch pre-classifier (UPDATED for Nov 9 deprecation)

| Property | Value |
|---|---|
| **Model ID (current):** | ~~`nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`~~ → **DEPRECATED Nov 9** |
| **Model ID (replacement):** | `nvidia/Nemotron-3_5-Lightning` |
| **Why:**
 | $0.06/$0.03/$0.24 per 1M — same price tier. 314 tok/s. Text-to-text. Efficient reasoning. |
| **Input price:** | $0.06 / 1M tokens |
| **Cached input:** | $0.03 / 1M tokens |
| **Output price:** | $0.24 / 1M tokens |
| **Context:** | 1024K tokens |
| **Region:** | eu-north1 |
| **Note:** | Not critical for MVP. Only useful if you're doing high-volume pre-filtering (thousands of claims/day). Skip for v1. |

### 2d. For future fine-tuning (Phase 2 — not before Dec)

| Property | Value |
|---|---|
| **Model ID:** | `Qwen/Qwen3.8-27B` |
| **Why:** | Supports LoRA + full fine-tuning. Apache 2.0 license. 262K context. Vision + tool calling. 218 tok/s. |
| **Input price:** | $0.45 / 1M tokens |
| **Output price:** | $3.00 / 1M tokens |
| **Fine-tuning:** | LoRA rank 8–16 supported. Checkpoint download to repo. |
| **Deprecation:** | **NOT deprecated.** ✅ |

**Models to AVOID for this job:**
- `deepseek-ai/DeepSeek-R1-0528` — reasoning model, expensive, overkill for extraction
- `moonshotai/Kimi-K3` — $3/$15 per 1M, would burn $25 credits in minutes
- `reflection/beam` — 501B params, overkill
- `meta-models/muse-spark-open` — $1.25/$4.25 per 1M, too expensive for bulk

---

## 3. EXACT PROMPTS — AI Claim-Judge

All prompts tested against the DeepSeek V4.1 Flash-1017 endpoint on 2026-10-31.

### 3.1 System Prompt (copy-paste into API/playground)

```
You are a claim verification judge for an AI agent fleet. Your job is to analyze agent messages and extract structured claims about completed work, then classify each claim as PASS, FAIL, or UNCLEAR.

VERIFICATION RULES:
1. A claim is a specific, testable assertion that a unit of work is complete.
2. Common claim types: commit pushed, file written, deploy done, build complete, tests pass.
3. A claim is PASS only if the agent provides specific evidence (SHA, path, URL, exit code).
4. A claim is FAIL if the agent states completion without evidence.
5. A claim is UNCLEAR if the message mentions work but doesn't make a testable completion claim.
6. "Hallucinated done" = agent says it's done but provides no verifiable evidence.
7. Multiple claims in one message are extracted separately.

OUTPUT ONLY valid JSON. No preamble, no explanation.
```

### 3.2 User Prompt Template

```
Analyze this agent message and extract all completion claims:

---
{AGENT_MESSAGE}
---

Return a JSON object with the schema below. If no claims are found, return an empty "claims" array.
```

### 3.3 JSON Output Schema (enforced via `response_format: json_object`)

```json
{
  "message_text": "<original message, truncated to 1000 chars>",
  "claims": [
    {
      "claim_type": "commit|file|deploy|build|test|other",
      "claimed_completion": "<what the agent says is done>",
      "evidence_provided": "<the evidence text, if any, or null>",
      "status": "PASS|FAIL|UNCLEAR",
      "status_reason": "<one-sentence verdict explanation>",
      "hallucinated_done": true|false,
      "verification_command": "<exact verify-claim command to run, or null>"
    }
  ],
  "summary": {
    "total_claims": 0,
    "pass": 0,
    "fail": 0,
    "unclear": 0,
    "hallucinated_done_count": 0
  }
}
```

### 3.4 Example invocation (cURL — copy-paste this)

```bash
curl -s https://api.tokenfactory.nebius.com/v1/chat/completions \
  -H "Authorization: Bearer $NEBIUS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-ai/DeepSeek-V4.1-Flash-1017",
    "messages": [
      {
        "role": "system",
        "content": "You are a claim verification judge for an AI agent fleet. Your job is to analyze agent messages and extract structured claims about completed work, then classify each claim as PASS, FAIL, or UNCLEAR.\n\nVERIFICATION RULES:\n1. A claim is a specific, testable assertion that a unit of work is complete.\n2. Common claim types: commit pushed, file written, deploy done, build complete, tests pass.\n3. A claim is PASS only if the agent provides specific evidence (SHA, path, URL, exit code).\n4. A claim is FAIL if the agent states completion without evidence.\n5. A claim is UNCLEAR if the message mentions work but doesn'\''t make a testable completion claim.\n6. \"Hallucinated done\" = agent says it'\''s done but provides no verifiable evidence.\n7. Multiple claims in one message are extracted separately.\n\nOUTPUT ONLY valid JSON. No preamble, no explanation."
      },
      {
        "role": "user",
        "content": "Analyze this agent message and extract all completion claims:\n\n---\nPushed commit abc123 to feature-x. All tests pass.\n---\n\nReturn a JSON object with the schema below. If no claims are found, return an empty \"claims\" array."
      }
    ],
    "response_format": { "type": "json_object" },
    "temperature": 0.0
  }' | jq .
```

### 3.5 Python SDK equivalent

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://api.tokenfactory.nebius.com/v1/",
    api_key="<NEBIUS_API_KEY>"
)

response = client.chat.completions.create(
    model="deepseek-ai/DeepSeek-V4.1-Flash-1017",
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_PROMPT}
    ],
    response_format={"type": "json_object"},
    temperature=0.0
)
result = response.choices[0].message.content
```

---

## 4. STEP-BY-STEP BUILD SEQUENCE

Assume NaSy is logged in at [tokenfactory.nebius.com](https://tokenfactory.nebius.com).

### Step 0 — Navigate the UI

The Token Factory UI has a left sidebar with these sections:
- **Model endpoints** — where you pick models and see pricing
- **Playground** — test prompts interactively
- **Data Lab** — create datasets, run batch inference
- **Post-training** — fine-tuning jobs
- **Organization** → **API Keys** — create/manage keys
- **Organization** → **Billing** — check credits and usage

### Step 1 — Create an API Key

**Action:** Organization → API Keys → "Create API key"
**Name:** `verify-claim-judge`
**Copy the key immediately** — it won't be shown again.
```bash
# Set it as env var:
export NEBIUS_API_KEY="sk-..."
# Add to your shell rc for the session:
echo 'export NEBIUS_API_KEY="sk-..."' >> ~/.bashrc  # optional
```

### Step 2 — Check credits are applied

**Action:** Click your balance in the top-right corner.
**Verify:** The promo code `XdRUdjnvJm7NQeci` has been applied. If not:
1. Click **Top up**
2. Select **With promo code**
3. Enter `XdRUdjnvJm7NQeci`
4. Confirm

Balance should show the total (~$275). If it shows less, don't worry — some credits are allocated per-service (LangSmith, Toloka are separate accounts).

**Cost:** $0

### Step 3 — Test Connectivity (cost: ~$0.0002)

```bash
curl -s https://api.tokenfactory.nebius.com/v1/models \
  -H "Authorization: Bearer $NEBIUS_API_KEY" | jq '.data[].id' | head -10
```
Expected output: a list of model IDs including `deepseek-ai/DeepSeek-V4.1-Flash-1017`.
If you get a 401, the API key is wrong. If you get 402, credits are exhausted.

### Step 4 — Test the Claim-Judge Prompt (cost: ~$0.001)

Run the cURL command from §3.4 with three test messages:

```bash
# Test 1 — Agent claims done but no evidence
curl -s https://api.tokenfactory.nebius.com/v1/chat/completions \
  -H "Authorization: Bearer $NEBIUS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-ai/DeepSeek-V4.1-Flash-1017",
    "messages": [
      {"role": "system", "content": "You are a claim verification judge for an AI agent fleet..."},
      {"role": "user", "content": "Analyze this agent message and extract all completion claims:\n\n---\nDone.\n---\n\nReturn JSON."}
    ],
    "response_format": {"type": "json_object"},
    "temperature": 0.0
  }' | jq '.choices[0].message.content | fromjson'
# Expected: hallucinated_done = true, status = FAIL
```

Then test a PASS case ("Deployed to https://staging.example.com — build 452.") and an UNCLEAR case ("Working on the parser, will push shortly.").

### Step 5 — Upload the Eval Dataset

**Action:** Data Lab → Datasets → Create Dataset
- **Name:** `claim-judge-eval-v1`
- **Format:** JSONL (conversational — each line is `{"messages": [{"role": "user", "content": "..."}]}`)
- **Upload file:** `evals/claim-judge-eval-v1.jsonl` (create from §5 eval set below)

**Cost:** $0 (Data Lab dataset storage up to 50GB)

**Alternative — create from scratch via Data Lab UI:**
1. Click "Create dataset" → "Import Chat Completions"
2. Paste your JSONL directly or upload the file
3. The file must use the conversational format shown in §5.1

### Step 6 — Run Batch Inference

**Action:** Data Lab → Batch Inference → New Batch
- **Model:** `deepseek-ai/DeepSeek-V4.1-Flash-1017`
- **Dataset:** `claim-judge-eval-v1`
- **System prompt:** §3.1 (copy-paste the full system prompt)
- **Max tokens:** 1024
- **Temperature:** 0.0

**Cost:** Batch runs at ~50% of real-time price (verified at nebius.com/solutions/inference). For a 50-sample eval set: ~$0.012 (real-time $0.024 ÷ 2). Basically free.

**Important:** Batch inference results are downloadable as JSONL but are NOT saved to LangSmith automatically. You need to either:
- (a) Download results and re-run through Python with LangSmith wrapper, OR
- (b) For the first eval, just review the output manually.

### Step 7 — Wire LangSmith Observability

**Action:** Set up LangSmith as the tracing layer (separate from Token Factory — it's a Builder program credit).

1. Go to [langsmith.dev](https://langsmith.dev) → Sign up (use Builder credits: $100 free)
2. API Keys → Create key (`ls_...`)
3. Set env vars:
   ```bash
   export LANGCHAIN_API_KEY="ls_..."
   export LANGCHAIN_PROJECT="verify-claim-judge"
   ```
4. Wrap your OpenAI client:
   ```python
   from langsmith import Client
   from langsmith.wrappers import wrap_openai
   from openai import OpenAI
   
   ls_client = Client()
   openai_client = wrap_openai(
       OpenAI(
           base_url="https://api.tokenfactory.nebius.com/v1/",
           api_key="<NEBIUS_API_KEY>"
       )
   )
   # Now every .create() call is traced with latency, token usage, model
   ```
5. Run the eval dataset through this wrapped client.

**Cost:** $0 (covered by $100 Builder credits). LangSmith credits don't expire with the Nebius credits — they're their own account.

### Step 8 — Eval Results Review

**Action:** After batch completes or after running through LangSmith:
1. Download results from Data Lab or read from LangSmith traces
2. Compare each output against ground truth (the spreadsheet from §5.1)
3. Check metrics:

| Metric | Target | Method |
|--------|--------|--------|
| Structural validity (valid JSON) | **100%** | Every response must parse as valid JSON matching the schema |
| Precision of FAIL flags | **≥ 85%** | Judge's FAIL claims ÷ actual FAIL in ground truth |
| Recall of hallucinated done | **≥ 80%** | Hallucinated flags ÷ actual hallucinated in ground truth |
| FP rate (PASS flagged as FAIL) | **≤ 15%** | False FAIL ÷ total ground-truth PASS |

4. If metrics are below targets, iterate on the system prompt (§3.1) and re-run Step 6.

### Step 9 — Wire the Judge into the CLI

Once the prompt+model is validated, integrate into `verify-claim` as a new subcommand:

```python
# In verify-claim.py, add:
# verify-claim judge --message "..." [--format json]
# 
# Uses the openai SDK with NEBIUS_API_KEY env var.
# Model: deepseek-ai/DeepSeek-V4.1-Flash-1017
# Temperature: 0.0
# response_format: json_object
```

**This is a local-dev step** (not a Nebius UI action). The Nebius build validates the model+prompt; the CLI integration happens back in the repo.

### Step 10 — (Phase 2) Serverless Fine-Tuning

**Only if eval shows need** (precision < 85% or recall < 80% even after prompt iteration).

**Action:** Post-training → Supervised Fine-tuning
- **Base model:** `Qwen/Qwen3.8-27B` (supports LoRA)
- **Dataset:** `claim-judge-eval-v1` (uploaded in Step 5)
- **Context length:** 8192 (default for fine-tuning)
- **Hyperparameters:**
  ```json
  {
    "lora": true,
    "lora_r": 16,
    "lora_alpha": 16,
    "lora_dropout": 0.05,
    "batch_size": 8,
    "n_epochs": 3,
    "learning_rate": 1e-5,
    "packing": true,
    "context_length": 8192
  }
  ```
- **Integration:** Set up wandb if you want training metrics

**Cost:** ~$0.20–$0.50 per epoch on this dataset (~50 samples × ~400 tokens each). Still within Token Factory credits.

**Export:** Checkpoints are downloadable via API (Python SDK or cURL) → store in our repo.

---

## 5. EVAL PLAN (LangSmith + Toloka)

### 5.1 Eval Dataset — 50 samples

Create file `evals/claim-judge-eval-v1.jsonl`:

Each line:
```json
{"messages": [{"role": "user", "content": "Pushed commit abc123 to feature-x. All tests pass."}]}
```

**Ground truth table (do NOT upload this to Nebius — keep as local CSV/TSV):**

| # | Input | Expected status | Hallucinated? | Claim type |
|---|-------|----------------|---------------|------------|
| 1 | "Pushed commit abc123 to feature-x. All tests pass." | FAIL | true | commit+test |
| 2 | "Done." | FAIL | true | other |
| 3 | "Deployed to https://staging.example.com — build 452." | PASS | false | deploy |
| 4 | "Working on the parser, will push shortly." | UNCLEAR | false | other |
| 5 | "Written `src/foo.ts` with the new parser — ready for review." | FAIL | true | file |
| 6 | "Written `src/foo.ts` (sha256: a1b2c3...)." | PASS | false | file |
| 7 | "PR #42 merged to main." | FAIL | true | commit |
| 8 | "PR https://github.com/foo/bar/pull/42 merged." | PASS | false | commit |
| 9 | "Build completed successfully." | FAIL | true | build |
| 10 | "Build #1234 — all checks green." | PASS | false | build |
| 11–30 | Mix of real fleet messages from #engineering | Varies | Varies | — |
| 31–40 | Synthetic edge cases (partial evidence, multiple claims, nested claims) | Varies | Varies | — |
| 41–50 | "No, I haven't started yet" / "Still debugging" / etc. | UNCLEAR | false | other |

**Distribution target:** 40% PASS, 40% FAIL, 20% UNCLEAR.

**Create the file:**
```bash
mkdir -p evals
# Write each line as a conversation JSONL entry
cat > evals/claim-judge-eval-v1.jsonl << 'EOF'
{"messages":[{"role":"user","content":"Pushed commit abc123 to feature-x. All tests pass."}]}
{"messages":[{"role":"user","content":"Done."}]}
{"messages":[{"role":"user","content":"Deployed to https://staging.example.com -- build 452."}]}
{"messages":[{"role":"user","content":"Working on the parser, will push shortly."}]}
# ... (add all 50 samples)
EOF
```

### 5.2 LangSmith Traces

Every judge invocation is wrapped via `langsmith.wrappers.wrap_openai`. This gives:
- **Trace ID + link** for every call
- **Latency, token usage, model ID** — cost tracking
- **Feedback** — annotate PASS/FAIL per trace for accuracy
- **Comparison view** — side-by-side across prompt versions

### 5.3 Toloka Labeling ($100 free)

Use Toloka for human-rated ground truth on a 50-sample subset:
1. Go to [toloka.dev](https://toloka.dev) → Create project "Claim verification"
2. Task design: "Does the agent provide specific, verifiable evidence? (PASS/FAIL/UNCLEAR)"
3. Set 3 labels per sample, majority vote
4. Cost estimate: ~$0.03/label × 3 × 50 = **~$4.50 total** (out of $100 free)
5. Export results → merge with ground truth CSV

### 5.4 "Good enough to ship" bar

| Metric | Threshold | How to measure |
|--------|-----------|----------------|
| **Precision** (of FAIL/hallucinated flags) | ≥ 85% | Compare judge FAIL classifications against Toloka ground truth |
| **Recall** (of actual hallucinated done) | ≥ 80% | What fraction of Toloka-tagged hallucinated-done did the judge catch? |
| **False positive rate** (PASS flagged FAIL) | ≤ 15% | Toloka PASS items that judge flags as FAIL |
| **Structural validity** (valid JSON) | 100% | Every response must parse as valid JSON matching the schema |
| **Turnaround** (P95 latency) | ≤ 10s | From LangSmith traces |

If precision < 85% or recall < 80%: iterate system prompt first, re-run batch. Only consider fine-tuning if two prompt iterations fail to reach the bar.

---

## 6. COST MAP

### Free steps ($0)

| Step | What | Notes |
|------|------|-------|
| Pre-build checklist (§1) | Repo, worktree fix, landing page | All local |
| API key creation (§4 Step 1) | Token Factory UI | $0 |
| Step 2 — Check credits | UI action | $0 |
| Step 3 — Connectivity test | `GET /v1/models` | Free endpoint |
| Step 5 — Dataset creation | Data Lab | Free up to 50GB |
| Step 7 — LangSmith setup | langsmith.dev | $100 Builder credits |
| Step 7 — Toloka setup | toloka.dev | $100 Builder credits |
| Step 8 — Results review | Local | $0 |
| Step 9 — CLI integration | Local dev | $0 |

### Credit-cost steps

| Step | Model | Tokens (est.) | Real-time cost | Batch cost (~50%) |
|------|-------|--------------|----------------|-------------------|
| Step 4 — Prompt test (3 calls) | DeepSeek V4.1 Flash-1017 | ~1.5K in + ~600 out | ~$0.0012 | ~$0.0006 |
| Step 6 — Batch eval (50 samples) | DeepSeek V4.1 Flash-1017 | 20K in + 15K out | $0.024 | ~$0.012 |
| Step 10 — Fine-tune LoRA 1 epoch | Qwen3.8-27B | ~2.5M tokens | ~$0.50–$1.00 | — |
| **Total MVP burn** | — | — | **~$0.03** | — |

### Credit pool breakdown

| Pool | Balance | MVP burn | Remaining |
|------|---------|----------|-----------|
| Token Factory | $25 | ~$0.02–$1.50 | $23.50+ |
| LangSmith | $100 | ~$0 (traces) | $100 |
| Toloka | $100 | ~$4.50 (labels) | $95.50 |
| Tavily | $25 | $0 (not used in v1) | $25 |
| NVIDIA×Nebius cert | $1 | $0 | $1 |
| **Total used** | | **<$10 of $275** | **$265+** |

### What would cost real money (not for MVP)
- **Dedicated GPU endpoint:** from $1.55/hr (L40S) to $9.50/hr (B300 on-demand) — NOT needed for eval. Only for production serving.
- **Full fine-tuning (not LoRA):** significantly more expensive. Start with LoRA.

---

## 7. EXPORT CHECK

**Non-negotiable:** Every artifact must be portable. Nothing hostage to Nebius.

### 7.1 What runs anywhere

| Asset | Where it lives | How to migrate |
|-------|----------------|----------------|
| **Prompt (§3)** | `verify-claim-tool/prompts/claim-judge.md` | Copy-paste to ANY OpenAI-compatible endpoint |
| **Eval dataset (§5)** | `evals/claim-judge-eval-v1.jsonl` in repo | JSONL — upload to any platform |
| **Fine-tuned weights** (Phase 2) | Downloaded to `models/` in repo | LoRA safetensors → any vLLM |
| **API caller code** | `verify-claim judge` subcommand | Uses `openai` SDK — change `base_url` to migrate |
| **Ground truth labels** | `evals/claim-judge-ground-truth.csv` in repo | CSV — portable |
| **LangSmith traces** | langsmith.dev (SaaS) | Exportable |

### 7.2 What stays on Nebius

- **API key** (create a new one on another provider)
- **Batch inference results** (download as JSONL before deleting)
- **Data Lab datasets** (source JSONL is in repo — re-upload elsewhere)

### 7.3 Migrating away — change one line

```python
client = OpenAI(
    base_url="https://api.tokenfactory.nebius.com/v1/",  # → https://api.together.xyz/v1/
    api_key=NEW_API_KEY
)
```

All OpenAI-compatible providers (Together, Fireworks, OpenRouter, DeepInfra, Groq) support the same `chat.completions.create` interface. The model ID may differ slightly (`deepseek-ai/DeepSeek-V4.1-Flash-1017` → may differ on other providers), but the prompt and schema are identical.

### 7.4 Checkpoint export procedure (Phase 2)

```bash
# 1. List checkpoints
curl -s "https://api.tokenfactory.nebius.com/v1/fine_tuning/jobs/<job_id>/checkpoints" \
  -H "Authorization: Bearer $NEBIUS_API_KEY" | jq .

# 2. Download each result file
for file_id in $(curl -s "https://api.tokenfactory.nebius.com/v1/fine_tuning/jobs/<job_id>/checkpoints" \
  -H "Authorization: Bearer $NEBIUS_API_KEY" | jq -r '.data[0].result_files[]'); do
  curl -s "https://api.tokenfactory.nebius.com/v1/files/$file_id/content" \
    -H "Authorization: Bearer $NEBIUS_API_KEY" \
    -o "models/checkpoint-$file_id.bin"
done

# 3. Commit to repo
git add models/
git commit -m "export: claim-judge fine-tune checkpoint v1"
```

### 7.5 Dogfood the build

Before every credit-costing step, verify the build tool works:
```bash
cd /path/to/verify-claim-tool
./verify-claim commit --sha f1d45b1 --branch pain-01-verify-claim --repo . --format json
# Expected: {"result": "PASS", ...}
```
If verify-claim itself doesn't pass, don't spend credits yet.

---

## CREDIBILITY GATE — Source Verification

| Claim | Source | Status |
|-------|--------|--------|
| DeepSeek V4.1 Flash-1017 model ID + pricing ($0.30/$0.006/$1.20 per 1M) | tokenfactory.nebius.com/model-catalog.md (fetched 2026-10-31) | VERIFIED ✅ |
| Qwen3-30B-A3B-Instruct-2507 model ID + pricing ($0.10/$0.10/$0.30) | tokenfactory.nebius.com/model-catalog.md | VERIFIED ✅ |
| Nemotron-3_5-Lightning model ID + pricing ($0.06/$0.03/$0.24) | tokenfactory.nebius.com/model-catalog.md | VERIFIED ✅ |
| Qwen3.8-27B model ID + pricing ($0.45/$0.10/$3.00) | tokenfactory.nebius.com/model-catalog.md | VERIFIED ✅ |
| Batch inference at ~50% real-time price | nebius.com/solutions/inference ("Batch inference is available at half the real-time price") | VERIFIED ✅ |
| Fast flavor: append `-fast` to model ID | docs.tokenfactory.nebius.com/ai-models-inference/overview | VERIFIED ✅ |
| OpenAI-compatible API (`/v1/chat/completions`) | docs.tokenfactory.nebius.com/quickstart example | VERIFIED ✅ |
| Data Lab free up to 50GB | docs.tokenfactory.nebius.com/post-training/datasets | VERIFIED ✅ |
| Serverless SFT: LoRA + full, per-token, checkpoint download | docs.tokenfactory.nebius.com/post-training/how-to-fine-tune | VERIFIED ✅ |
| Builder credits ($25 TF / $25 Tavily / $100 LS / $100 Toloka / $1 cert) | dev.nebius.com/builders (fetched 2026-10-30) | VERIFIED ✅ |
| Our ~$275 balance · 31/12 expiry · promo XdRUdjnvJm7NQeci | Internal AGENTS.md + memory (not re-verified externally) | [INTERNAL ONLY] |
| November 2026 model deprecation list | docs.tokenfactory.nebius.com/model-deprecations-november-2026.md | VERIFIED ✅ |
| v0.1.2 worktree fix description | verify-claim.py line 81-86 `os.path.isdir` check | VERIFIED (code inspection) ✅ |
| GPU dedicated endpoint pricing ($1.55–$9.50/hr) | nebius.com/prices (previous research) | VERIFIED ✅ |
| Consumer prices for exact credit burn (<$0.05 for MVP) | Calculated from published token prices | VERIFIED (arithmetic) ✅ |

---

*Last updated: 2026-10-31 by SATORI · For questions: @SATORI in #engineering*
