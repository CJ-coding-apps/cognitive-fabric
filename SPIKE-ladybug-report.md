# SPIKE (do not merge): LadybugDB in place of Kùzu 0.11.3

**Status:** spike report. Nothing here is a port, a dependency decision, or a merge request.
**Date:** 2026-11-08. **Pin used for every check:** `ladybug==0.22.3` (latest on PyPI at run time).
**Repos:** `CJ-coding-apps/cognitive-fabric` @ `8789d19` on `spike/ladybug`; `getzep/graphiti` @ `v0.30.2` as a scratch clone only (never pushed, never forked).
**Environments named:** CJ's Mac — macOS 15.5, x86_64, CPython 3.11.13 / 3.12.11 / 3.13.5 / 3.14.10; Linux — `python:3.11-slim` under `docker run --network none`.

**Order deviations (ruled by CJ, 2026-11-08):**
- A3's full profile is written in the order as `.[dev,semantic]`; CI's exact full profile is `.[dev,cloud,semantic]`. Per the ruling, CI's profile was used and the order's narrower wording is an error in the order.
- A4's macOS "switch Wi-Fi off" was replaced by a per-process network denial (`sandbox-exec`), approved by CJ, with a control connection that must fail. The Mac stayed online.
- The order says `uv python install 3.14` after updating uv. The system `uv` is 0.7.19 and its 3.14 index stops at a beta; a scratch `uv` 0.13.7 (`/tmp/lb/uv/bin/uv`) was used to install CPython **3.14.10 final**. The system `uv` was not replaced.

No test was edited or weakened. The branch changes 4 files, 6 insertions and 6 deletions (plus this report).

---

## 1. Verdict

**cognitive-fabric: GO-WITH-CONDITIONS.** With only an import rename in three `db/` modules and the dependency swap, the suite is identical to the Kùzu baseline once the ALGO extension is installed and loaded — 188 passed / 1 skipped (minimal) and 191 / 1 (full), the same as `8789d19`; a real 0.11.3 database migrates with identical table counts and query results; and Ladybug supplies cp314 macOS wheels, so 3.14 works for the minimal profile. The conditions are not cosmetic: ALGO is **not bundled**; it is downloaded from `https://extension.ladybugdb.com/` on first `INSTALL`, cached under `~/.lbdb/extension/0.22.0/<platform>/`, and `LOAD EXTENSION ALGO` is required **per Connection** (a projected graph is per-Connection too). Without that install, 12 tests fail and every graph algorithm is unavailable; the repository docstring that says ALGO is "statically linked into the wheel" is false. On Linux the downloaded extension cannot load in a stock `python:3.11-slim` until `libnetworkit`, `libarrow` and `libgomp` are satisfied, and the current PyPI `networkit` (11.3) fails with an ABI symbol mismatch. A local-first port therefore has to solve extension provisioning before it can claim parity.

**graphiti / docugraph: GO-WITH-CONDITIONS, and the condition is a fork.** Of the 48 Kùzu-parameter tests, 25 passed on Kùzu 0.11.3 and 14 pass on Ladybug; 11 regress and none improve. Every regression has one cause: graphiti filters `None` arguments out of its parameter dict, and Ladybug raises `Parameter <name> not found.` where Kùzu binds NULL. Passing the key explicitly as `None` works on Ladybug (verified on a reduced query), so the fix is small — but it is a change to graphiti, whose Kùzu driver is deprecated upstream and will not receive one. If docugraph is willing to vendor or fork `graphiti-core` and re-run the full suite against that patch, the migration is viable; if it insists on upstream graphiti, the honest answer is NO-GO.

---

## 2. Answers to Q1–Q6

### Q1 — PyPI name, import name, Python API

- **PyPI:** `ladybug` (MIT, no required runtime dependencies). **Import:** `import ladybug`. **Version measured:** `0.22.3`. `requires-python`: `>=3.10,<3.15`.
- **No renames.** The six classes cognitive-fabric uses — `Database`, `Connection`, `AsyncConnection`, `PreparedStatement`, `QueryResult`, `Type` — exist under the same names, and the public method sets are identical:
  - `QueryResult` (19): `check_for_query_result_close`, `close`, `get_all`, `get_as_arrow`, `get_as_df`, `get_as_networkx`, `get_as_pl`, `get_as_torch_geometric`, `get_column_data_types`, `get_column_names`, `get_compiling_time`, `get_execution_time`, `get_n`, `get_next`, `get_num_tuples`, `get_schema`, `has_next`, `reset_iterator`, `rows_as_dict`.
  - `AsyncConnection` (6): `acquire_connection`, `close`, `execute`, `prepare`, `release_connection`, `set_query_timeout`.
