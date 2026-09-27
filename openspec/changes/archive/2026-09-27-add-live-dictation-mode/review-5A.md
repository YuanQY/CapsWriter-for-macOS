# Code review 5A: add-live-dictation-mode

- Reviewer: Opus (one tier above the Sonnet authors). Read-only on the review tree.
- Tree: `/Users/qingyun.yuan/code/open-source/CapsWriter-wt/review`, detached at 28c89ea.
- Diff: `git diff 33eba19 28c89ea -- . ':!openspec'` (17 files).
- Judged against: spec.md, design.md D1-D9, the KISS / Ponytail checklist (10 checks), correctness, privacy, hold mode, AGENTS.md.
- Result: **0 HIGH, 9 MEDIUM, 11 LOW.** No privacy leak and no crash found.

## Commands run (one line of output each)

All test runs use `/Users/qingyun.yuan/code/open-source/CapsWriter-for-macOS/.venv/bin/python`, from the review tree unless noted. `test_live_e2e.py` was not run.

| Command | Output |
|---|---|
| `git diff --stat 33eba19 28c89ea -- . ':!openspec'` | 17 files changed, 1615 insertions(+), 5 deletions(-) |
| `tools/test_live_preview.py -v` | Ran 6 tests in 0.001s OK |
| `tools/test_live_pipeline.py -v` | Ran 8 tests in 0.005s OK |
| `tools/test_live_client.py -v` (shows a real panel for under 1 s) | Ran 8 tests in 1.713s OK |
| `tools/test_worker_scheduling.py -v` | Ran 10 tests in 0.002s OK |
| `tools/test_mic_shortcut_lifecycle.py -v` | Ran 9 tests in 0.023s OK |
| `tools/test_stream_stop_leak.py -v` | Ran 14 tests in 0.049s OK |
| `tools/test_editor_annotation.py` | 8 PASS, "annotation_store 全部断言通过" |
| `tools/test_editor_result_flow.py` | 16 PASS, 0 FAIL |
| `tools/test_editor_ui_contract.py` | PASS: editor UI contract |
| `ruff check --no-cache --isolated --select F,B` on the 6 new files | 4 hits: F841 `duration_s` (test_live_e2e.py:311); 3x B905 zip strict (nits, ignored) |
| `ruff check --no-cache --isolated --select F` on the 8 changed files | 8 hits, all on pre-existing lines; none on changed lines |
| `scratchpad/5a/nsrange_probe.py` (AppKit objects only) | `'😀好世界' py_len 4 ns_len 5`: idx 1 grey, idx 4 no colour and no font |
| `scratchpad/5a/wrap_probe.py` (same label setup as live_panel) | CJK text: 0/110 lengths clipped; mixed Latin/CJK: 11/370 get less height than the label needs (e.g. needs 38 pt, gets 20 pt) |
| `scratchpad/5a/probe_mutations.py` on a `git archive 28c89ea` copy in the scratchpad | CAUGHT: M1 (only by test_worker_scheduling), M2, M3, M4, M6, M7, M10, M11, M13. MISSED: M5 / M5b (`next_due`), M12 (empty-preview guard), M14 (auto-hide generation) |
| same copy, test_live_client.py with lines 35-44 deleted | Ran 8 tests OK |
| hold-path cost probe (scratch copy) | first `live_panel` import 11.2 ms (edit_panel not yet loaded); `hide()` 0.007 ms per call |
| `grep` of `review/logs/*.log` for the test preview markers after the runs | 0 hits for every preview-only marker; `你好世界` / `最终文本` only on final-result lines |

## Findings

