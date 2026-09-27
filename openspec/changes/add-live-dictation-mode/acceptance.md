# Acceptance review: add-live-dictation-mode

- Change: `add-live-dictation-mode`
- Git range: `33eba19..44146fa` (commit `5e4ff2b` is a separate change, excluded)
- Review tree: `/Users/qingyun.yuan/code/open-source/CapsWriter-wt/integ` at `44146fa`
- Date: 2026-09-27
- Reviewer model: fable (five parallel reviewers, one per question)

## Commands the five reviewers ran

Question 1 (entry points):
- `cd /Users/qingyun.yuan/code/open-source/CapsWriter-wt/integ`
- `git log --oneline 33eba19..HEAD` # 29 commits, HEAD 44146fa
- `git status --short` # (empty: working tree clean)
- `git diff --stat 33eba19..HEAD` # 33 files; production files listed below
- `git diff 33eba19..HEAD -- config_client.py core/client/audio/recorder.py core/client/output/result_processor.py core/protocol.py core/server/connection/ws_recv.py core/server/connection/ws_send.py core/server/schema.py core/server/worker/qwen_mlx_runner_pipeline.py core/server/worker/work_handler.py`
- `git show HEAD:core/client/output/live_panel.py`
- `git show HEAD:core/server/worker/live_preview.py`
- `git show HEAD:tools/test_live_client.py` (and the same for `test_live_e2e.py`, `test_live_pipeline.py`, `test_live_preview.py`)
- `git grep -n -e <entry> HEAD -- tools/test_live_*.py` # one grep per entry point
- `git grep -n "cleanup_tasks" HEAD -- tools/` # -> test_live_pipeline.py:245, test_worker_scheduling.py:159
- `git grep -n -e "\.cleanup()" -e "sockets_id.remove\|sockets_id.clear" HEAD -- tools/test_live_*.py` # -> only test_live_e2e.py:215 cls.recognizer.cleanup()
- `git diff --name-only 33eba19..HEAD | grep -i "ui\|menu\|tray"` # -> only adversarial-requirements.md
- `python3 -c "from config_server import ModelPaths, ServerConfig; ..."` # printed model dir/weights/config presence and model_type
- `which say` # /usr/bin/say

Question 2 (fails before):
- Baseline whole-suite run 1 of 2: `tools/test_*.py -v`, e2e with `HF_HUB_OFFLINE=1`
- Previous behaviour extracted with `git archive` into the scratchpad at commits `33eba19` and `8d30c2d`, run against the four new test files
- Call-site mutations by hand (`scratchpad/hand_muts.py`, `hand_muts.log`, `hand_muts_rerun.log`, `hand_muts_extra.log`), 31 rows, file restored and sha256-checked after each row
- Re-run of the 40-row `mutations.toml` claim at HEAD from a narrowed copy (`scratchpad/mutations_narrow.toml`) with `__pycache__` cleared and `PYTHONDONTWRITEBYTECODE=1`
- Baseline whole-suite run 2 of 2 (final verification)
- `git status --porcelain` after every mutation batch and at the end

Question 3 (real versus simulated):
- `git log --oneline 33eba19..HEAD` (29 commits), `git diff --stat 33eba19..HEAD` (33 files, 3592 insertions)
- `git show HEAD:<path>` on the four test files, the two new modules, every changed production file, and the production wiring each harness stands in for
- `git diff 33eba19..HEAD --stat -- mlx-qwen3-asr` # submodule pointer unchanged
- `ls -la /Users/qingyun.yuan/code/open-source/CapsWriter-wt/integ/mlx-qwen3-asr/`, venv `direct_url.json` check, `cmp` of venv runner files against submodule source
- `ls -la models/Qwen3-ASR-MLX/Qwen3-ASR-1.7B-8bit/` # symlinks confirm e2e model gate is real
- `git grep` over `tools/` for `live_tick|WorkPipeline|live=` outside the four live test files
- `git grep` for `callAfter|present_editor|runUntilDate_` outside the live tests

Question 4 (open items):
- `git status --short`
- `git log --oneline 33eba19..HEAD` # 30 commits, top 44146fa
- `ls .../add-live-dictation-mode/notes.md` # No such file or directory
- `grep -n '^- \[ \]' tasks.md` # 5 unchecked: 8.1, A1, A2, A3, A4
- `/Users/qingyun.yuan/.local/bin/openspec validate add-live-dictation-mode` # valid, exit 0
- `git rev-parse feature/live-dictation` vs `git rev-parse HEAD` # SAME
- `git rev-parse --verify origin/feature/live-dictation` # fatal: no such ref (not pushed)
- `git diff --stat 3380b4e..HEAD -- . ':!openspec'`
- `git show HEAD:.../mutations.toml | grep -c '^[[mutation]]'` # 40
- `grep -c 'def test_'` on the four new test files at HEAD
- `grep -E '^| F[0-9]+'` on both adversarial files
- `git show HEAD:<file>` greps for each review-5A finding

Question 5 (scope, tolerances, design drift):
- `git log --oneline 33eba19..HEAD` # 30 commits, 8d30c2d..44146fa
- `git diff --stat 33eba19..HEAD` # 33 files, +3592 / -6
- `git log --format='--- %h %s' --name-only 33eba19..HEAD -- .gitignore config_server.py tools/test_mlx_model_resolution.py openspec/config.yaml openspec/specs/.gitkeep openspec/changes/archive/.gitkeep`
- `git show --stat 5e4ff2b`
- `git check-ignore --no-index -v tools/test_live_*.py`
- `git log -p --diff-filter=M 33eba19..HEAD -- tools/test_live_*.py | grep '^[-+].*[0-9]'`
- same log -p diff for the 11 production files
- `git show eee60f4:tools/test_live_e2e.py` (first commit) vs HEAD
- `git grep -c -w <name> HEAD -- ':!openspec' ':!*.md' ':!*.toml'` for 25 added names
- `git grep -n -E '^_PANEL_W|^_MARGIN|^_CORNER_RADIUS|^def panel_origin_y|NSVisualEffectMaterial' HEAD -- core/client/output/edit_panel.py`
- `git show HEAD:core/server/worker/work_handler.py | sed -n '55,62p'`
- `git grep -n '模型输出' HEAD -- 'core/**'`

---

## 1. Entry points

Reviewer constraints honoured: judged `HEAD` = `44146fa` via `git show HEAD:<path>`; ran no build or test; opened no recording, transcript or log; did not touch 127.0.0.1:6016. Commit `5e4ff2b` (`config_server.py`, `.gitignore`, `tools/test_mlx_model_resolution.py`) is a separate change and is excluded.

### What I ran

```
cd /Users/qingyun.yuan/code/open-source/CapsWriter-wt/integ
git log --oneline 33eba19..HEAD            # 29 commits, HEAD 44146fa
git status --short                         # (empty: working tree clean)
git diff --stat 33eba19..HEAD              # 33 files; production files listed below
git diff 33eba19..HEAD -- config_client.py core/client/audio/recorder.py \
  core/client/output/result_processor.py core/protocol.py \
  core/server/connection/ws_recv.py core/server/connection/ws_send.py \
  core/server/schema.py core/server/worker/qwen_mlx_runner_pipeline.py \
  core/server/worker/work_handler.py
git show HEAD:core/client/output/live_panel.py
git show HEAD:core/server/worker/live_preview.py
git show HEAD:tools/test_live_client.py ; ...test_live_e2e.py ; ...test_live_pipeline.py ; ...test_live_preview.py
git grep -n -e <entry> HEAD -- tools/test_live_*.py      # one grep per entry point, output quoted per row below
git grep -n "cleanup_tasks" HEAD -- tools/                # -> test_live_pipeline.py:245, test_worker_scheduling.py:159
git grep -n -e "\.cleanup()" -e "sockets_id.remove\|sockets_id.clear" HEAD -- tools/test_live_*.py
                                                          # -> only test_live_e2e.py:215 cls.recognizer.cleanup() (engine, not WorkHandler)
git diff --name-only 33eba19..HEAD | grep -i "ui\|menu\|tray"   # -> only adversarial-requirements.md (no UI code)
python3 -c "from config_server import ModelPaths, ServerConfig; ..."
  # printed: 8bit dir: models/Qwen3-ASR-MLX/Qwen3-ASR-1.7B-8bit exists: True
  #          weights.safetensors: True config.json: True ; model_type: qwen_asr_mlx
which say                                  # /usr/bin/say
```

The `git diff` of the working tree printed nothing, so HEAD and the working tree were identical when I read them.

### Production entry points the diff adds or changes, and the test that enters each

This is a Python asyncio + PyObjC app. There are no Tauri commands; the diff adds no CLI path and no UI/menubar action (proposal "Non-goals" says so and `git diff --name-only` confirms no `core/ui` file changed). The entry points are: one client background worker (recorder loop), one client event handler (result dispatcher), one client UI module (panel), one client setting, two protocol readers, two server connection coroutines, the worker loop, three pipeline methods, and the pure rule module.