- **Added top-level names only:** `ArrowQueryResult`, `ArrowRelTableLayout`, `CSRResult`, `Path`, `constants`, `get_capi_module`, `get_pybind_module`. `kuzu` additionally leaks `os` and `sys`; `ladybug` does not. No name is removed.
- **Behaviour probes, all PASS (A2, scratch script against `ladybug` only):** `execute` without params (`[[1]]`), with params (`['repo1']`), `MERGE` with params, `has_next`, `get_column_names` (`['id','name']`), `get_next` (`['repo1','demo2']`), `get_all`, `rows_as_dict`, `get_as_df`, `close`, `Database(..., read_only=True)`, `AsyncConnection.execute`, `CALL SHOW_CONNECTION('DEPENDS_ON')`, and the `list_transform(nodes(p), …)` variable-length path form. `get_as_df` requires pandas; ladybug, like kuzu, does not declare pandas — it is only in its `dev` extra. The async probe's first failure was my own (`await ac.close()`; `close` is sync in both) and is not a difference.
- **One API-semantic difference** (this is the whole graphiti story): parameter binding. See Q5.

**Evidence: A2.** `module=ladybug version=0.22.3`; all 25 DDL statements (11 node tables, 14 relationship tables) executed verbatim; no API adaptation was needed to run cognitive-fabric's queries.

### Q2 — Does Ladybug accept cognitive-fabric's Cypher?

**Yes, including the algorithms — provided ALGO is installed and loaded.** With the extension loaded, these all returned correct results on a seeded graph (chain `a→b→c→d→e`, triangle `f→g→h→f`):

```
project_graph('g', ['Component'], ['DEPENDS_ON'])   # ok
page_rank('g', dampingFactor := 0.85, ...)          # returned ranks
k_core_decomposition('g') ... k_degree >= 2         # [['f','F',2],['g','G',2],['h','H',2]]
louvain('g')                                        # 3 communities
shortest path a→e                                   # [[['a','b','c','d','e'],4]]
```

Without the extension, the same script fails on `page_rank`, `k_core_decomposition` and `louvain` with:

```
Catalog exception: function weakly_connected_components is not defined.
This function exists in the ALGO extension. You can install and load the extension
by running 'INSTALL ALGO; LOAD EXTENSION ALGO;'.
```

The DDL forms (`CREATE NODE TABLE IF NOT EXISTS … PRIMARY KEY …`, `CREATE REL TABLE … FROM … TO …`), `MATCH`, `MERGE`, `SET`, `RETURN`, list parameters and `$parameter` binding all parse and run. The in-suite proof is A3: with ALGO, the ported suite is byte-for-byte the same pass/fail/skip set as the baseline.

**Evidence: A2 and A3 (below).**

### Q3 — Are the algo (and FTS/vector) extensions bundled and usable offline?

**Not bundled.** The 0.22.3 wheel contains only the engine (`_lbug.cpython-311-darwin.so` on this Mac); there is no ALGO binary inside it.

- Before any install, `LOAD EXTENSION ALGO` fails:
  ```
  Binder exception: Extension: algo is an official extension and has not been installed.
  You can install it by: install algo.
  ```
- `INSTALL ALGO` succeeds with network and downloads from **`https://extension.ladybugdb.com/`** (string in the binary), caching under:
  - macOS: `~/.lbdb/extension/0.22.0/osx_amd64/algo/`
  - Linux: `~/.lbdb/extension/0.22.0/linux_amd64/algo/`
- After one install, `LOAD EXTENSION ALGO` works **offline** (A4, seeded HOME).
- **LOAD is per Connection, not per Database.** A second `Connection` sees:
  ```
  Catalog exception: function k_core_decomposition is not defined. This function
  exists in the ALGO extension. ...
  ```
  until it runs `LOAD EXTENSION ALGO` itself. A projected graph is also per Connection: a second connection that did not create it sees `Projected graph g does not exist.` even after loading ALGO.
