# Design: live dictation mode

## Context

Today one recording flows like this:

```
client recorder --AudioMessage (every block)--> ws_recv --Work--> queue_in
  --> worker process: WorkHandler.loop -> QwenMLXRunnerPipeline.process
      -> recognizer.feed_audio_patch(task_id, is_final=False)  (buffer only, returns None)
      -> ... release ... feed_audio_patch(is_final=True) -> Result
  --> queue_out --> ws_send --RecognitionMessage--> client result_processor
      -> paste final text
```

- One worker process, one thread, one model on the GPU.
- `WorkHandler.loop` drains up to 64 packets, pops one, calls `process()`.
  `process()` returns `None` for non-final packets.
- The client drops every non-final message (`result_processor.py`,
  `if not message.is_final: return`).
- The runner and its session log no text. `feed_audio_patch` with a new
  `task_id` and `is_final=True` transcribes the given audio in one call and
  drops that task's state (`_finalize_task`).

The evaluation (`evidence.md`) chose M3-1.0-a3: every 1 s re-transcribe the
audio heard so far, commit only what three passes agree on, hold back the last
four units, hold open numeral runs, and align the tail by content. The eval's
extra 15 s pause freeze (w15) was implemented first and then removed (D5).

## Goals / Non-Goals

Goals:

- A `'live'` value for a new `dictation_mode` setting shows a preview panel
  while Caps Lock is held.
- `'hold'` stays the default and its code path does not change.
- The final pasted text is produced by the same call as in hold mode.

Non-goals are listed in `proposal.md` (in-field typing, menubar toggle, library
streaming, new dependencies).

## Decisions

### D1. Tag the task in the audio message

- `AudioMessage` gets `live: bool = False`. `from_dict` reads it with
  `.get('live', False)`, like the other optional fields.
- The recorder sets `live = (Config.dictation_mode == 'live')` on its three
  `AudioMessage` constructions. An unknown value is not `'live'`, so it falls
  back to hold with no extra code.
- `ws_recv._submit_qwen_mlx_runner_patch` copies it into `Work.live`
  (`Work` gets `live: bool = False`).
- Why: the server needs to know per task, and the message already carries the
  per-task settings (`context`, `language`). Old clients send no field and get
  hold behaviour.
- Other engines: only `QwenMLXRunnerPipeline` implements the live hook (D2).
  With another engine the flag is ignored and dictation works as hold.

### D2. Partial passes run in the worker loop, in the gaps between packets

- `WorkHandler.loop`: when `process()` returns `None` and the buffer is empty,
  call `self.pipeline.live_tick()` if the pipeline has it. This reuses the
  existing optional-hook pattern (`hasattr(self.pipeline, 'cleanup_tasks')`),
  so `WorkPipeline` is not touched.
- If `live_tick()` returns a `Result`, put it on `queue_out`.
- A tick runs at most one pass. A pass is one `LiveTask.step()`: one model call
  over all audio received so far.
- Why here:
  - The model is single-threaded on one GPU. A pass in the same loop needs no
    thread, no lock and no second model copy.
  - Finals keep priority for free: a tick runs only when the buffer is empty.
    A final that arrives during a pass waits for that one pass only, then no
    tick runs while it is buffered.
  - Order is kept: previews and the final of one task go through the same
    `queue_out` and the same `ws_send` coroutine, so no preview of a task can
    reach the client after its final.
- Rejected:
  - A thread in the worker: MLX calls are not safe to interleave; it needs a
    lock around every model call and still blocks the final.
  - A second process: a second 2.5 GB model and GPU contention.
  - Client-driven "preview now" requests: an extra message type and a round
    trip per pass, with no gain.

### D3. The pass clock is audio time

- A live task is due when it has received at least 1.0 s more audio than when
  its last pass started. The first pass runs at 1.0 s of audio.
- Microphone audio arrives in real time, so this is "about once per second".
- A slow pass lets audio pile up, so the next tick is due at once. This is the
  eval's wall-clock rule (a pass starts at the later of its tick and the end of
  the previous pass).
- No new audio means no pass.
- The macOS client sends 20 ms blocks (`stream.py:297`), so `process()`,
  `feed()` and `due()` run 50 times a second. `feed()` appends one array and
  `due()` compares two integers; audio is concatenated only inside a pass.
