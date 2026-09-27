# Acceptance review: add-live-dictation-mode

- Change: `add-live-dictation-mode`
- Git range: `44146fa..d3217e8` (delta round; the full change is `33eba19..d3217e8`; commit `5e4ff2b` is a separate change, excluded)
- Review tree: `/Users/qingyun.yuan/code/open-source/CapsWriter-wt/integ` at `d3217e8`
- Date: 2026-09-27
- Reviewer model: opus (one reviewer for questions 1-4)
- Prior rounds:
  - Round 1: fable, five reviewers, at `44146fa` (`git show 2a01c1b:openspec/changes/add-live-dictation-mode/acceptance.md`), verdict FAIL on question 2.
  - Round 2 (interrupted): fable, at `2a01c1b`; questions 1, 3, 4 answered; question 2 not answered after a rate limit.

## Commands this round ran

Question 1 (entry points):
- `cd /Users/qingyun.yuan/code/open-source/CapsWriter-wt/integ`
- `git log --oneline -12` # HEAD d3217e8
- `git status` # "nothing to commit, working tree clean"
- `git diff` # (empty: working tree == HEAD)
- `git diff --stat 44146fa..HEAD` # CLAUDE.md 4, acceptance.md +497, mutations.toml +11, tasks.md 19, tools/test_live_client.py +28, tools/test_live_pipeline.py +74/-2
- `git diff --quiet 44146fa..HEAD -- core config_client.py config_server.py start_client_macos.py start_client.py capswriter.py && echo "no production diff"` # -> "no production diff in core/config/start"
- `git diff --stat e673283..HEAD` # CLAUDE.md, tasks.md only (docs)
- `grep -n "handler.loop()\|handler.cleanup()\|sockets_id.remove\|handler.pipeline = \|_handle_message(message)\|RecognitionMessage.from_dict\|to_json()" tools/test_live_pipeline.py tools/test_live_client.py`
- `grep -n "sockets_id\|finally" core/server/connection/ws_recv.py`
- Call-site mutations by inline script at `work_handler.py:178`, `result_processor.py:224`, `qwen_mlx_runner_pipeline.py:166` and `work_handler.py:144` (toml rows 41-42, plus an entry-check row); each file restored and checked by sha256; narrowest test selection; `PYTHONDONTWRITEBYTECODE=1`; no `__pycache__` in the tree

Question 2 (fails before):
- `python3 ~/.claude/tools/test_mutate.py` # -> mutate canary: 8/8 passed
- `find . -name __pycache__ -not -path './models/*'` and the same for `*.pyc` (before the first run; printed nothing, so no stale bytecode could hide a mutation)
- Whole suite, run 1 of 2 (baseline): every `tools/test_*.py -v` (e2e with `HF_HUB_OFFLINE=1`); all 11 files exit 0
- `git diff 44146fa..HEAD -- tools/ | grep '^-'` # -> only `-from core.server.schema import Work` and `-        result = pipeline.live_tick()`
- `git diff 44146fa..HEAD -- .../mutations.toml | grep '^-'` # -> nothing (two rows appended)
- `git diff --quiet 44146fa..HEAD -- core config_client.py config_server.py start_client_macos.py start_client.py capswriter.py` # -> no production diff
- Six call-site mutations by inline script (R41, R42, HC, HC2, HD, HD2): exact text must occur once; file written, narrowest test run, file restored, sha256 compared
- `git status --porcelain` after every mutation batch and at the end (empty)
- Whole suite, run 2 of 2 (final verification)

Question 3 (real versus simulated):
- `git diff 44146fa..HEAD -- tools/ openspec/.../tasks.md openspec/.../mutations.toml CLAUDE.md` (read in full)
- `git diff --stat 2a01c1b..HEAD` # CLAUDE.md, mutations.toml (+6), tasks.md, tools/test_live_client.py (+28)
- `sed -n 270,345p tools/test_live_client.py` (helpers `_FakeCorrector`, `_FakeHotword`, `_FakeState`, `_new_result_processor`)
- `sed -n 494,526p tools/test_live_client.py` (`test_final_hides_panel`)
- `sed -n 1,130p tools/test_live_pipeline.py` (helpers, `NoLiveTickPipeline` at :80-91)
- `sed -n 200,250p tools/test_live_pipeline.py`
- `sed -n 348,362p tools/test_live_pipeline.py`
- `cat -n core/server/worker/work_handler.py | sed -n 60,200p`
- `cat -n core/server/worker/work_pipeline.py | sed -n 55,135p`
- `cat -n core/server/connection/ws_send.py | sed -n 20,80p`
- `sed -n 70,140p core/protocol.py`
- `cat -n core/client/output/result_processor.py | sed -n 205,290p`
- `grep -rn "WorkPipeline\|set_engine" tools/ | grep -v test_live_e2e.py` # -> only the docstring and comment in test_live_pipeline.py:81, :353
- `grep -n "only fakes allowed" -A12 tasks.md` # -> now names `_FakeState`, `_FakeHotword` and `NoLiveTickPipeline` (lines 92-94)
- Mutations R41, R42, HC, HC2 (see question 2) to confirm which fakes the new tests depend on