| # | Entry point (HEAD path:line) | Test that enters through it | Grep confirmation | Fakes on the path | Row verdict |
|---|---|---|---|---|---|
| E1 | `AudioRecorder.record_and_send` (`core/client/audio/recorder.py:87`), three `AudioMessage(... live=Config.dictation_mode == 'live')` at :165, :192, :222 | `tools/test_live_client.py::RecorderLiveModeTests` — `test_recorder_default_sends_hold`, `test_recorder_unknown_mode_sends_hold` (hit :165 and :222), `test_recorder_live_mode_tags_messages`, `test_recorder_live_mode_tags_cache_flush_message` (hit :192) | `test_live_client.py:144` and `:166` `await recorder.record_and_send()`; `:118 app.ws = WebSocketManager(app)`; real `ClientState`; real `websockets.serve` capture server on `127.0.0.1:0` (`_CaptureServer`) | `app` = `SimpleNamespace(state, loop, ws)` — declared allowed in tasks.md ("a minimal `app` object that holds the real `ClientState` and the real `WebSocketManager`"). `Config.save_audio=False`, `Config.dictation_mode` patched = settings, not dependencies | PASS |
| E2 | `ResultProcessor._handle_message` preview branch → `live_panel.show` (`core/client/output/result_processor.py:224-227`) | `test_live_client.py::LivePanelTests.test_preview_message_updates_real_panel`, `::test_show_does_not_activate_app`, `::test_final_hides_panel` (preview half), `::ResultProcessorLoggingTests.test_preview_is_not_logged` | `test_live_client.py:264, :358, :457, :480` `await processor._handle_message(message)`; message built by real `RecognitionMessage(...).to_json()` → `json.loads` → real `from_dict` (`:243, :355, :454, :479`); real `NSPanel` created; `NSRunLoop` pumped (`_pump_main_runloop`) | None on the preview branch (it returns before state/hotword/output). Note: the unchanged outer loop `ResultProcessor.start()` (`:159-204`) → `WebSocketManager.receive()` (`websocket_manager.py:157`) is not driven with a preview; the changed code is entirely inside `_handle_message`, which the tests call with a real message | PASS |
| E3 | `ResultProcessor._handle_message` final branch → `live_panel.hide()` when `Config.dictation_mode == 'live'` (`result_processor.py:236-239`) | `test_live_client.py::LivePanelTests.test_final_hides_panel` | `:493 await processor._handle_message(final_message)` under `patch.object(Config, 'dictation_mode', 'live')` (`:490`); `:497 assertFalse(_panel.isVisible())` | Downstream of the changed line: `processor._emit_text = AsyncMock` (`:319`; `_emit_text` exists at HEAD `:478` and is the only output exit on the final path, calls at `:420` and `:546`, so the stub really intercepts and no text is typed into a real app), `_FakeState`, `_FakeHotword`, `get_active_window_info` patched. tasks.md lists "the output/paste side of `ResultProcessor`" as the allowed fake; `_FakeState`/`_FakeHotword` go beyond that wording (they mirror the existing `test_editor_result_flow` pattern). They sit after the changed line, so the entry is still the real one | PASS (note: fake list in tasks.md understates the fakes) |
| E4 | `core/client/output/live_panel.py` (new): `show`, `hide` (any-thread API via `AppHelper.callAfter`), `_show_on_main`, `_hide_on_main`, `_auto_hide` (timer callback via `AppHelper.callLater`) | via E2/E3 plus direct: `test_long_mixed_text_label_is_not_clipped`, `test_utf16_color_ranges_across_surrogate_pair`, `test_panel_auto_hides`, `test_stale_auto_hide_does_not_hide_newer_panel`; `hide()` in `tearDown` | `test_live_client.py:334 self.live_panel.hide()`; `:388, :395, :421, :505, :519, :521 self.live_panel.show(...)`; real `NSRunLoop.currentRunLoop().runUntilDate_` pumps the real `callAfter`/`callLater` queue; asserts on real `_panel.styleMask()`, `canBecomeKeyWindow()`, `hidesOnDeactivate()`, `isVisible()`, `NSWorkspace.frontmostApplication()` | `AUTO_HIDE` patched to 0.5 s (a module constant, not a dependency) | PASS |
| E5 | `ClientConfig.dictation_mode = 'hold'` (`config_client.py:56`) | `test_recorder_default_sends_hold` (no patch on `dictation_mode`; asserts every message has `live is False`) | `test_live_client.py:170-181` | none | PASS |
| E6 | `RecognitionMessage.from_dict` reads `preview`, `text_tentative` (`core/protocol.py:128-129`) | all E2/E3 tests and both e2e receivers | `test_live_client.py:243, :355, :454, :479`; `test_live_e2e.py:179, :191` `RecognitionMessage.from_dict(json.loads(raw))` on real server output | The production caller `WebSocketManager.receive()` (`websocket_manager.py:157`) is unchanged; the changed function is called directly with real JSON | PASS |
| E7 | `ws_recv` coroutine (`core/server/connection/ws_recv.py:254`) → `AudioMessage.from_dict` (`live` read, `protocol.py:60`) → `message_handler` → `_submit_qwen_mlx_runner_patch` (`live=msg.live` into `Work`, `ws_recv.py:208`) | `tools/test_live_e2e.py::LiveE2ETests` — all four tests; hold/live split by `test_hold_run_sends_no_preview` (asserts `previews == []`) vs `test_live_run_streams_previews` (asserts `>= 2` previews) | `test_live_e2e.py:121 handler = functools.partial(ws_recv, app=self.app)` under `websockets.serve(..., '127.0.0.1', 0)`; `_record` sends real `AudioMessage(... live=live).to_json()` per 20 ms packet (`:151-163`). Routing into the qwen path needs `ServerConfig.model_type == 'qwen_asr_mlx'`: printed `qwen_asr_mlx`. Skip gates: `weights.safetensors` present in `models/Qwen3-ASR-MLX/Qwen3-ASR-1.7B-8bit` (symlinked tree) and `/usr/bin/say` present, so the class does not skip on this machine | Real `ServerState`, real `websockets`, real engine `EngineFactory.create_asr_engine('qwen_asr_mlx')` (`:206`); queues are `queue.Queue` instead of `multiprocessing.Queue`, `sockets_id` a list instead of a Manager list — same-process substitutes of transport primitives, not of any changed code | PASS (static; not run by me, see below) |
| E8 | `WorkHandler.loop` — `live_tick` call guarded by `result is None and work.live and self.buffer.is_empty and hasattr(self.pipeline, 'live_tick')` (`core/server/worker/work_handler.py:178-183`) | e2e: real `handler.loop` in a thread with the real engine and real `set_engine` → `QwenMLXRunnerPipeline` (`recognizer.uses_task_runner`); also `test_live_pipeline.py::WorkHandlerLiveTests` (3 tests) | `test_live_e2e.py:112 threading.Thread(target=self.handler.loop)`; `test_live_pipeline.py:288, :316, :339 handler.loop()` | e2e: none. Pipeline tests: `ScriptedQueue`, `ScriptedRecognizer` — both declared allowed (tasks.md "the model in `test_live_pipeline.py`", "the queue in scheduling tests"); B8 ordering is a declared gap | PASS |
| E9 | `QwenMLXRunnerPipeline.process` — live feed on non-final, `self.live.pop` on final (`qwen_mlx_runner_pipeline.py:60-71`) | e2e through E7/E8 (previews appear only when `live=True`; `test_live_final_matches_hold` asserts live final text == hold final text and no preview within 1.5 s after final); direct in `test_live_pipeline.py::PipelineLiveTests` | `test_live_pipeline.py:121, :135, :141, :153, :164, :180, :186, ...` `pipeline.process(make_work(live=...))` | e2e: none. Pipeline tests: scripted recognizer (declared) | PASS |
| E10 | `QwenMLXRunnerPipeline.live_tick` (new, `:118-162`): throwaway id `f"{task_id}#live{n}"`, `is_final=True`, exception guard, `Result(preview=True, text_tentative=...)` | e2e `test_live_run_streams_previews`, `test_live_final_matches_hold`, `test_long_live_run_keeps_up` (via E8); direct in `test_live_pipeline.py` | `test_live_pipeline.py:122, :137, :142, :149, :154, :166, :190, :201, :208, :215, :232, :249, :262 pipeline.live_tick()` | Exception guard reachable only with an injected fault → `test_failing_pass_does_not_break_final` (`:199-225`); tasks.md B11 declares this gap with its reason | PASS |
| E11 | `QwenMLXRunnerPipeline.cleanup_tasks` — `self.live.pop(task_id, None)` (`:167`). Production entry is `WorkHandler.cleanup()` (`work_handler.py:137-149`): stale ids come from `state.sessions` whose `socket_id` left `sockets_id`; reachable, since `WorkBuffer.enqueue` (`:33`) and `process` (`:50`) both call `state.get_session` for non-final live packets | Only `test_live_pipeline.py::test_cleanup_drops_live_task` | `test_live_pipeline.py:245 pipeline.cleanup_tasks(['t1'])` — a direct call on the pipeline. `git grep` for `.cleanup()` or `sockets_id.remove/clear` in the three live test files finds nothing (only `cls.recognizer.cleanup()` at `test_live_e2e.py:215`, which is the engine). The pre-existing `tools/test_worker_scheduling.py:159` checks `WorkHandler.cleanup → cleanup_tasks` wiring, but on a mocked pipeline, so it never reaches the new live pop | tasks.md B13: "Declared gap: needs a socket drop mid-recording; covered by the real `WorkHandler.cleanup` path with a controlled socket list." The gap declaration and its reason hold. The second clause is not true at HEAD: no test drives `WorkHandler.cleanup()` for a live task; the test enters one level below the production entry. No `## Acceptance` item covers a disconnect either | NEEDS-HUMAN |
| E12 | `ws_send` — copies `preview`, `text_tentative` into `RecognitionMessage` (`ws_send.py:43-44`); log guard `result.source == 'mic' and not result.preview` (`:61`) | e2e (all tests receive through the real `ws_send`); log guard asserted by `test_live_run_streams_previews` | `test_live_e2e.py:126 await ws_send(self.app)`; fields asserted on received messages (`m.preview`, `m.text_tentative`); `assertLogs('server', level='DEBUG')` + `redirect_stdout` (`:240-243`) and the per-fragment check (`:274-287`) | none | PASS |
| E13 | Data fields: `AudioMessage.live` (`protocol.py:41`), `Work.live` (`schema.py:47`), `Result.preview`, `Result.text_tentative` (`schema.py:94-95`) | exercised by E7 and E12 end to end | as E7/E12 | none | PASS |
| E14 | `core/server/worker/live_preview.py` (new): `Agreement.update`, `LiveTask.feed/due/step`, `ukey`, `is_numeral` — inner pure module called only from E9/E10 | e2e "committed text only grows" (`test_live_e2e.py:258-262`, `:342-345`) and cadence (`>= duration/2` previews, `:337`); direct spec-scenario tests in `tools/test_live_preview.py` | `test_live_preview.py:52-60, :63-75, :78-90, :93-98, :101-112, :121-137` | `ScriptedTranscribe` in the unit tests only; e2e uses the real model | PASS |

### Findings

