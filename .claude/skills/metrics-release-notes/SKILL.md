---
name: metrics-release-notes
description: Use when the user asks to enhance, refine, polish, or "look at" the release notes for a tag — typically a fresh CI-generated pre-release (e.g. `0.1.0-rc.1`) or a stable cut. Reads the auto-generated notes off the GitHub release, classifies and rewrites each bullet in this project's editorial voice, builds the `Deployment Changes` section from `README.md` (its Environment Variables table) / `aidial_admin_evaluation_metrics/app_config.py` / PR bodies, and saves a draft to `claude/release-notes/`. When the target is a stable cut (e.g. `0.1.0`) and its `-rc.*` pre-releases already carry enhanced notes, it assembles the stable draft by merging those rc notes — reusing their approved wording — instead of re-deriving every bullet from the raw stable notes. Never edits GitHub directly.
allowed-tools: Read Grep Glob LSP Bash(gh release view:*) Bash(gh release list:*) Bash(gh pr view:*) Bash(gh pr list:*) Bash(gh pr diff:*) Bash(git log:*) Bash(git show:*) Bash(git diff:*) Bash(git tag:*) Bash(git rev-parse:*) Bash(date:*) Write(claude/release-notes/*) Bash(mkdir -p claude/release-notes)
argument-hint: "[tag]"
arguments: tag
model: opus
effort: xhigh
context: fork
agent: general-purpose
---

# Evaluation Metrics release-notes enhancer

The CI publishes a release for every tag with bullets that are just the PR titles. The shared `epam/ai-dial-ci` `python_docker_release.yml` workflow groups them by conventional-commit **type** into sections (`## Features`, `## Fixes`, `## CI`, `## Other`), strips the type from the bullet, but **keeps the scope** as a `(scope)` prefix — so `ci(deps): bump the ai-dial-ci group` becomes `* (deps) bump the ai-dial-ci group` under `## CI`, and `fix: ci issues` becomes `* ci issues` under `## Fixes`. Those bullets still carry a lot of dirt: bare branch-slug phrasing, orphan commits with no PR (`* Initial commit`), pure dependency bumps and test-only churn misfiled next to consumer-relevant items, and a `## Other` / `## CI` split that mixes things a maintainer cares about with pure internal housekeeping. This skill applies a human editorial pass over those raw notes: classify each bullet by real user impact, rewrite it in terse house style, and assemble an operator-facing `Deployment Changes` section. The releases visible at `https://github.com/epam/ai-dial-admin-evaluation-metrics/releases` are the corpus this skill edits. As of writing only `0.1.0-rc.0` exists and its body is still **raw CI output** — so until a stable cut with enhanced notes exists, the editorial style is defined by this skill's §5 rules and example transformations, not by a prior release body.

You are running in a forked, isolated context. Read and research freely — only the final summary you return reaches the main conversation. All file writes happen in this fork; the draft lands at `claude/release-notes/<tag>-draft.md`.

## When to use

- "Enhance the release notes for `0.1.0-rc.1`"
- "Look at the latest pre-release notes and refine them"
- "Help me adjust release notes for the current rc"
- "The CI just published `<tag>`, make it readable"

Do **not** trigger on requests like "what changed in 0.1.0?" — that is a recall question, not a notes-editing task.

## Inputs

`tag` = `$tag` — the GitHub release tag to enhance (e.g. `0.1.0-rc.1`, `0.2.0`). If empty, pick the most recent tag from `gh release list --limit 5` and confirm with the user before editing.

## Mode selection

After resolving the tag, decide which path to follow:

- **Merge path** — the target is a **stable** `X.Y.Z` (no `-rc` suffix) *and* one or more `X.Y.Z-rc.*` pre-releases exist whose release bodies are **already enhanced**. A stable's notes are exactly the union of its pre-releases plus whatever landed after the last rc, and those rc bodies have already been through this editorial pass — so assemble the stable draft by merging them and reserve fresh work for the post-last-rc commits. This is what "enhance `0.1.0`" means once the rc notes are done. Follow the **Merge path** section below.
- **From-scratch path** — everything else: any `-rc.N` target, a stable with no pre-releases, or a stable whose rc bodies are still raw CI output. This is the current default, since no enhanced release exists yet. Process every bullet from the raw notes via the **Workflow** steps below.

To tell whether an rc body is enhanced or raw, sample one (`gh release view <X.Y.Z-rc.0> --json body`): enhanced bullets read as `* <Capitalized clause> — <why> #<issue> (#<PR>)` with `—` em-dashes and backticked identifiers; raw CI bullets read as terse lowercase phrases, often with a leading `(scope)` (`* (deps) bump the ai-dial-ci group with 4 updates (#20)`, `* ci issues (#19)`).

## Workflow (from-scratch path)

These steps process every bullet from the raw GitHub notes. For a stable cut whose `-rc.*` notes are already enhanced, use the **Merge path** section instead (it reuses these steps only for the post-last-rc delta).

### 1. Resolve target and reference styles

1. `gh release view <tag> --json body,name,tagName` — capture the raw CI notes. The raw section headings are emitted by the shared `epam/ai-dial-ci` `python_docker_release.yml` workflow (pinned at `@4.7.2` in `.github/workflows/release.yml`). Observed headings so far: `## Features`, `## Fixes`, `## CI`, `## Other` — grouped by conventional-commit type (`feat` → Features, `fix` → Fixes, `ci` → CI, everything else → Other). If a release surfaces a heading not in that list (e.g. `## Performance`, `## Documentation`), fold it per the §4 rules and note the new heading in your return summary.
2. `gh release list --limit 10` — locate the previous tag of the same kind (last stable for a stable release, the predecessor `rc` for a delta `rc.N+1`).
3. `gh release view <prev-stable-tag> --json body` and `gh release view <prev-rc-tag> --json body` (when relevant) — these are the style anchors. Match their terseness — one line per bullet. **First-release fallback:** when no prior tag of the same kind carries enhanced notes (the case until the first cut), the style anchor is this skill's §5 rules and example transformations.
4. `git tag --list | sort -V` + `git log <prev-tag>..<tag> --oneline` — full commit list for the range, so you can spot hotfix commits the CI dropped because they had no PR (e.g. the `Initial commit` / orphan commits that show up with no `#PR`).

### 2. Pull source context for each bullet

For every bullet in the raw notes:

1. Parse out the trailing `#<issue> (#<PR>)` or `(#<PR>)`. If only a PR number is present, that's the canonical reference; if both, keep `#<issue> (#<PR>)` order. Note the CI puts the PR number in `(#NN)` — the squash-merge convention — so most bullets carry a `(#NN)`.
2. `gh pr view <PR> --json title,body,labels` — read the PR body, not just the title. The body is where the *why* and the *what-it-replaces* live; the title is usually too compressed. Labels also reveal `dependabot`-authored bumps.
3. For bullets without a PR number (`* Initial commit`, `* fix tests`, `* Merge remote-tracking branch ...`), find the commit with `git log <prev-tag>..<tag> --oneline | grep -i <keywords>` and `git show <hash>` — these are usually hotfix commits that should fold into a related entry, not stand alone.
4. If a PR body references a doc under `docs/`, the OpenAPI schema (`docs/api/openapi.json`), or a design note, skim it for the headline framing.

### 3. Cross-check `README.md` / `app_config.py` / source for deployment changes

The `Deployment Changes` section is built from primary sources, not PR titles:

- `git diff <prev-tag>..<tag> -- README.md .env.example` — env-var additions/removals/renames. The canonical operator-facing env-var table is the **Environment Variables** table in `README.md` (three columns: `Variable | Default | Description`).
- `git diff <prev-tag>..<tag> -- aidial_admin_evaluation_metrics/app_config.py` — the source of truth for settings. All configuration is loaded by the `AppSettings` (`pydantic_settings.BaseSettings`) class and its nested `BaseModel` groups (`AppRuntimeSettings`, `CommonGroupSettings`, `DeepEvalGroupSettings`, `AidialRagEvalGroupSettings`, `RagasGroupSettings`, `MetricsSettings`).
- **Deriving the canonical env-var name — code wins over PR bodies.** `AppSettings` uses `env_prefix="EVAL__"` with `env_nested_delimiter="__"`, so a nested field maps to `EVAL__<GROUP>__<FIELD>` uppercased — e.g. `metrics.ragas.embeddings_model` → `EVAL__METRICS__RAGAS__EMBEDDINGS_MODEL`, `app.max_concurrent_evaluations` → `EVAL__APP__MAX_CONCURRENT_EVALUATIONS`. **Watch the deliberate aliases:** the top-level `dial_url` and `dial_api_key` fields carry an explicit `validation_alias` (`DIAL_URL`, `DIAL_API_KEY`) that **bypasses** the `EVAL__` prefix — the env var is `DIAL_URL`, *not* the naive `EVAL__DIAL_URL`. Verify every var against the actual field/alias in `app_config.py` before it lands in the table.
- Confirm defaults and bounds by reading the field definition in `app_config.py`: the `= <value>` default on the model field, any `Field(..., ge=, le=, gt=, lt=)` constraints, and any `@model_validator` logic (e.g. `_resolve_group_fallbacks` fills a group's `None` model list from `common`, and `_warn_missing_settings` makes `DIAL_URL` effectively required by raising when empty). The README default column reflects these; if the two disagree, code wins.

### 4. Classify each bullet (move things between sections, drop the noise)

The raw notes' `## Features` / `## Fixes` / `## CI` / `## Other` partition keys off the conventional-commit **type** in the PR title. That routing is mostly correct (type is stripped, scope kept), so a `feat(x)` reliably lands under Features — but it still mixes housekeeping with consumer- and maintainer-relevant items. Reclassify by the change's actual user impact:

| Where CI put it | Where it belongs | Rule |
|---|---|---|
| `Other` / `CI` for a security dependency or base-image bump | `Fixes` | Security items are user-relevant even when authored as `chore(deps)` / `ci(deps)`. Confirm it's actually security (CVE / advisory) via the PR body — a routine version bump is not. |
| `Features` / `Fixes` for a pre-release-only regression | `Fixes` with note "(affects pre-release users of \<feature\> only)" | Don't surface a transient bug as a feature. |
| Multiple PRs / hotfix commits on one feature | one folded entry under the appropriate section | Cite the commit hashes or PR numbers in parens. |
| `CI` item a release maintainer must know about (e.g. a pinned `ai-dial-ci` version bump that changes the release process) | `Other` with a one-line rationale | Keep it visible without pretending it's a consumer feature. |

**Drop these from the notes entirely** — they have no consumer-visible effect:

- Pure renames of internal classes/functions (`chore: rename CompletionResult to TestCaseRunResult`).
- Module/package re-layouts (`chore: split metrics into a package`).
- Regenerated API-doc churn (`make docs` output: diffs confined to `docs/api/openapi.json`, `swagger-ui.html`, `redoc.html`) **unless** the OpenAPI contract actually changed — then it's an API/contract change (see §6).
- Formatting / static-analysis housekeeping (`chore: format`, Black / isort / autoflake sweeps, flake8 / pyright fixes, `no-untyped` cleanups).
- Internal refactors with no behavior change (`chore: extract … helper`, `chunk processing refactoring`).
- Dependency / Poetry housekeeping that isn't security-relevant (`chore: bump pillow from 12.2.0 to 12.3.0`, `chore: update nltk`, `ci(deps): bump the ai-dial-ci group`, `poetry.lock` refreshes). Dependabot auto-merges the `ai-dial-ci` group (see `.github/workflows/dependabot-automation.yml`); those are pure plumbing. Keep only the ones tied to a CVE/advisory (→ Fixes, per the table).
- Claude Code agent setup / docs / skill scaffolding, OpenSpec artifact churn (`init claude documentation`, `add review skill`, change-proposal edits under `openspec/`).
- Test-only additions or realignments (`chore: add skipping e2e test`, new `pytest` cases, `pytest-recording` / `vcrpy` cassettes, `integration`-marked tests) that don't change product behavior.
- `Merge remote-tracking branch …` commits and the bootstrap `Initial commit`.
- CI-only changes (release-candidate branching, workflow edits) **unless** a maintainer needs to know — then keep under `Other` with a one-line rationale.

**Keep in `Other`** — items maintainers or operators care about even if they're not features:

- Security-adjacent dependency / base-image bumps that don't clearly restore broken behavior (borderline cases; when a CVE is named, prefer `Fixes`).
- OpenAPI / API-contract doc updates visible to API consumers (changes to `docs/api/openapi.json` that reflect a real request/response shape change).
- Forwarded-headers / auth-handling / DIAL-connection behavior checks.
- Issue templates, `SECURITY.md`, contributor-facing governance docs.

If you find yourself unsure whether to drop a bullet, ask: *would a customer reading these notes care that this happened?* If no, drop it.

### 5. Rewrite each kept bullet

The raw form is `* <scope-in-parens?> <lowercase phrase> #<issue> (#<PR>)`. Rewrite to:

```
* <Active-voice description of what changed> — <brief why-it-matters or what-it-replaces> #<issue> (#<PR>)
```

Rules in order of importance:

1. **One line per bullet.** No multi-paragraph descriptions. If you need more detail, save it to the companion editorial-notes file (see §8), not the main draft.
2. **Drop any leftover conventional-commit residue** — the CI already strips the type, but drop the trailing `(scope)` fragment the CI leaves in (`(deps)`, `(metrics)`) and replace it with prose.
3. **Drop branch-style slugs.** `async-dial-instead-of-dial-core-client` → `Replace the dial-core client with async-dial`. The PR title is the prompt, not the output.
4. **Use a `—` em-dash for the "why" clause**, not a hyphen or colon.
5. **Backticks for code identifiers**: env vars (`EVAL__APP__MAX_CONCURRENT_EVALUATIONS`, `DIAL_API_KEY`), file paths, config field/property keys (`metrics.ragas.embeddings_model`), class names (`AppSettings`), metric names (`ragas.answer_relevancy`, `exact_match`), package names (`aidial-rag-eval`).
6. **Preserve issue + PR refs at the end** in `#<issue> (#<PR>)` order, or `(#<PR>)` when there is no issue. Don't strip them — these notes ship as the GitHub release body where the numbers auto-link.
7. **Flag regressions explicitly**: `(regression fix)` for items restoring previously-working behavior.
8. **Quote CVE IDs verbatim** for security upgrades: `Upgrade pillow to 12.3.0 to address CVE-2026-XXXXX`.

> This project has no preview-feature gating (no feature flag or per-app feature manifest). If one is later introduced, reinstate the convention: a `[Preview]` prefix for preview-gated features and a `Graduate <feature> to GA — <gate removed>` lead for graduations.

#### Example transformations

Each pair is `raw CI` → `enhanced`. Backticks in the enhanced form denote code identifiers in the actual output.

```
# Adding a "what changed" clause, dropping the residual scope:
- * (metrics) support ragas answer relevancy #40 (#41)
+ * Add the `ragas.answer_relevancy` metric — semantic-similarity scoring backed by a configurable embeddings deployment #40 (#41)

# Replacing a branch slug with the concrete mechanism:
- * configurable-evaluation-concurrency #55 (#56)
+ * Configurable evaluation concurrency — `EVAL__APP__MAX_CONCURRENT_EVALUATIONS` caps in-flight requests, `EVAL__APP__MAX_QUEUE_BACKLOG` bounds the queue #55 (#56)

# Promoting a security bump out of Other/CI into Fixes, naming the advisory:
- * bump pillow from 12.2.0 to 12.3.0 (#24)
+ * Upgrade `pillow` to 12.3.0 to address the transitive image-parsing advisory (#24)

# Marking a regression fix and naming the precise gap:
- * ci issues (#19)
+ * Restore the release pipeline after the `ai-dial-ci` bump broke the Docker build (regression fix) (#19)

# Reclassified (raw had it under Other because it was authored as chore(deps)):
- * update nltk to 3.10.0 (#26)      # KEEP only if CVE-linked; otherwise drop as routine bump

# Folded orphan hotfix commits into a related fix entry:
- * fix sse double-quoted json        (orphan commit, no PR)
- * fix tests                          (orphan commit, no PR)
+ * Stop double-quoting JSON in the streamed evaluation response — progress events now parse on the client (`27a0340`, `1500580`)
```

### 6. Build the `Deployment Changes` section

Add this section **only** when the range introduces at least one env-var, behavioral, or API-contract change. Pick subsections — include only the ones with entries:

```markdown
## Deployment Changes

### New environment variables
<table: Variable | Default | Description>

### Deprecated environment variables
> [!CAUTION]
> Still works, but will be removed in future versions.
<table: Variable | Replacement | Description>

### Removed environment variables
<table: Variable | Reason>

### Behavioral changes
> [!NOTE]
> <one-line explaining the behavioral shift, e.g. a changed default or error-handling shift>
- **<Feature>** — <field / module> (#<PR>)

### DIAL Configuration changes
> [!IMPORTANT]
> <one-line stating the operator-facing change>
>
> **Required migration** (#<PR>):
>
> 1. **Remove** <the legacy config block in DIAL Core / the DIAL Admin metrics registration>.
> 2. **Add** <the new config block(s)> to <exact location in the external system, e.g. the metrics-service deployment entry in DIAL Core / DIAL Admin>. Apply the snippet from PR #<PR> verbatim.

### API / contract changes
> [!NOTE]
> Note removed/renamed endpoints, changed request/response shapes, or status-code changes that break existing API consumers. Point readers at the interactive docs (`/docs`, `/redoc`) and the checked-in schema (`docs/api/openapi.json`). (#<PR>)
```

There is **no database in this service** — it is a stateless FastAPI metrics calculator with no persistence layer or migrations. Do not add a `Database migrations` subsection; if a future release introduces storage, add one then.

#### Which subsection: telling Behavioral, DIAL Configuration, and API/contract apart

These look adjacent but answer different operator questions:

- **Behavioral changes** — *"How does the deployed service behave differently at runtime?"* Default values changing (e.g. a new `EVAL__METRICS__COMMON__DEFAULT_MODEL`), concurrency/queue-limit changes, fallback-resolution behavior, error-handling shifts. Operator does nothing; the change is automatic on upgrade. Uses `> [!NOTE]`.
- **DIAL Configuration changes** — *"What must I change outside this repo for this release to work?"* This service is registered as a deployment in DIAL Core and surfaced in the DIAL Admin Panel's metrics-configuration UI. If a release requires operators to re-register the endpoint, change its DIAL Core deployment entry, or update the supported-models list an admin sees, it belongs here with a numbered **Required migration** list and literal config keys — not buried in Behavioral changes, where operators will miss it.
- **API / contract changes** — *"Did the HTTP contract change in a way that breaks existing API consumers?"* Endpoint additions/removals under `aidial_admin_evaluation_metrics/api/` (`evaluate`, `metrics_list`, `health`), request/response shape changes, new required fields, status-code changes. Diff `docs/api/openapi.json` to confirm. Uses `> [!NOTE]`.

**Crucial — what does *not* belong here**: per-metric / per-request options (a new metric parameter, a per-evaluation config field). Those changes belong in the **Features** bullet body where they're introduced. `Deployment Changes` is for operator-facing concerns: env vars, behavioral shifts, external-config migrations, and API-contract breaks. Don't promote an app-level request field to a deployment concern.

**Don't enumerate sub-properties of a single config block.** Name the top-level key the operator is pasting in and stop there. Inner nested fields (e.g. the individual per-group model overrides under `EVAL__METRICS__…`) are payload the operator gets for free by copying the snippet, not independent operator actions. If a nested key matters enough to flag, it must be a peer of the block being added — verify nesting against `app_config.py` before listing it.

For the env-var table, the `Default` and `Description` columns come from the README **Environment Variables** table (`README.md`), and the canonical variable name from `app_config.py` (§3 rule — code wins). This README table has three columns (`Variable | Default | Description`) — there is no separate `Required` column; when a var is effectively required (like `DIAL_URL`, which raises on startup if empty), the README default column shows `*Required*` — carry that through. Confirm bounds from `Field(...)` constraints in `app_config.py`.

### 7. Pre-release / delta handling

If the target is `<X.Y.Z>-rc.N` with `N ≥ 1`:

- The release covers only what changed since the previous rc — do **not** consolidate or rewrite the predecessor's notes. Each pre-release tag has its own GitHub release page; the consolidation happens at the stable cut (see the **Merge path** section).
- Drop sections that have no entries in the delta (e.g. no `Deployment Changes` if no env vars or API changes landed in this rc).
- Do **not** prepend a "Delta since <prev-rc>" pointer at the top. The CI doesn't emit one and the `-rc.N` version suffix already signals what the release is. Adding a header just creates editorial noise the user has to clean up.

Note on rc numbering: the CI cuts pre-releases off the `development` and `release-*` branches (`.github/workflows/release.yml`), and promotes to stable via the `workflow_dispatch` `promote` input on a `release-*` branch. So `rc.0` is the first cut of a version line, not `rc.1`.

### 8. Save the draft (and optional editorial companion)

Create `claude/release-notes/` if missing, then write:

- **`claude/release-notes/<tag>-draft.md`** — the final notes, ready to paste into the GitHub release body. No preamble, no commentary — just the headings and bullets.
- **`claude/release-notes/<tag>-editorial-notes.md`** *(optional)* — only when there are non-obvious calls worth surfacing to the user:
    - Rename mapping (raw bullet → enhanced bullet) for items where the rewrite is non-trivial.
    - List of items dropped, with one-line reason per item.
    - Open questions for the user (e.g. "Should the `ai-dial-ci` bump PR stay under Other? It's invisible to consumers but visible to release maintainers.").
    - Any place the source-of-truth diverged from the PR body (e.g. canonical env-var name / alias).

### 9. Verify nothing was pushed to GitHub

This skill **never** runs `gh release edit`, `gh release create`, or any write operation against the repo. Everything is drafted in local files — don't push anything or change anything in GitHub. Draft files are the only output. If the user later asks you to apply, that is a separate, explicit request.

## Merge path — assembling a stable cut from enhanced rc notes

A stable `X.Y.Z` ships exactly what its `X.Y.Z-rc.*` pre-releases shipped, plus whatever landed between the last rc and the stable tag. Each rc release body has **already** been through this skill — every bullet is classified, rewritten, and deduped within its own delta. Re-deriving all of that from the raw stable notes throws away wording the user already approved and invites drift. So reuse the rc bullets and reserve fresh work for the post-last-rc commits only.

The raw stable GitHub notes still matter here — not as a bullet source, but as the authoritative **inventory** of what's in the release, so you can prove nothing slipped through the merge.

### M1. Gather the rc chain and the stable inventory

1. `gh release list --limit 30` — every `X.Y.Z-rc.*` tag for this version (ordered `rc.0`, `rc.1`, …) and the previous stable `X.Y'.Z'`.
2. `gh release view <X.Y.Z-rc.N> --json body` for each rc — these enhanced bodies are the bullet source.
3. `gh release view <X.Y.Z> --json body` — the raw stable notes, used as an inventory checklist. Skip if the stable release isn't published yet and use the git range below as the inventory instead.
4. `git log <prev-stable>..<X.Y.Z> --oneline` (full range) and `git log <last-rc>..<X.Y.Z> --oneline` — the second is the **post-last-rc delta**, the only commits no rc has seen.

### M2. Confirm the rc bodies are enhanced

Sample each (see *Mode selection* for the enhanced-vs-raw tell). If one rc is still raw, enhance that rc's delta first — Steps 2–6 over `git log <prev-rc>..<rc>` — before merging it. If most rcs are raw, abandon the merge and run the whole from-scratch **Workflow** on the stable instead.

### M3. Union the bullets

Collect the `Features`, `Fixes`, and `Other` bullets from every rc body. **Copy the enhanced wording exactly — do not re-fetch the PR or rewrite it.** The editorial work is already done; your job is assembly, not re-authoring. Preserve each bullet's trailing `#<issue> (#<PR>)` references character-for-character as the rc wrote them — don't re-parenthesize, reorder, or normalize them (a stray `#283` → `(#283)` is exactly the kind of drift that creeps in when copying by eye).

For ordering, follow the established stable layout rather than a rigid rc-by-rc concatenation: lead with headline features, keep related items together, and place minor enhancements last. Ordering is low-stakes and the user reviews it — don't agonize, but don't fragment the list strictly by rc either.

### M4. Deduplicate and consolidate across the rc boundary

The rcs were edited in isolation, so the union needs reconciliation:

- **A feature touched by more than one rc** — introduced in one rc, refined in a later one (same `#PR`/`#issue`, or a follow-up PR on the same feature) — collapses to one bullet with the most complete wording. Cite both PR numbers in parens when each carried real change.
- **Pre-release-only regression fixes → drop.** When an rc bullet fixes something that broke *within this version's own pre-release cycle* — it carries an `(affects pre-release users of <feature> only)` marker, or it's an orphan `hotfix:` commit patching a feature first shipped in an earlier rc of this same version — leave it out. A consumer upgrading from the previous stable never saw the broken intermediate state, so that feature's own bullet already describes the working result. Fixes for bugs that existed in the *previous stable* are real fixes — keep those.
- **Merge the `Deployment Changes` subsections** — union all `New environment variables` rows into one table; carry over every `DIAL Configuration changes` migration and every `API / contract changes` note; combine `Behavioral changes` into a single block. If two rcs list the same env var with different defaults or descriptions, reconcile to one row and verify the canonical name/default from `app_config.py` (§6 rule — code wins over PR bodies).

### M5. From-scratch pass on the post-last-rc delta only

For the commits in `git log <last-rc>..<X.Y.Z>` (M1.4), run Steps 2–6 of the from-scratch **Workflow** — parse refs, read PR bodies, classify, drop the noise, rewrite, and pull any new deployment changes — then fold the survivors into the unioned sections and tables. If the delta is empty, skip this step; the merge is just the reconciled rc union.

### M6. Reconcile against the stable inventory

Walk every PR/issue number in the raw stable notes (M1.3). Each must resolve to exactly one of:

- **kept** — present in the unioned rc bullets,
- **new** — handled by the M5 delta pass, or
- **dropped** — an internal item the rc passes already excluded. Re-apply §4's drop rules, and **don't resurrect** something the rcs deliberately left out just because it's missing from the union (those internal refactors and routine bumps were dropped on purpose, not overlooked).

Anything that fits none of these three is a genuine gap — surface it in the editorial companion rather than guessing.

### M7. Save

Write the assembled notes to `claude/release-notes/<tag>-draft.md` in the standard Output format. In `claude/release-notes/<tag>-editorial-notes.md`, record: the rcs merged (tag → bullet counts), cross-rc dedup/folds, pre-release-only fixes dropped, post-last-rc delta items added, and any inventory gaps from M6.

## Output format

The file saved to `claude/release-notes/<tag>-draft.md` follows this shape exactly:

```markdown
## Features

* <one bullet per change>

## Fixes

* <one bullet per change>

## Other

* <only consumer- or maintainer-relevant items>

## Deployment Changes

### New environment variables
<table>

### Deprecated environment variables
> [!CAUTION]
> …
<table>

### Behavioral changes
> [!NOTE]
> …
- <item>

### DIAL Configuration changes
> [!IMPORTANT]
> …
>
> **Required migration** (#<PR>):
> 1. **Remove** …
> 2. **Add** … Apply the snippet from PR #<PR> verbatim.

### API / contract changes
> [!NOTE]
> … (#<PR>)
```

Section order: `Features` → `Fixes` → `Other` → `Deployment Changes`. Subsections inside `Deployment Changes` appear in the order: New env vars → Deprecated env vars → Removed env vars → Behavioral changes → DIAL Configuration changes → API / contract changes. (There is no `## CI` section in the enhanced output — CI-typed bullets are either dropped or folded into `Other` per §4.)

A delta `rc` release uses the same shape — no preamble paragraph, no header pointing at the previous rc. A merged stable cut (**Merge path**) uses this same shape too; it just sources its bullets from the rc notes plus the post-last-rc delta rather than from the raw stable notes.

## Return to the main conversation

Return a short summary — five lines or fewer. Include:

- The draft path (`claude/release-notes/<tag>-draft.md`).
- Counts of bullets per section after enhancement.
- Reclassifications that happened (e.g. "moved 1 from CI → Fixes for the security bump").
- Items dropped (count, with one example).
- Whether a `Deployment Changes` section was added and which subsections.
- Any open questions for the user (env-var name/alias disagreement between PR body and source, ambiguous categorization).

Example (from-scratch):

> Drafted `claude/release-notes/0.1.0-rc.1-draft.md`. 4 Features, 2 Fixes, 1 Other. Reclassified 1 from CI → Fixes (`ci(deps)` pillow CVE bump). Dropped 5 internal items (Black sweep, `docs/api` regen, e2e-test skip, nltk routine bump, merge commit). Added Deployment Changes with New env vars (`EVAL__APP__MAX_CONCURRENT_EVALUATIONS`, `EVAL__APP__MAX_QUEUE_BACKLOG`) + Behavioral changes. One open: PR body says `EVAL__DIAL_URL` but the `dial_url` field's `validation_alias` binds to `DIAL_URL` — used the code name; flagged in editorial notes.

Example (merge):

> Drafted `claude/release-notes/0.2.0-draft.md` by merging rc.0 (6F/4Fx/2O), rc.1 (3F/1Fx). Result: 8 Features, 5 Fixes, 2 Other. Merged 2 env-var rows into one table; combined Behavioral changes and carried over the `/evaluate` request-shape API change. Dropped the SSE-JSON hotfix (pre-release-only). Post-rc.1 delta was empty. One open: the `ai-dial-ci` bump PR — keep under Other or drop? flagged in editorial notes.

## Safety rails

- **Never edit GitHub.** No `gh release edit`, no `gh release create`. Drafts only.
- **Never invent items.** Every kept bullet maps to a PR or a commit hash in the range.
- **Never silently rename or drop a PR reference.** The bullet ends with the canonical `#<issue> (#<PR>)` so links resolve on the release page.
- **Verify canonical names from source** (`app_config.py`), not from PR bodies. The `EVAL__` prefix and the `validation_alias` overrides mean the naive name is often wrong; the code is the source of truth.
- **Each rc page stands alone; the stable cut consolidates them.** When the target is a `-rc.N`, never pull sibling-rc notes into it. When the target is the **stable cut** and the rc notes are already enhanced, merging them is the expected path (**Merge path**) — but only ever write the local stable draft; never edit or overwrite the individual rc release pages on GitHub.
- **Match the terseness of the predecessor's notes.** If they're one-liners, your bullets are one-liners.

## Maintenance

Conventions drift as the project grows. If you notice a pattern in the raw CI notes that this skill doesn't handle (a new section the `python_docker_release.yml` workflow emits, a new conventional-commit scope that misroutes items, storage/migrations getting added to the service, a recurring rewrite the user keeps asking for), surface it in your return summary and offer to update this `SKILL.md`. The user can confirm before any edit lands.