Question 4 (open items):
- `grep -n '^- \[ \]' tasks.md` # 5 unchecked: 8.1 (:151), A1 (:157), A2 (:158), A3 (:159), A4 (:160)
- `grep -c '^- \[x\]' tasks.md` # 22 ticked
- `grep -c 'def test_'` on the four live test files # live_preview 6, live_pipeline 13, live_client 13, live_e2e 4
- `grep -cE "def <name>\("` over `tools/test_live_*.py`, one per test name in the B1-B14 table # every name resolves to a def
- `grep -c '^\[\[mutation\]\]' mutations.toml` # 42
- `git diff --stat e673283..HEAD` # CLAUDE.md, tasks.md only
- `sed -n 1,12p CLAUDE.md`
- `grep -n "only fakes allowed" -A12 tasks.md`
- `/Users/qingyun.yuan/.local/bin/openspec validate add-live-dictation-mode` # valid, exit 0
- `git rev-parse --verify -q origin/feature/live-dictation` # no output (no remote branch; not pushed)
- Test and mutation runs (see question 2): whole suite twice, all pass; rows 41 and 42 CAUGHT

---

## 1. Entry points

Round 3. Review tree `/Users/qingyun.yuan/code/open-source/CapsWriter-wt/integ`, detached at `d3217e8`. Delta judged: `44146fa..HEAD` (commits `10f9121`, `2a01c1b`, `e64f078`, `e673283`, `d3217e8`). Commit `5e4ff2b` is a separate change and is excluded. Round 1 (`acceptance.md`, at `44146fa`) listed entry points E1-E14. This section judges only what the delta changes about them.

### What I ran

```
cd /Users/qingyun.yuan/code/open-source/CapsWriter-wt/integ
git log --oneline -12                          # HEAD d3217e8
git status                                     # "nothing to commit, working tree clean"
git diff                                       # (empty: working tree == HEAD)
git diff --stat 44146fa..HEAD
  # CLAUDE.md 4, acceptance.md +497, mutations.toml +11, tasks.md 19,
  # tools/test_live_client.py +28, tools/test_live_pipeline.py +74/-2
git diff --quiet 44146fa..HEAD -- core config_client.py config_server.py \
  start_client_macos.py start_client.py capswriter.py && echo "no production diff"
  # -> "no production diff in core/config/start"
git diff --stat e673283..HEAD                  # CLAUDE.md, tasks.md only (docs)
grep -n "handler.loop()\|handler.cleanup()\|sockets_id.remove\|handler.pipeline = \|_handle_message(message)\|RecognitionMessage.from_dict\|to_json()" \
  tools/test_live_pipeline.py tools/test_live_client.py
  # test_live_pipeline.py:364 handler.loop()   (B14 test)
  # test_live_pipeline.py:386 handler.pipeline = pipeline; :392 sockets_id.remove('s1'); :393 handler.cleanup()   (B13 test)
  # test_live_client.py:480-481 to_json() -> RecognitionMessage.from_dict; :486 await processor._handle_message(message)   (new client test)
grep -n "sockets_id\|finally" core/server/connection/ws_recv.py
  # :292 finally; :297-298 sockets_id.remove(socket_id)   (pre-existing disconnect path)
```

Call-site mutations (inline script; each file restored and checked by sha256; narrowest selection; `PYTHONDONTWRITEBYTECODE=1`; no `__pycache__` in the tree):

| Mutation | Test run | Result |
|---|---|---|
| `work_handler.py:178` drop ` and hasattr(self.pipeline, 'live_tick')` (toml row 41, verbatim) | `test_live_pipeline.py WorkHandlerLiveTests.test_other_engine_pipeline_sends_no_partials` | CAUGHT: `AssertionError: True is not false : 没有 live_tick 的管线不应该让工作循环报错` |
| `result_processor.py:224` `if message.preview:` -> `if not message.is_final:` (toml row 42, verbatim) | `test_live_client.py LivePanelTests.test_non_preview_partial_does_not_open_panel` | CAUGHT: `AssertionError: False is not true : 非 preview 的非最终消息不得弹出/唤醒预览面板` |
| `qwen_mlx_runner_pipeline.py:166` `self.live.pop(task_id, None)` -> `pass` | `test_live_pipeline.py WorkHandlerLiveTests.test_cleanup_via_work_handler_drops_live_task` | CAUGHT: `AssertionError: 't1' unexpectedly found in {'t1': <...LiveTask ...>}` |
| `work_handler.py:144` `if stale_task_ids and ...` -> `if False and stale_task_ids and ...` (entry check: does the test reach the pop only through `WorkHandler.cleanup()`?) | same test | CAUGHT: same assertion. So the test reaches the live pop through the real `WorkHandler.cleanup()`, not by a direct call |