| # | Severity | File:line | Rule / check | Finding | Minimal fix | Lines removable |
|---|---|---|---|---|---|---|
| 1 | MEDIUM | core/client/output/live_panel.py:130-132 | Correctness (panel) | `_resize_panel` sizes the label from `attr.boundingRectWithSize_options_` at the full label width. The NSTextField cell lays text out narrower. So near a wrap point the label wraps one more line than measured, and the last line (the newest tentative words) is clipped. Probe with the same label setup: CJK only 0/110 lengths; mixed Latin/CJK 11/370 lengths (e.g. needs 38 pt, gets 20 pt). EVIDENCED | After `setAttributedStringValue_`, measure with the cell: `text_h = max(_MIN_LABEL_H, _label.cell().cellSizeForBounds_(NSRect(NSPoint(0, 0), NSSize(width, 1.0e7))).height)`. Drop the `attr` argument and the `NSStringDrawingUsesLineFragmentOrigin` import | 1 |
| 2 | MEDIUM | core/client/output/result_processor.py:235-237 | Check 8 (hold path) | Every hold-mode final now runs a function-local import of `live_panel` and `live_panel.hide()`. `hide()` posts `AppHelper.callAfter` to the main thread for a no-op. Cost is small (0.007 ms per call; import 11 ms only if edit_panel was not loaded, and the app loads it at startup), but hold mode did not run this code before. EVIDENCED | Wrap the import and `hide()` in `if Config.dictation_mode == 'live':` (the same setting the recorder reads) | 0 |
| 3 | MEDIUM | core/server/worker/work_handler.py:178; core/server/worker/qwen_mlx_runner_pipeline.py:60-63 | Check 8 (hold path) | In hold mode with qwen_asr_mlx, every non-final packet that leaves the buffer empty (about 50 per second) calls `live_tick()`, which loops over an empty dict. Every final runs `self.live.pop()`. EVIDENCED (quoted lines) | work_handler: `if result is None and work.live and self.buffer.is_empty and hasattr(self.pipeline, 'live_tick'):`. Pipeline: put both branches under `if work.live:` (the final packet carries the same flag, recorder.py:231) | 0 |
| 4 | MEDIUM | qwen_mlx_runner_pipeline.py:152, 157-160, 163; core/server/worker/live_preview.py:123-127; tools/test_live_pipeline.py:152, 154, 163-166 | Check 1 | The preview `Result` fills `duration`, `time_start`, `time_submit`, `time_complete` and the default `is_final=False`. No consumer reads them. The client preview branch reads only `text` and `text_tentative` (result_processor.py:224-227). ws_send reads `duration` only when `source == 'file'`. `LiveTask.duration` exists only to fill this field. The test asserts the unused fields. EVIDENCED | Drop the 5 field lines, `now = time.time()`, the `duration` property, and the 6 test lines. If the fix for #8 needs a "last preview near the end" check, use client receive times, not this field | 17 |
| 5 | MEDIUM | tools/test_live_pipeline.py:63-72 (asserts at 117, 127, 137, 141, 181, 195, 213) | Check 10 / TDD gate | `ScriptedRecognizer` pops `_live_responses`. An unscripted pass raises IndexError. The production `except Exception` (pipeline.py:144) swallows it and returns None. So every "no pass ran" check, `assertIsNone(pipeline.live_tick())`, passes even when a pass runs. Mutation: moving `self.next_due = …` (live_preview.py:146) after the model call leaves all tests green (MISSED); deleting the line is also MISSED. This is the "failed pass uses up its slot" and "no pass without 1 s of new audio" rule (spec, D3, D4; tasks.md 5C lists this call site). EVIDENCED | Assert on the call count, which is recorded before the pop: `self.assertEqual(sum('#live' in c.task_id for c in recognizer.calls), 1)` after lines 137, 141 and 195. The same count can replace the `pipeline.live` internals at 118, 134, 180, 194, 211 | 0 |
| 6 | MEDIUM | qwen_mlx_runner_pipeline.py:149-150 | TDD gate | Spec: the panel opens with the first partial "whose text is not empty". Deleting `if not committed and not tentative: return None` leaves all fast tests green (MISSED). EVIDENCED | Add a pipeline case: `queue_live_response('')`, feed 1 s, assert `live_tick()` is None and one `#live` call happened | 0 |
| 7 | MEDIUM | core/client/output/live_panel.py:159-161; tools/test_live_client.py:419-430 | TDD gate | Replacing `if gen == _generation:` with `if True:` leaves test_live_client green (MISSED). Without the check, the panel hides 5 s after the first show and then blinks off on every later pass. Spec: close "5 s after the last partial". EVIDENCED | In `test_panel_auto_hides`: show, pump 0.3 s, show again, pump 0.3 s, assert visible; pump 0.3 s more, assert hidden | 0 |
| 8 | MEDIUM | tools/test_live_e2e.py:168-174, 311, 315 | TDD gate (B7, B9) | `receiver()` returns at the first final. So the B7 production-entry test cannot see a preview that arrives after the final ("no later partial message … reaches the client"). `test_long_live_run_keeps_up` asserts only `len(previews) >= 3`. Three early previews pass it, so "previews keep coming until release" is not checked. `duration_s` is unused (ruff F841). EVIDENCED by reading (e2e not run) | After the final, keep reading for about 1.5 s under `wait_for` and assert nothing arrives. Stamp each message with its receive time and assert the last preview came within about 3 s of the last packet sent. Use or delete `duration_s` | 1 |
| 9 | MEDIUM | live_preview.py:37-39, 70-81; qwen_mlx_runner_pipeline.py:121, 124-126; live_panel.py:64-67, 111-112, 127-128 | Check 2 | Helpers with one caller: `units` (one production caller), `_tail_start` (only `update`), `_run_live_pass` (only `live_tick`), `_ensure_panel`, `_attributed_text`, `_resize_panel` (only `_show_on_main`). No behaviour impact. EVIDENCED (grep of callers) | Inline each at its call site. `_tail_start` becomes `start = n` plus `if cur_keys[:n] != self.keys:` and `if blocks:`; the panel helpers become blocks in `_show_on_main`. Per helper: units 4, `_tail_start` 5, `_run_live_pass` 3, `_ensure_panel` 4, `_attributed_text` 3, `_resize_panel` 3 | ~22 |
| 10 | LOW | core/client/output/live_panel.py:116, 120, 124 | NSRange vs str length | Ranges use Python `len()`. NSString counts UTF-16 units. With a non-BMP character in the committed text (`'😀好' + '世界'`), `好` is grey, and the last character gets no colour and no font. No crash: the Python length is never larger than the UTF-16 length, so ranges stay in bounds. Rare in ASR text. EVIDENCED (probe) | Use `len(s.encode('utf-16-le')) // 2` for the two lengths, or build two strings with `initWithString_attributes_` and join them with `appendAttributedString_` (no ranges) | 0 |
| 11 | LOW | tools/test_live_pipeline.py:236-264 | TDD gate (B8) | The B8 test never puts due live audio and the final in the buffer at the same time. Dropping `self.buffer.is_empty and` (work_handler.py:178) is caught only by the old test_worker_scheduling, because its `Mock()` pipeline auto-creates a `live_tick` attribute. That catch is accidental. EVIDENCED | Script `[live 1 s, final, empty, exit]` so both arrive in one drain; assert zero `#live` calls and exactly one result | 0 |
| 12 | LOW | tools/test_live_client.py:35-44 | Checks 4, 10 | The `pyclip` / `sounddevice` stubs are installed whenever the name is not yet in `sys.modules`, which is always true at that point. Both packages are installed in the venv. So the comment "未安装可选依赖时" is false, and B1-B3 ("real recorder loop") run with an empty `sounddevice` module. These fakes are not in tasks.md's allowed list; the block is copied from test_editor_result_flow. With the 10 lines deleted, all 8 tests pass. EVIDENCED | Delete lines 35-44 | 10 |
| 13 | LOW | tools/test_live_preview.py:53, 75-76, 84, 93 | Check 10 | Line 53 `rstrip()` hides the trailing space the spec names (`"我刚用Cloud "`; the real value has it). Lines 75-76 write `committed` and `keys` directly; three public `update('你好世界今天天气')` calls reach the same state. Lines 84 and 93 repeat what the `assertEqual` above them already proves. EVIDENCED | Assert `'我刚用Cloud '` exactly; reach the state through `update()`; drop lines 84 and 93 | 2 |
| 14 | LOW | core/client/output/live_panel.py:33, 82 | Checks 2, 5 (copied seam) | `NSWindowLevelFloating = NSFloatingWindowLevel` is copied from edit_panel, where a comment explains it. Here the classic name can be used directly. `setReleasedWhenClosed_(False)`: the panel is never closed, only `orderOut_`. EVIDENCED | Use `NSFloatingWindowLevel` directly; drop line 82 | 2 |
| 15 | LOW | live_preview.py:45, 51, 148; qwen_mlx_runner_pipeline.py:134, 140 | Checks 4, 5 | `[\w㐀-鿿]`: `\w` already matches CJK (checked: True for 㐀, 鿿, 𠀀). `bool(s) and`: a unit is never empty. `if len(self._chunks) > 1 else self._chunks[0]`: `np.concatenate` handles one chunk. `.strip()`: the runner already strips, and `units()` strips again. `sample_rate=16000`, while the same file uses `work.samplerate` (line 75). EVIDENCED | Shorten each expression; use `work.samplerate` | 0 |
| 16 | LOW | core/client/audio/recorder.py:180 | Check 7 | Whitespace-only change: a line of 20 spaces became empty. Outside the task. EVIDENCED (`git diff … | sed -n l`) | Restore the original line | 0 |
| 17 | LOW | readme.md:190-191; CLAUDE.md:7; tools/test_live_client.py:8, 59; recorder.py:177, 203, 231; ws_recv.py:208, 237 | AGENTS.md rules | readme says "黑色文字", but committed text uses `labelColor`, which is white in dark mode. readme states the focus behaviour as fact while Acceptance A1 is still open (AGENTS: readme holds only settled facts, and must separate "已验证可用" from "仅完成代码接入"). CLAUDE.md status "实现按并行 lane 推进中，尚未合并" is stale (lanes merged at b286b4f). test_live_client cites `lane-rules.md` and "lane-contract", which are not in the repo. The five one-line `live=` additions have no Chinese comment (AGENTS: all new code gets Chinese comments). EVIDENCED | "正文色 / 灰色"; add "待真机验收" until A1-A4 pass; update the status line (5D); drop the dangling references; add one comment line at the first recorder site | 0 |
| 18 | LOW | core/client/output/live_panel.py:19-36, 50-51, 56-58, 62 | Check 4 | `_APPKIT_OK` guards a platform without PyObjC. On macOS, PyObjC always comes in as a transitive dependency (it is not in requirements-client.txt). D8 keeps the guard for `start_client.py`. If non-macOS is not a supported target of this fork, this is dead code. Related: under `start_client.py` on macOS, no NSApp run loop runs on the main thread, so `callAfter` never fires and live mode shows no panel there. INFERRED | Decide whether non-macOS is supported; if not, drop the guard | ~8 (conditional, not counted in the total) |
| 19 | LOW | core/server/worker/live_preview.py:137-151 (design D5) | Correctness (long dictation) | Each pass re-reads all audio. evidence.md measures 1.4 s per pass at 65-74 s. If the cost stays about linear, a pass takes longer than AUTO_HIDE (5 s) at about 4 minutes. Then the panel blinks off between updates, and the final waits up to one such pass. This is within the spec (the scenario is one minute), but readme does not say it. INFERRED | Add one sentence to readme next to the 45 s remark; no code change | 0 |
| 20 | LOW (author: Opus) | core/protocol.py:68-79 | Check 5 | The `RecognitionMessage` docstring "Attributes" lists every other field but not `preview` and `text_tentative` (they have an inline comment instead). Field names, defaults and the `.get` reads in `from_dict` are correct. EVIDENCED | Add the two fields to the docstring list, or leave it (nit) | 0 |