- **Other extensions exist and download the same way.** `INSTALL`/`LOAD` succeeded for `FTS`, `VECTOR`, `JSON` and `HTTPFS`; the cache shows `libfts.lbug_extension`, `libvector.lbug_extension`, `libjson.lbug_extension`, `libhttpfs.lbug_extension`. Neither repo needs them: cognitive-fabric uses only ALGO, and graphiti's Kùzu driver deliberately avoids full-text indexes.

**Offline proof (A4, macOS).** Each run began with the control required by the ruling, in the same process:

```
$ /usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' \
    /tmp/lb/venvs/a1-3.11/bin/python -c \
    'import socket; socket.create_connection(("pypi.org",443),timeout=5)'
control blocked: gaierror: [Errno 8] nodename nor servname provided, or not known
```

- With an empty `HOME` (no cache): `LOAD EXTENSION ALGO` fails with the "has not been installed" binder error; `page_rank`, `k_core_decomposition` and `louvain` fail; `project_graph` and shortest path still work (both are built in).
- With a seeded `HOME` (extension installed earlier, network still denied): `LOAD` succeeds and all four algorithms return results, as pasted in Q2.

**Linux (A4, `docker run --network none`, `python:3.11-slim`).** Control:
```
control blocked: gaierror: [Errno -3] Temporary failure in name resolution
```
DDL, `project_graph` and shortest path work. `LOAD EXTENSION ALGO` from the cached `linux_amd64` extension fails:
```
libnetworkit.so: cannot open shared object file: No such file or directory
```
`ldd` on the extension shows missing `libnetworkit.so`, `libarrow.so.2600`, `libgomp.so.1`. Installing `pyarrow==26.0.1`, `networkit==11.3`, `libgomp1` and setting `LD_LIBRARY_PATH` to the site-packages root gets further but dies on an ABI mismatch:
```
undefined symbol: _ZTVN9NetworKit3BFSE
```
`networkit` 11.3 is the latest on PyPI, so pip cannot supply a matching library. This is a **Linux blocker for the algorithm features**, not for DDL or plain Cypher.

### Q4 — Can a Kùzu 0.11.3 database be moved to Ladybug?

**Yes, with `EXPORT DATABASE` → `IMPORT DATABASE`. Direct file reuse fails.**

Direct open of the Kùzu file with `ladybug.Database(path)`:
```
RuntimeError : Runtime exception: Unable to open database. The file is not a valid Lbug database file!
```
After import, counts and query results were **identical** (A6): 1017 `Symbol`, 120 `File`, 1017 `DEFINED_IN` edges, all other tables 0; kinds `function_definition` 831 / `class_definition` 186; the same top-five files in the same order. The procedure is in §5.

### Q5 — Does Ladybug accept the Cypher graphiti v0.30.2's Kùzu layer sends?

**Almost. It rejects 11 tests that passed on Kùzu, all through one semantic difference in parameter binding.**

- **B1 baseline** (Kùzu 0.11.3): `21 failed, 348 passed, 36 skipped` in 21.27 s; 48 tests carry `[GraphProvider.KUZU]`, of which **25 passed, 18 failed, 5 skipped**.
- **B2** (only `import kuzu` → `import ladybug as kuzu` in `graphiti_core/driver/kuzu_driver.py`, package swapped): `32 failed, 337 passed, 36 skipped` in 21.65 s; 48 Kùzu tests: **14 passed, 29 failed, 5 skipped** — **11 PASSED→FAILED, 0 FAILED→PASSED**. The 11 are listed in §6. The error is `RuntimeError: Parameter expired_at not found.` or `Parameter reference_time not found.` — 39 occurrences (22 and 17) across the 11 tests.
- **Cause, proved with a minimal repro:**

| call | Kùzu 0.11.3 | Ladybug 0.22.3 |
|---|---|---|
| no `parameters` argument | binds NULL | binds NULL |
| `parameters={}` | binds NULL | binds NULL |
| non-empty dict, a **referenced** key absent | **binds NULL** | **`RuntimeError: Parameter <name> not found.`** |
| non-empty dict, every referenced key present | works | works |
| non-empty dict, an **unreferenced** extra key | `RuntimeError: Parameter <name> not found.` | **ignored** |