### Entry points the delta adds or changes

- The delta adds or changes no production file. No new background worker, event handler, UI action or CLI path. Round 1's E1-E14 stand as recorded; I do not repeat that evidence.
- The delta changes the test evidence for four rows:

| # | Entry point (HEAD) | Test that enters through it | Grep / run proof | Fakes on the path | Row verdict |
|---|---|---|---|---|---|
| E11 | `QwenMLXRunnerPipeline.cleanup_tasks` live pop (`qwen_mlx_runner_pipeline.py:166`), production entry `WorkHandler.cleanup()` (`work_handler.py:138-151`) | `test_live_pipeline.py::WorkHandlerLiveTests::test_cleanup_via_work_handler_drops_live_task` | `:392 sockets_id.remove('s1')`, `:393 handler.cleanup()`; live task and session built by the real `process()`; both mutations above CAUGHT | `ScriptedRecognizer` (declared); plain `list` for `sockets_id` (declared in B13: "the socket drop itself is simulated by removing the socket id") | PASS (round 1: NEEDS-HUMAN) |
| E8 | `WorkHandler.loop` tick guard `hasattr(self.pipeline, 'live_tick')` (`work_handler.py:178`) | `test_live_pipeline.py::WorkHandlerLiveTests::test_other_engine_pipeline_sends_no_partials` | `:364 handler.loop()`; toml row 41 CAUGHT | `ScriptedQueue`, `NoLiveTickPipeline` (both declared; see Q3 for fidelity) | PASS |
| E2 | `ResultProcessor._handle_message` preview condition `if message.preview:` (`result_processor.py:224`) | `test_live_client.py::LivePanelTests::test_non_preview_partial_does_not_open_panel` | `:480-481` real `RecognitionMessage(...).to_json()` -> `from_dict`; `:486` real `_handle_message`; real `live_panel` NSPanel; toml row 42 CAUGHT | `_FakeState`, `_FakeHotword`, `_emit_text = AsyncMock` (declared) | PASS |
| E10 | `live_tick` exception guard log line (`qwen_mlx_runner_pipeline.py:144`) | `test_live_pipeline.py::PipelineLiveTests::test_failing_pass_does_not_break_final` (now wraps the call in `assertLogs('server')`) | see Q2 (HD CAUGHT, HD2 MISSED) | injected fault (declared gap B11, unchanged) | PASS (declared gap unchanged) |

### Findings

- Round 1's only open row (E11) is closed. The live pop is now reached through the real `WorkHandler.cleanup()`. The entry-check mutation proves the test depends on that path. tasks.md B13 now describes this correctly.
- The one simulated link left for E11 is the websocket close that removes the socket id (`ws_recv.py:297-298`). That code is pre-existing and outside the diff.
- The tick guard (E8) and the client preview condition (E2) each have a test through their real entry point, and each toml row is caught by it.
- The delta breaks no round-1 row: it changes no production file, and in the test files it removes no assertion (the only `-` lines are the old import line and the unwrapped `live_tick()` call, now wrapped in `assertLogs`).

Verdict for question 1: PASS — the delta changes no production file; round 1's open row E11 now enters through the real `WorkHandler.cleanup()` (proven by an entry-point mutation), and the tick guard and the preview condition each have a real-entry test that catches their toml row.

---

## 2. Fails before

Round 3. Tree `/Users/qingyun.yuan/code/open-source/CapsWriter-wt/integ` at `d3217e8`. Interpreter `/Users/qingyun.yuan/code/open-source/CapsWriter-for-macOS/.venv/bin/python`. Every run used `PYTHONDONTWRITEBYTECODE=1` (and `HF_HUB_OFFLINE=1`). Before the first run, `find . -name __pycache__ -not -path './models/*'` and the same for `*.pyc` printed nothing, so no stale bytecode could hide a mutation. Round 1 found one FAIL here: "Another engine sends no partials" had no test (the `hasattr` guard mutation survived). Round 2's Q2 reviewer did not answer. This section judges the delta `44146fa..HEAD`.

