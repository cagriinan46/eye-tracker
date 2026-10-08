# Local data inventory and private transfer

Verified: **2026-10-08, Europe/Istanbul** on Çağrı's Mac. A Git clone does not
contain these local captures, models or one-shot provenance. **Availability of
all listed local assets on Fatih's computer is UNVERIFIED until he checks.**
No transfer occurred during this handoff.

## Inspection boundary and critical identities

The inventory used filesystem names/sizes and opaque streaming SHA-256 hashing,
without decoding any capture JSON/CSV, inspecting targets, or calculating
experimental outcomes. Only the separate one-shot provenance marker was read
to confirm its historical status/identities. Both geometry byte hashes and sizes
matched the recorded values; the marker matched its original recorded hash.
The table contains metadata, not participant geometry or raw frames. No local
asset was modified or uploaded. Capture hashing verifies identity, not scientific
integrity or accuracy; prior integrity results live in PR #71's failure report.

| Critical local path | Role and handling | Bytes | SHA-256 |
| --- | --- | --- | --- |
| `.venv/raw-geometry-gaze-cagri-geometry-1.json` | Development capture; recovery input only after approval | 42114167 | `c7f64d5e5e6a305b689c3488f20ef1a4a4932f797c265496b1df5be7dd97ae25` |
| `.venv/raw-geometry-gaze-cagri-geometry-2.json` | Consumed original holdout; no rerun authorized | 42100225 | `cce93847ba928413a5571e92fb94318783a2661edb32770d181ce128042f9409` |
| `.venv/stage-b2-one-shot-evaluation.json` | Original attempted evaluation marker, status `started`; critical provenance, not cache | 445 | `763a89a38347a7cdea895c6fa6b843aa63d05d441fecd38d45fc67537e467660` |
| `.venv/stage-b2-integrity.json` | Retained input-integrity audit artifact, not candidate outcomes | 1835 | `71d12875ab862e5b06b2d5c8e5995dedb9063d92767b9aad7af8153c43734bd8` |
| `.venv/models/face_landmarker.task` | Local detector model for approved camera work; no participant imagery | 3758596 | `64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff` |