- Every entry point the diff adds or changes has at least one automated test that calls it, and for all but one the test enters at the real production entry with real dependencies (E1 real recorder loop + real socket manager + real server on port 0; E2/E3/E4 real `_handle_message` + real `NSPanel` + real run loop; E7-E10, E12-E14 real `ws_recv`/`ws_send`/`WorkHandler.loop`/engine over a real websocket).
- E11 is the exception. The only test of the live pop in `cleanup_tasks` calls the pipeline method directly; the production entry `WorkHandler.cleanup()` is never driven for a live task. tasks.md declares this as a gap (B13), which by the rule makes the row NEEDS-HUMAN rather than FAIL, but the declaration's coverage claim ("covered by the real `WorkHandler.cleanup` path with a controlled socket list") does not match HEAD and should be corrected or the test should be added (a `WorkHandlerLiveTests` case that removes `'s1'` from `sockets_id` after a live packet and asserts `pipeline.live == {}` would do it with the already-allowed fakes).
- tasks.md's allowed-fake list understates `test_final_hides_panel`: `_FakeState` and `_FakeHotword` are on the path, not only "the output/paste side". They sit after the changed line, so E3 still enters at the real point; the list should name them.
- The e2e file is the production-entry test for E7-E10 and E12-E14. I confirmed it will not skip here (model weights and `say` present, `model_type == 'qwen_asr_mlx'`) but I did not run it, per the instruction not to run tests while another reviewer mutates the tree. tasks.md 7.1's "test_live_e2e 4/4 on the real model" therefore stays a claim in this section; the test-running reviewer's result decides it.
- No Tauri command, CLI path or UI action exists in this diff to check.

Verdict for question 1: NEEDS-HUMAN — every entry point is tested at its real production entry except the live pop in `cleanup_tasks` (E11), whose only test bypasses `WorkHandler.cleanup()`; tasks.md declares the gap but misdescribes its coverage, and no Acceptance item covers a mid-recording disconnect.

---

## 2. Fails before

Reviewer: fresh subagent, paths and commands only. Tree: `/Users/qingyun.yuan/code/open-source/CapsWriter-wt/integ` detached at 44146fa. Interpreter: `/Users/qingyun.yuan/code/open-source/CapsWriter-for-macOS/.venv/bin/python` (Python 3.13.12). Every "Result:" note in tasks.md was treated as a claim and re-run.

### What I ran

1. Baseline, whole suite, run 1 of 2 (`tools/test_*.py -v`, e2e with `HF_HUB_OFFLINE=1`):

| File | Result |
|---|---|
| test_live_preview | Ran 6, OK |
| test_live_pipeline | Ran 11, OK |
| test_live_client | Ran 12, OK |
| test_worker_scheduling | Ran 10, OK |
| test_editor_annotation | 8 PASS, 0 FAIL |
| test_editor_result_flow | 16 PASS, 0 FAIL |
| test_editor_ui_contract | `PASS: editor UI contract` |
| test_mic_shortcut_lifecycle | Ran 9, OK |
| test_stream_stop_leak | Ran 14, OK |
| test_mlx_model_resolution | Ran 4, OK (belongs to 5e4ff2b, a separate change) |
| test_live_e2e | Ran 4 in 62.5 s, OK (real model, `weights.safetensors` present through the symlinks) |

2. Previous behaviour, two commits, each extracted with `git archive` into the scratchpad (no worktree added to the repo), `models/` symlinked to the integ tree, the four new test files copied in:
   - `33eba19` (before the change; `git diff 33eba19..HEAD` is the change).
   - `8d30c2d` (contract fields only: `AudioMessage.live`, `RecognitionMessage.preview/text_tentative`, `Work.live`, `Result.preview/text_tentative`; no behaviour). This is the commit where the signatures allow the tests to run.

   At `33eba19`:
   - `test_live_preview.py`: `ImportError: cannot import name 'live_preview' from 'core.server.worker'` (new module; counts as fails-before).
   - `test_live_pipeline.py`: 11 errors, all `TypeError: Work.__init__() got an unexpected keyword argument 'live'` (signature; not an assertion).
   - `test_live_client.py`: `Ran 5 ... FAILED (failures=4, errors=2)`. The four recorder tests fail by assertion: `AssertionError: False is not true : [{... 'language': 'auto'}]` (no `live` key in any message). `test_preview_is_not_logged`: `TypeError: RecognitionMessage.__init__() got an unexpected keyword argument 'preview'`. `LivePanelTests.setUpClass`: `ImportError: cannot import name 'live_panel'`.
   - `test_live_e2e.py`: not run here; `AudioMessage(live=...)` raises the same TypeError, so the signature does not allow it.

   At `8d30c2d`:
   - `test_live_preview.py`: ImportError as above.
   - `test_live_pipeline.py`: `Ran 11 ... FAILED (failures=1, errors=8)`. 8 errors `AttributeError: 'QwenMLXRunnerPipeline' object has no attribute 'live'` / `'live_tick'`. `test_final_is_not_queued_behind_passes` fails by assertion: `AssertionError: 1 != 2` (only the final reached `queue_out`, no preview). `test_live_and_final_drained_together_skips_live_tick` and `test_empty_preview_reaches_no_queue_out` pass (negative properties; pinned by mutations H4 and H24 below).
   - `test_live_client.py`: `Ran 5 ... FAILED (failures=3, errors=1)`. `test_recorder_live_mode_tags_messages` and `test_recorder_live_mode_tags_cache_flush_message` fail by assertion (`'live': False` on every message). `test_preview_is_not_logged` fails by assertion: `AssertionError: True is not false : ['接收到识别结果，文本: 罕见委托文本极光, 时延: 0.10s']` (the old non-final path logged the text). `test_recorder_default_sends_hold` and `test_recorder_unknown_mode_sends_hold` pass (they describe the old behaviour; pinned by H2 and H2c). Panel class: ImportError.
   - `test_live_e2e.py` (real model): `Ran 4 in 62.4 s, FAILED (failures=2)`. `test_live_run_streams_previews`: `AssertionError: 0 not greater than or equal to 2 : 几秒钟的live录音至少应产生两次预览`. `test_long_live_run_keeps_up`: `AssertionError: 0 not greater than or equal to 14`. `test_hold_run_sends_no_preview` and `test_live_final_matches_hold` pass (identity properties; pinned by H1 and by the toml rows "preview pass reuses the real task id", "ws_send drops preview").

3. Call-site mutations by hand (`scratchpad/hand_muts.py`, `hand_muts.log`, `hand_muts_rerun.log`, `hand_muts_extra.log`): 31 rows, each run against the narrowest selection (one test method or one class), file restored and sha256-checked after each row. 30 CAUGHT, 1 MISSED (H29, see Findings). Three rows (H12, H13, H14) first came back MISSED; the mutation kept the file size and ran within the same second as the previous row, so Python reused the previous row's `.pyc`. Re-run with `__pycache__` cleared and `PYTHONDONTWRITEBYTECODE=1`: all three CAUGHT with assertion failures (`'今天下午三点开会' != ''`, `'你好世界今' != '你好世界'`, `'价格是一万五千' != '价格是'`).

4. The 40-row `mutations.toml` claim ("40/40 CAUGHT at 3380b4e"): re-run at HEAD from a narrowed copy (`scratchpad/mutations_narrow.toml`, same rows, each test command cut to the file or class that pins it; 6 rows keep the e2e but run only `test_live_run_streams_previews` [+ `test_live_final_matches_hold` for the task-id row]), with `__pycache__` cleared and `PYTHONDONTWRITEBYTECODE=1`:
   `RESULT mutate caught=40 missed=0 skipped=0 errors=0`.

5. Whole suite, run 2 of 2, at the end: see the table at the bottom.

6. `git status --porcelain` after every mutation batch and at the end: empty. The only files I removed in the tree were `__pycache__` directories (git-ignored, `.gitignore:6`). No source file, test file or spec file was left changed.

### Scenario table

Fails-before column: "prev" = fails by assertion against 8d30c2d (or 33eba19 where stated); "import" = ImportError on a new module; "H*" = hand mutation at the production call site, CAUGHT with the quoted failure; "toml" = row in mutations.toml, CAUGHT in the narrowed run.