### What I ran

1. `python3 ~/.claude/tools/test_mutate.py` -> `mutate canary: 8/8 passed`.
2. Whole suite, run 1 of 2 (baseline), every `tools/test_*.py -v`: all 11 files exit 0 (counts in the table at the end).
3. `git diff 44146fa..HEAD -- tools/ | grep '^-'` -> only `-from core.server.schema import Work` and `-        result = pipeline.live_tick()` (now wrapped in `assertLogs`). `git diff 44146fa..HEAD -- .../mutations.toml | grep '^-'` -> nothing (two rows appended). `git diff --quiet 44146fa..HEAD -- core config_client.py ...` -> no production diff.
4. Six call-site mutations by an inline script: exact text must occur once; file written, narrowest test run, file restored, sha256 compared. All six restored (`restored=True`). `git status --porcelain` empty afterwards.

| Id | Mutation at the production call site | Narrowest selection | Verdict and failure line |
|---|---|---|---|
| R41 | `core/server/worker/work_handler.py:178` drop ` and hasattr(self.pipeline, 'live_tick')` (toml row 41, `old`/`new` verbatim, found once) | `tools/test_live_pipeline.py WorkHandlerLiveTests.test_other_engine_pipeline_sends_no_partials` | CAUGHT, rc=1: `AssertionError: True is not false : 没有 live_tick 的管线不应该让工作循环报错` |
| R42 | `core/client/output/result_processor.py:224` `if message.preview:` -> `if not message.is_final:` (toml row 42 verbatim, found once) | `tools/test_live_client.py LivePanelTests.test_non_preview_partial_does_not_open_panel` | CAUGHT, rc=1: `AssertionError: False is not true : 非 preview 的非最终消息不得弹出/唤醒预览面板` |
| HC | `qwen_mlx_runner_pipeline.py:166` `self.live.pop(task_id, None)` -> `pass` | `tools/test_live_pipeline.py WorkHandlerLiveTests.test_cleanup_via_work_handler_drops_live_task` | CAUGHT: `AssertionError: 't1' unexpectedly found in {'t1': <...LiveTask ...>}` |
| HC2 | `work_handler.py:144` prefix the cleanup condition with `False and` | same test | CAUGHT: same assertion (the test reaches the pop only through `WorkHandler.cleanup()`) |
| HD | `qwen_mlx_runner_pipeline.py:144` error log adds `, msg={exc}` | `tools/test_live_pipeline.py PipelineLiveTests.test_failing_pass_does_not_break_final` | CAUGHT: `AssertionError: 'boom' unexpectedly found in 'ERROR:server:实时预览 pass 失败: task=t1, exc_type=RuntimeError, msg=boom'` |
| HD2 | same line adds `, committed={task.agreement.committed!r}` | same test | MISSED: `Ran 1 test ... OK` (see Findings 2) |

Previous commit: the two new behaviour tests describe negative properties. On `33eba19` there was no tick and no panel, so a pipeline without `live_tick` never errs and a non-preview partial never opens anything; the tests cannot fail there. The call-site mutations R41 and R42 are the proof instead, as the question allows.

### Scenario table (rows the delta changes)

| Requirement / scenario | Test that pins it | Fails before | Row verdict |
|---|---|---|---|
| Dictation mode setting / Another engine sends no partials (round 1: FAIL) | Server: `test_live_pipeline::WorkHandlerLiveTests::test_other_engine_pipeline_sends_no_partials` (real `WorkHandler.loop`, pipeline with no `live_tick`). Client: `test_live_client::LivePanelTests::test_non_preview_partial_does_not_open_panel` (real to_json/from_dict, real `_handle_message`, real panel; asserts panel not shown and `_emit_text` not called) | R41 CAUGHT, R42 CAUGHT. The server half uses a stand-in; tasks.md B14 now declares that gap with a reason (see Q3). "Final text output as in hold mode" rests on unchanged output code plus round-1 rows (`test_final_hides_panel`, e2e `test_live_final_matches_hold`) | PASS |
| Partial failures / A failing partial pass: "error is logged without text" (round 1: minor note, no assertion) | `test_live_pipeline::PipelineLiveTests::test_failing_pass_does_not_break_final` | HD CAUGHT (exception message in the log). HD2 MISSED (committed text in the log) | PASS, with note |
| Live preview / "no panel stays on screen" and disconnect clean-up (B13, round 1 Q1) | `test_live_pipeline::WorkHandlerLiveTests::test_cleanup_via_work_handler_drops_live_task` | HC, HC2 CAUGHT | PASS |

