# Artifact: altk-evolve (Middleware 2026, paper #332)

Evaluator guide for *"Memory as Middleware for Self-Improving AI Agents"* (Big Ideas).

This repository holds the evaluation guide (this file) and `smoke_test.py`. The artifact itself is the altk-evolve release named below.

| | |
|---|---|
| **Badges requested** | Artifacts Available, Artifacts Functional |
| **Not requested** | Results Reproduced (see *Out of scope*) |
| **Repository** | https://github.com/AgentToolkit/altk-evolve (Apache-2.0) |
| **Evaluate exactly** | release **v1.3.0**, commit **`703d033`** |
| **Also on PyPI** | `pip install "altk-evolve==1.3.0"` |
| **Archival copy** | This exact release will be deposited on Zenodo; the DOI will be added to the submission before 3 November 2026. |

## What the artifact contains

altk-evolve is the reference implementation of memory middleware described in Section 4 of the paper: a memory layer between agents and storage, with pluggable storage backends, an agent-facing tool surface over MCP, typed memory entities with provenance and visibility, extraction of reusable guidelines from agent trajectories, and bindings for four agent hosts.

## Requirements

- Linux or macOS, x86-64 or ARM. No GPU. About 3 GB of free disk for the full dependency set.
- Python 3.12 or newer. We use [`uv`](https://docs.astral.sh/uv/) below; plain `pip` also works.
- **No API key is needed** for the steps in this guide. Components that call an LLM (trajectory-to-guideline extraction, conflict resolution) need an OpenAI-compatible key and are optional here; see *Optional: LLM-backed components*.

Tested on a fresh Ubuntu 24.04 container with Python 3.12.

## Install (about 3 minutes)

```bash
git clone https://github.com/AgentToolkit/altk-evolve.git
cd altk-evolve
git checkout v1.3.0            # commit 703d033
uv venv --python 3.12 .venv && source .venv/bin/activate
uv sync --all-extras           # installs the pgvector, Milvus, and other optional backends
```

## Run: five checks, about 6 minutes in total

**1. Test suite** (about 1 minute):
```bash
python -m pytest -q
```
Expected: `1261 passed, 4 skipped, 329 deselected`. The deselected tests are marked `llm` or `e2e` and need an API key; the repository's `pyproject.toml` excludes them by default.

**2. Keyless smoke test of the middleware surface** (a few seconds). From the altk-evolve checkout:
```bash
curl -fsSLO https://raw.githubusercontent.com/jayaramkr/Middleware-2026-artifact-evaluation/main/smoke_test.py
python smoke_test.py
```
Expected: `9/9 checks passed`. The script exercises the operations described in Section 4.1 and Section 4.2 on the filesystem backend: namespace creation, typed entities (a guideline and a fact), type-filtered retrieval, publish and unpublish (private-by-default visibility across namespaces), preserved provenance metadata, and delete. It writes to a local directory and needs no services.

**3. Host bindings** (about 2 minutes):
```bash
python plugin-source/build_plugins.py check          # exit code 0: every host binding matches its single source
python -m pytest -q tests/platform_integrations      # expected: 302 passed
```

**4. MCP server** (the agent-facing interface):
```bash
python -m altk_evolve.frontend.mcp --help   # stdio (default) or SSE transport
```
The log line "Evolve UI dist directory not found" is expected. The optional web UI must be built separately with `npm`, and the evaluation does not need it.

**5. End-to-end tests against a live MCP server and real storage** (about 30 seconds). Checks 1–3 use mocked backends where a database would otherwise be required. This check does not: it starts the MCP server and runs the operations against real storage on the filesystem backend.
```bash
python -m pytest -q -m e2e -o addopts="" tests/e2e/test_mcp.py tests/e2e/test_sharing.py \
  -k "filesystem and not save_trajectory and not user_facts"
```
Expected: `13 passed, 17 deselected`. The 13 tests cover entity create and delete, publish and unpublish, cross-namespace public discovery, and metadata patching. The deselected tests either call an LLM (trajectory-to-guideline extraction, user-fact extraction) or target the Milvus backend.

## How the paper's claims map to the artifact

| Paper claim | Where in the paper | Where in v1.3.0 | How to check |
|---|---|---|---|
| Two-sided pluggability: one store abstraction, three interchangeable backends | §3.3; Table 1 | `altk_evolve/backend/base.py` (`BaseEntityBackend`); `filesystem.py`, `postgres.py` (pgvector), `milvus.py` | Backend unit tests (50 pass); check 1 |
| Agent-facing tool surface over a standard protocol | §4.2 | `altk_evolve/frontend/mcp/mcp_server.py` | Check 4; check 2 exercises the same operations through the client |
| Typed memory: typed entities with trigger, provenance, ownership, visibility | §3.2; §4.1 | `altk_evolve/schema/core.py`; metadata conventions in `mcp_server.py` | Check 2 |
| Private-by-default visibility; deliberate publishing; owner-checked delete | §3.5; §3.7 | `publish_entity`, `unpublish_entity`, `delete_entity` in `mcp_server.py`; `get_public_entities` in the client | Check 2 |
| Extraction from trajectories: segmentation, generalization, clustering and consolidation | §4.3 | `altk_evolve/llm/guidelines/` (`segmentation.py`, `clustering.py`); `EvolveClient.consolidate_guidelines` | Code inspection; unit tests with a mocked LLM in check 1; live runs need a key |
| Host-native interposition: one layer, four hosts | §3.4; §4.2, Table 2; §5 | `platform-integrations/` (`claude`, `codex`, `claw-code`, `bob`); `plugin-source/` | Check 3 |
| Lifecycle governance: retention, deletion, audit | §3.8; Table 1 | `altk_evolve/retention/`; the retention and compliance MCP tools | Retention unit tests in check 1 |

**Differences between the paper and v1.3.0.** v1.3.0 was released after the paper was finalized.
- The paper says consolidation *and inspection* are kept off the agent's tool surface. In v1.3.0, inspection is available over MCP as read-oriented tools (`list_entities`, `get_entity`, `patch_entity_metadata`). Consolidation is still available only through the client library and CLI, as the paper describes.
- Table 1 lists retention and eviction policy as open directions. v1.3.0 ships retention policies and scheduling, which goes beyond what the paper claims.

## What the tests verify, and their limits

Checks 1 to 5 cover every claim in the table above at the level of mechanism. Three limits apply.
- **Database backends.** The pgvector and Milvus unit tests run against mocked database clients. Real-storage behavior is verified for the filesystem backend (checks 2 and 5). The end-to-end suite can also run against embedded Milvus Lite; it downloads a roughly 90 MB embedding model (`sentence-transformers/all-MiniLM-L6-v2`) from Hugging Face on first use, so it needs network access. A real pgvector run needs a PostgreSQL server with the `vector` extension.
- **LLM-dependent output.** The extraction pipeline, conflict resolution, and consolidation are tested with a mocked LLM. The tests verify the mechanism, for example that support counts are conserved when guidelines are merged, but not the quality of what a real model generates.
- **Live host runs.** The host sandbox tests need Docker and the host products themselves. Check 3 verifies the bindings instead.

## Out of scope, and why

- **Purpose-directed gisting and tiered gist storage (§4.4), and the gist-compaction entry in Table 1.** This mechanism is not part of the v1.3.0 release, so this artifact makes no claim about it.
- **The AppWorld results (§5, Table 3).** The release contains the memory layer, not the experiment harness. Reproducing Table 3 requires the AppWorld benchmark environment and a GPT-4.1 agent, with nontrivial API cost. You will need to run a React agent on the train and dev partitions of Appworld, altk-evolve will then extract guidelines, and then run the react agent on the test-normal split -- this will take hours and will cost around $200. That is why we request Available and Functional, not Results Reproduced. The claim §5 rests on is that memory is a separable layer: the agent and model are unchanged, and only the memory layer differs. That claim concerns the architecture, and checks 1–4 cover it.
- **Live runs inside the host products.** Claude Code, Codex, Claw Code, and IBM Bob need their own installations and accounts. Check 3 verifies instead that all four bindings are generated from one source and pass their integration tests.

## Optional: LLM-backed components

With an OpenAI-compatible endpoint configured (`OPENAI_API_KEY`, and optionally `OPENAI_BASE_URL`), the extraction pipeline can run on real trajectories through the MCP `save_trajectory` tool, and the key-gated tests can run with `python -m pytest -m llm`. This is not needed for the requested badges.

## Contact

The authors are available throughout the evaluation period through HotCRP.
