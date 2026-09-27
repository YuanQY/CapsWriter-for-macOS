# Tasks: add-live-dictation-mode

Roles: orchestrator = the main session (Opus). Code and tests = Sonnet agents.
Code review = Opus agent (one tier above Sonnet). Redteam = Fable. Acceptance
= Fable in round 1, Opus from round 3 on (the user asked to save Fable quota).
Each writing agent works in its own git worktree; read-only agents read
`HEAD` of `feature/live-dictation`.

Run tests as `.venv/bin/python tools/<name>.py -v`.

## Lanes and order


| Group                   | Runs with  | Waits on | Owner                                        | Files owned                                                                                                                                                                                                  |
| ----------------------- | ---------- | -------- | -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1 Baseline and contract | -          | -        | orchestrator                                 | `core/protocol.py`, `core/server/schema.py`, `openspec/`                                                                                                                                                     |
| 2 Unit test plan audit  | -          | 1        | Fable redteam (with requirements and design) | none (writes`adversarial-*.md`)                                                                                                                                                                              |
| 3A Server tests         | 3B, 3C, 3D | 2        | Sonnet                                       | `tools/test_live_preview.py`, `tools/test_live_pipeline.py`, `tools/test_live_e2e.py`                                                                                                                        |
| 3B Server code          | 3A, 3C, 3D | 2        | Sonnet                                       | `core/server/worker/live_preview.py` (new), `core/server/worker/qwen_mlx_runner_pipeline.py`, `core/server/worker/work_handler.py`, `core/server/connection/ws_recv.py`, `core/server/connection/ws_send.py` |
| 3C Client tests         | 3A, 3B, 3D | 2        | Sonnet                                       | `tools/test_live_client.py`                                                                                                                                                                                  |
| 3D Client code          | 3A, 3B, 3C | 2        | Sonnet                                       | `config_client.py`, `core/client/audio/recorder.py`, `core/client/output/result_processor.py`, `core/client/output/live_panel.py` (new)                                                                      |
| 4 Merge and validate    | -          | 3A-3D    | orchestrator                                 | merge commits; fixes go back to the lane's author                                                                                                                                                            |
| 5A Code review          | 5B, 5C, 5D | 4        | Opus, read-only                              | none                                                                                                                                                                                                         |
| 5B Simplify             | 5A, 5C, 5D | 4        | Sonnet, read-only, reports                   | none until 6                                                                                                                                                                                                 |
| 5C Mutations            | 5A, 5B, 5D | 4        | orchestrator, verification worktree          | `openspec/changes/add-live-dictation-mode/mutations.toml`                                                                                                                                                    |
| 5D Docs                 | 5A, 5B, 5C | 4        | Sonnet                                       | `readme.md`, `CLAUDE.md`                                                                                                                                                                                     |
| 6 Apply findings        | -          | 5A-5D    | lane authors                                 | the files each finding names                                                                                                                                                                                 |
| 7 Verify and clean      | -          | 6        | orchestrator                                 | none                                                                                                                                                                                                         |
| 8 Acceptance review     | -          | 7        | Fable, fresh context                         | `acceptance.md`                                                                                                                                                                                              |

- Only `tools/test_live_e2e.py` loads the model (GPU). It runs in group 4 and 7,
  never in parallel with itself.
- Worktrees have no `.venv` and no `models/` (both gitignored), and the model
  path is relative to the working directory. So every run uses the main
  checkout's interpreter by absolute path, and every run that needs the model
  (e2e, mutations) happens in one verification worktree whose `models` is a
  symlink to the main checkout's `models`. Test processes then write their logs
  to that worktree's `logs/`, not to the log the running server holds open.
- 3A and 3C write tests from `design.md` and `spec.md` only, without seeing the
  lane code, so the tests check the spec and not the implementation.

## 1. Baseline and contract

- [X]  1.1 Run every `tools/test_*.py` on `feature/live-dictation` and record the pass counts here. At 33eba19: annotation 8/8, editor_result_flow 16/16, editor_ui_contract PASS, mic_shortcut_lifecycle 9 OK, stream_stop_leak 14 OK, worker_scheduling 10 OK.
- [X]  1.2 Add the contract fields with Chinese comments: `AudioMessage.live`, `RecognitionMessage.preview` and `text_tentative` (read with `.get` in `from_dict`), `Work.live`, `Result.preview` and `text_tentative`. All default to the hold values.
- [X]  1.3 Rerun 1.1; the counts must not change. Commit the openspec change and the contract.