graphiti's `KuzuDriver.execute_query` filters `None` values out (`{k: v for k, v in kwargs.items() if v is not None}`), so `expired_at`/`reference_time` are absent from a non-empty dict on edge writes. Kuzu tolerated that; Ladybug does not.

- **Candidate fix, verified but not applied:** pass the optional keys explicitly as `None`. On Ladybug:
  ```
  parameters={'value':'v','expired_at':None} → [[1, None]]
  ```
  Applying that to graphiti is a change to graphiti, which is outside this spike and, per the non-goals, was not done. It must be re-run against all 48 Kùzu tests before it can be called a fix.
- **What works under Ladybug:** all the other Kùzu-parameter paths that pass in B1 — node/episode/community CRUD and edges, basic search, and the driver's DDL. graphiti does not use ALGO, so it needs no extension install.
- **Skips are the driver's own:** 4 full-text tests (`Skipping as fulltext indexing not supported for Kuzu`) and `get_relevant_nodes` (`Skipping as tests fail on Kuzu`) skip identically in both runs. They are not regressions; they are pre-existing gaps (see B3).

### Q6 — Platform floors

**Wheels install without a source build** (`pip install --only-binary :all:`), recorded in fresh venvs on this Mac and in Linux:

| Python | macOS x86_64 | Linux x86_64 |
|---|---|---|
| 3.11 | `ladybug-0.22.3-cp311-cp311-macosx_15_0_x86_64.whl` | `ladybug-0.22.3-cp311-cp311-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl` |
| 3.12 | `…-cp312-cp312-macosx_15_0_x86_64.whl` | — (not run; wheel exists: `manylinux_2_27_x86_64.manylinux_2_28_x86_64`) |
| 3.13 | `…-cp313-cp313-macosx_15_0_x86_64.whl` | — (not run; wheel exists) |
| 3.14 | `…-cp314-cp314-macosx_15_0_x86_64.whl` | — (not run; wheel exists) |

PyPI also publishes arm64 macOS (`macosx_15_0_arm64`), arm64/x86_64 manylinux (`manylinux_2_26_aarch64.manylinux_2_28_aarch64`, `manylinux_2_27_x86_64.manylinux_2_28_x86_64`), musllinux, and Windows wheels for cp310–cp314. So: **macOS floor 15.0, glibc floor 2.27 (x86_64) / 2.26 (aarch64), Python 3.10–3.14.**

Against cognitive-fabric's current claims:

| | Today (README + `requires-python`) | Under Ladybug |
|---|---|---|
| Python | 3.11–3.13 (`>=3.11,<3.14`) | 3.10–3.14 available; A5 measured 3.11–3.14 |
| macOS | tested on macOS 15 | wheel requires macOS 15.0+; older macOS builds from source |
| Linux | tested | glibc 2.27+ x86_64 (2.26+ arm64); musllinux also published |
| Windows | explicitly not claimed | wheels exist; not tested here |

A5: on 3.14.10 final, the **minimal** profile reproduces A3 exactly (`12 failed, 176 passed, 1 skipped` without ALGO; `188 passed, 1 skipped` with it). The **full** profile cannot resolve on this Mac for a reason unrelated to Kùzu:
```
fastembed>=0.8.0 depends on onnxruntime>=1.24.2 ...
hint: You require CPython 3.14 (`cp314`), but we only found wheels for `onnxruntime`
(v1.19.2) ... cp38, cp39, cp310, cp311, cp312
hint: Wheels are available for `onnxruntime` (v1.31.1) on ... macosx_14_0_arm64 ...
```
i.e. the full profile's 3.14 ceiling is fastembed/onnxruntime on **macOS x86_64**, not Ladybug. Lifting cognitive-fabric's `requires-python` on Ladybug alone would admit 3.14 for the minimal profile and still fail for the full one.

---

## 3. API diff table (`kuzu` 0.11.3 → `ladybug` 0.22.3)

