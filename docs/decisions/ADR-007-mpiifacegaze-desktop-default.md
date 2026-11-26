# ADR-007 — MPIIFaceGaze ResNet-18 as the desktop development default

## Decision

The project owner selected the [MPIIFaceGaze ResNet-18 checkpoint](https://huggingface.co/hysts/ptgaze-mpiifacegaze-resnet-simple)
on 2026-11-26 after the same-frame keyboard comparisons. It is the default for
the prepared macOS desktop application. UniGaze remains available with
`--model unigaze`. MGaze remains available with `--model mgaze`. Each engine
starts with a fresh personal calibration.

The platform adapter, 13-target 20-sample calibration, five-point independent
check and 12 guided tasks use the existing desktop flow. Evaluate any shortened
calibration in a separate comparison on unseen targets and guided tasks.

## Evidence

| Local keyboard run | MPIIFaceGaze mean error | UniGaze mean error |
| --- | ---: | ---: |
| `ten-model-keyboard-6ea9b4597295` | 38.1 px | 47.1 px |
| `six-model-keyboard-a276ad495f14` | 47.9 px | 54.8 px |
| `finalists-keyboard-a7dd910e0210` | 60.6 px | 86.6 px |

Each run scored 240 shared frames from one participant. On the final run,
correct-key rates were 16.3% and 12.5% respectively. The initiative still has an
open 20 px accuracy target and pending human validation through the desktop flow.