All other scenario rows are carried from round 1 (verified at `44146fa`: prev-commit failures, 31 hand mutations, 40/40 toml rows in a narrowed run). They cannot have changed: no production file changed since `44146fa`, the 40 older toml rows are byte-identical, and the test files only gained tests and assertions (step 3), which can only add failures under a mutation.

TDD quality gate / Gate before hand-off:
- All new tests pass and the existing `tools/` tests pass at HEAD (runs 1 and 2).
- Rows 41 and 42: reproduced here with their verbatim `old`/`new` text, each found exactly once, each CAUGHT.
- Rows 1-40: carried from round 1 at `44146fa` (reason above).
- tasks.md 5C claims one tool run `RESULT mutate caught=42 missed=0 skipped=0 errors=0` at `e673283`. I did not repeat that single run. `git diff --stat e673283..HEAD` shows only `CLAUDE.md` and `tasks.md`, so HEAD has the same code and tests as `e673283`, and my row-by-row evidence agrees with the claim.

### Findings

1. Round 1's FAIL is closed. Both new call sites for "Another engine sends no partials" now have a test that fails when the call site is mutated.
2. Note (not blocking): the new log assertion in `test_failing_pass_does_not_break_final` only catches a leak of the exception message. The failing pass is the first pass, so there is no committed or tentative text yet, and a mutation that logs the committed text (HD2) survives. The production line builds its message from `task_id[:8]` and the exception type only, so there is no leak today. A stronger test would run one good pass (for example `'你好世界'` committed) before the failing one. The commit message of `10f9121` says the assertion checks "none of the committed/tentative/scripted text"; for committed and tentative text that check is empty in this test.
3. The delta weakens no earlier evidence (no assertion removed, no toml row changed).

### Whole-suite runs (run 1 baseline, run 2 at the end)

Run 2 started and ended with `git status --porcelain` empty; no `__pycache__` in the tree after it.

| File | Run 1 | Run 2 |
|---|---|---|
| test_editor_annotation | rc 0 | 8 PASS, 0 FAIL |
| test_editor_result_flow | rc 0 | 16 PASS, 0 FAIL |
| test_editor_ui_contract | `PASS: editor UI contract` | `PASS: editor UI contract` |
| test_live_client | Ran 13, OK | Ran 13, OK |
| test_live_e2e (real model) | Ran 4 in 62.5 s, OK | Ran 4 in 62.4 s, OK |
| test_live_pipeline | Ran 13, OK | Ran 13, OK |
| test_live_preview | Ran 6, OK | Ran 6, OK |
| test_mic_shortcut_lifecycle | Ran 9, OK | Ran 9, OK |
| test_mlx_model_resolution (belongs to 5e4ff2b) | Ran 4, OK | Ran 4, OK |
| test_stream_stop_leak | Ran 14, OK | Ran 14, OK |
| test_worker_scheduling | Ran 10, OK | Ran 10, OK |

Run 2 total: 97 cases (73 unittest cases plus 24 editor script cases) and the editor UI contract check, 0 failures. Round 1 had 94; the difference is the three new tests (live_pipeline +2, live_client +1). The e2e did not skip (62 s on the real model).

Verdict for question 2: PASS — round 1's FAIL is closed: toml rows 41 (`hasattr` guard) and 42 (`if message.preview:`) are each CAUGHT by their new test, the cleanup pop is CAUGHT through `WorkHandler.cleanup()`, and all other rows carry forward unchanged; one note: the new failing-pass log check cannot see a committed-text leak (HD2 MISSED).

---

## 3. Real versus simulated

Round 3. Tree at `d3217e8`, working tree equal to HEAD (`git status` clean). Delta `44146fa..HEAD`. Round 1 rows 1-19 are not re-argued. Round 2 (at `2a01c1b`) added rows 20-25 and asked for B14 to be re-labelled as a declared gap. This section checks the rest of the delta (`e64f078`, `e673283`, `d3217e8`) and what it does to those findings.

### What I ran