| Item | `kuzu` 0.11.3 | `ladybug` 0.22.3 | Action |
|---|---|---|---|
| Distribution | `kuzu` | `ladybug` | change pin |
| Import | `import kuzu` | `import ladybug` | rename, or `import ladybug as kuzu` |
| `Database(path, read_only=…)` | present | present, same signature | none |
| `Connection`, `AsyncConnection` | present | present, same 6-method public surface | none |
| `PreparedStatement`, `QueryResult`, `Type` | present | present, same 19-method `QueryResult` surface | none |
| `execute(query, parameters=…)` | dict must not contain extra keys; **missing referenced keys bind NULL** | extra keys ignored; **missing referenced keys raise** | audit callers (graphiti) |
| `get_next` / `get_all` / `get_as_df` / `rows_as_dict` | present | identical | none |
| `close` | present | identical | none |
| DDL | accepted | accepted, 25/25 statements | none |
| `CALL SHOW_CONNECTION` columns | `source table name` / `destination table name` | same | none |
| Extensions | ALGO statically linked | not bundled; `INSTALL` + per-connection `LOAD` | provisioning work |
| Direct Kùzu file open | n/a | `RuntimeError: … not a valid Lbug database file!` | migrate via export/import |
| Top-level extras | — | `ArrowQueryResult`, `ArrowRelTableLayout`, `CSRResult`, `Path`, `constants`, `get_capi_module`, `get_pybind_module` | none |
| Top-level leakage | `os`, `sys` | none | none |

The only source change cognitive-fabric needs is the import rename in `connection_manager.py` (type-only and runtime), `query_executor.py` (type-only), and `schema_manager.py` (type-only), plus `pyproject.toml`; 6 insertions, 6 deletions.

---

## 4. Platform floors

See the Q6 table. In one line: **Ladybug widens the interpreter range (3.10–3.14) and narrows the macOS floor to 15.0**; glibc 2.27 (x86_64) / 2.26 (aarch64). cognitive-fabric's current macOS-15-tested claim already meets the macOS floor. Windows wheels exist but are untested here and remain unclaimed.

Two side notes for a real change:
- `pyproject.toml`'s dependency comment still says "kuzu is archived upstream (0.11.3 is the final release)" above the `ladybug` pin. It is stale on the spike branch and must be rewritten in a real port.
- `graph_projection.py`'s docstring claims ALGO is "statically linked into the wheel". It is false for 0.22.3; a real port must correct it and add a runtime check (or install step) for the extension.

---

## 5. Migration procedure that worked (A6)

Performed on the Mac with `kuzu==0.11.3` and `ladybug==0.22.3` in separate venvs.

1. **Create and populate the source graph with cognitive-fabric on Kùzu:**
   ```bash
   cognitive-fabric init /tmp/lb/mig/kuzu-db
   cognitive-fabric fabric-ingest /tmp/lb/mig/kuzu-db cognitive-fabric \
       --path /Users/james/projects/Cognitive-Fabric-v1
   ```
   Output: `Ingested: 1039 symbols, 120 files, 1039 DEFINED_IN edges` (semantic indexing skipped; no lancedb).
2. **Export it.** There is no CLI verb for this; run it through the pinned driver:
   ```python
   import kuzu
   c = kuzu.Connection(kuzu.Database("/tmp/lb/mig/kuzu-db"))
   c.execute("EXPORT DATABASE '/tmp/lb/mig/export' (format='csv')")
   ```
3. **Do not try to open the Kùzu file with Ladybug.** It fails with `RuntimeError : Runtime exception: Unable to open database. The file is not a valid Lbug database file!`
4. **Import into a fresh Ladybug database** (no prior `init` was needed; `IMPORT DATABASE` creates the tables from the CSVs):
   ```python
   import ladybug
   db = ladybug.Database("/tmp/lb/mig/lb-db")
   c = ladybug.Connection(db)
   c.execute("IMPORT DATABASE '/tmp/lb/mig/export'")
   ```
5. **Verify before switching.** Counts per node and relationship table, plus fixed queries, must match. Measured — identical on both sides:
   ```
   node Symbol: 1017      node File: 120        rel DEFINED_IN: 1017   (all other tables 0)
   Q1 Symbol count: [[1017]]
   Q2 File count: [[120]]
   Q3 DEFINED_IN edge count: [[1017]]
   Q4 symbols by kind: [['function_definition', 831], ['class_definition', 186]]
   Q5 top files: entity.py 41, core/interfaces.py 37, test_docs_consistency.py 34,
                 types/entities.py 29, test_optimizer_limits.py 29
   ```