## Total removable lines

- 55 lines: #1 (1) + #4 (17) + #8 (1) + #9 (~22) + #12 (10) + #13 (2) + #14 (2).
- 63 lines if the `_APPKIT_OK` guard in #18 also goes.
- Fixes #2, #3, #5, #6, #7, #8, #10 and #11 each add a few lines.

## What held

- **Tests.** All fast tests pass. The pre-existing counts match the tasks.md 1.1 baseline: annotation 8, editor_result_flow 16, ui_contract PASS, mic_shortcut 9, stream_stop_leak 14, worker_scheduling 10. New tests: live_preview 6, live_pipeline 8, live_client 8.
- **Commit rule.** The three spec scenarios reproduce exactly. Tail word: committed `'我刚用Cloud '`. Numeral run: `'价格是'`, then `'价格是一万五千块'`. Insertion: `'你好世界今天'`, with tentative `'天气很好'`. The content-alignment, numeral-hold and trailing-punctuation mutations are CAUGHT.
- **Worker ordering (check 3).**
  - The final pops the live task before the final call (pipeline.py:60-63).
  - Previews and finals share one `queue_out`, one `ws_send` coroutine and the per-socket FIFO in `WorkBuffer`. So no preview can reach the client after its final.
  - A tick runs only when the buffer is empty (work_handler.py:178). So no pass starts while a final is buffered.
  - Worst case, the final waits one pass. This includes the ~0.1 ms window between the drain's `Empty` and the tick check, which gives the same bound.
  - Mutations M2 (pop on final), M3 (pop in cleanup) and M6 (ignore `due()`) are CAUGHT.
