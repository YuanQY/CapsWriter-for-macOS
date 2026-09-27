# Add a live dictation mode

## Why

Today the user holds Caps Lock, speaks, and sees nothing until release. For
longer dictation this is blind: the user cannot tell whether the words are being
heard correctly until the end. The user asked for a second mode that shows the
words while speaking and corrects them as more audio arrives, while keeping the
current hold-and-release mode as the default.

An offline evaluation (see `evidence.md`) shows this is feasible on this Mac with
the model already shipped: re-transcribing the audio heard so far once per
second, and committing only text that three consecutive passes agree on, shows
the first words about 0.9 s after speech starts, changes about 1 in 100 shown
words at release, and leaves the final pasted text exactly as accurate as today.
The library's own chunked streaming API was measured and rejected (final MER
34.6 % against 3.6 % on the user's voice).

The evaluation missed four of its pre-registered thresholds on the user's voice
(preview error, release jump p90, commit error 1.4 % against 0.5 %, commit lag
about 3 s against 2 s; see `evidence.md`, Known limits). The user reviewed the
results and chose to build live mode as an option, with hold mode as default.

This reverses the earlier "流式识别策略" decision in `CLAUDE.md` (streaming
display was not a goal for that stage). The evidence above is the reason; the
decision row is updated with this change.

## What Changes

- New client setting `dictation_mode` in `config_client.py`: `'hold'` (default,
  current behaviour, unchanged) or `'live'`.
- In live mode the client shows a floating, non-activating preview panel while
  a recording is in progress. Committed text is shown normally, tentative text
  in blue with an underline. Keyboard focus stays in the target app. The preview shows raw model
  text; only the final text gets formatting and hotword substitution.
- In live mode the server runs a partial transcription of the audio received so
  far about once per second for the recording task, applies the commit rule, and
  pushes a partial message (committed + tentative text) to that client.
- On release, the existing final transcription and output path run unchanged.
  The pasted text is the final text, not the preview. The panel then closes.
- Each partial pass re-reads the whole recording so far, so committed text
  never changes. Past about 45 s a pass takes more than 1 s and updates slow
  down accordingly.
- Partial passes never change the final pass and delay its start by at most one
  pass that is already running. Partial text is kept in memory only: not
  logged, saved, broadcast or pasted.
- Live mode works with the `qwen_asr_mlx` engine only (the macOS default).
- readme.md documents the setting; the `CLAUDE.md` decision row
  "流式识别策略" and its task list are updated.

## Non-goals

- Writing live text into the target app's input field. That needs repeated
  delete-and-reinsert through the clipboard or key events, breaks the app's undo
  history and fights Chinese input methods. A real in-field experience needs an
  input method (InputMethodKit) and is a separate project.
- A menubar toggle for the mode. The user asked for a setting; a toggle can be
  added later.
- Using `mlx_qwen3_asr.streaming` (rejected by the evaluation).
- New dependencies.

## Capabilities

### New Capabilities

- `live-dictation`: show the transcript while the user is speaking, with
  committed and tentative text, selectable by a setting, with the hold mode as
  default and the final result unchanged.

### Modified Capabilities

None. The hold mode keeps its behaviour; the live mode is additive.

## Impact

- Client: `config_client.py`, the recording/connection path that tags a task as
  live, the result dispatcher for the new partial message, a new preview panel
  module next to `core/client/output/edit_panel.py`.
- Server: the receive/worker path that feeds audio to the runner, a partial-pass
  scheduler per task, the commit-rule module, the message sent back.
- Submodule `mlx-qwen3-asr`: none planned; the runner's existing transcription
  call is reused for partial passes.
- Protocol: two optional fields, both defaulting to hold behaviour. Client to
  server: `AudioMessage.live`. Server to client: `RecognitionMessage.preview`
  and `text_tentative` on a non-final message. Old clients never receive a
  preview because only live tasks request it.
- Compute: while holding in live mode, one extra transcription per second on the
  GPU (measured p95 0.22-0.46 s for utterances up to 30 s).