| Requirement / scenario | Test that pins it | Fails before | Row verdict |
|---|---|---|---|
| Dictation mode setting / Default keeps today's behaviour | `test_live_client::test_recorder_default_sends_hold`; `test_live_pipeline::test_hold_task_never_runs_a_pass`; `test_live_e2e::test_hold_run_sends_no_preview` | Cannot fail on the old commit (it is the old behaviour). H2c recorder `live=True` at all three sites: CAUGHT (`test_recorder_default_sends_hold` FAIL). H1 pipeline `elif work.live:` -> `else:`: CAUGHT (`{} != {'t1': LiveTask}`; hold packets were fed as live) | PASS |
| Dictation mode setting / Unknown value falls back to hold | `test_live_client::test_recorder_unknown_mode_sends_hold` | 33eba19: assertion (no `live` key). H2 recorder `== 'live'` -> `!= 'hold'`: CAUGHT (unknown-mode test fails, default test passes) | PASS |
| Dictation mode setting / Another engine sends no partials | none | H29 removes `and hasattr(self.pipeline, 'live_tick')` from the tick condition in `work_handler.py`: MISSED across `test_live_pipeline` (11 OK), `test_worker_scheduling` (10 OK), `test_stream_stop_leak` (14 OK). `WorkPipeline` has no `live_tick`; the scheduling tests use `Mock()` pipelines (which answer `hasattr` True) and never set `work.live`. Not declared as a gap in tasks.md | FAIL |
| Live preview / First words appear while speaking | `test_live_e2e::test_live_run_streams_previews` (>= 2 previews, first non-empty); `test_live_pipeline::test_pass_cadence_follows_audio_time` (first pass at 1 s, none without new audio) | prev e2e: `0 not greater than or equal to 2`. H3 `live_tick()` call -> `None`: CAUGHT (`1 != 2`). H11 `INTERVAL` 1.0 -> 0.5: CAUGHT (`1 != 0`). The "within 2 s" wall-clock bound is not asserted (design: bounds only, GPU shared); it is Acceptance A1 | PASS (timing to user) |
| Live preview / Focus stays in the target app | `test_live_client::test_show_does_not_activate_app`; `::test_preview_message_updates_real_panel` (style mask, `canBecomeKeyWindow` False, ignores mouse, no hide-on-deactivate) | import (new module). H17 style mask -> 0: CAUGHT (`False is not true` on the mask assert). H18 `activateIgnoringOtherApps_(True)` after `orderFrontRegardless`: CAUGHT (`83684 != 1400 : 显示面板不得改变最前台应用`). toml: hides on deactivate, takes mouse events, never ordered front: CAUGHT | PASS (real app to user, A1) |
| Live preview / Committed text does not change during the utterance | `test_live_preview::LiveTaskTests` (committed only grows); `test_live_e2e::test_live_run_streams_previews` and `::test_long_live_run_keeps_up` (each committed text extends the previous) | H28 `self.committed +=` -> `=`: CAUGHT (`'今天' != '你好世界今天'`). H10 pass reads only the last second: CAUGHT (`[16000, 16000, 16000, 16000] != [16000, 32000, 48000, 64000]`) | PASS |
| Live preview / A short press or a cancelled recording | `test_live_client::test_panel_auto_hides`; `::test_stale_auto_hide_does_not_hide_newer_panel`; `test_live_pipeline::test_empty_preview_produces_no_result`, `WorkHandlerLiveTests::test_empty_preview_reaches_no_queue_out` (no panel before any text) | import. H20 `callLater(AUTO_HIDE, ...)` -> `pass`: CAUGHT (`超过 AUTO_HIDE 后必须自动隐藏`). H19 generation check -> `if True`: CAUGHT. H24 empty-preview guard -> `if False`: CAUGHT (a `Result(preview=True, text='')` was returned) | PASS |
| Live preview / colours, raw text | `test_preview_message_updates_real_panel` (labelColor / secondaryLabelColor); `test_utf16_color_ranges_across_surrogate_pair` | H21 committed grey: CAUGHT (`secondaryLabelColor != labelColor`). toml: tentative in normal colour, label height: CAUGHT. "No formatter on preview" is by construction in `live_tick` (no `TextFormatter` call); no separate test, covered by the e2e text checks only loosely | PASS |
| Commit rule / A tail word is not committed early | `test_live_preview::test_tail_word_not_committed_early` | import. H12 `AGREE` 3 -> 2: CAUGHT (`'我刚用cloud ' != ''`). H13 `HOLDBACK` 4 -> 3: CAUGHT (`'我' != ''`). H27 case-sensitive keys: CAUGHT (`'我刚用' != '我刚用Cloud '`) | PASS |
| Commit rule / An open numeral run waits | `::test_open_numeral_run_waits` | H14 numeral hold off: CAUGHT (`'价格是一万五千' != '价格是'`) | PASS |
| Commit rule / An insertion inside committed text does not duplicate the tail | `::test_insertion_does_not_duplicate_tail` | H15 alignment off: CAUGHT (`'你好世界界今天' != '你好世界今天'`) | PASS |
| Commit rule / Tentative text does not end with punctuation | `::test_trailing_punctuation_hidden` | H16: CAUGHT (`'你好，世界。' != '你好，世界'`) | PASS |
| Final unchanged / The output is the final text | `test_live_e2e::test_live_final_matches_hold` (live final == hold final; nothing after the final for 1.5 s); `test_live_client::test_final_hides_panel` (hide before output); `test_live_pipeline::test_final_pops_live_task` | H6 `hide()` -> `pass`: CAUGHT (`final 到达后面板必须隐藏`). H8 pop on final -> `pass`: CAUGHT (`'t1' unexpectedly found`). toml "preview pass reuses the real task id" (e2e): CAUGHT. H22/H23 `from_dict` drops `preview`/`text_tentative`: CAUGHT | PASS (paste to user, A2) |
| Final unchanged / Final is not queued behind several partials | `WorkHandlerLiveTests::test_final_is_not_queued_behind_passes`; `::test_live_and_final_drained_together_skips_live_tick` | prev: `1 != 2`. H3: CAUGHT. H4 drop `self.buffer.is_empty`: CAUGHT (`1 != 0`, a pass ran with a final buffered). Real-socket ordering: declared gap B8 in tasks.md | PASS |
| Each pass reads the whole recording / A one-minute dictation | `test_live_e2e::test_long_live_run_keeps_up` (about 30 s TTS clip, >= duration/2 previews, last preview within 3 s of send end, committed only grows); `LiveTaskTests`; `test_pass_cadence_follows_audio_time` | prev e2e: `0 not greater than or equal to 14`. H10, H11: CAUGHT. toml "next_due advanced after the model call": CAUGHT (H25: `2 != 1 : 不足1秒新音频时不应该再重试失败的pass`). A 60 s recording is Acceptance A4 | PASS (60 s to user) |
| Private and transient / No partial text in logs | server: `test_live_pipeline::test_preview_is_not_logged`, `test_live_e2e::test_live_run_streams_previews` (server logger at DEBUG + stdout); client: `test_live_client::test_preview_is_not_logged` | prev client: assertion (`'接收到识别结果，文本: 罕见委托文本极光...'`). H5 drop `return` after `show()`: CAUGHT (same line). toml "ws_send logs preview text" (e2e): CAUGHT. Diary/clipboard/UDP: the preview branch returns before all of them and a preview has `is_final=False`, so the final branch is unreachable; no separate test | PASS |
| Partial failures do not break dictation / A failing partial pass | `test_live_pipeline::test_failing_pass_does_not_break_final` | H7 `except Exception` -> `except ZeroDivisionError`: CAUGHT (`RuntimeError: boom` escapes). H25: CAUGHT. "error is logged without text": the log line carries only `task_id[:8]` and the exception type; no test asserts it. Real-model fault: declared gap B11 | PASS (minor note) |
| TDD quality gate / Gate before hand-off | this review | All new tests pass (run 1 and run 2). Existing tools/ tests pass. mutations.toml: 40/40 CAUGHT at HEAD | PASS for the three listed checks; the gate's own text ("every new behaviour ... a test that fails before") is what the other-engine row fails |

Declared gaps (B8 real-socket ordering, B11 real-model fault, B13 socket drop mid-recording) are stated in tasks.md with reasons and are covered by the real `WorkHandler`/pipeline with a scripted engine; accepted as declared.

### Findings

1. FAIL: "Another engine sends no partials" has no test that can fail. Removing the `hasattr(self.pipeline, 'live_tick')` guard in `core/server/worker/work_handler.py` survives every test that drives `WorkHandler` (H29). In production the loop's `except Exception` would turn the missing guard into one logged error per 20 ms live packet on a non-MLX engine, with the final still delivered, so the user-visible harm is log noise, not lost text. The fix is one test in `tools/test_live_pipeline.py`: drive the real `WorkHandler.loop` with a pipeline object that has `process` but no `live_tick` (a plain class, not `Mock()`), feed one live non-final packet and one final, assert `queue_out` holds only the final and the `server` logger recorded no error. tasks.md's B-table should list it (or declare it as a gap with a reason).
2. Note for `~/.claude/tools/mutate.py`, not for this change: a mutation that keeps the file size and runs within one second of the previous row can be served a stale `.pyc` and be reported MISSED (or CAUGHT for the wrong reason). Three rows of my narrow run hit it before I cleared `__pycache__` and set `PYTHONDONTWRITEBYTECODE=1`. The 5C run at 3380b4e ran four files per row (several seconds), so it was not exposed; the recorded 40/40 stands and reproduces.
3. The two timing statements in the spec ("within 2 s", "60 s") and the focus behaviour in a real target app are not asserted by automation; they are Acceptance A1, A2, A4 and stay with the user.
4. Minor: no test asserts that the failing-pass error log carries no text (the line is built from `task_id[:8]` and `type(exc).__name__` only).

### Final whole-suite run (run 2 of 2)

Run after all mutations were restored; `git status --porcelain` empty before and after; HEAD 44146fa.

| File | Pass | Fail |
|---|---|---|
| test_live_preview | 6 | 0 |
| test_live_pipeline | 11 | 0 |
| test_live_client | 12 | 0 |
| test_worker_scheduling | 10 | 0 |
| test_editor_annotation | 8 | 0 |
| test_editor_result_flow | 16 | 0 |
| test_editor_ui_contract | PASS | - |
| test_mic_shortcut_lifecycle | 9 | 0 |
| test_stream_stop_leak | 14 | 0 |
| test_mlx_model_resolution | 4 | 0 |
| test_live_e2e (real model, 62.6 s) | 4 | 0 |

Total: 94 unittest cases + the editor UI contract check, 0 failures. Same counts as run 1.

Verdict for question 2: FAIL — every requirement is pinned and shown failing on 8d30c2d or by a call-site mutation (31 hand rows, 40/40 toml rows), except the delta-spec scenario "Another engine sends no partials", which has no test: dropping the `hasattr(..., 'live_tick')` guard survives the whole suite.

---

## 3. Real versus simulated

Judged at HEAD `44146fa` (`git rev-parse HEAD`). `git status --short` and `git diff --stat` printed nothing, so the working tree equalled HEAD when read. Every source read below used `git show HEAD:<path>`. No build or test was run.

### What I ran