- Tests need no clock mock: feeding N seconds of audio gives a known number of
  passes.

### D4. A pass reuses the engine call with a throwaway task id

- The pipeline keeps its own copy of a live task's audio (a list of float32
  chunks). The runner's buffer is private and the real task's buffer must stay
  untouched, so the final is the same call as in hold mode.
- A pass calls
  `recognizer.feed_audio_patch(task_id=f"{task_id}#live{n}", audio=segment,
  sample_rate=16000, is_final=True, context=..., language=..., source=...)`.
  It returns a runner result with `.text`; the runner drops that task's state.
- `step()` moves `next_due` forward before it calls the model, so a failed
  pass uses up its slot and a lasting fault retries once per second, not on
  every 20 ms packet.
- On an exception the pipeline logs the exception type and task id (no text)
  and returns `None`. The live task keeps its state and the client keeps the
  last good text. No `cancel_task` call: the runner pops the pass state before
  it transcribes (`capswriter_runner.py:202`), and the only earlier step
  (`_prepare_audio`) gets the same float32 audio the real task gets.
- No formatter on preview text: the final is formatted as today; the preview
  shows raw model text.
- Memory: 60 s of 16 kHz float32 is 3.8 MB, for live tasks only.
- No engine or submodule change.

### D5. A pure module for the commit rule

New file `core/server/worker/live_preview.py`. It imports `re` and `difflib`
(and numpy for the audio chunks) only, no MLX, so it runs in fast unit tests.

- `units`, `ukey`, `is_numeral`: ported from the eval harness.
- `Agreement`: the M3-a3 path only, with no flags. Constants `AGREE = 3`,
  `HOLDBACK = 4`. Numeral hold and content alignment are always on.
  `update(text) -> str` returns committed + tentative (tentative with its
  trailing punctuation removed), and `committed` holds the committed part.
- `LiveTask`: the per-task state and the one step function.
  - Fields: audio chunks, total samples, `agreement`, `next_due` (samples),
    `passes`, and the first `Work` (socket, source, context, language,
    start time).
  - `feed(samples)`, `due() -> bool`.
  - `step(transcribe) -> (committed, tentative)`: `transcribe` is a callable
    `audio -> str` over all audio so far. The pipeline passes a closure over
    `feed_audio_patch`; unit tests pass a scripted function. This keeps the
    rule free of the model and lets the pipeline test use the real one.
- No segment window. The first version ported the eval's `M3-1.0-a3-w15`
  window (freeze the segment start at a pause past 15 s, force it at 25 s).
  The real-model e2e run on a 30 s clip showed its failure mode: the head
  transcript over 0-12 s read "聊医疗" while every full pass read "聊一聊", so
  no agreed freeze happened, and the forced freeze at 26 s replaced correct
  committed text with the wrong head. The window was removed because:
  - "committed text never changes" is the property that makes black text
    trustworthy, and without the window it has no exception;
  - on the user's own recordings (D) a3 and a3-w15 gave identical results;
  - its only measured gain is pass cost past about 30 s (1.29 s to 0.73 s p95
    on 30-74 s clips);
  - it removes about 40 lines and four tests.
  The cost: past about 45 s a pass takes more than 1 s, so updates slow down.
  The two alignment-based freeze variants measured earlier were worse still
  (`evidence.md`, "Long-utterance window").

### D6. Preview results and messages

- `Result` and `RecognitionMessage` get `preview: bool = False` and
  `text_tentative: str = ''`. For a preview, `text` is the committed text,
  `is_final` is False. `from_dict` reads both with `.get`.
- A separate `preview` flag is needed: other engines already send non-final
  messages that the client must keep dropping.
- `live_tick()` builds a fresh `Result` (it does not touch the task's
  `RecognitionSession`, which the final still owns).
- `ws_send` copies the two fields and skips the `麦克风识别结果: {text}` log line
  for previews. The debug line that logs only the text length stays.
- Logging facts this relies on: production logs go only to the named loggers
  `server` and `client` (`core/logger.py`, `propagate=False`). The root logger
  has no handler in production (the only `basicConfig` is under `__main__` in
  `core/ui/toast.py`), so the `websockets` library's DEBUG frame logs, which
  carry message payloads, are dropped. This change adds no root handler. Tests
  capture the named loggers at DEBUG, not the root.

