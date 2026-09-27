# Adversarial review: design stage

- Stage: design
- Files reviewed: `openspec/changes/add-live-dictation-mode/design.md`, `openspec/changes/add-live-dictation-mode/tasks.md` (plus `specs/live-dictation/spec.md`, `proposal.md`, `evidence.md` as the claims they rest on)
- Repository root: `/Users/qingyun.yuan/code/open-source/CapsWriter-for-macOS`
- Date: 2026-09-27
- Model: fable
- Previous round: none named; no other `adversarial-*.md` or `acceptance.md` was read.

## Commands run to check premises

| Command | What it printed |
|---|---|
| `git branch --show-current; git worktree list` | `feature/live-dictation`; one worktree only (main tree at 33eba19) |
| `git log --oneline -1 local/privacy-setup; git merge-base feature/live-dictation local/privacy-setup` | both at `33eba19`; the feature branch has no commits yet |
| `git status --short` | only `?? openspec/` |
| `ps aux \| grep -i capswriter…` | server `start_server.py` pid 70500, worker pid 70506 (2.4 GiB RSS), `CapsWriter.app` pid 70516 all running from this tree |
| `lsof -nP -iTCP -sTCP:LISTEN \| grep python` | pid 70500 listens on `127.0.0.1:6016` |
| `lsof -a -p 70516 -d cwd; lsof -a -p 70500 -d cwd` | both cwd = repository root |
| `lsof -p 70500 \| grep logs/` | server holds `<repo>/logs/server_latest.log` open (worker 70506 too) |
| `.venv/bin/python --version` | Python 3.13.12 (symlink to uv cpython 3.13) |
| `.venv/bin/python -c "import AppKit…"` | pyobjc 12.2.2; `NSWindowStyleMaskNonactivatingPanel=128`, `NSFloatingWindowLevel=3`; `callLater`, `callAfter`, `orderFrontRegardless`, `setIgnoresMouseEvents_`, `setHidesOnDeactivate_` all present |
| `say -v '?' \| grep -i eddy \| grep zh` | `Eddy (Chinese (China mainland)) zh_CN` exists (a first `head`-cut grep hid it) |
| `ls -la ~/code/open-source/capswriter-ab/stream_eval/run_eval.py` | exists, 14373 bytes, modified 2026-09-27 10:48 |
| `which openspec; openspec --version` | `/Users/qingyun.yuan/.local/bin/openspec`, 1.13.0 |
| `openspec validate add-live-dictation-mode` | `Change 'add-live-dictation-mode' is valid` |
| `ls -la ~/.claude/tools/mutate.py ~/.claude/tools/test_mutate.py` | both exist |
| `sed -n 105,140p ~/.claude/tools/mutate.py` | verdict is the test command exit code: `CAUGHT if result.returncode != 0 else MISSED` (line 133) |
| `ls models/Qwen3-ASR-MLX/; du -sh …8bit` | `Qwen3-ASR-1.7B-8bit` present, 2.3G |
| `git ls-files models \| wc -l; grep -n models .gitignore` | 15 tracked notebook/txt files only; `*.safetensors`, `*.json`, `*.bin`… under `models/**` ignored (lines 157-171) |
| `grep -n -E "venv\|config_client_local\|logs" .gitignore` | `.venv` (114), `config_client_local.py` (200), `logs/` (177) ignored |
| `git check-ignore -v 2026/09/assets/x.wav` | `.gitignore:174:[0-9][0-9][0-9][0-9]/` |
| `ls 2026/09/assets \| wc -l` | 192 files (the user's recordings; names not listed) |
| `sysctl -n hw.memsize` | 64 GiB |
| `cat .gitmodules; git submodule status` | `mlx-qwen3-asr` at `f745f5e`, branch `capswriter-macos` |
| `grep -n "^version" mlx-qwen3-asr/pyproject.toml; grep Version .venv/…/mlx_qwen3_asr-0.3.5.dist-info/METADATA` | both `0.3.5`; site-packages copy is a normal install, not editable |
| `sed -n 282,296p core/server/engines/qwen_asr_mlx/asr_engine.py` | `_ensure_local_package_precedence` inserts `<repo>/mlx-qwen3-asr` at `sys.path[0]` if the dir exists |
| `sed -n 100,262p mlx-qwen3-asr/mlx_qwen3_asr/capswriter_runner.py` | `feed_audio` creates state, `is_final=True` calls `_finalize_task` which pops state first (line 202) then transcribes; `transcribe_audio` is `feed_audio(is_final=True)`; `cancel_task` is `_states.pop(id, None)`; `min_audio_seconds=0.1`; no `logger`/`print` in the file |
| `grep -n verbose …capswriter_runner.py` | `verbose: bool = False` default (line 36) |
| `grep -n "block_duration" core/client/audio/stream.py` | `block_duration = 0.02 if is_macos` (line 297) |
| `sed -n 38p ~/code/open-source/capswriter-ab/stream_eval/run_eval.py` | `PIECE = int(0.2 * SR)  # mic delivers audio in 0.2 s pieces` |
| `sed -n 153,207p …run_eval.py` | M3 w15 path: force at `window + 10`; head transcription then current transcription; `passes.append(cost)` sums both |
| `sed -n 66,118p …run_eval.py` | `Agreement(agree, holdback=4, numeral_hold, align)` as described in D5 |
| `grep -n … core/client/output/result_processor.py` | `_handle_message` at 218; `if message is None` 220; DEBUG log `接收到识别结果，文本: {text[:50]}` at 247; `if not message.is_final: return` at 252 |
| `grep -n log_level config_client.py config_server.py` | client `'DEBUG'` (91), server `'DEBUG'` (30) |
| `cat core/logger.py` | named loggers, `propagate=False`, file handler at the configured level, log dir `<BASE_DIR>/logs` |
| `grep -rn "basicConfig\|getLogger()" core start_*.py` | only under `if __name__ == "__main__"` in `core/ui/toast.py` and inside `toast_logger.configure_toast_logging`; no root DEBUG on the app path |
| `.venv/bin/python -c "import websockets…"` | websockets 17.1 |
| `grep -n "self.debug" .venv/…/websockets/protocol.py` | `self.debug = logger.isEnabledFor(logging.DEBUG)` (108); `self.logger.debug("< %s", frame)` (609), `("> %s", frame)` (755) |
| `.venv/bin/python - <<EOF … str(Frame(Opcode.TEXT, data))` on a 342-byte preview JSON | `TEXT '{"task_id": "3f0a9e2c-9b5d-11f1-8c3a-acde480011...TIVE_TEXT_PLACEHOLDER"}' [342 bytes]` |
| `sed -n 10,24p; 484,496p; 700,710p start_client_macos.py` | main thread `AppHelper.runEventLoop()`, asyncio in a sub-thread, `init_panel()` on main thread |
| `grep -n "def callLater" -A 8 .venv/…/PyObjCTools/AppHelper.py` | `callLater` posts to the main thread via `performSelectorOnMainThread_` |
| `/usr/libexec/PlistBuddy -c print CapsWriter.app/Contents/Info.plist` | `LSUIElement = true`, `LSBackgroundOnly = false` |
| `sed -n 272,335p core/client/shortcut/task.py` | `cancel()` stops capture and cancels the recorder task; only `finish()` enqueues `'finish'` |
| `sed -n 128,180p core/client/audio/recorder.py` | data before `Config.threshold` (0.3 s) is cached, not sent |
| `sed -n 56,110p core/client/audio/file_manager.py` | `folder_path = Path() / time_year / time_month / 'assets'` (CWD-relative), mp3 via ffmpeg or wav |
| `grep -n save_audio tools/*.py` | only `test_editor_result_flow.py` patches `save_audio=False` |
| `grep -n … tools/test_editor_ui_contract.py` | no `NSApplication`; line 28 says the test env may lack PyObjC; tests are pure functions |
| `grep -n … tools/test_mic_shortcut_lifecycle.py` | uses `SimpleNamespace(record_and_send=consume)`, not the real recorder |
| `sed -n 74,92p core/server/worker/process_manager.py` | worker liveness is checked only during model load; no respawn after |
| `sed -n 96,126p core/client/launcher/macos_caps_supervisor.py` | one `Popen` + `wait()`; no restart loop |
| `sed -n 94,115p config_server.py` | `model_dir = Path()/'models'` (CWD-relative); if both local dirs are empty, returns hub id `mlx-community/Qwen3-ASR-1.7B-4bit` |
| `cat -n core/server/worker/work_handler.py` | `MAX_DRAIN_ITEMS = 64`; `drain_queue` blocks `get(timeout=1)` when the buffer is empty; `hasattr(self.pipeline, 'cleanup_tasks')` at 144 |
| `cat -n core/server/connection/ws_send.py` | one coroutine, `to_thread(queue_out.get)`; `麦克风识别结果: {text}` at 60; length-only debug at 57 |
| `cat -n core/client/output/edit_panel.py` (53-55, 207-218, 307) | `_PANEL_W`, `_MARGIN`, `_CORNER_RADIUS` exist; floating level, all spaces, `setHidesOnDeactivate_(False)`; `show_panel` calls `NSApp.activateIgnoringOtherApps_(True)` |
| `cat core/protocol.py core/server/schema.py` | `AudioMessage.from_dict` uses `.get` for optionals; `Work` ends with `samplerate: int = 16000`; `Result` has defaults |

## Angle 1. Shared state

Looked for: files, ports, processes and folders that a test lane, a worktree, or the user's running app both touch.

Found:

- The user's server (pid 70500, worker 70506) and client (pid 70516) run from this working tree, cwd = repository root. Group 4 merges into `feature/live-dictation`, the branch this tree has checked out. Python does not reload imported modules, and neither the worker watchdog (checks only during model load) nor the client supervisor (single `wait()`) respawns, so the running processes stay on old code until a restart. Held for the running processes; see F10 for the rollback text.
- `<repo>/logs/server_latest.log` is held open by the running server and worker. `core/server/__init__.py:21` runs `setup_logger('server')` on import, so any test that imports `core.server.*` appends to the same file, and `TruncatingFileHandler.doRollover` (10 MB) from a test process would truncate the user's log. Existing tests already do this. F11.
- `AudioFileManager.create` writes to `Path()/YYYY/MM/assets`, CWD-relative. That is the user's recordings folder (`2026/09/assets`, 192 files). `Config.save_audio = True` by default. The B2/B3 tests run the real recorder loop and the plan does not say to turn `save_audio` off. The year folder is gitignored, so 7.2's `git status` cannot see stray test audio. F3.
- Worktrees: `.venv` and the model weights are gitignored, and `config_server.model_dir` is CWD-relative. A fresh worktree has no `.venv/bin/python`, no `models/Qwen3-ASR-MLX/*` weights, and an empty `mlx-qwen3-asr` dir (the same 0.3.5 wheel in site-packages then takes over, so behaviour does not change today). F4.
- GPU: the e2e loads a second model next to the running worker. 64 GiB RAM makes memory fine; Metal time is shared only while the user dictates. F9 (timing).
- `WebSocketManager.connect` reads `Config.addr:Config.port` at connect time (`websocket_manager.py:83`), so a test can point the real manager at a port-0 capture server instead of the user's server on 6016. Held, provided the test sets the port.

## Angle 2. Isolation claims

Looked for: "private", "untouched", "does not touch", "no text".

- D4 "the real task's buffer must stay untouched": a throwaway id is a separate `_TaskAudioState`; `_finalize_task` pops it (runner 118-140, 200-243). Held.
- D4 "the runner drops that task's state": held (line 202 pops before transcribing). Side effect: `cancel_task(pass_id)` after a model exception is a no-op because the state is already gone; it only matters if `_prepare_audio` (line 133) raises. F13.
- Context "The runner and its session log no text": no `logger`/`print` in `capswriter_runner.py`; `verbose` defaults to False. Held.
- D6 "no partial text in logs": the `websockets` library logs frame payloads when its logger is DEBUG-enabled; the repr keeps the start and the end of the payload, and D6 appends `text_tentative` at the end of the JSON. Reproduced: the log line ends with `...TIVE_TEXT_PLACEHOLDER"}`. The app does not set the root logger to DEBUG, so production holds today; the claim depends on that and nothing states or tests it. F2.
- Client side: `result_processor.py:247` logs non-final text at DEBUG, and the client log level is DEBUG. D9 puts the preview branch above it, which is right, but no test in the plan reads client logs. F1.
- D8 "never activates the app": `orderFrontRegardless` and no `makeKeyAndOrderFront_`; `edit_panel.show_panel` (line 307) does activate, and the design does not reuse it. Held (focus behaviour itself stays an acceptance item, as the design says).

## Angle 3. False green and false red

- `test_live_e2e.py` "skips with a clear message if the model directory is missing": a unittest skip exits 0, so 7.1 "test_live_e2e.py passes" and any mutation row that only e2e catches read green or MISSED without running. In the main tree the model exists; in the 5C worktree it does not. F4.
- B10 e2e "captures every log record; none before the final contains preview text": if the capture is a root DEBUG handler, `websockets.server` becomes DEBUG-enabled and logs the frame with the tentative text. The test then fails for a reason unrelated to the pipeline, and the natural fix (mute `websockets` in the test) hides a real config-dependent leak. F2.
- B4 via e2e with a real engine: D3 says a slow pass makes the next tick due at once, so the pass count over N seconds depends on pass latency and on GPU sharing with the running worker. An exact-count assertion is a false-red risk. F9.
- 3A.3 / 3C.2 "each must fail (import error for the new module counts)": one import error fails every test in the file, so this step does not show that a single test can fail for its own behaviour. The mutation run is the real gate. F17.
- Mutation "cancel_task on failure": with the real runner semantics the call is unreachable for a model exception, so the row is either MISSED or caught by a test that asserts the call was made (implementation, not behaviour). F13.
- `test_final_matches_hold` compares two model outputs on the same audio. The evidence reports the final MER equal to OFF in every run; I did not reproduce it. Held on evidence.

## Angle 4. Rollback and one-way doors

- `local/privacy-setup` and `feature/live-dictation` are the same commit today, so `git checkout local/privacy-setup` is a real rollback of the code. The running server and client keep the old modules until restarted; the design's rollback section does not say "restart", tasks 5D does. F10.
- No migration, no schema, no permission grant, nothing under `$HOME` in the design. The only data written outside the repo is by tests: `say` output into a temp dir (fine) and, through the real recorder, into the recordings folder inside the repo (F3).

## Angle 5. Permission and trust bypass

- `say -v Eddy` (zh_CN present) needs no TCC. The real recorder test feeds a queue and does not open the microphone. A test-process `NSPanel` needs no grant. Held.
- Network: `resolve_qwen3_asr_mlx_model()` falls back to the hub id `mlx-community/Qwen3-ASR-1.7B-4bit` when both local dirs are empty. If the e2e's skip check trusts the engine instead of checking the directory itself, a run in a worktree or on a model-less machine starts a download. F14.
- No step widens an existing permission. Held.

## Angle 6. Side effects on failure

- A failing pass: D4 keeps the task and retries. The runner has already dropped the throwaway state. What the design does not say is whether a failed pass consumes its due slot. If `next_due` only advances on success, a persistent model fault retries on every packet: 50 times per second with 20 ms mic blocks, each logging a traceback. F15.
- A cancelled recording (`task.cancel()`) sends no final. In hold mode cancel happens only under the 0.3 s threshold, before any packet is sent, so no server task exists; a boundary race can leave a stale `LiveTask` that is never due and is freed on disconnect. D8's 5 s auto-hide covers the panel. Held.
- A test process that dies after `orderFrontRegardless`: the window dies with the process. Held.
- The e2e process holds a second 2.3 GB model until exit. Held.

## Angle 7. Premises about the machine

Checked and held: Python 3.13.12 in `.venv`; pyobjc 12.2.2 with every AppKit name D8 uses; `say -v Eddy` zh_CN; the eval harness at the stated path with the M3 w15 code path (constants 3, 4, 15, 25, ratio 0.2, 320-sample frames, `[seg_start + W/2, end - 3 s]`, head-then-current, replace on forced freeze) matching D5 line for line; `openspec` 1.13.0 and the change validates; `mutate.py` and its canary present; `websockets` 17.1; `numpy` in use; the 8-bit model present; the runner's `feed_audio(is_final=True)` equals `transcribe_audio` so the eval's call path is the design's call path; `min_audio_seconds=0.1` below the 1.0 s first pass; the three `AudioMessage` constructions in the recorder; `hasattr(pipeline, 'cleanup_tasks')` precedent; `MAX_DRAIN_ITEMS=64`; `RecognitionMessage`/`AudioMessage` `.get` pattern; the client's main-thread `runEventLoop` and sub-thread asyncio; `LSUIElement=true` (windows allowed).

Premises that did not hold as written: "mic delivers audio in 0.2 s pieces" (evidence) and "0.2 s packets" (e2e) against the macOS client's 20 ms blocks (F8); the tasks' relative `.venv/bin/python` in worktrees (F4).

## Angle 8. Unmapped requirements

- Spec "later partial messages for that task are ignored" (final-result scenario): no decision on the client. D2's single `queue_out` and single `ws_send` coroutine make a late preview unreachable, so no test can enter it. A THEN with no decision. F5.
- D8 auto-hide after 5 s: no SHALL. D1 "with another engine the flag is ignored and dictation works as hold": the spec's live-preview requirement has no engine condition. Two decisions without a spec statement. F6.
- Every other SHALL maps: setting and fallback (D1, 3D.1), panel and colours (D8), first text and cadence (D3), commit rule (D5), final unchanged (D4/D7), long utterances (D5 window rule, verified against the harness), privacy (D6/D9, with the gaps in F1/F2), failure (D4), TDD gate (tasks 5C/7.1).

## Angle 9. Concurrency and ordering

- "No preview of a task can reach the client after its final": previews and the final leave the worker on one `queue_out`, read by one coroutine (`ws_send`), and D7 pops the live task before the final call. Held.
- "A final that arrives during a pass waits for that one pass only": after a 0.4 s pass about 20 packets (20 ms each) plus possibly the final sit in `queue_in`; `drain_queue` takes them, the buffer stays non-empty until the final is processed, and D2 ticks only on an empty buffer. Passes longer than 1.28 s (64 packets) still drain before any tick because the buffer refills each iteration. Held.
- Two clients: a file transcription's final blocks live ticks for its full decode time, as it blocks finals today. By design; not a break.
- One-pass-per-tick with two model calls in a step (head + current) when a cut is found, and a head call on every tick between 15 and 25 s while the head disagrees (harness lines 177-194). The evidence's pass p95 includes both calls, so the numbers hold; the words "one pass" do not. F7.

## Angle 10. Task and test plan honesty

- The Acceptance items A1-A4 are user-only and say so. Held.
- B8, B11, B13 declare gaps instead of claiming entry tests. Honest.
- B2/B3's "real recorder loop, real WebSocketManager": both take `app` and read `app.state.queue_in`, `app.ws`, `app.state.register_audio_file/bind_task_trace/pop_audio_file`, `app.state.websocket`. An `app` stand-in is required and is not in the allowed-fakes list. F16.
- B12 "real live_panel NSPanel, main run loop pumped": no precedent in the repo (`test_editor_ui_contract.py` avoids `NSApplication` on purpose). The test needs `NSApplication.sharedApplication()` and a pumped main run loop, and `orderFrontRegardless` puts a floating panel on the user's screen while tests run. Feasible, new ground. F12.
- 5C "in its own worktree" cannot run as written (F4).
- The "import error counts" validation is weak (F17).
- 1.1 "record the pass counts" is a real baseline. Held.

## Findings

| Finding | Verdict | One line | Disposition |
|---|---|---|---|
| F1 | FIXED | MEDIUM EVIDENCED `result_processor.py:247` logs non-final text at DEBUG and the client log level is DEBUG (`config_client.py:91`); D9 relies on branch order, and B10's tests read only server logs, so a client-side leak or a misplaced preview branch is caught by nothing. | B10 now has a client test through the real ResultProcessor with the client logger captured at DEBUG; D9 names the line the branch must precede. |
| F2 | FIXED | MEDIUM EVIDENCED `websockets` 17.1 logs frame payloads at DEBUG (`protocol.py:609,755`) and the elided repr ends with the appended `text_tentative` (reproduced: `...TIVE_TEXT_PLACEHOLDER"}`); the privacy claim depends on the root/`websockets` logger staying above DEBUG, which the design does not state, and an e2e that captures logs at the root will fail or be muted. | Checked: production logs only to named loggers with propagate=False; the only root basicConfig is under __main__ in core/ui/toast.py. D6 states this; tests capture named loggers, not root. |
| F3 | FIXED | MEDIUM EVIDENCED path, INFERRED trigger: the real recorder loop (B2/B3) with default `save_audio=True` writes test audio into `<cwd>/2026/09/assets`, the user's recordings folder (192 files), and the year folder is gitignored (`.gitignore:174`) so 7.2's `git status` cannot see it; the plan never says to set `save_audio=False`. | Test notes: recorder tests set Config.save_audio = False and assert no file under 2026/. |
| F4 | FIXED | MEDIUM EVIDENCED tasks prescribe worktrees and `.venv/bin/python tools/<name>.py`, but `.venv` (`.gitignore:114`) and the model weights (`157-171`) are gitignored and `model_dir = Path()/'models'` is CWD-relative, so in a worktree the interpreter is missing, `test_live_e2e.py` skips with exit 0, and 5C's rows caught only by e2e report MISSED (`mutate.py:133`). | Every run uses the main .venv by absolute path; e2e and mutations run in one verification worktree with models symlinked; 5C moved there. |
| F5 | NOTE | LOW EVIDENCED spec THEN "later partial messages for that task are ignored" has no client decision; D2's single queue makes the case unreachable, so either the spec clause goes or a client guard and test are added. | Spec now says no later partial reaches the client (server order guarantee); tested in e2e. No client guard. |
| F6 | NOTE | LOW EVIDENCED D8's 5 s auto-hide and D1's "other engines run as hold" are decisions with no SHALL; the spec's live-preview requirement has no engine condition. | Spec now carries the 5 s auto-hide and the qwen_asr_mlx-only condition with a scenario. |
| F7 | NOTE | LOW EVIDENCED D2/D4 say "one pass" per tick, but a D5 step makes two model calls when a cut is found and pays a head call on every tick between 15 and 25 s while the head disagrees (`run_eval.py:177-196`); the evidence's p95 includes both, so define "pass" as one step. | D2 defines a pass as one step (one or two model calls). |
| F8 | NOTE | LOW EVIDENCED evidence and e2e assume 0.2 s packets (`run_eval.py:38`, tasks test notes) while the macOS client sends 20 ms blocks (`stream.py:297`), so production runs `process()`, `feed()` and `due()` 50 times per second and the e2e is not at production cadence. | e2e uses 20 ms packets at real-time pace; D3 notes the per-packet cost. |
| F9 | NOTE | LOW INFERRED an exact pass-count assertion in the e2e depends on pass latency and on the GPU shared with the running worker (pid 70506); D3's catch-up rule makes the count vary, so assert bounds. | Test notes: e2e asserts bounds, not exact counts. |
| F10 | NOTE | LOW EVIDENCED rollback "check out local/privacy-setup" (same commit today) does not change the running server and client, which run from this tree (lsof cwd); the design omits the restart that 5D mentions. | Rollback now includes capswriter restart. |
| F11 | NOTE | LOW EVIDENCED importing `core.server` in a test runs `setup_logger('server')` (`core/server/__init__.py:21`) and appends to the `logs/server_latest.log` the running server holds open; a 10 MB rollover from a test process truncates the user's log. | Test runs happen in the verification worktree, so their logs go to its logs/ (BASE_DIR is the checkout). |
| F12 | NOTE | LOW INFERRED B12's real-`NSPanel` entry test has no precedent (`test_editor_ui_contract.py:28` avoids `NSApplication`), needs a pumped main run loop, and shows a floating panel on the user's screen during test runs. | Accepted; the test hides the panel in teardown; noted in design Risks. |
| F13 | NOTE | LOW EVIDENCED `cancel_task(pass_id)` after a model exception is a no-op because `_finalize_task` pops the state before transcribing (`capswriter_runner.py:202`); the mutation row "cancel_task on failure" is catchable only by a fault in `_prepare_audio` or by asserting the call. | cancel_task removed from D4 and from the mutation list (KISS: the case cannot occur). |
| F14 | NOTE | LOW EVIDENCED `resolve_qwen3_asr_mlx_model()` returns the hub id `mlx-community/Qwen3-ASR-1.7B-4bit` when local dirs are empty (`config_server.py:110`); an e2e skip check that trusts the engine would start a network download in a worktree. | e2e sets HF_HUB_OFFLINE=1 and skips unless the local 8-bit dir exists. |
| F15 | NOTE | LOW INFERRED D4 does not say a failed pass consumes its due slot; if `next_due` advances only on success, a persistent fault retries on every 20 ms packet with a traceback each time. | D4: step() advances next_due before the model call; mutation row added. |
| F16 | NOTE | LOW EVIDENCED B2/B3's "real recorder loop, real WebSocketManager" both take `app` and read `app.state.*` and `app.ws`, so an `app` stand-in is required and is not in the allowed-fakes list. | Allowed fakes now include a minimal app object holding the real ClientState and WebSocketManager. |
| F17 | NOTE | LOW EVIDENCED 3A.3/3C.2 accept an import error as "fails before", which fails every test in the file at once and shows nothing about any single test; the mutation run is the only real gate. | Test notes: import error counts only for new modules; changed modules need an assertion failure. |

## What I could not break

- D5 port fidelity: every constant, window bound, freeze branch and join in D5 matches `run_eval.py` lines 66-207 (checked line by line).
- D4's call path: `feed_audio(is_final=True)` on a fresh id is exactly `transcribe_audio` (runner 142-166), which is what the evaluation measured; state is popped per call; `cancel_task` tolerates unknown ids.
- D2 ordering and final priority: one `queue_out`, one `ws_send` coroutine; `drain_queue` keeps the buffer non-empty until queued packets and the final are processed, so no tick runs between them (work_handler 99-136, 158-191).
- D7 cleanup path: `WorkHandler.cleanup` already calls `pipeline.cleanup_tasks(stale_ids)` behind `hasattr` (line 144-147).
- D8 threading: the macOS client runs `AppHelper.runEventLoop()` on the main thread and asyncio in a sub-thread; `callAfter` and `callLater` both post to the main thread (`AppHelper.py:64-79, 108-127`). Every AppKit name D8 uses exists in pyobjc 12.2.2. `LSUIElement=true`, `LSBackgroundOnly=false`, so windows can show.
- D1 compatibility: `AudioMessage.from_dict` and `RecognitionMessage.from_dict` pick keys explicitly, so an old server ignores `live` and an old client ignores `preview`/`text_tentative`.
- Runner logging: no `logger` or `print` in `capswriter_runner.py`; `verbose=False`.
- Machine premises: `say -v Eddy` zh_CN, `openspec` 1.13.0 (change validates), `mutate.py` and canary, model 8-bit present, 64 GiB RAM.
- Rollback in git: `local/privacy-setup` is the parent commit and exists.
- Permissions: no step needs a new grant; no step widens one.

Verdict: RESOLVED