- `git log --oneline 33eba19..HEAD` (29 commits), `git diff --stat 33eba19..HEAD` (33 files, 3592 insertions).
- `git show HEAD:` on the four test files (`tools/test_live_preview.py`, `tools/test_live_pipeline.py`, `tools/test_live_client.py`, `tools/test_live_e2e.py`), the new modules (`core/server/worker/live_preview.py`, `core/client/output/live_panel.py`), the diff of every changed production file, and the production wiring each harness stands in for: `core/server/worker/work_handler.py`, `worker.py`, `model_loader.py`, `process_manager.py`, `core/server/connection/ws_recv.py`, `ws_send.py`, `server_manager.py`, `core/server/state.py`, `core/server/engines/qwen_asr_mlx/asr_engine.py`, `core/client/connection/websocket_manager.py`, `core/client/output/result_processor.py`, `core/client/output/edit_panel.py`, `core/client/app.py`, `core/client/main.py`, `start_client.py`, `start_client_macos.py`, `capswriter.py`, `config_server.py`, `openspec/changes/add-live-dictation-mode/mutations.toml`.
- `git diff 33eba19..HEAD --stat -- mlx-qwen3-asr` printed nothing: the submodule pointer is unchanged (`f745f5e`).
- `ls -la /Users/qingyun.yuan/code/open-source/CapsWriter-wt/integ/mlx-qwen3-asr/` printed an empty directory. `direct_url.json` of the venv package says `{"url":"file:///Users/qingyun.yuan/code/open-source/CapsWriter-for-macOS/mlx-qwen3-asr","dir_info":{}}` (non-editable snapshot). `cmp` of the venv `capswriter_runner.py` and `__init__.py` against the main checkout's submodule source printed `IDENTICAL` for both.
- `ls -la models/Qwen3-ASR-MLX/Qwen3-ASR-1.7B-8bit/` in the worktree: symlinks to the main checkout, including `weights.safetensors`, so the e2e gate `_MODEL_READY` is true here and the e2e is not silently skipped.
- `git grep` over `tools/` for `live_tick|WorkPipeline|live=` outside the four live test files: no hits. `git grep` for `callAfter|present_editor|runUntilDate_` outside the live tests: only `test_editor_result_flow.py`, which patches `present_editor` out.

### Bypass inventory

Each row: where the production path is replaced, what decision that skips, and what else covers it.

| # | File / test | Bypass | Decision skipped | Covered elsewhere? |
|---|---|---|---|---|
| 1 | `test_live_pipeline.py` `ScriptedRecognizer` | Fake engine (`feed_audio_patch`, `cancel_task`) | Real model call; runner state for the `#liveN` throwaway id | Yes. Fake matches the real contract I read in `capswriter_runner.py:118-140,200-240` (non-final buffers and returns `None`; final pops state and returns `.text` stripped; unknown id is created on first sight). Real engine runs in `test_live_e2e.py` via `handler.set_engine(...)` for B1, B4-B7, B9, B10. Declared allowed fake in `tasks.md` "Test notes". |
| 2 | `test_live_pipeline.py` `ScriptedQueue` | Fake `queue_in` | Arrival order of live packet vs final (B8) | Declared gap in `tasks.md` B8 ("cannot be forced through a real socket without timing"). Real `WorkHandler.loop` and real pipeline run; only the queue is scripted. Same pattern as existing `test_worker_scheduling.py`. |
| 3 | `test_live_pipeline.py` `handler.pipeline = pipeline` | Skips `WorkHandler.set_engine` | The `uses_task_runner` pipeline selection | Yes. `test_live_e2e.py` `ServerHarness` calls `set_engine(recognizer=<real QwenASRMLXEngine>)`; `asr_engine.py:77` has `uses_task_runner = True`, so the real selection picks `QwenMLXRunnerPipeline`. |
| 4 | `test_live_pipeline.py`, `test_live_e2e.py` | `sockets_id` is a plain `list`, not `Manager().list()` | ListProxy `in` semantics | Unchanged code; same as `test_worker_scheduling.py`. Not a decision of this change. |
| 5 | `test_live_preview.py` `ScriptedTranscribe` | Scripted `transcribe` callable in `LiveTask.step` | Model text | By design D5 the rule is pure and `transcribe` is injected. Real closure over the real engine runs through `live_tick()` in the e2e (B6 "committed only extends", B9 long run). |
| 6 | `test_live_e2e.py` `ServerHarness` | `ServerState(sockets_id=[], queue_in=queue.Queue(), queue_out=queue.Queue())`; `WorkHandler.loop` in a thread, not a child `Process` | Pickling of `Work.live`, `Result.preview`, `Result.text_tentative` across `multiprocessing.Queue`; the worker running in another process | No automated test crosses a real process boundary. The new fields are a `bool` and a `str` on dataclasses that already cross the queue; `LiveTask` (holds numpy chunks) never leaves the worker (`pipeline.live` dict). Low risk, but only the user's Acceptance A1-A4 exercise the real `ProcessManager` path (`process_manager.py:49-62`). |
| 7 | `test_live_e2e.py` `set_engine(recognizer, punc_model=None, aligner=None)` | No punc model, no aligner | Formatter and aligner on the final | `punc_model=None` matches production: `asr_engine.py` `capabilities` returns `[ASR, PUNC]`, so `model_loader.py` skips `_load_punc_model`; `TextFormatter(None)` in both. `aligner=None` differs from production (`ManagedAlignerProxy`), but `QwenMLXRunnerPipeline.process` (HEAD lines 38-115) never reads `self.aligner`, and the diff touches no aligner line. Not a decision of this change. |
| 8 | `test_live_e2e.py` `EngineFactory.create_asr_engine('qwen_asr_mlx')` literal | Skips `Config.model_type` | Engine choice | On darwin `config_server.py` `model_type = 'qwen_asr_mlx'`; `ws_recv._use_qwen_mlx_runner_path()` reads the real `Config.model_type`, so harness engine and recv path agree for the same reason production does. |
| 9 | `test_live_e2e.py` `os.environ.setdefault('HF_HUB_OFFLINE', '1')` | Environment override | Hub fallback during model load | Affects only model loading, not any decision under test. The local model dir exists (symlinks), so production would not reach the hub either. |
| 10 | `test_live_e2e.py` `_record()` | Hand-built `AudioMessage(live=...)` and `RecognitionMessage.from_dict(json.loads(raw))` instead of `AudioRecorder` and `WebSocketManager.receive` | Client tagging and client decoding | Yes. `test_live_client.py` `RecorderLiveModeTests` run the real `AudioRecorder.record_and_send` and real `WebSocketManager.connect/send` to a port-0 capture server and assert `live` on the wire for all three `AudioMessage` sites. `websocket_manager.py:receive()` body is exactly `json.loads` then `RecognitionMessage.from_dict`, the same two calls the tests make. |
| 11 | `test_live_e2e.py` `ServerHarness._serve` | Runs `ws_recv`/`ws_send` without `SocketManager._watch_connections()` | Disconnect watcher | Unchanged code (`server_manager.py:121-141` wires the same `partial(ws_recv, app=...)` and `ws_send(app)`). Not a decision of this change. |
| 12 | Environment: e2e in this worktree imports the venv's `mlx_qwen3_asr` snapshot, because `mlx-qwen3-asr/` here is empty and `_ensure_local_package_precedence` (`asr_engine.py:282-295`) inserts an empty dir | Runner copy | Verified: venv `capswriter_runner.py` and `__init__.py` are byte-identical to the submodule source at the pinned `f745f5e`. Not a real divergence. |
| 13 | `test_live_client.py` `_CaptureServer` | Fake server for recorder tests | Server handling of `live` | Yes. Real `ws_recv` copies `live=msg.live` in the e2e; mutation row "ws_recv does not pass live into the non-final Work" is gated on the e2e. |
| 14 | `test_live_client.py` `SimpleNamespace(state=ClientState(), loop=...)`, `app.ws = WebSocketManager(app)` | Minimal `app` | `CapsWriterClient` construction | Declared allowed in `tasks.md`. Real `ClientState` and real `WebSocketManager`; `app.py:73-93` shows production uses the same three members. |
| 15 | `test_live_client.py` `_FakeState`, `_FakeHotword`, `processor._emit_text = AsyncMock`, `patch(get_active_window_info)`, `patch.multiple(Config, editor_mode/llm_enabled/save_audio/hot=False)` | Output side stubbed on the final branch | Paste, hotword, editor, diary | Declared allowed ("so tests never type into the user's apps"). The new `hide()` call sits before any of these (`result_processor.py` final branch, first statement). The rest of the final path is unchanged code covered by `test_editor_result_flow.py` (16/16 at 33eba19 per tasks 1.1). |
| 16 | `test_live_client.py` `patch.object(Config, 'dictation_mode', ..., create=True)` | `create=True` | Existence of the setting | Inert at HEAD (`config_client.py` defines `dictation_mode = 'hold'`). `test_recorder_default_sends_hold` uses no patch, so a removed setting would still fail there. |
| 17 | `test_live_client.py` `_pump_main_runloop` | `_handle_message` runs on the main thread and the test pumps `NSRunLoop.currentRunLoop()`; production runs `_handle_message` on `CapsWriterClientThread` (`start_client_macos.py:98,658-680`) while the main thread runs `AppHelper.runEventLoop()` (`:707`) | The cross-thread `AppHelper.callAfter` hop into the real AppKit run loop | Not covered by any automated test (grep above). Production precedent: `edit_panel.present_editor` uses the same `AppHelper.callAfter` from the same thread (`edit_panel.py:161`) and is shipped. Design D8 and `tasks.md` declare the running-app checks as Acceptance A1-A4 for the user. Declared, assigned to a human. |
| 18 | `test_live_client.py` `setActivationPolicy_(Accessory)` | Test process policy | Whether `orderFrontRegardless` can show a window | Matches production: `start_client_macos.py:70` sets `NSApplicationActivationPolicyAccessory`. Not a bypass. |
| 19 | `test_live_client.py` `patch.object(live_panel, 'AUTO_HIDE', 0.5)` | Constant override | The 5 s value itself | Mechanism (generation counter, timer) is real; the literal `5.0` is unverified by test and has no mutation row. Minor. |

### Declared gaps I checked against the code

- B8, B11, B13 are declared in `tasks.md` §2 with reasons. B8 and B13 run the real `WorkHandler.loop` / `cleanup` with fake queue and engine (rows 1-2). B11 needs an injected fault; no real-engine test can force it. All three are declared, so not counted as undeclared bypasses.
- `tasks.md` "The only fakes allowed" lists: the model in `test_live_pipeline.py`, the queue in scheduling tests, the output side of `ResultProcessor`, and a minimal `app`. Every fake I found is in that list except `ScriptedTranscribe` in `test_live_preview.py` (design D5 makes the injected callable part of the API, so it is a design seam, not a fake) and `_CaptureServer` (a socket peer that receives only, covered by the real server in the e2e).

### Notes outside this question's scope (for the other reviewers)