- **Throwaway pass ids.** The runner's `_finalize_task` pops the task state before it transcribes (mlx-qwen3-asr f745f5e, `capswriter_runner.py:202`). A failed pass leaves nothing behind in the runner. Runner `verbose=False`, so the session prints nothing.
- **Failure path.** Exceptions in `step()` are caught. The log line carries only the task id prefix and the exception type (pipeline.py:146). `next_due` moves before the model call. The code is correct; the test gap is #5.
- **Privacy (check 4).**
  - Client: the preview branch returns before every log, console print, diary, clipboard, UDP and `last_case` step (result_processor.py:224-227). Mutation M13 (preview branch disabled) is CAUGHT by the client log test.
  - Server: ws_send logs only the length of a preview and skips the `麦克风识别结果` line (ws_send.py:59-64). The pipeline and the runner log no text.
  - Named loggers use `propagate=False`. Root handlers are set only under `__main__` (toast.py, toast_logger.py), so the `websockets` DEBUG frame logs are dropped.
  - After my test runs, `review/logs/*.log` has no preview-only marker ('罕见委托文本极光', '暂定尾巴星尘', 'MARKER_', '已提交', '暂定', '自动隐藏'). `你好世界` and `最终文本` appear only on final-result lines.
- **Threads.**
  - `show()` and `hide()` only post `AppHelper.callAfter`. All AppKit work and `_generation` stay on the main thread.
  - `callAfter` runs in FIFO order, so show/hide order is kept.
  - Exceptions in main-thread callbacks are caught by `AppHelper.runEventLoop` (start_client_macos.py:707), so they cannot crash the client.
  - Caveat (INFERRED): `hide()` is queued before output, but paste runs on the asyncio thread. So "the panel closes before output" holds in practice, not by a hard barrier. Focus is not affected either way.