- `git diff 44146fa..HEAD -- tools/ openspec/.../tasks.md openspec/.../mutations.toml CLAUDE.md` (read in full).
- `git diff --stat 2a01c1b..HEAD` -> `CLAUDE.md`, `mutations.toml` (+6), `tasks.md`, `tools/test_live_client.py` (+28).
- `sed -n 270,345p tools/test_live_client.py` (helpers `_FakeCorrector`, `_FakeHotword`, `_FakeState`, `_new_result_processor`); `sed -n 494,526p` (`test_final_hides_panel`); the new test read from the diff (HEAD lines 466-492).
- `sed -n 1,130p tools/test_live_pipeline.py` (helpers, `NoLiveTickPipeline` at :80-91); `sed -n 200,250p` and `sed -n 348,362p`; the B13 test read from the diff (HEAD lines 378-397).
- `cat -n core/server/worker/work_handler.py | sed -n 60,200p`; `cat -n core/server/worker/work_pipeline.py | sed -n 55,135p`; `cat -n core/server/connection/ws_send.py | sed -n 20,80p`; `sed -n 70,140p core/protocol.py`; `cat -n core/client/output/result_processor.py | sed -n 205,290p`.
- `grep -rn "WorkPipeline\|set_engine" tools/ | grep -v test_live_e2e.py` -> only the docstring and comment in `test_live_pipeline.py:81, :353`. No test runs a real `WorkPipeline`.
- `grep -n "only fakes allowed" -A12 tasks.md` -> the list now names `_FakeState`, `_FakeHotword` and `NoLiveTickPipeline` (lines 92-94).
- Mutations R41, R42, HC, HC2 (see Q2) to confirm which fakes the new tests depend on.

### Bypass inventory for the delta (numbering continues round 2)

| # | File / test | Bypass | Decision skipped | Covered elsewhere? |
|---|---|---|---|---|
| 20 | `test_live_pipeline.py:80-91, :351-376` `NoLiveTickPipeline`, set by `handler.pipeline = ...` | Stand-in for another engine's pipeline; skips `set_engine`'s `else` branch (`work_handler.py:96-97`) | (a) a non-task-runner engine resolves to `WorkPipeline`; (b) what `WorkPipeline` does with a live packet | Declared: tasks.md B14 now says "Declared gap on the server side: the stand-in returns None for non-final packets, while the real `WorkPipeline` returns a Result, so no test runs a real other-engine pipeline". I confirmed the fact: `WorkPipeline.process(...) -> Result` returns `result` at `work_pipeline.py:76` and `:127`, never `None`, so with the real class `work_handler.py:178` stops at `result is None` and never reads the `hasattr` clause. (a) and (b) are unchanged code. The part that reaches the client (a non-final Result with `preview` left at its default `False`) is now covered by row 26. Round 2's re-label request: closed. Note: the stated reason "it needs a second model" is weaker than it reads; a real `WorkPipeline` could run with a scripted recognizer, as `QwenMLXRunnerPipeline` does here. Such a test would still not reach the guard and would only pin unchanged code, so the gap costs nothing this change owns |
| 21-25 | round 2 rows (ScriptedQueue in B14 test; live task built by direct `process()`; `handler.cleanup()` called directly; plain-list socket drop; `assertLogs` handler swap) | unchanged since round 2 | as round 2 | as round 2. Row 24 is now also backed by mutation HC2: the B13 test fails when `WorkHandler.cleanup()` skips `cleanup_tasks`, so it does enter through the real handler |
| 26 | `test_live_client.py:466-492` `test_non_preview_partial_does_not_open_panel` | The other engine's partial is built by hand as `RecognitionMessage(..., is_final=False, text=...)` with `preview` at its default, not produced by a real `WorkPipeline` Result through `ws_send` | That `ws_send` sends `preview=False` for another engine's partial | Yes. `ws_send.py:43` copies `preview=result.preview`; `Result.preview` defaults to `False` and `WorkPipeline` never sets it. The copy runs for real in the e2e (live previews with `preview=True`, finals with `False`). The message still goes through the real `to_json` / `from_dict` (`:480-481`). R42 is CAUGHT by this test |
| 27 | same test, via `_new_result_processor` | `_FakeState`, `_FakeHotword`, `processor._emit_text = AsyncMock`, `patch.object(Config, 'dictation_mode', 'live', create=True)` | Paste/typing output; hotword and state collaborators | Declared: now named in tasks.md "only fakes allowed" (round 1/2 doc nit closed). The non-final message returns at `result_processor.py:261-262`, before any of these fakes is reached; `_emit_text.assert_not_called()` only checks that the drop happened. `create=True` is inert: `config_client.py` defines `dictation_mode` |
| 28 | same test | `_handle_message` runs on the main thread and the test pumps `NSRunLoop`; production runs it on the client thread and hops to AppKit with `AppHelper.callAfter` | Cross-thread dispatch into the real run loop | Same as round 1 row 17. No automated test. Left to the user (A1-A4) |

### What the delta does to earlier Q3 findings