- The spec scenario "Another engine sends no partials" has no test and no row in the B table. In every configuration that exists today `work.live` is `False` for a non-MLX engine (`ws_recv` legacy path builds `Work` without `live`), so the `hasattr(self.pipeline, 'live_tick')` guard in `work_handler.py` is unreachable. Not a simulated-path issue; a coverage/simplify question.
- Under `start_client.py` (`core/client/main.py:17`, asyncio on the main thread, no AppKit run loop) `AppHelper.callAfter` never runs, so the panel never shows. `live_panel.py` docstring states this. Production on macOS runs `CapsWriter.app` (`capswriter.py:_build_client_plist`, `exe = APP_EXECUTABLE`), which is `start_client_macos.py`.

### Verdict

- No undeclared bypass found. Every fake is either in the allowed list, backed by a real-path test in `test_live_e2e.py` or `test_live_client.py`, or sits on code the diff does not touch.
- The one bypass with a real behavioural stake and no automated cover is row 17 (same-thread run-loop pump vs. the production cross-thread dispatch into `AppHelper.runEventLoop()`), together with row 6 (thread instead of `multiprocessing.Process`). Both are declared and assigned to the user's Acceptance A1-A4, which remain unticked.

Verdict for question 3: NEEDS-HUMAN — no undeclared bypass; the cross-thread AppKit dispatch (row 17) and the real worker process boundary (row 6) are covered only by the user's Acceptance A1-A4.

---

## 4. Open items

Judged at HEAD `44146fa` in `/Users/qingyun.yuan/code/open-source/CapsWriter-wt/integ`. `git status --short` printed nothing, so the working-tree `tasks.md` equals `HEAD:openspec/changes/add-live-dictation-mode/tasks.md`. No build or test was run. `openspec validate` (read-only) was run once. There is no `notes.md` in the change directory (`ls` printed "No such file or directory"), so the CLAUDE.md status block from commit `6474bf0` is the only final summary and is compared below.

### What I ran

| Command | Output |
|---|---|
| `git status --short` | (empty) |
| `git log --oneline 33eba19..HEAD` | 30 commits, top `44146fa Tick verification tasks for live dictation` |
| `ls .../add-live-dictation-mode/notes.md` | No such file or directory |
| `grep -n '^- \[ \]' tasks.md` (by reading the file) | 5 unchecked: 8.1, A1, A2, A3, A4 |
| `/Users/qingyun.yuan/.local/bin/openspec validate add-live-dictation-mode` | `Change 'add-live-dictation-mode' is valid`, exit 0 |
| `git rev-parse feature/live-dictation` vs `HEAD` | SAME (`44146fa`) |
| `git rev-parse --verify origin/feature/live-dictation` | `fatal: Needed a single revision` (no remote ref, so not pushed) |
| `git diff --stat 3380b4e..HEAD -- . ':!openspec'` | only `.gitignore`, `CLAUDE.md`, `config_server.py`, `tools/test_mlx_model_resolution.py` (the separate 5e4ff2b change plus docs) |
| `git show HEAD:.../mutations.toml \| grep -c '^[[mutation]]'` | 40 |
| `grep -c 'def test_'` on the four new test files at HEAD | live_preview 6, live_pipeline 11, live_client 12, live_e2e 4 |
| `grep -E '^\| F[0-9]+'` on both adversarial files | requirements: 23 FIXED, 3 ACCEPTED (F4, F24, F26); design: 4 FIXED, 13 NOTE; none OPEN or DEFERRED |
| `git show HEAD:<file>` greps for each review-5A finding (see below) | all 20 present in HEAD |

### Unchecked tasks (open)

| Task | Text | Who can close it | Status |
|---|---|---|---|
| 8.1 | Fable acceptance in a fresh subagent (`opsx:accept`) | this review | In progress. It is the only unchecked non-user task. |
| A1 | Live mode: panel shows text within about 2 s of the first word and updates while speaking; the text field keeps focus and its caret | user, in the running app | Open. No automated test can check focus in a real target app (design D8 risk, review-5A "waiting for the user"). |
| A2 | On release in live mode, the pasted text is the final text and the panel closes | user | Open. |
| A3 | With the default `'hold'`, dictation looks and behaves as before (no panel) | user | Open. |
| A4 | A dictation of about one minute in live mode keeps updating to the end | user | Open. The e2e long case uses a 30 s TTS clip, not one minute. |

The user must also judge the accepted requirements finding F4: on the user's own voice the offline eval missed four pre-registered thresholds (commit error 1.4 % vs 0.5 %, commit lag about 3 s vs 2 s, preview MER, jump p90). The proposal states this and defers the "feel" to A1. Nothing in the code can settle it.

### Checked tasks whose note I verified