### D7. Pipeline lifecycle of a live task

In `QwenMLXRunnerPipeline`:

- `self.live: dict[str, LiveTask] = {}`.
- `process(work)`: for a non-final `work.live` packet, create the task on first
  sight and `feed()` it; for any final, `self.live.pop(work.task_id, None)`
  before the final call. After that pop no preview of the task can be built.
- `live_tick()`: the first due task in insertion order runs one `step()`.
- `cleanup_tasks(ids)`: also pops those live tasks (client disconnect).

### D8. Client preview panel

New file `core/client/output/live_panel.py`, beside `edit_panel.py`.

- A borderless `NSPanel` with `NSWindowStyleMaskNonactivatingPanel`,
  `setIgnoresMouseEvents_(True)`, floating level, all spaces and full-screen
  auxiliary (as `edit_panel`), `setHidesOnDeactivate_(False)` (CapsWriter is
  never the active app, so the default would keep the panel hidden).
- Shown with `orderFrontRegardless()`. It never calls `makeKeyAndOrderFront_`,
  never activates the app, and the class does not override
  `canBecomeKeyWindow` (a borderless panel returns False). `edit_panel`'s
  `show_panel` activates the app and is not reused.
- Content: one wrapping `NSTextField` label with an attributed string:
  committed text in `labelColor`, tentative text in `secondaryLabelColor`.
  Same width, corner radius, blur material and top position as the editor
  panel (reuse `_PANEL_W`, `_MARGIN`, `_CORNER_RADIUS`, `panel_origin_y`).
- API: `show(committed, tentative)` and `hide()`. Both may be called from the
  asyncio thread; they dispatch to the main thread with `AppHelper.callAfter`.
  The panel is created on first `show`.
- Auto-hide: each `show` bumps a generation counter and schedules
  `AppHelper.callLater(5.0, ...)`, which hides only if the generation did not
  change. This covers a cancelled or failed recording with no final.
- AppKit import follows `edit_panel` (`try` import, module flag), because
  `result_processor` is shared with `start_client.py`.

### D9. Client dispatch

- `result_processor._handle_message`: right after the `None` check,
  `if message.preview: live_panel.show(message.text, message.text_tentative);
  return`. It must come before the existing DEBUG line that logs non-final
  text (`result_processor.py:246`). No logging, no diary, no clipboard, no UDP
  on this branch.
- In the final branch, call `live_panel.hide()` before output. It is a no-op
  when the panel was never shown.
- No startup warning for an unknown value: it already means hold (D1), and a
  warning in `app.py` could only be tested by starting the whole client, which
  registers global hotkeys. readme.md lists the two values.

## Patterns and size

- Optional hook method (`live_tick`, existing `cleanup_tasks` precedent)
  instead of a new scheduler class.
- Functional core, thin shell: the rule is pure (`live_preview.py`); the
  pipeline and the panel are thin adapters.
- Dependency injection by a plain callable (`transcribe`) instead of an engine
  interface.
- No new config beyond `dictation_mode`. Interval, agreement and holdback are
  module constants (YAGNI: the eval fixed them).
- Expected size: `live_preview.py` about 100 lines, `live_panel.py` about 110
  lines, about 60 changed lines elsewhere, plus tests.

## Risks / Trade-offs

- GPU load while holding in live mode: one pass per second (p95 0.22-0.46 s up
  to 30 s; about 1.3-1.4 s for 60-74 s). Hold mode has no extra load.
- A final that arrives during a pass waits for it (at most one pass: under
  0.5 s up to 30 s, about 1.4 s for a 70 s recording).
- Preview text is raw model text; the pasted final is formatted. Small
  differences in punctuation and spacing at release are expected.
- The panel cannot be checked for focus behaviour without the running app;
  that is an Acceptance item for the user.
- One worker serves every socket. Partial passes for one client delay work for
  another. Single local client is the product's use.
- The real-panel test shows a floating panel on screen for under a second.

## Migration / Rollback

- Default is `'hold'`; nothing changes until the user sets `'live'`.
- Rollback: set `dictation_mode = 'hold'`, or check out
  `local/privacy-setup`; then `capswriter restart`, because the launchd
  server and client run from this checkout and read the code at start.

## Open Questions

None. The a3 + w15 pairing was measured before coding and removed after the
real-model e2e run (D5, `evidence.md`).
