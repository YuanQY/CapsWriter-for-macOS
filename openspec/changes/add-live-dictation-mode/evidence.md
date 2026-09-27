# Evidence: offline evaluation of live dictation strategies

The harness lives outside this repository in
`~/code/open-source/capswriter-ab/stream_eval/` (scripts, manifests, results).
The full table is `results/report.md` there. Layer D holds the user's own
recordings; its result files are mode 600 and its text was never printed.

## Method

- Model: Qwen3-ASR 1.7B, 8-bit MLX, through CapsWriter's own `QwenASRRunner`.
- Audio arrives in 0.2 s pieces, as from the microphone.
- Metric: mixed error rate (MER): one token per CJK character, one per Latin
  word, after NFKC, casefold and punctuation removal. Checked by 7 hand cases.
- Commit-rule logic checked by 9 hand cases, including a known positive for the
  old positional drift.
- Two clocks: ideal (accuracy) and wall (a pass cannot start before the previous
  one ends). Ideal and wall gave the same accuracy on B.

## Data

| Layer | Source | Clips |
|---|---|---|
| A | FLEURS cmn_hans_cn test, read Mandarin | 30 |
| B | CS-Dialogue test, mainland Mandarin-English code-switching, 6 speakers | 30 |
| C | 30-74 s clips concatenated from A and B | 4 |
| D | the user reading 20 work prompts (tech terms, mixed, numbers, long) | 20 |

Rows whose reference has digits (or Chinese numerals in D) are reported apart.

## Strategies

- OFF: current behaviour, transcribe at release.
- M0: `mlx_qwen3_asr.streaming`, 2 s chunks.
- M2-1.0: every 1 s re-transcribe all audio so far, LocalAgreement-2, hold back
  the last 4 units, positional compare.
- M3-1.0: M2 plus numeral hold and content alignment (difflib).
- M3-1.0-a3: M3 with three agreeing passes. **Chosen** (the w15 window was tried with it and removed; see below).
- M3-1.0-w15: M3 plus freezing the segment start at a pause past 15 s.

## Results (main subsets)

| Layer | Method | Final MER | Shown then changed | Tail not yet shown | First text after speech | Commit error |
|---|---|---|---|---|---|---|
| B | M0 | 34.8 % | - | 19.8 % | 1.28 s | 1.3 % |
| B | M2-1.0 | 8.9 % | 1.3 % | 2.4 % | 0.28 s | 1.4 % |
| B | M3-1.0 | 8.9 % | 0.6 % | 1.9 % | 0.28 s | 0.8 % |
| B | M3-1.0-a3 | 8.9 % | 0.3 % | 1.6 % | 0.28 s | 0.5 % |
| D | OFF | 3.6 % | - | - | - | - |
| D | M0 | 34.6 % | - | 26.8 % | 1.36 s | 1.5 % |
| D | M3-1.0 | 3.6 % | 1.7 % | 4.6 % | 0.88 s | 2.3 % |
| D | M3-1.0-a3 | 3.6 % | 0.8 % (p90 1.5 %) | 2.1 % | 0.88 s | 1.4 % |

- Final MER of every M2/M3 variant equals OFF by construction (the final pass is
  the same call); the runs confirmed it.
- Pass cost (wall clock): p95 0.22-0.46 s for clips up to 30 s. Full re-decode
  of 65-74 s clips costs 1.4 s per pass; with the 15 s pause freeze it is under
  1.0 s.
- Numbers (D, 5 clips): commit error 0.5-0.6 %, final MER 0.5 %.
- Commit lag (median, estimated from token position): about 2.8-3.2 s for a3,
  measured from recording start, which includes a median 0.72 s of silence
  before the user starts speaking.

## Long-utterance window (measured 2026-09-27, wall clock)

The chosen a3 rule was first measured without the window. This run pairs it
with the 15 s freeze and two simpler freeze rules. C has 4 clips of 30-74 s
(main 2, numbers 2); D clips are mostly under 15 s, so the window rarely acts.

| Layer | Subset | Method | Preview MER | Jump p90 | Commit error | Commit rewrites | Pass p95 |
|---|---|---|---|---|---|---|---|
| C | main | a3 | 4.9 % | 3.7 % | 2.2 % | 0 | 1.29 s |
| C | main | a3-w15 | 4.9 % | 2.5 % | 1.4 % | 1 | 0.73 s |
| C | main | a3-w15, align at every pause | 7.4 % | 6.3 % | 5.0 % | 0 | 0.33 s |
| C | main | a3-w15, align on forced freeze | 13.6 % | 17.4 % | 10.3 % | 0 | 0.72 s |
| C | numbers | a3 | 7.4 % | 5.6 % | 0.0 % | 0 | 1.39 s |
| C | numbers | a3-w15 | 6.4 % | 5.7 % | 1.0 % | 3 | 0.96 s |
| D | main | a3 / a3-w15 | 6.2 % | 10.9 % | 1.4 % | 0 | 0.22 s |
| D | numbers | a3 / a3-w15 | 5.8 % | 15.6 % | 0.6 % | 0 | 0.44 / 0.33 s |

- a3-w15 keeps D unchanged and brings C passes under 1 s. It was chosen first.
- Both alignment variants keep committed text but make it wrong more often.
- Final MER is the same for every row (5.6 % / 10.8 % on C, 3.6 % / 0.5 % on D).

Real-model check of the implementation (2026-09-27, `tools/test_live_e2e.py`
long case, a 30 s Tingting TTS clip, then an offline trace of `LiveTask` with
the real engine): pauses were found at every tick from 16 s, but the head
transcript over 0-12 s read "聊医疗" while every full pass read "聊一聊", so no
agreed freeze happened. The forced freeze at 26 s replaced correct committed
text ("一聊") with the wrong head ("医疗"). **Decision: the window was removed;
the implemented rule is M3-1.0-a3** (every pass reads all audio so far). On D
the two are identical; the cost is slower passes past about 30-45 s (1.29 s
p95 on C's 30-74 s clips, against 0.73 s with the window).

## Known limits

- Small samples (B 30 clips from 6 speakers, C 4 clips, D 20 clips).
- Commit lag uses a linear estimate of when each token was spoken.
- The user's spontaneous speech with fillers and self-corrections was not
  recorded; B (natural conversation) covers fillers from other speakers.
- Pre-registered thresholds that a3 did not meet on D: preview MER vs OFF + 2
  pts (6.2 % vs 5.6 %), jump p90 10 % (10.9 %), commit error 0.5 % (1.4 %),
  commit lag 2 s. Most of the preview gap is the last second not yet shown.