- **Focus.** The panel is a borderless NSPanel with `NSWindowStyleMaskNonactivatingPanel`. It is shown only with `orderFrontRegardless`, never made key, never activates the app, has `canBecomeKeyWindow` False, ignores the mouse, and has `hidesOnDeactivate` False. Both the test and the code confirm this. Focus in a real target app is still Acceptance A1, **waiting for the user**.
- **NSRange.** Ranges are never out of bounds, so there is no crash (#10 is cosmetic).
- **Hold mode (check 8).** The recorder and ws_recv only read or pass the flag. The final call and its output path are unchanged. The only extra hold-mode work is #2 and #3.
- **Other engines.** Only the qwen path copies `live` into `Work`. `WorkPipeline` has no `live_tick`.
- **Checks 3, 6, 9.** No new knob besides `dictation_mode`. Ruff F is clean on changed lines, except `duration_s` in #8. No new dependency, tooling or config change.
- **AGENTS.md.** No file was deleted. The new modules have Chinese comments. readme and CLAUDE.md are updated. The CLAUDE.md MER figures (34.6 % vs 3.6 %) match evidence.md.
- **Opus-authored protocol and schema.** Field names, defaults and `.get` reads are correct. Old clients and old servers fall back to hold. Only nit #20.
- **Panel tests reading `live_panel._panel` and `_label`.** This is acceptable under check 10: window style and colours cannot be observed any other way.

## Not covered by this review

- `tools/test_live_e2e.py` was not run (it loads the model).
- The ws_send preview log guard is covered only by e2e; I checked it by reading.
- The real-app items A1-A4 are **waiting for the user**.