The evaluator/failure report is preserved in active [PR #71](https://github.com/cagriinan46/eye-tracker/pull/71),
not main. Code must come from Git, not an accidental stale folder copy. Its
RESULTS/JSON contain failure/provenance records, not recovered scientific metrics.
Read [STAGE_B2_RECOVERY](STAGE_B2_RECOVERY.md) before any approved use of B2 assets.

## Complete relevant local asset manifest

All 57 entries below are **local-only, ignored, not committed**, and require
Fatih-machine confirmation. Expected relative paths are exact; filenames are
part of protocol/provenance identity. Association describes why future approved
work might need a file; it does not authorize replay. Capture files support
reproduction/audit of their named historical study; summary files preserve
historical numerical reports but cannot replace missing source captures. Invalid
pilot/failure artifacts are audit evidence and must not enter valid-data pools.

| Expected relative path / filename | Experiment association | Bytes | SHA-256 |
| --- | --- | --- | --- |
| `.venv/2d-gaze-mapping-rerun.csv` | 006 | 253373 | `35975670f4df4ed932569e12db72a690df697c2649c6ff1a6a277913c61ef7c0` |
| `.venv/2d-gaze-mapping.csv` | 006 | 345 | `7cda08ecfcc675a0c376145df1c8e5e9e5375a28317321d533530b029eabae0f` |
| `.venv/alt-feature-live1-summary.json` | Alternative-feature summary | 195105 | `d4d640a3eabe4befacd76243508c88e6524217043a09b11482b209bd9df20741` |
| `.venv/alternative-vertical-benchmark-summary.json` | Alternative-feature summary | 1024859 | `de94adf9b6cc53ce67517e82f67072c7e8811c7d1146652d226890a9403837b7` |
| `.venv/coarse-gaze-cagri-live-1.json` | Coarse v1 | 1774825 | `f671ce8361376954187ce748887442cf9af9e3a70538099d4f4623a7ff47c540` |
| `.venv/coarse-gaze-cagri-live-2.json` | Coarse v1 | 875704 | `00b2c10c8cb495fef8ff4f3b2cc9071e6ec552562a5d00a75d825ad716276b71` |
| `.venv/coarse-gaze-cagri-live-3.json` | Coarse v1 | 601501 | `ebccdf6b9902a5559c592f1188069fd7f2ab40c4e94c53d8a5466a308894b978` |
| `.venv/coarse-gaze-cagri-live-4.json` | Coarse v1 | 710053 | `54119078ddcd5a1412548909aea9462b9f12a42c51bc508a7c264a1fcf151aec` |
| `.venv/coarse-gaze-cagri-live-5.json` | Coarse v1 | 693106 | `3b7c8018849a385a0594b4a2f9a980b1d311ccb6cfc726a1ff2f12345408ca80` |
| `.venv/eye-geometry-cagri-live-1.json` | Eye geometry | 6231219 | `7d7ba2ee0a140185dcfab10e483650d189376aa58da3272c000c1ef6be3d237e` |
| `.venv/eye-geometry-cagri-live-2.json` | Eye geometry | 6234841 | `585d9b2a648bc6f34984a2eb147e9d85864c4568ab1d701a1ade0d98bd4feb2d` |
| `.venv/eye-geometry-cagri-live-3.json` | Eye geometry | 6238684 | `9ff6dcfcaabde8aada0022bf4e2ce4466b269131f703380999cef76ecd4dba06` |
| `.venv/eye-opening-analysis-primary-protocol-invalid.json` | Eye opening | 382516 | `7004d98fde7bddb65d136b2f9624f76b639a50457c8f68865af2449a26a3279e` |
| `.venv/eye-opening-cagri-live-1-attempt-1.invalid.json` | Eye opening | 218 | `6e5adae750c7657cdd3f3277cdde9c82dfbb196fadd3a7f37e1ac15ba272d2e3` |
| `.venv/eye-opening-cagri-live-1-precorrected-20261003-214006.invalid.json` | Eye opening | 218 | `6e5adae750c7657cdd3f3277cdde9c82dfbb196fadd3a7f37e1ac15ba272d2e3` |
| `.venv/eye-opening-cagri-live-1-protocol-invalid.json` | Eye opening | 1131411 | `0f526aaafbbbf31ad2a0a9db35e59e10cb98e056cdced54e8380764170e75146` |
| `.venv/eye-opening-cagri-live-1.json` | Eye opening | 1130349 | `03dcfb0b9b006f6632630fb85ef6fe5409f9ce908e70a4cc38063236c3f9e1c8` |
| `.venv/eye-opening-cagri-live-2-protocol-invalid.json` | Eye opening | 1131199 | `5ef3660552a861b28c675c7ccb8686a44e1cc8e885768e50eacd70a91245acd2` |
| `.venv/eye-opening-cagri-live-2.json` | Eye opening | 1134062 | `64dc68b8b5679408d68ed730ba6a4905972ec0aaf24e9db833cf8cd775f6c834` |
| `.venv/eye-opening-cagri-live-3-protocol-invalid.json` | Eye opening | 1128423 | `587bfe27c5412cadeaee9550db3b1f0c4eb31075dca4e71bb973dccb83c40570` |
| `.venv/eye-opening-cagri-live-3.json` | Eye opening | 1131353 | `89a84fc98e68972817681e162ae6fbd07bf863abcecfa89f7c3d3befb197dc8d` |
| `.venv/face-reference-cagri-live-1.json` | Face reference/feature benchmarks | 10648175 | `393b36d8dc3c2d9ba9d1c76b9e58fcd8eadfde3220fcb41dd872fdd682c19875` |
| `.venv/face-reference-cagri-live-2.json` | Face reference/feature benchmarks | 10640289 | `11c960bb330a784c12cabaa6fd47023c331420f30475e953cd1269ae34fce51f` |
| `.venv/face-reference-cagri-live-3.json` | Face reference/feature benchmarks | 10631157 | `d6b9428b2a5670853f081869875d8b75f5becbec6605fbeaa1905a3be487162e` |
| `.venv/fixed-center-live-cagri-1.json` | Fixed CENTER | 35919 | `31a780bc9ca47b4387b6531d8d6af228604e2aa1c6315790594a458aa6be9f45` |
| `.venv/fixed-center-live-cagri-2.json` | Fixed CENTER | 35929 | `712da528ddfbe7c22f4f4007cfd471ee7cbde391e36dd864abc4c6808a96b8cd` |
| `.venv/fixed-window-final-analysis-20261006-reviewed.json` | Fixed-window summary | 734519 | `b2da909f2a3d8c52f2492838801f455d213d39b3a3d774efe17208c97ac361d8` |
| `.venv/fixed-window-final-analysis-20261006.json` | Fixed-window summary | 734519 | `b2da909f2a3d8c52f2492838801f455d213d39b3a3d774efe17208c97ac361d8` |
| `.venv/fixed-window-gaze-cagri-diagnostic-1.json` | Fixed-window capture | 2119643 | `f645485fb723d8f406d6a044d217fa4c320499107aa0fe5393124b34a6a731a8` |
| `.venv/fixed-window-gaze-cagri-diagnostic-2.json` | Fixed-window capture | 2122063 | `c5bf81a34012b0824d4526cfdd4f282c1fb78bdcdd013f4be600f3e1152d243f` |
| `.venv/gaze-failure-benchmark-summary.json` | Solution summary | 152256 | `01a0df410e560e5a8831243bafcec09ac8cacd30f8b4ca9c16cd4600ba31709f` |
| `.venv/gaze-features.csv` | 003 | 155627 | `e2c8e207c2181773598773d21957b9cb96230cffc95208fc4176fab430089f45` |
| `.venv/intentional-gaze-cagri-live-1-reset-gated-pilot.invalid.json` | Intentional v2/solution benchmark | 325 | `315223979a2bca38b5ccf76c2ec07067aeb2af5a3c5a7f65a8672c8974cd8bc9` |
| `.venv/intentional-gaze-cagri-live-1.json` | Intentional v2/solution benchmark | 2264794 | `4a584da988b155aa2feec80dbb85796e510175e536f7ef41e98761a33c0fd294` |
| `.venv/intentional-gaze-cagri-live-2-reset-gated-pilot.invalid.json` | Intentional v2/solution benchmark | 325 | `3e7cc716accfa7b77f0c8fbec0784f89f2ec9929185573418a0def780b1d6197` |
| `.venv/intentional-gaze-cagri-live-2.json` | Intentional v2/solution benchmark | 2003040 | `c52afdb1e885e0dd6f601ce66cf77d3dc1dab28d478608b8c54b43d47325ddc3` |
| `.venv/lid-reference-development-summary.json` | Lid-reference summary | 318444 | `3029cb7321956203abfb12fef5328c387859580d4cf4c4c6eb0bef4426ef7ae3` |
| `.venv/lid-reference-historical-summary.json` | Lid-reference summary | 478398 | `fbdc6c76413cd83951b09a4fae5322471920063a01bd1d7003253fdce15ef72a` |
| `.venv/lid-reference-holdout-summary.json` | Lid-reference summary | 160339 | `3df3d9eabe86b797d4045c9f0594aca38edee8eee50a82d247197b467fad5056` |
| `.venv/models/face_landmarker.task` | Vision model | 3758596 | `64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff` |
| `.venv/raw-geometry-gaze-cagri-geometry-1.json` | B2 input | 42114167 | `c7f64d5e5e6a305b689c3488f20ef1a4a4932f797c265496b1df5be7dd97ae25` |
| `.venv/raw-geometry-gaze-cagri-geometry-2.json` | B2 input | 42100225 | `cce93847ba928413a5571e92fb94318783a2661edb32770d181ce128042f9409` |
| `.venv/real-calibration-cagri.json` | Production validation | 16966 | `03a4f167800674833d6486482b206be06b2a0fe5c7f84e23172b4193dd76f545` |
| `.venv/stage-b2-integrity.json` | B2 audit | 1835 | `71d12875ab862e5b06b2d5c8e5995dedb9063d92767b9aad7af8153c43734bd8` |
| `.venv/stage-b2-one-shot-evaluation.json` | B2 audit | 445 | `763a89a38347a7cdea895c6fa6b843aa63d05d441fecd38d45fc67537e467660` |
| `.venv/vertical-collapse-cagri-A.json` | Collapse | 779807 | `640663416d388b79910be10036a16e89f75abf48c2125815adcba75020edae23` |
| `.venv/vertical-collapse-cagri-B.json` | Collapse | 781635 | `c8244803f6de341c60eb7d341a1e4a9f0eee0940da503ee581bcc1f8ae3769b3` |
| `.venv/vertical-drift-cagri-A.json` | Drift/decomposition/offset | 973321 | `db76246bba3afd71d8c4bf1a181b788fab7e47419c299953e1cf633aae633909` |
| `.venv/vertical-drift-cagri-B.json` | Drift/decomposition/offset | 974468 | `7c3d6ce98ebe232839ba44ecc5c7077c8863a9224476892f1d14c71b8d725462` |
| `.venv/vertical-feature-covariates-analysis.json` | Covariates summary | 208900 | `fe77ba9d3ef5dfd27c1e66ba30cde31663660ac5db75bf600736f7d268f7c44a` |
| `.venv/vertical-gaze-stable.csv` | 004/005 | 363525 | `297cf36612f31686ea3d4d65a444e4e7e1a0052b3ac24264f067da8904e220e2` |
| `.venv/vertical-gaze-stable2.csv` | 004/005 | 364263 | `ea729d9015134884f55aaf5e3c36eb97b530a48d57fa69d27751c305ff579f9f` |
| `.venv/vertical-gaze-stable3.csv` | 004/005 | 365272 | `3a72fea9c24669fcbff6c49fd3c0d1045e740787911618eb117cad3da42a8953` |
| `.venv/vertical-position-cagri-controlled-1.json` | Position variability | 836427 | `4fc3cb8d79d210786953b50c748c3cb123755fcd9884cb8b28a1a78d75fc1dbc` |
| `.venv/vertical-sensitivity-cagri-live-1.json` | Sensitivity/covariates | 868433 | `6bcdc4ff51d646aaf594fc6804b4138e85b670168f70beacde825b48b86bc8a4` |
| `.venv/vertical-sensitivity-cagri-live-2.json` | Sensitivity/covariates | 871865 | `f22a62217f9110e9430a506f5b6e06779b8d9e166e741fa20eec7de950909194` |
| `.venv/vertical-sensitivity-cagri-live-3.json` | Sensitivity/covariates | 867438 | `5ee6811e54a92335f614c20a7c9b19f6dffd5724bede24cc83f8e4c5cf9a502e` |

Manifest cautions and missing material:

- `.venv/2d-gaze-mapping.csv` is the historically failed, header-only 345-byte
  export, not a reproducible full capture. The `-rerun.csv` is distinct valid
  historical evidence; see [006 RESULTS](../../experiments/006-2d-gaze-mapping/RESULTS.md).
- Eye-opening `protocol-invalid` / `.invalid` artifacts and intentional
  `reset-gated-pilot.invalid` files document withdrawn attempts. Preserve those
  identities and exclusions; a filename is not proof a capture is valid.
- Coarse live-1 used another setup and live-2 was invalid for primary inference;
  live-3/4/5 were the primary natural-use group. Follow its RESULTS, not filename
  numbering, when interpreting historical cohorts.
- The two fixed-window final-summary files have identical hashes; retain names
  for provenance. Do not treat duplicate reports as independent evidence.
- `.venv/real-calibration-fatih.json` is **absent on Çağrı's Mac**. Fatih's PR43
  comment documents the historical run; confirm its file on his machine. Other
  older recordings not listed here are not verified available; published RESULTS
  do not imply every original CSV remains recoverable.
- No serialized B2 numerical outcome was recovered. The presence of integrity,
  marker or failure JSON does not establish a completed benchmark.

Committed configuration/protocol authority is [pyproject.toml](../../pyproject.toml),
[requirements-dev.txt](../../requirements-dev.txt), experiment-owned `protocol.py`
files/READMEs, the [raw preregistration](../../experiments/raw_geometry_gaze_diagnostic/PREREGISTRATION.md)
and [representation freeze](../../experiments/gaze_representation_benchmark/REPRESENTATION_FREEZE.md).
These are Git-tracked, not missing private assets. No additional local protocol
configuration was established as necessary. Local audit helpers, temporary PR
metadata, venv packages/executables, caches, credentials, editor state and
unrelated personal files are excluded from this manifest. Preserve existing
ignored work, but do not blindly transfer it as required research data.

## Practical AirDrop / trusted-storage transfer

1. Finish/save the handoff, commit/push its branch and retain the open PR link.
   Record which code commit/branch should be checked out; main currently lacks
   the unmerged B2 evaluator. Transfer does not authorize its execution.
2. With human agreement, make a private safe backup of the repository and
   required data/model/provenance files. Keep the original copies intact. A ZIP
   is convenient but must not be committed or uploaded to GitHub.
3. Review the proposed transfer for secrets, credentials, personal files and
   unrelated caches. Agree the private recipients/channel; participant geometry
   must never go to the public repository or an AI service.
4. Transfer via AirDrop or trusted physical storage. This document records a
   workflow, **not confirmation that transfer was approved or completed**.
5. On Fatih's Mac, verify byte sizes and SHA-256 values, especially both geometry
   captures, detector model and original marker. `shasum -a 256 <file>` performs
   identity hashing without parsing; compare against the manifest. Record any
   mismatch/missing file and stop approved work that depends on it.
6. Preserve the original one-shot marker and first-attempt/failure provenance
   exactly. Missing or transferred marker is never permission to run B2 again.
7. Do not overwrite Fatih's existing Git work. Use a clean synchronized clone or
   worktree as code authority, verify origin/branch/SHA, and keep his existing
   uncommitted work intact. PR71 must remain preserved and unmerged.
8. Copy only assets needed by the approved task into their correct ignored paths.
   Recheck ignore rules before staging; do not commit raw facial/iris geometry,
   participant CSV/JSON, models, backups or the local marker.
9. Create a machine-specific Python 3.12 environment using repository dependency
   instructions in [validation/README](../../validation/README.md) and ADR004.
   Do not rely on transferred venv executables: they embed machine paths and may
   have platform-specific binaries. Keep private data/model backup outside the
   environment being rebuilt; never delete the original data-bearing `.venv`.
10. If an entire directory was transferred, explicitly confirm hidden `.git`,
    `.venv` and other hidden directories arrived. Their absence can lose local
    provenance/data; their presence does not make them safe to merge into an
    existing clone or reuse as an environment. Restore only approved assets to
    the fresh environment after preserving originals.

Fatih should append transfer/identity verification, code SHA and remaining missing
files to [WORK_LOG](WORK_LOG.md), then update [CURRENT_STATE](CURRENT_STATE.md).
Until that happens, Fatih data availability remains **UNVERIFIED**. No need to
read a capture's contents just to establish availability and identity.