- Round 1 found no undeclared bypass. The delta adds rows 20 and 26-28. All are named in tasks.md or covered by another test. Still none undeclared or uncovered.
- Round 2's one change request (re-label B14 as a declared gap with its reason) is done in `e673283`.
- Round 1 rows 6 (worker in a thread, not a `multiprocessing.Process`) and 17 (same-thread run-loop pump) are untouched: no production file, e2e file or harness changed. A1-A4 are still `[ ]` at HEAD (tasks.md:157-160). So the human items remain.
- Doc nit left: the B14 test comment (`test_live_pipeline.py:352-353`) still says "真实的WorkPipeline就是这个形状". That is true for "no `live_tick`" and false for the return value. tasks.md B14 states the difference correctly.

### Does the delta break anything?

- No test that used a real path in round 1 now uses a fake. `NoLiveTickPipeline` is used by one test. The new client test adds no new kind of fake.
- No new environment override (the only `patch.object(Config, ...)` in the new test follows the pattern round 1 accepted as row 16).

Verdict for question 3: NEEDS-HUMAN — the delta adds no undeclared or uncovered bypass and closes round 2's B14 re-label; the cross-thread AppKit dispatch (round 1 row 17) and the real worker process boundary (round 1 row 6) are still covered only by the user's Acceptance A1-A4.

---

## 4. Open items

Round 3. Tree at `d3217e8` (`git status` clean; `git rev-parse feature/live-dictation` = `d3217e8...`, so the branch equals HEAD). Delta `44146fa..HEAD`. Round 1 and round 2 lists are not repeated; this section checks what the delta closed, what it left, and what it made stale.

### What I ran

| Command | Output |
|---|---|
| `grep -n '^- \[ \]' tasks.md` | 5 unchecked: 8.1 (:151), A1 (:157), A2 (:158), A3 (:159), A4 (:160) |
| `grep -c '^- \[x\]' tasks.md` | 22 ticked |
| `grep -c 'def test_'` on the four live test files | live_preview 6, live_pipeline 13, live_client 13, live_e2e 4 |
| every `test_*` name in the B1-B14 table, `grep -cE "def <name>\("` over `tools/test_live_*.py` | every test name resolves to a def (the only zero hits are the module names `test_live_client`, `test_live_e2e`, `test_live_pipeline`, `test_live_preview`) |
| `grep -c '^\[\[mutation\]\]' mutations.toml` | 42 |
| `git diff --stat e673283..HEAD` | `CLAUDE.md`, `tasks.md` only |
| `sed -n 1,12p CLAUDE.md` | status: "自动化检查通过（e673283）… live_preview 6 项、live_pipeline 13 项、live_client 13 项 … 端到端测试 4/4、mutations 42/42"; "独立验收记录见 …acceptance.md"; "真机验收（A1–A4）等待用户确认，尚未完成" |
| `grep -n "only fakes allowed" -A12 tasks.md` | now names `_FakeState`, `_FakeHotword`, `NoLiveTickPipeline` |
| `/Users/qingyun.yuan/.local/bin/openspec validate add-live-dictation-mode` | `Change 'add-live-dictation-mode' is valid`, exit 0 |
| `git rev-parse --verify -q origin/feature/live-dictation` | no output (no remote branch; not pushed) |
| test and mutation runs | see Q2 (whole suite twice, all pass; rows 41 and 42 CAUGHT) |

### Unchecked tasks at HEAD

| Task | Text (short) | Who can close it | Status |
|---|---|---|---|
| 8.1 | Fable acceptance in a fresh subagent (`opsx:accept`) | this review | In progress (round 3). Round 1 is recorded in `acceptance.md` with verdict FAIL; rounds 2 and 3 are not recorded there yet. |
| A1 | Live mode: text in the panel within about 2 s, updates while speaking, the text field keeps focus and caret | user, running app | Open |
| A2 | On release, the pasted text is the final text and the panel closes | user | Open |
| A3 | Default `'hold'` behaves as before, no panel | user | Open |
| A4 | About one minute in live mode keeps updating to the end | user | Open (the e2e long case is 30 s of TTS, not a minute) |

No ticked task carries a note that says "not done", "deferred" or "needs the user".

### Round 2 findings for this question, and what the delta did