| Task | Note in tasks.md | What I checked at HEAD | Result |
|---|---|---|---|
| 3B.1 | w15 window ported first, removed after the real-model e2e run | commits `8c1453c`, `64663ac`, `28c89ea`; design D5; `live_preview.py` has no window code | Matches. |
| 5A | "0 HIGH, 9 MEDIUM, 11 LOW; all applied in group 6" | Each finding: #1 `cellSizeForBounds_` at `live_panel.py:117`; #2 `if Config.dictation_mode == 'live'` at `result_processor.py:236`; #3 `work.live` in `work_handler.py:178` and `elif work.live` in pipeline (the pop on final stays unconditional, with a comment giving the reason at `qwen_mlx_runner_pipeline.py:61-63`; a deliberate deviation, documented in code); #4 preview `Result` has only `task_id, socket_id, source, text, text_tentative, preview`; #5/#6/#7/#11 new tests `test_empty_preview_produces_no_result`, `test_live_and_final_drained_together_skips_live_tick`, `test_stale_auto_hide_does_not_hide_newer_panel`, `test_empty_preview_reaches_no_queue_out`; #8 e2e asserts no preview after final (`test_live_e2e.py:313-314`) and last-preview bound (`:336-338`); #9 helpers `_run_live_pass`, `_ensure_panel`, `_attributed_text`, `_resize_panel`, `_tail_start` gone; #10 attributed strings appended, no NSRange (`live_panel.py:99-109`); #12 no `sys.modules` stubs in `test_live_client.py`; #13 exact `'我刚用Cloud '` at `test_live_preview.py:54`; #14 `NSFloatingWindowLevel` direct, no `setReleasedWhenClosed_`; #15 `work.samplerate`, `\w` comment at `live_preview.py:40`; #16 recorder diff has only `+` lines; #17 readme "正文颜色/灰色", "按设计", CLAUDE.md status, no `lane-rules` refs, Chinese comment on first `live=`; #18 no `_APPKIT_OK`; #19 readme sentence on minutes-long recordings; #20 docstring at `protocol.py:82-83` | All 20 applied. |
| 5B | ws_send merge applied; hoisted import superseded by #2 | `ws_send.py:61` `if result.source == 'mic' and not result.preview:`; imports stay inside the two branches | Matches. |
| 5C | 40 rows, 40/40 CAUGHT at 3380b4e | 40 rows at HEAD; every call site in the 5C list has a row (32 listed + 8 extra). The RESULT line is a claim from another tree; I did not run mutations (tests reviewer's question). | Rows present. Run not reproduced here. |
| 5D | readme and CLAUDE.md (decision row and the task list) | readme section "实时预览模式（可选）" present; CLAUDE.md 流式识别策略 row updated; new dated status block at top. The 任务看板 table (CLAUDE.md:197+) has no live-dictation row. | Done, with one doc nit (below). |
| 7.1 | all tests pass at 1c760dc; e2e 4/4; mutations 40/40 at 3380b4e; only later code change is 5e4ff2b; openspec validate passes | `openspec validate` reproduced: valid. The diff stat confirms the only later non-openspec changes are the 5e4ff2b files and CLAUDE.md. Test, e2e and mutation runs not reproduced here (other reviewer). | Validate reproduced. Runs are claims for the tests question. |
| 7.2 | no stray files; commit on `feature/live-dictation`; no push | clean tree; branch == HEAD; no `origin/feature/live-dictation` | Matches. |

### Final summary vs tasks.md

CLAUDE.md status block (HEAD, lines 3-9): "实现完成，待验收", tests live_preview 6 / live_pipeline 11 / live_client 12 / e2e 4/4, mutations 40/40, "Fable 验收评审待进行", "真机验收 A1–A4 等待用户确认，尚未完成". The test counts match HEAD. The two open groups (8.1, A1-A4) match tasks.md. No item is marked done in one place and open in the other.

### Declared gaps (planned, not open tasks)

Plan table in tasks.md section 2 declares three behaviours with no production-entry test: B8 (final not queued behind passes; needs socket timing), B11 (failing pass; needs an injected fault), B13 (disconnect drops the live task; needs a socket drop). Each has a controlled-environment test. These are declared with a reason as the TDD gate allows. A4 partly covers B8/B9 by hand.

### Doc nits found (not blocking)

- tasks.md section 2, row B12 names `test_live_client::test_panel_is_non_activating` and `::test_panel_colours`. Neither name exists at HEAD. The same assertions live in `test_preview_message_updates_real_panel` (`test_live_client.py:364-376`: style mask, ignoresMouseEvents, hidesOnDeactivate False, labelColor / secondaryLabelColor) and `test_show_does_not_activate_app` (`:464`). Stale names in the plan table only.
- tasks.md 5D says the CLAUDE.md "task list" is updated. The dated status block was added, but the 任务看板 table has no row for this change. Whether "task list" meant the table is unclear.
- Lane table row 8 says the output file is `acceptance-*.md`; task 8.1 says `opsx:accept` (which writes `acceptance.md`). Naming only.

### What the user must still verify (plain words)

1. Set `dictation_mode = 'live'`, run `capswriter restart`, hold Caps Lock in a text field and speak. Text should appear in the floating panel within about 2 s and keep updating. The text field must keep focus and its caret. (A1)
2. Release Caps Lock. The pasted text must be the final result, and the panel must close. (A2)
3. Set `dictation_mode` back to `'hold'` (the default) and restart. Dictation must look and behave as before, with no panel. (A3)
4. In live mode, dictate for about one minute. The panel must keep updating until release. (A4)
5. Decide whether the measured preview quality on your own voice (1.4 % wrong committed text, about 3 s commit lag) feels acceptable. (accepted finding F4)

Verdict for question 4: NEEDS-HUMAN — 8.1 is this review; A1-A4 and the F4 quality judgement are open and only the user in the running app can close them; every ticked task's note held up under read-only checks, with three doc nits (stale B12 test names, no 任务看板 row, acceptance file name).

---

## 5. Scope, tolerances and design drift

Judged at HEAD = 44146fa (`git rev-parse HEAD`). `git status --short` and `git diff --stat` printed nothing at the time of review; every source line below is from `git show HEAD:<path>`. No build or test was run.

### What I ran and what it printed

| Command | Output (condensed) |
|---|---|
| `git log --oneline 33eba19..HEAD` | 30 commits, 8d30c2d .. 44146fa |
| `git diff --stat 33eba19..HEAD` | 33 files, +3592 / -6 |
| `git log --format='--- %h %s' --name-only 33eba19..HEAD -- .gitignore config_server.py tools/test_mlx_model_resolution.py openspec/config.yaml openspec/specs/.gitkeep openspec/changes/archive/.gitkeep` | `.gitignore`, `config_server.py`, `tools/test_mlx_model_resolution.py` only in 5e4ff2b; `openspec/config.yaml` and the two `.gitkeep` only in 8d30c2d |
| `git show --stat 5e4ff2b` | exactly those 3 files, +72 / -2 |
| `git check-ignore --no-index -v tools/test_live_*.py` | all four match `.gitignore:233 tools/test_*.py`; `git ls-files` shows all four tracked |
| `git log -p --diff-filter=M 33eba19..HEAD -- tools/test_live_*.py \| grep '^[-+].*[0-9]'` | numeric changes listed in 5.2 below |
| same for the 11 production files | only D5 window constants removed (8c1453c); `AGREE`, `HOLDBACK`, `INTERVAL`, `AUTO_HIDE` never changed |
| `git show eee60f4:tools/test_live_e2e.py` (first commit) vs HEAD | before/after values in 5.2 |
| `git grep -c -w <name> HEAD -- ':!openspec' ':!*.md' ':!*.toml'` for 25 added names | counts in 5.4 |
| `git grep -n -E '^_PANEL_W\|^_MARGIN\|^_CORNER_RADIUS\|^def panel_origin_y\|NSVisualEffectMaterial' HEAD -- core/client/output/edit_panel.py` | all four names exist (lines 53-55, 89); material is `NSVisualEffectMaterialPopover` (line 238), same as live_panel.py:79 |
| `git show HEAD:core/server/worker/work_handler.py \| sed -n '55,62p'` | `is_empty` is a `@property` (so `self.buffer.is_empty` at line 178 is a bool, not a bound method) |
| `git grep -n '模型输出' HEAD -- 'core/**'` | qwen_mlx_runner_pipeline.py:93, inside `process()` after `if runner_result is None: return None` (final path only; live passes call the recognizer directly, so they never hit this line) |

### 5.1 Files, config, dependencies, ignore rules outside the tasks

Files named in tasks.md (Files owned + 5C + 5D): `core/protocol.py`, `core/server/schema.py`, `openspec/`, the four `tools/test_live_*.py`, `live_preview.py`, `qwen_mlx_runner_pipeline.py`, `work_handler.py`, `ws_recv.py`, `ws_send.py`, `config_client.py`, `recorder.py`, `result_processor.py`, `live_panel.py`, `mutations.toml`, `readme.md`, `CLAUDE.md`.

Files in the diff that are not named:

| File | Commit | Judgement |
|---|---|---|
| `.gitignore` (+1: `!tools/test_mlx_model_resolution.py`) | 5e4ff2b | Separate change per the environment facts. Not part of this change. Noted, not counted. |
| `config_server.py` (+7/-2) | 5e4ff2b | Same. |
| `tools/test_mlx_model_resolution.py` (new, 64 lines) | 5e4ff2b | Same. |
| `openspec/config.yaml` (new, 34 lines), `openspec/specs/.gitkeep`, `openspec/changes/archive/.gitkeep` | 8d30c2d | OpenSpec init files. Covered by group 1's ownership of `openspec/`. Declared by ownership, not by name. NOTE. |

- Dependencies: none added. `live_preview.py` imports `re`, `difflib`, `typing`, `numpy`; `live_panel.py` imports AppKit/Foundation/PyObjCTools, already used by `edit_panel.py`.
- Config keys: only `dictation_mode` (config_client.py:58). Matches design "No new config beyond dictation_mode".
- Ignore rules: this change touched none. NOTE: the four new tests match the ignore pattern `tools/test_*.py` (`.gitignore:233`) and have no `!` exception, unlike every other committed test and unlike 5e4ff2b's own test. They are tracked only because they were force-added. Concrete cost: the next test file added beside them (for example a regression test after A1-A4) is hidden from `git status` and `git add tools/` until someone force-adds it, and `git clean -X` deletes an uncommitted copy. Not a FAIL: no ignore rule was changed; one was not added.
- readme.md and CLAUDE.md: declared in 5D. The CLAUDE.md diff touches the "流式识别策略" row and adds a status block; readme adds one section. Both inside 5D's stated scope.

### 5.2 Test tolerances, thresholds, timeouts, expected values

Production constants: `INTERVAL = 1.0`, `AGREE = 3`, `HOLDBACK = 4` (live_preview.py:28-30), `AUTO_HIDE = 5.0` (live_panel.py:34). Never changed after their first commit. The removed `WINDOW = 15.0`, `FORCE = 25.0`, `PAUSE_RATIO = 0.2`, `FRAME = 320` (8c1453c) are the D5 window removal, declared in design D5 and tasks 3B.1.

Test changes, with before and after:

| Test | Before | After (HEAD) | Direction | Declared where |
|---|---|---|---|---|
| `test_live_e2e::test_long_live_run_keeps_up`, preview count | `>= int(duration_s / 3)` (eee60f4) | 64663ac: `>= 3`; d537558: `>= int(duration_s / 2)` (HEAD line 338) | 64663ac loosened (10 -> 3 for a 30 s clip), d537558 tightened past the original (15). Net tighter. | The intermediate `3` is not declared anywhere; it was superseded 1 commit later. HEAD value declared by review-5A #8 (applied per tasks 6.1). NOTE. |
| same test, "last preview near the end" | d537558: `previews[-1].duration >= duration_s - 3.0` | 87c8def: `sent_at - receive_times[preview_idx[-1]] <= 3.0` (HEAD line 339) | Changed metric, not loosened. `Result.duration` is no longer filled for previews (review-5A #4), so the old check could not hold. | review-5A #4 and #8. Noted. |
| `test_live_e2e::test_live_run_streams_previews`, log leak scan | eee60f4: every preview fragment (>= 4 chars) must appear in no server log line and not in stdout | 64663ac (HEAD lines 273-293): a line that contains a fragment must also contain the full final text (formatted, or raw from the `模型输出：` line) | Loosened. The old rule failed on the final lines (`麦克风识别结果: <final>`, `模型输出：<raw>`), which by design contain every committed prefix. | Commit message "fix e2e final-text log false positive" and the in-test comment. Not in tasks.md by name. The spec's own wording allows it ("no log record ... contains partial text before the final result"). NOTE. Residual weakness: the rule is content-based, not order-based. A leaked line whose text equals the whole final text would pass. That needs the last committed text to equal the formatted final, which `HOLDBACK = 4` and formatting make unlikely. |
| `test_live_e2e::test_live_final_matches_hold` | returns at the first final | 87c8def: `linger=1.5` s after the final, then asserts no preview arrived (HEAD lines 305, 313-315) | Added check, tighter. | review-5A #8. |
| `test_live_pipeline` | `assertAlmostEqual(result.duration, 1.0, delta=0.01)` | removed (87c8def) | Dropped expected value. | review-5A #4 (preview `Result` no longer fills `duration`). Declared. |
| `test_live_client::test_panel_auto_hides` | `AUTO_HIDE` patched to 0.05; pumps 0.15 then 0.3 | be31893: patched to 0.5; pumps 0.15 then 0.6 | Test-internal timer. The original was self-inconsistent (first pump 0.15 s already past a 0.05 s timer while asserting "still visible"). | Lane 3C's own pre-merge commit "fix two panel test bugs". Not in tasks.md. Not a production tolerance. NOTE. |
| e2e socket timeouts `len(audio)/SR + 20` and `+ 30` | unchanged | unchanged | - | - |

No undeclared loosening below the spec was found. The two changes not named in tasks.md (the leak-scan rework, the auto-hide timer) each have a stated reason in the commit and match the spec text.

### 5.3 (a) Design decisions, one by one

| Decision | Code at HEAD | Judgement |
|---|---|---|
| D1 `AudioMessage.live`, `.get('live', False)`, three recorder sites, `Work.live`, ws_recv copy | protocol.py:41, 60; recorder.py:178, 204, 232; schema.py:47; ws_recv.py:208 | Matches. |
| D2 tick in the worker loop when `process()` returns None for a live packet and the buffer is empty; `hasattr` hook; result to `queue_out`; `WorkPipeline` untouched | work_handler.py:178-183, 188; `work_pipeline.py` not in the diff | Matches. `is_empty` is a property (line 58-60), so the condition is a real check. |
| D3 audio-time clock: first pass at 1.0 s, next due 1.0 s of audio after the last pass started | live_preview.py:113, 122, 133 | Matches. |
| D4 throwaway id `f"{task_id}#live{n}"`, `is_final=True`, `next_due` moved before the model call, exception logged as type + task id, no `cancel_task`, no formatter | pipeline.py:130-138, live_preview.py:133-136, pipeline.py:141-145 | Matches. One declared deviation: design writes `sample_rate=16000`; code uses `sample_rate=work.samplerate` (pipeline.py:133). Same value today (`Work.samplerate` defaults to 16000). Declared: review-5A #15, applied in 5cd608d. Noted. |
| D5 pure module: `units`, `ukey`, `is_numeral`; `Agreement` with `AGREE=3`, `HOLDBACK=4`, `update(text)->str`, `committed`; `LiveTask` with `feed`, `due`, `step(transcribe)->(committed, tentative)`; no window; imports `re`, `difflib`, numpy only | live_preview.py:21-25, 37-47, 50-100, 103-138 | Matches, with one declared deviation: there is no `units` function; `_UNIT.findall(...)` is inlined at line 68. Declared: review-5A #9 ("Helpers with one caller: `units` ... Inline each"), applied per tasks 5A/6.1. Noted. |
| D6 `Result` and `RecognitionMessage` get `preview`, `text_tentative`; `from_dict` uses `.get`; fresh `Result` in `live_tick`; ws_send copies both fields and skips the mic info line for previews; debug length line stays; no root handler added | schema.py:95-96; protocol.py:101-102, 128-129; pipeline.py:151-158; ws_send.py:43-44, 59-63 | Matches. The fresh `Result` fills only `task_id`, `socket_id`, `source`, `text`, `text_tentative`, `preview`; D6 does not prescribe more. |
| D7 `self.live` dict; create on first live non-final and `feed`; pop on any final before the final call; `live_tick` runs the first due task in insertion order; `cleanup_tasks` pops | pipeline.py:36, 60-71, 120-123, 163-166 | Matches. |
| D8 borderless non-activating `NSPanel`, ignores mouse, floating, all spaces + full-screen auxiliary, `setHidesOnDeactivate_(False)`, `orderFrontRegardless` only, no `canBecomeKeyWindow` override, one wrapping `NSTextField` with `labelColor`/`secondaryLabelColor`, reuse of `_PANEL_W`, `_MARGIN`, `_CORNER_RADIUS`, `panel_origin_y`, `show`/`hide` via `AppHelper.callAfter`, lazy creation, `callLater(5.0)` with a generation counter, no AppKit import guard | live_panel.py:16-32, 44-51, 56-70, 87-97, 102-110, 123, 130-133, 141-143 | Matches. The first version had an `_APPKIT_OK` guard, which D8 rules out; f448d6e removed it (review-5A #18). This is a return to the design, not a departure. |
| D9 preview branch right after the `None` check, before the non-final DEBUG line; `show(text, text_tentative)`; `return`; `hide()` in the final branch only when `dictation_mode == 'live'` | result_processor.py:220-227, 235-239; the DEBUG line is at 254-258 | Matches. The `live_panel` import is function-local in both branches. D9 does not say where the import goes; review-5A #2 asked for it to run only in live mode, and simplify-5B's hoist proposal was rejected for that reason (tasks 5B note). Noted. |

No undeclared departure. Declared ones: D4 `work.samplerate` (5A #15), D5 `units` inlined (5A #9). Informational: design "Expected size" said about 100 + 110 + 60 lines; actual is 138 (live_preview.py, of which 17 are the module docstring), 143 (live_panel.py) and about 117 added lines elsewhere. That paragraph is an estimate, not a numbered decision.

### 5.3 (b) Abstractions the diff adds, with caller counts

Counts are `git grep -w` hits at HEAD outside `openspec/`, `*.md`, `*.toml`; "prod" excludes `tools/`. Definition lines are included in the raw count; the "callers" column subtracts them.

| Abstraction | Prod callers | Test refs | Judgement |
|---|---|---|---|
| `AudioMessage.live` (protocol field) | recorder x3, `from_dict`, ws_recv | many | OK |
| `Work.live` | ws_recv (set), pipeline.process, work_handler.loop | many | OK |
| `Result.preview`, `Result.text_tentative` | pipeline.live_tick (set), ws_send x2 / x1 | 5 / 2 | OK |
| `RecognitionMessage.preview`, `.text_tentative` | ws_send (set), `from_dict`, result_processor x1 each | 17 / 6 | OK |
| `Config.dictation_mode` (config key) | recorder x3, result_processor x1 | 10 | OK. Design allows exactly this key. |
| module `live_preview` | pipeline (1 import) | 2 test modules | Per D5 ("A pure module for the commit rule"). |
| `SR`, `INTERVAL`, `AGREE`, `HOLDBACK` (constants) | 2, 2, 3, 1 uses in live_preview.py | tests use `SR` | Per D5 ("Constants AGREE = 3, HOLDBACK = 4") and "Patterns" ("module constants"). `HOLDBACK` has one use; a named constant is what the design asks for. No cost to name; dropped. |
| `_UNIT`, `_NUMERAL` | 1 use each | 0 | Compiled once at import; inlining would recompile the regex per pass. No cost to name; dropped. |
| `ukey` | 2 (update lines 69, 98) | 0 | OK |
| `is_numeral` | 1 line (line 89, two calls) | 0 | Per D5 (named there). Inlining would repeat the `_NUMERAL` membership test twice on one line. No cost to name; dropped. |
| class `Agreement`, `Agreement.update`, `Agreement.committed` | 1 (LiveTask.__init__ / step) | 7 | Per D5 and "Functional core, thin shell". Second caller would appear only if another engine got a live path; design D1 rules that out for now. No cost to name; dropped. |
| class `LiveTask`; `feed`, `due`, `step`, `passes`, `work` | 1 each (pipeline.py:69, 71, 122, 141, 131, 124) | 4-5 | Per D5 and D7. Same reasoning as above. |
| `QwenMLXRunnerPipeline.live` (dict) | process, live_tick, cleanup_tasks | 3 | OK |
| `QwenMLXRunnerPipeline.live_tick` | 1 (work_handler.py:183, behind `hasattr`) | 15 | Per D2 ("Optional hook method ... instead of a new scheduler class"). NOTE with cost: the binding is a string in `hasattr`; a rename on either side fails silently and hold mode would not notice (only live mode stops updating). D2 accepts this to leave `WorkPipeline` untouched. Same trade-off as the existing `cleanup_tasks` hook (work_handler.py:144). |
| closure `transcribe` inside `live_tick` | 1 (`task.step(transcribe)`) | 0 | Per D5 ("The pipeline passes a closure over feed_audio_patch"). No cost to name; dropped. |
| module `live_panel`; `show`, `hide` | 1 each (result_processor.py:226, 239) | many | Per D8, D9. Second caller: none expected; a menubar toggle (non-goal) would still go through `dictation_mode`. No cost to name; dropped. |
| `_show_on_main`, `_hide_on_main`, `_auto_hide` | 1, 2, 1 | 0 | Per D8 ("dispatch to the main thread with AppHelper.callAfter"). Required by the thread hop. Dropped. |
| `AUTO_HIDE`, `_FONT_SIZE`, `_MIN_LABEL_H` | 1, 1, 3 uses | `AUTO_HIDE` patched in 10 test lines | `AUTO_HIDE` exists as a name so tests can patch it (D8 says `callLater(5.0, ...)`). NOTE with cost: the tests couple to the module attribute name; renaming it breaks 10 test lines with no production change. Acceptable; the spec value (5 s) is otherwise untestable in under a second. |
| module globals `_panel`, `_label`, `_effect`, `_generation` | internal | `_panel`, `_label` read by tests | Per D8 ("The panel is created on first show"). `_effect` is the blur view D8 asks for. Dropped. |
| test helpers: `ScriptedRecognizer` (12), `live_call_count` (14), `make_work` (20 / 2), `RunnerResult` (5), `ScriptedQueue` (4), `ScriptedTranscribe` (2), `_pump_main_runloop` (14), `_CaptureServer` (2), `_year_folder_snapshot` (6), `_new_result_processor` (4), `_FakeCorrector` (3), `_FakeHotword` (2), `_FakeState` (2), `ServerHarness` (2), `_synthesize` (2), `_record` | test-only | as listed | Each has at least two uses in its file except `ScriptedTranscribe`, `_CaptureServer`, `ServerHarness`, `_synthesize` (definition + one use). These are the fakes tasks.md "Test notes" allows. `_FakeCorrector`/`_FakeHotword` duplicate `test_editor_result_flow.py`; simplify-5B considered and rejected importing them (cross-file coupling). Noted. |

No abstraction is forbidden by a design decision. No FAIL under (b).

### Summary

- Off-task files in the range: three from 5e4ff2b (separate change, excluded) and three OpenSpec init files under the owned `openspec/` prefix (noted).
- No dependency, no new config key beyond `dictation_mode`, no ignore rule changed. One missing `!` line for the four new tests (noted with cost).
- No production tolerance changed. Test tolerance changes: two declared by review-5A (#4, #8) and applied; two declared only in their commit messages (leak-scan rework in 64663ac, auto-hide timer in be31893), both consistent with the spec text; the one intermediate loosening (`>= 3`) was superseded a commit later by a bound tighter than the original.
- Design D1-D9 all match at HEAD. Two declared deviations (D4 `work.samplerate`, D5 `units` inlined), both from review-5A rows tasks.md says were applied.
- Every one-caller abstraction is one the design prescribes (D2 hook, D5 pure module, D8 panel API). Two NOTEs carry a named cost (`live_tick` string binding, `AUTO_HIDE` test patching); the rest are dropped.

Verdict for question 5: PASS — no undeclared file, dependency, tolerance or design change; deviations from design.md are the review-5A rows tasks.md declares as applied, and every one-caller abstraction is one the design prescribes.

---

## Summary table

| Question | Verdict | One line |
|---|---|---|
| 1. Entry points | NEEDS-HUMAN | every entry point is tested at its real production entry except the live pop in `cleanup_tasks` (E11), whose only test bypasses `WorkHandler.cleanup()`; tasks.md declares the gap but misdescribes its coverage, and no Acceptance item covers a mid-recording disconnect. |
| 2. Fails before | FAIL | every requirement is pinned and shown failing on 8d30c2d or by a call-site mutation (31 hand rows, 40/40 toml rows), except the delta-spec scenario "Another engine sends no partials", which has no test: dropping the `hasattr(..., 'live_tick')` guard survives the whole suite. |
| 3. Real versus simulated | NEEDS-HUMAN | no undeclared bypass; the cross-thread AppKit dispatch (row 17) and the real worker process boundary (row 6) are covered only by the user's Acceptance A1-A4. |
| 4. Open items | NEEDS-HUMAN | 8.1 is this review; A1-A4 and the F4 quality judgement are open and only the user in the running app can close them; every ticked task's note held up under read-only checks, with three doc nits (stale B12 test names, no 任务看板 row, acceptance file name). |
| 5. Scope, tolerances and design drift | PASS | no undeclared file, dependency, tolerance or design change; deviations from design.md are the review-5A rows tasks.md declares as applied, and every one-caller abstraction is one the design prescribes. |

Verdict: FAIL