## 2. Unit test plan

Behaviours (B), their tests, and the production entry test. A production entry
test runs from the real entry point without replacing a real dependency.


| B   | Behaviour                                                                                                               | Tests                                                                                                                                                                                                                                                            | Production entry                                                                                                                                                                                                                                                                                                                                                                       |
| --- | ----------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| B1  | Default hold: recorder sends`live=False`, server runs no pass, no preview message, final unchanged                      | `test_live_client::test_recorder_default_sends_hold`, `test_live_pipeline::test_hold_task_never_runs_a_pass`                                                                                                                                                     | `test_live_e2e::test_hold_run_sends_no_preview`                                                                                                                                                                                                                                                                                                                                        |
| B2  | Unknown`dictation_mode` means hold                                                                                      | `test_live_client::test_recorder_unknown_mode_sends_hold`                                                                                                                                                                                                        | `test_live_client::test_recorder_unknown_mode_sends_hold` (real recorder loop, real `WebSocketManager`, local capture server on 127.0.0.1)                                                                                                                                                                                                                                             |
| B3  | Live mode tags every audio message                                                                                      | `test_live_client::test_recorder_live_mode_tags_messages`                                                                                                                                                                                                        | same test (real recorder loop and socket, as B2)                                                                                                                                                                                                                                                                                                                                       |
| B4  | Server runs a pass per 1 s of new audio, first at 1 s, none without new audio                                           | `test_live_pipeline::test_pass_cadence_follows_audio_time`                                                                                                                                                                                                       | `test_live_e2e::test_live_run_streams_previews`                                                                                                                                                                                                                                                                                                                                        |
| B5  | Preview message carries committed and tentative text and reaches the client                                             | `test_live_pipeline::test_preview_result_fields`                                                                                                                                                                                                                 | `test_live_e2e::test_live_run_streams_previews` (real `ws_recv`, `ws_send`, `WorkHandler.loop`, engine, socket)                                                                                                                                                                                                                                                                        |
| B6  | Commit rule (three passes, holdback 4, numeral hold, content alignment)                                                 | `test_live_preview::test_tail_word_not_committed_early`, `::test_open_numeral_run_waits`, `::test_insertion_does_not_duplicate_tail`, `::test_trailing_punctuation_hidden`, `::test_commits_on_third_agreeing_pass`                                              | `test_live_e2e::test_live_run_streams_previews` (committed text of each preview extends the previous one)                                                                                                                                                                                                                                                                              |
| B7  | Final equals the hold-mode final; no preview after the final                                                            | `test_live_pipeline::test_final_pops_live_task`                                                                                                                                                                                                                  | `test_live_e2e::test_live_final_matches_hold`                                                                                                                                                                                                                                                                                                                                          |
| B8  | Final waits for at most the running pass; no pass while a final is buffered                                             | `test_live_pipeline::test_final_is_not_queued_behind_passes`                                                                                                                                                                                                     | Declared gap: the order cannot be forced through a real socket without timing. Covered by the real`WorkHandler.loop` and real pipeline with a scripted engine and a controlled queue.                                                                                                                                                                                                  |
| B9  | Each pass reads all audio so far; committed text only grows over a long recording                                       | `test_live_preview::` step test (transcriber gets all fed samples; committed only grows)                                                                                                                                                                         | `test_live_e2e::test_long_live_run_keeps_up` (30 s TTS clip; previews keep coming, each committed text extends the previous one, final matches hold)                                                                                                                                                                                                                                   |
| B10 | Partial text is not logged or printed, on server and client                                                             | `test_live_pipeline::test_preview_is_not_logged`, `test_live_client::test_preview_is_not_logged` (real `ResultProcessor`, `client` logger captured at DEBUG)                                                                                                     | `test_live_e2e::test_live_run_streams_previews` (captures the `server` logger at DEBUG and stdout; none before the final contains preview text)                                                                                                                                                                                                                                        |
| B11 | A failing pass skips the update and uses up its slot; final still works; error logged without text                      | `test_live_pipeline::test_failing_pass_does_not_break_final`                                                                                                                                                                                                     | Declared gap: a model failure needs an injected fault.                                                                                                                                                                                                                                                                                                                                 |
| B12 | Client shows preview in a non-activating panel (committed normal, tentative system blue with an underline, height capped at 40 % of the visible screen with the newest lines shown), hides on final, auto-hides after 5 s | `test_live_client::test_show_does_not_activate_app`, `::test_final_hides_panel`, `::test_panel_auto_hides`, `::test_stale_auto_hide_does_not_hide_newer_panel`, `::test_long_mixed_text_label_is_not_clipped`, `::test_utf16_color_ranges_across_surrogate_pair`, `::test_panel_height_is_capped_for_long_text` | `test_live_client::test_preview_message_updates_real_panel` (real JSON from the server's `RecognitionMessage.to_json`, real `from_dict`, real `ResultProcessor._handle_message`, real `live_panel` NSPanel, main run loop pumped)                                                                                                                                                      |
| B13 | Disconnect drops the live task                                                                                          | `test_live_pipeline::test_cleanup_drops_live_task`                                                                                                                                                                                                               | `test_live_pipeline::test_cleanup_via_work_handler_drops_live_task` (real `WorkHandler.cleanup()` with a controlled socket list; the socket drop itself is simulated by removing the socket id)                                                                                                                                                                                        |
| B14 | Another engine: no pass, no error, no panel                                                                             | `test_live_pipeline::test_other_engine_pipeline_sends_no_partials` (real `WorkHandler.loop` with a pipeline that has no `live_tick`), `test_live_client::test_non_preview_partial_does_not_open_panel`                                                           | Client side:`test_live_client::test_non_preview_partial_does_not_open_panel` (real `ResultProcessor`, real panel; the other engine's ordinary non-final message is dropped). Declared gap on the server side: the stand-in returns None for non-final packets, while the real `WorkPipeline` returns a Result, so no test runs a real other-engine pipeline (it needs a second model). |

Test notes:

- `test_live_e2e.py` makes its audio with `say -v Tingting` (Mandarin; the Eddy and Flo zh_CN voices produce near-silent Chinese audio on this machine) into a temp
  file, so no user recording is used. It sets `HF_HUB_OFFLINE=1` and skips
  with a clear message unless the local 8-bit model directory exists; it never
  lets the engine fall back to a hub id (`config_server.py:110`). It sends
  20 ms packets at real-time pace (the production block size), runs the real
  `ws_recv` and `ws_send` under `websockets.serve` on 127.0.0.1 port 0 with the
  real server state, and runs `WorkHandler.loop` with the real engine in a
  thread. It must not change production code to make this possible. It
  asserts bounds (at least N previews, first preview within T), not exact
  counts, because pass timing depends on the shared GPU.
- Recorder tests set `Config.save_audio = False` and assert that no file was
  written under the repository's year folders (`2026/`), which hold the user's
  recordings. They connect only to their own capture server on port 0.
- The real-panel test hides the panel in teardown.
- For a test of a new module, an import error counts as "fails before". For a
  test of a changed existing module, "fails before" must be an assertion
  failure.
- Every test case has `# Given / When / Then` comments (Chinese, as the repo).
- The only fakes allowed: the model in `test_live_pipeline.py` (a scripted
  `feed_audio_patch`), the queue in scheduling tests, the output/paste side of
  `ResultProcessor` (so tests never type into the user's apps), and a minimal
  `app` object that holds the real `ClientState` and the real
  `WebSocketManager` for the recorder tests. Also used: `_FakeState` and
  `_FakeHotword` on the `ResultProcessor` final path (state and hotword
  collaborators, as in `test_editor_result_flow.py`), and `NoLiveTickPipeline`
  in `test_live_pipeline.py` (a pipeline without `live_tick`, standing in for
  another engine).

- [X]  2.1 Fable redteam audits requirements, design and this plan in one round; findings in `adversarial-*.md`; orchestrator answers each and updates the artifacts.

## 3. Generate tests and implement (four lanes in parallel)

- [X]  3A.1 Write `tools/test_live_preview.py` and `tools/test_live_pipeline.py` (B1, B4-B11, B13) against the API in `design.md`.
- [X]  3A.2 Write `tools/test_live_e2e.py` (B1, B4-B7, B9, B10).
- [X]  3A.3 Validate: run the new tests on the group 1 commit; each must fail (import error for the new module counts), and record the failure lines.
- [X]  3B.1 Implement `live_preview.py` by porting the eval's `M3-1.0-a3` path (no flags) from `~/code/open-source/capswriter-ab/stream_eval/run_eval.py`. (The w15 window was ported first and removed after the real-model e2e run; see design D5.)
- [X]  3B.2 Implement D2, D4, D6 and D7 in the pipeline, work handler, `ws_recv` and `ws_send`.
- [X]  3C.1 Write `tools/test_live_client.py` (B1-B3, B12) against the API in `design.md`.
- [X]  3C.2 Validate: run it on the group 1 commit; each case must fail; record the failure lines.
- [X]  3D.1 Add `dictation_mode = 'hold'` to `config_client.py` with a Chinese comment; set `live` in the recorder's three `AudioMessage` calls.
- [X]  3D.2 Implement `live_panel.py` (D8) and the `result_processor` branch (D9).

## 4. Merge and validate

- [X]  4.1 Merge 3A-3D into `feature/live-dictation`.
- [X]  4.2 Run all new tests and all existing `tools/test_*.py`. A mismatch between a test and the code goes back to the lane that is wrong by the spec, not to whichever is easier to change.

## 5. Review, simplify, mutations, docs (parallel)

- [X]  5A Opus code review (report: `review-5A.md`: 0 HIGH, 9 MEDIUM, 11 LOW; all applied in group 6) of the diff against `spec.md` and `design.md`: correctness, privacy (no partial text in logs), focus behaviour, hold mode unchanged, and the KISS / Ponytail audit checklist (every line serves a scenario, no one-caller abstraction, no new knob, no impossible-case branch, no touched line outside the task, hold path does no extra work).
- [X]  5B Simplify pass (report: `simplify-5B.md`: two proposals, -2 lines; the ws_send merge was applied; the hoisted import was superseded by review #2, which imports live_panel only in live mode) over the whole diff (the five checks in the user's rules plus the KISS / Ponytail checklist); report the line reduction.
- [X]  5C (row count and RESULT lines: see acceptance.md; earlier runs found 5 MISSED rows and acceptance round 1 found 2 more gaps, each closed with a new test, never by deleting a row) Write `mutations.toml` with one row per new production call site (list below) and run `python3 ~/.claude/tools/mutate.py openspec/changes/add-live-dictation-mode/mutations.toml` in the verification worktree after `python3 ~/.claude/tools/test_mutate.py` reports 8/8.
- [X]  5D Update `readme.md` (the setting, what live mode shows, GPU cost, restart needed) and `CLAUDE.md` (the "流式识别策略" decision row and a dated status section; the 任务看板 table is not used for this change).

Call sites to mutate (5C):

- recorder: `live=` value in each of the three `AudioMessage` calls
- `AudioMessage.from_dict`: the `live` read
- `ws_recv`: `live=msg.live` into `Work`
- pipeline `process`: live task feed; pop on final
- pipeline `live_tick`: `is_final=True`; the `#live` task id suffix; the exception guard
- `LiveTask.step`: `next_due` advanced before the model call
- pipeline `cleanup_tasks`: live task pop
- work handler loop: the `live_tick` call and its empty-buffer condition
- `ws_send`: `preview` and `text_tentative` copies; the preview log guard
- `RecognitionMessage.from_dict`: `preview` and `text_tentative` reads
- `result_processor`: preview branch `show`; `hide` on final
- `live_panel`: non-activating style; `setHidesOnDeactivate_(False)`; `orderFrontRegardless`; auto-hide generation check
- `live_preview`: `AGREE`, `HOLDBACK`, `INTERVAL`, the numeral hold, the content alignment, the trailing-punctuation trim, the whole-audio slice passed to `transcribe`

## 6. Apply findings

- [X]  6.1 Apply accepted findings from 5A and 5B; rerun only the tests the fixes touch, plus the mutation rows on touched call sites.

## 7. Verify and clean

- [X]  7.1 (run with PYTHONDONTWRITEBYTECODE=1; pass counts and mutation RESULT lines: see acceptance.md) All `tools/test_*.py` pass; `test_live_e2e.py` passes; every `mutations.toml` row is CAUGHT; `openspec validate add-live-dictation-mode` passes.
- [X]  7.2 `git status` shows no stray files; commit on `feature/live-dictation`. Push only to `origin` (the user's fork) and only when the user asks; never to `upstream`. (Pushed at the user's request on 2026-09-27.)

## 8. Acceptance review

- [X]  8.1 (round 1 Fable at 44146fa: FAIL on Q2, fixed; round 3 Opus at d3217e8: `Verdict: NEEDS-HUMAN`, the Acceptance items below and the preview-quality decision F4 left for the user; round 4 Opus delta at 67efc8b: FAIL, fixed in group 9; see acceptance.md) Fable acceptance in a fresh subagent with paths and commands only (`opsx:accept`).

## 9. Post-acceptance changes (2026-09-27, after the user's first real-app check)

Code and tests: one Sonnet lane in worktree `live/pause-commit` (9.3, 9.4).
Runs with it: the public-layer comparison (9.5, orchestrator) and these doc
edits (orchestrator). 9.6 and 9.7 wait on the merge.

- [X]  9.1 Tentative text in system blue with an underline; panel height capped at 40 % of the visible screen with the newest lines shown (92a04d7). The user found grey too close to the normal colour; a long dictation grew past the screen.
- [X]  9.2 A space between Latin words that meet across passes (`_join`, 5121066), found by the preview-loss diagnosis on the public layers.
- [ ]  9.3 Pause commits the tail (spec: Commit rule; scenarios "A pause commits the tail", "A numeral at a pause still waits"). The user saw the last tentative words never turn committed while pausing. Changed expected value, declared: `test_live_preview::test_insertion_does_not_duplicate_tail` committed "你好世界今天" becomes "你好世界今天天气很好" (its three passes are the same, so the pause rule applies).
- [ ]  9.4 Round-4 findings: Latin spacing and the pause rule tested through the real `WorkHandler.loop` / `live_tick`; mutation rows for `.lstrip()` in `LiveTask.step` and in `live_tick`, for the pause branch, for committing trailing punctuation, and for a 20 pt cap overshoot; the cap test bound tightened from `cap + 2 * margin + 0.5` to `cap + 1`. Declared gap: the real-model e2e has no mixed Chinese-English clip (the only reliable TTS voice reads Mandarin), so Latin spacing on the real engine is left to A7.
- [X]  9.5 Compare the current and the pause rule on the same passes of public layers A, B and C (commit error, rewrites, commit lag); result in `evidence.md`, "Pause rule".
- [ ]  9.6 Simplify pass over the group 9 diff.
- [ ]  9.7 Opus delta acceptance over 67efc8b..HEAD; rounds 4 and 5 go into `acceptance.md` after round 3, unchanged.

## Acceptance

Items for the user in the running app. Never ticked by an agent. A1 and A4
were confirmed on e586500 code and must be checked again, because group 9
changes the paths they exercise; A2 and A3 stay confirmed.

- [ ]  A1 With `dictation_mode = 'live'` and `capswriter restart`, hold Caps Lock in a text field and speak naturally, with fillers and self-corrections: the panel shows text within about 2 s of the first word and updates while speaking; the text field keeps focus and its caret.
- [X]  A2 On release in live mode, the pasted text is the final text and the panel closes.
- [X]  A3 With the default `'hold'`, dictation looks and behaves as before (no panel).
- [ ]  A4 A dictation of about one minute in live mode keeps updating to the end.
- [ ]  A5 Tentative words are blue with an underline and readable in light and dark mode; committed words are the normal colour.
- [ ]  A6 In a dictation of one to two minutes the panel stops growing at about 40 % of the screen height, and the newest words stay visible at the bottom.
- [ ]  A7 A Chinese sentence with an English phrase and a pause, e.g. "我们聊到了 dessert, you know, 还不错", never shows glued words such as "dessertyou".
- [ ]  A8 After you stop speaking and keep holding Caps Lock for about 3 s, the blue underlined tail turns to the normal colour (a sentence that ends in a number keeps the number blue).
- [ ]  A9 Decide whether the preview quality is acceptable: wrong committed text and commit lag on your own voice, figures in `evidence.md` (F4 in acceptance.md round 3).