| Round 2 item | At HEAD | Status |
|---|---|---|
| 5C note said "40 rows; 40/40 at 3380b4e" while the toml had 41 rows | 5C: "42 rows; `RESULT mutate caught=42 …` at e673283"; toml has 42 rows. Rows 41-42 reproduced in Q2; rows 1-40 carried from round 1; `e673283..HEAD` is docs only | Closed |
| 7.1 note said "at 1c760dc" | 7.1: "at e673283 … live_client 13, live_pipeline 13, live_preview 6; mutations 42/42". My runs at HEAD (same code as e673283) match: all files pass, same counts, e2e 4/4 | Closed |
| CLAUDE.md status: "11 项", "40/40", "Fable 验收评审待进行" | Now "13 项", "13 项", "42/42", and a pointer to `acceptance.md` | Closed |
| Allowed-fake list omitted `_FakeState`, `_FakeHotword` (and `NoLiveTickPipeline`) | All three named (tasks.md:92-94) | Closed |
| B14 production-entry column claimed a test that uses a stand-in | Re-labelled as a declared gap with the reason (see Q3 row 20) | Closed |
| No client test sent a non-final, non-preview message | `test_non_preview_partial_does_not_open_panel` added; toml row 42 | Closed |

### Doc nits still open (not blocking)

- `tools/test_live_pipeline.py:5` docstring: "覆盖 B1、B4、B5、B7、B8、B10、B11、B13" — B14 is missing.
- `tools/test_live_pipeline.py:81-82` `NoLiveTickPipeline` docstring labels the rule "B1"; tasks.md calls it B14.
- `tools/test_live_pipeline.py:352-353` comment "真实的WorkPipeline就是这个形状" is false for the return value (the real class never returns `None`); tasks.md B14 says this correctly.
- tasks.md "Call sites to mutate (5C)" list does not name the two call sites of rows 41 and 42 (the `hasattr` guard, the `if message.preview:` condition). The rows exist.
- CLAUDE.md says the acceptance record is in `acceptance.md` but not that round 1 there is a FAIL and later rounds are not yet recorded.
- The spec scenario "A failing partial pass" is only partly pinned for "error logged without text" (Q2 finding 2). A test change, not a task.

### What the user must still verify (plain words)

1. Set `dictation_mode = 'live'`, run `capswriter restart`, hold Caps Lock in a text field and speak. Text must appear in the floating panel within about 2 s and keep updating. The text field must keep focus and its caret. (A1)
2. Release Caps Lock. The pasted text must be the final result, and the panel must close. (A2)
3. Set `dictation_mode` back to `'hold'` (the default) and restart. Dictation must look and behave as before, with no panel. (A3)
4. In live mode, dictate for about one minute. The panel must keep updating until release. (A4)
5. Decide whether the measured preview quality on your own voice (1.4 % wrong committed text, about 3 s commit lag, from `evidence.md`) is acceptable. (accepted requirements finding F4)
6. Optional: decide whether a disconnect in the middle of a live recording (client quit while holding Caps Lock) needs a check in the running app. No Acceptance item covers it; the automated test now enters through the real `WorkHandler.cleanup()`, and only the socket close itself is simulated.

Verdict for question 4: NEEDS-HUMAN — the delta closes every round-2 item for this question (stale 5C/7.1/CLAUDE.md figures, fake list, B14 label, client test); 8.1 is this review, and A1-A4 plus the F4 quality judgement are open and only the user in the running app can close them; five doc nits remain, none blocking.

---

## 5. Scope, tolerances and design drift

Carried from 44146fa (round 1): the delta 44146fa..d3217e8 changes only tests, tasks.md, mutations.toml, acceptance.md and CLAUDE.md, and no file outside the declared scope.

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
| 1. Entry points | PASS | the delta changes no production file; round 1's open row E11 now enters through the real `WorkHandler.cleanup()` (proven by an entry-point mutation), and the tick guard and the preview condition each have a real-entry test that catches their toml row. |
| 2. Fails before | PASS | round 1's FAIL is closed: toml rows 41 (`hasattr` guard) and 42 (`if message.preview:`) are each CAUGHT by their new test, the cleanup pop is CAUGHT through `WorkHandler.cleanup()`, and all other rows carry forward unchanged; one note: the new failing-pass log check cannot see a committed-text leak (HD2 MISSED). |
| 3. Real versus simulated | NEEDS-HUMAN | the delta adds no undeclared or uncovered bypass and closes round 2's B14 re-label; the cross-thread AppKit dispatch (round 1 row 17) and the real worker process boundary (round 1 row 6) are still covered only by the user's Acceptance A1-A4. |
| 4. Open items | NEEDS-HUMAN | the delta closes every round-2 item for this question (stale 5C/7.1/CLAUDE.md figures, fake list, B14 label, client test); 8.1 is this review, and A1-A4 plus the F4 quality judgement are open and only the user in the running app can close them; five doc nits remain, none blocking. |
| 5. Scope, tolerances and design drift (carried from 44146fa) | PASS | no undeclared file, dependency, tolerance or design change; deviations from design.md are the review-5A rows tasks.md declares as applied, and every one-caller abstraction is one the design prescribes. |

Verdict: NEEDS-HUMAN
