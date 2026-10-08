# Appearance-based gaze estimation: options and decision request (Issue #79)

Date: **2026-10-08, Europe/Istanbul**. Author: Claude Code for Fatih. Status:
**proposal for a human decision.** Nothing was downloaded, installed or run. No
architecture, dependency or licensing decision is made here.

## Why this document

[Issue #77](../../experiments/vertical_signal_comparison/RESULTS.md) found no
landmark-based vertical signal that met the accepted exit criteria for Fatih.
The best candidate (COMBO: production vertical + eye opening + blendshape +
head pitch) reached validation y MAE 0.092 / 0.109. The remaining large
technical option is an appearance-based model, a neural network that estimates
gaze direction from face or eye image crops. This document collects the
evidence needed to decide whether to try one.

## Putting our numbers in physical units

Fatih's display is a 14-inch MacBook Pro panel, 3024×1964 px at 254 ppi, so
about **30.2 × 19.6 cm**. Viewing distance has **not been measured**; 55 cm is
assumed below only to convert to degrees (1° ≈ 0.96 cm at 55 cm).

| Quantity | Normalized | On screen | ≈ degrees at 55 cm |
| --- | --- | --- | --- |
| Vertical exit criterion (y MAE) | 0.08 | 1.57 cm | 1.6° |
| COMBO vertical, A / B | 0.092 / 0.109 | 1.80 / 2.14 cm | 1.9° / 2.2° |
| R0 vertical, A / B | 0.158 / 0.118 | 3.10 / 2.31 cm | 3.2° / 2.4° |
| Horizontal x MAE, A / B | 0.046 / 0.062 | 1.39 / 1.87 cm | 1.4° / 1.9° |

## What published systems report

These figures come from different datasets, people, head poses and metrics.
Most are combined 2D angular errors, not a vertical-only error. They are
context, not a like-for-like comparison.

| Source | Setting | Reported error | Verification |
| --- | --- | --- | --- |
| [L2CS-Net, arXiv:2203.03339](https://arxiv.org/abs/2203.03339) | Cross-person appearance model | 3.92° MPIIGaze, 10.41° Gaze360 | Abstract read |
| [FAZE, NVIDIA/ETH, ICCV 2019](https://research.nvidia.com/publication/2019-10_few-shot-adaptive-gaze-estimation) | Personalized with ≤ 9 calibration samples | 3.18° GazeCapture | Project page summary |
| [Noldus FaceReader white paper](https://noldus.com/download/document/white-paper-facereader-webcam-based-eye-tracking) | Commercial webcam tracker, 17 people, calibrated | ≈2.3–2.4 cm, ≈1.8° | Search summary only; PDF not readable here; vendor-reported |
| [Blakey et al., Durham](https://durham-repository.worktribe.com/output/3791240/a-study-on-the-impact-of-different-components-of-a-traditional-webcam-based-2d-gaze-tracking-algorithm) | Personalized laptop webcam | 2.26 cm | Search summary only |
| [Review, arXiv:1907.04325](https://arxiv.org/pdf/1907.04325) | Off-the-shelf cameras | 2–4° appearance-based, 5–6° model-based | Search summary only |

**Main observation.** Calibrated webcam systems in the literature report about
2 cm or about 2° on screen. COMBO's vertical error (1.8–2.1 cm) is already in
that range, and the exit criterion (1.57 cm) is at or below what those systems
report. An appearance-based model is therefore **not expected to bring a large
accuracy jump**. Its plausible benefits are robustness to head movement and
lighting, and behavior that transfers better between users. The size of any
accuracy gain for Fatih is unknown and can only come from measurement.

## Candidate models

| Model | Code license | Weights and training data | Backbone / input | Notes |
| --- | --- | --- | --- | --- |
| [L2CS-Net](https://github.com/Ahmednull/L2CS-Net) | MIT | Google Drive checkpoints (Gaze360, MPIIFaceGaze); weight terms not stated; both datasets are non-commercial research data ([MPIIGaze record](https://service.tib.eu/ldmservice/dataset/mpiigaze), [Gaze360 README mirror](https://gitee.com/weqsd23_ewr/gaze360)) | ResNet-50, face crop from its own face detector | Simplest to try; a third-party export is listed in the [Luxonis model zoo](https://models.luxonis.com/luxonis/l2cs-net/7051c9d2-78a4-420b-91a8-2d40ecf958dd?backTo=%2F); repo reportedly inactive about 2 years |
| [ETH-XGaze baseline](https://github.com/xucong-zhang/ETH-XGaze) | CC BY-NC-SA 4.0 | ETH-XGaze; checkpoint linked, terms not stated | ResNet-50, 224×224 normalized face, dlib landmarks | Benchmark values found conflict (≈4.7° vs 5.73°), not verified |
| [FAZE](https://github.com/NVlabs/few_shot_gaze) | LICENSE file not read | Weights on files.ait.ethz.ch; GazeCapture/MPIIGaze preprocessing | Encoder-decoder with meta-learned personal adapter | Designed for few-sample personalization, closest to our calibration flow; older PyTorch stack |
| [UniGaze](https://github.com/ut-vision/UniGaze) | LICENSE file not read | Weights under MG-NC-RAI-2.0 (non-commercial) | ViT B/L/H with MAE pre-training | Newest (WACV 2026); large models, likely slow on CPU |

None of the candidates has clearly permissive weights. Every set of weights is
either explicitly non-commercial or trained on non-commercial datasets with
unstated terms.

## Consequences for the project

- **Licensing (human decision):** non-commercial weights may be acceptable for
  the academic graduation prototype but could block later productization or
  any commercial TEKNOFEST outcome. The repository has no license yet.
- **Dependencies (ADR-004):** inference would need PyTorch or, preferably,
  ONNX Runtime plus a converted model. This is a new runtime dependency and a
  local model file next to `face_landmarker.task`.
- **Architecture (ADR-003):** a model producing gaze angles from image crops
  would sit in Vision as a vendor-neutral signal, with Gaze still owning
  calibration and mapping. Exposing it in production contracts is a later
  decision.
- **Local-first and privacy (ADR-001):** inference is local. Crops stay in memory
  and are never saved or uploaded, the same as MediaPipe today.
- **ML policy:** ML is allowed only with a measurable advantage over simpler
  methods. COMBO is the baseline any model must beat under the same protocol.
- **Latency (NFR-003):** CPU speed of ResNet-50 or ViT on Apple Silicon at
  ≈30 fps is unknown and must be measured.

## Options

1. **Bounded spike (proposed if licensing is acceptable).** Run L2CS-Net (MIT
   code, Gaze360 weights) through ONNX Runtime as an extra experiment-only
   signal in the Issue #77 protocol. Record only its per-frame pitch/yaw output.
   Preregister two new candidates, APP (model pitch alone) and COMBO+APP, with
   the unchanged Issue #77 rule. Run Fatih A/B. Stop rule: if neither passes,
   stop appearance-model work. Cost about 1.5–2 days. Requires approval to
   download the weights, accept their terms and add an experiment dependency.
2. **Design for coarse vertical.** About 0.10 normalized error supports roughly
   4–5 reliable vertical zones. Test zone-based or two-step (zoom) selection
   against the targeting criterion. This moves the product forward without a
   new model.
3. **Revisit the exit criterion.** The current 0.08 y MAE is at or below
   published webcam accuracy. An interaction-level criterion, such as selection
   success for a defined target size, may better fit an assistive product.
4. **Run the Issue #77 protocol with Çağrı** (code ready, about 5 minutes). This
   is needed for the two-user criterion in any case.

## Recommendation

Run option 4 when Çağrı returns, and decide options 1 and 3 together at the
team review. If the team accepts non-commercial weights for the prototype,
option 1 is the last bounded technical test before committing to option 2.
Expectations should be set from the evidence above: a large vertical
improvement from an appearance model is possible but not supported by the
published numbers.