6. **For algorithms, provision the extension:** with network, `INSTALL ALGO` once; then `LOAD EXTENSION ALGO` on **every** connection before `project_graph`/`page_rank`/`louvain`/`k_core_decomposition`. The cache under `~/.lbdb/extension/0.22.0/<platform>/` makes later loads offline.

Not tested: importing into a database that already contains data; migrating a graph with rows in the decision/rule/requirement tables (this ingest populated only Symbol/File/DEFINED_IN).

---

## 6. Cypher and test differences (A3, B2) and B3's uncovered statements

### 6.1 cognitive-fabric (A3)

Commands (CI's exact ones, both profiles):
```bash
pytest tests/unit/ tests/integration/ tests/e2e/ -v --tb=short -rs
```

| Run | Minimal `.[dev]` | Full `.[dev,cloud,semantic]` |
|---|---|---|
| Baseline, `8789d19` + kuzu 0.11.3 | **188 passed, 1 skipped** (92.23 s) | **191 passed, 1 skipped** (88.06 s) |
| Port, no ALGO | **12 failed, 176 passed, 1 skipped** (82.98 s) | **12 failed, 179 passed, 1 skipped** (94.18 s) |
| Port + ALGO installed and loaded per connection | **188 passed, 1 skipped** (86.97 s) | **191 passed, 1 skipped** (128.02 s) |

Skips are the same in every run: minimal skips `test_vector_store.py` (no lancedb); full skips `test_fabric_services.py:177` (`[semantic]` installed, full profile).

The 12 failures without ALGO are all the same error (`weakly_connected_components is not defined … ALGO extension`):
```
tests/integration/test_fabric_repos.py::TestGraphProjectionIsolation::test_projection_names_are_unique_per_call
tests/integration/test_optimizer_parity.py::TestOperatorDeletionCap::test_the_caller_cannot_lift_the_cap
tests/integration/test_optimizer_parity.py::TestOperatorDeletionCap::test_the_cap_holds_under_aggressive
tests/integration/test_optimizer_parity.py::TestOperatorDeletionCap::test_unset_means_the_strategys_own_limit
tests/integration/test_optimizer_parity.py::TestOptimizerParity::test_analysis_id_reuse_in_optimize
tests/integration/test_optimizer_parity.py::TestOptimizerParity::test_analyze_returns_analysis_id
tests/integration/test_optimizer_parity.py::TestOptimizerParity::test_optimize_dry_run_no_deletions
tests/integration/test_optimizer_parity.py::TestOptimizerParity::test_optimize_requires_confirm_when_not_dry_run
tests/integration/test_services.py::TestGraphServices::test_graph_statistics
tests/integration/test_snapshot_service.py::TestAFailedSnapshot::test_abort_leaves_every_row_where_it_was
tests/integration/test_snapshot_service.py::TestAFailedSnapshot::test_an_explicit_opt_out_still_deletes
tests/integration/test_snapshot_service.py::TestSnapshotRoundTrip::test_a_rollback_restores_every_row_the_optimizer_deleted
```
With the extension, all 12 pass and no other test changes state. That is the whole cognitive-fabric Cypher gap.

**Harness category (ruled):** 9 test files mention Kùzu (`conftest.py`, `test_fabric_handler.py`, `test_fabric_repos.py`, `test_fabric_schema.py`, `test_fabric_services.py`, `test_kuzu_operations.py`, `test_optimizer_parity.py`, `test_repos_extra.py`, `test_snapshot_service.py`). **None imports `kuzu` directly** (`grep -rE '^\s*(import kuzu|from kuzu)' tests` is empty), so no test failed merely because the module was absent, and no test file was edited.

### 6.2 graphiti (B1/B2)

Environment: scratch clone of `getzep/graphiti` at `v0.30.2`, Python 3.11.13.
Switches (from `tests/helpers_test.py`): `ENABLE_KUZU=1 DISABLE_NEO4J=1 DISABLE_FALKORDB=1`; Neptune is disabled unconditionally in that file.

```bash
ENABLE_KUZU=1 DISABLE_NEO4J=1 DISABLE_FALKORDB=1 python -m pytest tests -v
```

Seven provider-SDK modules were excluded with `--ignore` because their SDKs are not installed (one would pull torch); they do not touch the Kùzu driver:
`tests/llm_client/test_anthropic_client.py`, `tests/llm_client/test_anthropic_client_int.py`, `tests/llm_client/test_gemini_client.py`, `tests/embedder/test_gemini.py`, `tests/embedder/test_voyage.py`, `tests/cross_encoder/test_gemini_reranker_client.py`, `tests/cross_encoder/test_bge_reranker_client_int.py`.
Packages added for collection, beyond `graphiti-core[kuzu]` + pytest + pytest-asyncio: **`httpx`** (openai 3.46.0 installed `httpx2` instead).

Baseline failures (21) are pre-existing and fail identically in both runs; they were excluded from the pass/fail comparison:
- 11 × `test_add_triplet` (`zip() argument 2 is shorter than argument 1` / NodeNotFound);
- 5 × `test_entity_exclusion_int` (LLM/`OPENAI_API_KEY`);
- `test_graphiti_int::test_graphiti_init` (`OPENAI_API_KEY`);
- `test_edge_int::test_entity_edge` (fails in both, but its error changes from an assertion to the parameter error);
- 3 × `test_search_security` FalkorDB-only tests (falkordb package absent).

The 11 regressions (all `tests/test_graphiti_mock.py[…]`):
```
test_add_bulk
test_determine_entity_community
test_edge_bfs_search
test_edge_similarity_search
test_filter_existing_duplicate_of_edges
test_get_community_clusters
test_get_embeddings_for_edges
test_get_relevant_edges_and_invalidation_candidates
test_node_bfs_search
test_node_distance_reranker
test_remove_episode
```
All fail on `Parameter expired_at not found.` or `Parameter reference_time not found.` (22 + 17 = 39 occurrences). The failing Cypher is graphiti's edge write, e.g.:
```
MERGE (source)-[:RELATES_TO]->(e:RelatesToNode_ {uuid: $uuid})-[:RELATES_TO]->(target)
SET e.group_id = $group_id, ..., e.expired_at = $expired_at, ... e.reference_time = $reference_time ...
```
with a parameter dict that omits those keys because their values are `None`.

No Cypher text change was needed; no statement was rejected as syntax. The only difference is the binding rule above.

### 6.3 B3 inventory and uncovered statements

Inventory (measured on the `v0.30.2` tree):

- **14** Python files under `graphiti_core/driver/kuzu/` (2 are `__init__.py`, 1 is `record_parsers.py`; **11** operation modules contain hand-written Cypher).
- Cypher-keyword lines (`grep -E "MATCH |MERGE |CREATE |RETURN |CALL |UNWIND "`) by module: `search_ops` 21, `entity_node_ops` 14, `episode_node_ops` 13, `graph_ops` 12, `entity_edge_ops` 12, `community_node_ops` 9, `saga_node_ops` 7, `episodic_edge_ops` 6, `next_episode_edge_ops` 5, `has_episode_edge_ops` 5, `community_edge_ops` 5.
- **104** `GraphProvider.KUZU` branches across `graphiti_core` (drivers, nodes, edges, search, bulk, maintenance).

Coverage by the 48 Kùzu-parameter tests:

- **Exercised:** entity/episode/community node operations; entity/episodic/community edge operations; search operations (similarity, BFS, rerankers, and the non-skipped search paths); graph maintenance/init; bulk add; record parsing.
- **Not exercised by any Kùzu test (residual risk):**
  - `saga_node_ops`, `has_episode_edge_ops`, `next_episode_edge_ops` — no Kùzu-parameter test creates a saga, links an episode to a saga, or writes a next-episode edge;
  - every full-text-index statement (there is no FTS index creation in the Kùzu driver; 4 tests skip by design: edge/node/episode/community fulltext);
  - the `get_relevant_nodes` query (skipped with "tests fail on Kuzu");
  - the 11 paths that were exercised in B1 but regress in B2 — under Ladybug their statements are unverified until the parameter patch is made and the suite re-run.

This mapping is module/statement-class level, not a per-query-string census; anything not reached by a test above is residual risk, not evidence of correctness.

---

## 7. What a real port would change (estimate, not an implementation)

### cognitive-fabric

| File | Change | Rough size |
|---|---|---|
| `pyproject.toml` | `kuzu==0.11.3` → `ladybug==0.22.3`; rewrite the stale "kuzu is archived" comment; optionally widen `requires-python`/classifiers for 3.14 | ~10–15 lines |
| `src/cognitive_fabric/db/connection_manager.py` | import rename; extension provisioning: `INSTALL ALGO` policy (or a vendored extension), `LOAD EXTENSION ALGO` on every connection, and a clear failure if unavailable | ~10–40 lines |
| `src/cognitive_fabric/db/query_executor.py`, `schema_manager.py` | type-checking import rename | 2 lines |
| `src/cognitive_fabric/repositories/graph_projection.py` | delete the false "statically linked" claim; state the per-connection load requirement | 1 paragraph |
| new/updated tests and docs | an extension-availability test; README install/platform section; migration note | small |
| provisioning (the real work) | decide how a local-first install obtains the extension: first-run download (network), a separately distributed extension, or a build-time bundle | design decision, not LOC |

Total code: **well under 150 lines**. The cost is the offline-provisioning decision and the Linux shared libraries.

### graphiti / docugraph

| File | Change | Rough size |
|---|---|---|
| `graphiti_core/driver/kuzu_driver.py` | `import ladybug as kuzu` | 1 line |
| `graphiti_core/driver/kuzu_driver.py` (or call sites) | keep optional keys in the parameter dict as explicit `None` instead of filtering them | ~1–5 lines, plus re-run |
| `docugraph/pyproject.toml` `[graph]` | depend on the patched graphiti (git source or vendored) and `ladybug` instead of `kuzu` | 1–3 lines |
| docugraph source | none — it only names `KuzuDriver`; no direct `kuzu` import | 0 |

Code size is trivial; the governance cost is not. Upstream graphiti deprecated its Kùzu driver (graphiti #1548), so the patch has no upstream home. A real move means owning a fork or vendor, with the 21 pre-existing baseline failures still to triage.

---

## 8. Assumptions made and not verified

1. **A4's offline method** was `sandbox-exec` on macOS (process-only `deny network*`) and `docker --network none` on Linux, per CJ's ruling — not Wi-Fi off. The control probe blocks **name resolution**; a connection to a literal IP address was not separately attempted.
2. **A3's full profile** is `.[dev,cloud,semantic]` (CI), per CJ's ruling; the order's `.[dev,semantic]` is an order error.
3. **graphiti's seven excluded provider modules** were excluded, not fixed. They do not touch the Kùzu driver, but their tests were not run, so any indirect interaction is unverified.
4. **graphiti's 21 baseline failures** were not triaged beyond classification. They are pre-existing on Kùzu 0.11.3 and excluded from the comparison; the three FalkorDB tests fail because the falkordb package is absent, not because of Kùzu.
5. **B2 changed only the import.** No parameter adaptation was applied. The explicit-`None` fix was proven on a reduced query only; its effect on all 48 Kùzu tests is unmeasured.
6. **3.14 full profile was not run.** Only the minimal profile was measured; the full profile cannot resolve on macOS x86_64 because of fastembed/onnxruntime, independent of Ladybug.
7. **Linux was tested only on Python 3.11**, and only for A1 install plus the A4 algorithm probe — not the full test suite. cp312–cp314 Linux wheels exist but were not installed.
8. **`get_as_df` needs pandas**, which Ladybug does not declare (only its `dev` extra does). Same shape as kuzu; a deployment that calls `get_as_df` must install pandas itself.
9. **FTS/VECTOR/JSON/HTTPFS** were installed and loaded, but no functional test of those extensions was run; only their presence and caching were observed.
10. **A6 migrated one ingest** (1017 symbols, 120 files). The decision/rule/requirement/context tables were empty, so migration of populated rows in those tables is untested.
11. **Import into a non-empty database** was not tested; the measured path imports into a fresh path.
12. **No performance benchmarking** was done (non-goal). Suite wall times: full profile 88.06 s baseline vs 128.02 s port+ALGO (1.45×, not >5×); minimal 92.23 s vs 86.97 s.
13. **`uv`:** the system binary remains 0.7.19; a scratch `uv` 0.13.7 installed CPython 3.14.10 into `~/.local/share/uv/python/`. That interpreter remains on disk after cleanup.
14. **The extension URL** (`https://extension.ladybugdb.com/`) is a string read from the binary; the exact per-extension request path was not captured.
15. **No docugraph code was changed or run.** Q5's impact on docugraph's add/search paths is inferred from graphiti's call graph and the 11 failing mock tests, not from a docugraph end-to-end run.
