# Tasks: add-live-dictation-mode

Roles: orchestrator = the main session (Opus). Code and tests = Sonnet agents.
Code review = Opus agent (one tier above Sonnet). Redteam and acceptance =
Fable. Each writing agent works in its own git worktree; read-only agents read
`HEAD` of `feature/live-dictation`.

Run tests as `.venv/bin/python tools/<name>.py -v`.

## Lanes and order

| Group | Runs with | Waits on | Owner | Files owned |
|---|---|---|---|---|
| 1 Baseline and contract | - | - | orchestrator | `core/protocol.py`, `core/server/schema.py`, `openspec/` |
| 2 Unit test plan audit | - | 1 | Fable redteam (with requirements and design) | none (writes `adversarial-*.md`) |
| 3A Server tests | 3B, 3C, 3D | 2 | Sonnet | `tools/test_live_preview.py`, `tools/test_live_pipeline.py`, `tools/test_live_e2e.py` |
| 3B Server code | 3A, 3C, 3D | 2 | Sonnet | `core/server/worker/live_preview.py` (new), `core/server/worker/qwen_mlx_runner_pipeline.py`, `core/server/worker/work_handler.py`, `core/server/connection/ws_recv.py`, `core/server/connection/ws_send.py` |
| 3C Client tests | 3A, 3B, 3D | 2 | Sonnet | `tools/test_live_client.py` |
| 3D Client code | 3A, 3B, 3C | 2 | Sonnet | `config_client.py`, `core/client/audio/recorder.py`, `core/client/output/result_processor.py`, `core/client/output/live_panel.py` (new) |
| 4 Merge and validate | - | 3A-3D | orchestrator | merge commits; fixes go back to the lane's author |
| 5A Code review | 5B, 5C, 5D | 4 | Opus, read-only | none |
| 5B Simplify | 5A, 5C, 5D | 4 | Sonnet, read-only, reports | none until 6 |
| 5C Mutations | 5A, 5B, 5D | 4 | orchestrator, verification worktree | `openspec/changes/add-live-dictation-mode/mutations.toml` |
| 5D Docs | 5A, 5B, 5C | 4 | Sonnet | `readme.md`, `CLAUDE.md` |
| 6 Apply findings | - | 5A-5D | lane authors | the files each finding names |
| 7 Verify and clean | - | 6 | orchestrator | none |
| 8 Acceptance review | - | 7 | Fable, fresh context | `acceptance-*.md` |

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

- [x] 1.1 Run every `tools/test_*.py` on `feature/live-dictation` and record the pass counts here. At 33eba19: annotation 8/8, editor_result_flow 16/16, editor_ui_contract PASS, mic_shortcut_lifecycle 9 OK, stream_stop_leak 14 OK, worker_scheduling 10 OK.
- [x] 1.2 Add the contract fields with Chinese comments: `AudioMessage.live`, `RecognitionMessage.preview` and `text_tentative` (read with `.get` in `from_dict`), `Work.live`, `Result.preview` and `text_tentative`. All default to the hold values.
- [x] 1.3 Rerun 1.1; the counts must not change. Commit the openspec change and the contract.

## 2. Unit test plan

Behaviours (B), their tests, and the production entry test. A production entry
test runs from the real entry point without replacing a real dependency.

| B | Behaviour | Tests | Production entry |
|---|---|---|---|
| B1 | Default hold: recorder sends `live=False`, server runs no pass, no preview message, final unchanged | `test_live_client::test_recorder_default_sends_hold`, `test_live_pipeline::test_hold_task_never_runs_a_pass` | `test_live_e2e::test_hold_run_sends_no_preview` |
| B2 | Unknown `dictation_mode` means hold | `test_live_client::test_recorder_unknown_mode_sends_hold` | `test_live_client::test_recorder_unknown_mode_sends_hold` (real recorder loop, real `WebSocketManager`, local capture server on 127.0.0.1) |
| B3 | Live mode tags every audio message | `test_live_client::test_recorder_live_mode_tags_messages` | same test (real recorder loop and socket, as B2) |
| B4 | Server runs a pass per 1 s of new audio, first at 1 s, none without new audio | `test_live_pipeline::test_pass_cadence_follows_audio_time` | `test_live_e2e::test_live_run_streams_previews` |
| B5 | Preview message carries committed and tentative text and reaches the client | `test_live_pipeline::test_preview_result_fields` | `test_live_e2e::test_live_run_streams_previews` (real `ws_recv`, `ws_send`, `WorkHandler.loop`, engine, socket) |
| B6 | Commit rule (three passes, holdback 4, numeral hold, content alignment) | `test_live_preview::test_tail_word_not_committed_early`, `::test_open_numeral_run_waits`, `::test_insertion_does_not_duplicate_tail`, `::test_trailing_punctuation_hidden`, `::test_commits_on_third_agreeing_pass` | `test_live_e2e::test_live_run_streams_previews` (committed text of each preview extends the previous one) |
| B7 | Final equals the hold-mode final; no preview after the final | `test_live_pipeline::test_final_pops_live_task` | `test_live_e2e::test_live_final_matches_hold` |
| B8 | Final waits for at most the running pass; no pass while a final is buffered | `test_live_pipeline::test_final_is_not_queued_behind_passes` | Declared gap: the order cannot be forced through a real socket without timing. Covered by the real `WorkHandler.loop` and real pipeline with a scripted engine and a controlled queue. |
| B9 | Long segment: pass covers the audio after the last freeze; freeze keeps agreed committed text; waits below 25 s when the head disagrees; forced freeze at 25 s replaces | `test_live_preview::test_freeze_keeps_agreed_committed`, `::test_freeze_waits_when_head_disagrees`, `::test_forced_freeze_replaces_head`, `::test_pass_audio_is_bounded` | `test_live_e2e::test_long_live_run_keeps_up` (30 s TTS clip; previews keep coming, final matches hold) |
| B10 | Partial text is not logged or printed, on server and client | `test_live_pipeline::test_preview_is_not_logged`, `test_live_client::test_preview_is_not_logged` (real `ResultProcessor`, `client` logger captured at DEBUG) | `test_live_e2e::test_live_run_streams_previews` (captures the `server` logger at DEBUG and stdout; none before the final contains preview text) |
| B11 | A failing pass skips the update and uses up its slot; final still works; error logged without text | `test_live_pipeline::test_failing_pass_does_not_break_final` | Declared gap: a model failure needs an injected fault. |
| B12 | Client shows preview in a non-activating panel (committed normal, tentative grey), hides on final, auto-hides after 5 s | `test_live_client::test_panel_is_non_activating`, `::test_panel_colours`, `::test_final_hides_panel`, `::test_panel_auto_hides` | `test_live_client::test_preview_message_updates_real_panel` (real JSON from the server's `RecognitionMessage.to_json`, real `from_dict`, real `ResultProcessor._handle_message`, real `live_panel` NSPanel, main run loop pumped) |
| B13 | Disconnect drops the live task | `test_live_pipeline::test_cleanup_drops_live_task` | Declared gap: needs a socket drop mid-recording; covered by the real `WorkHandler.cleanup` path with a controlled socket list. |

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
  `WebSocketManager` for the recorder tests.

- [x] 2.1 Fable redteam audits requirements, design and this plan in one round; findings in `adversarial-*.md`; orchestrator answers each and updates the artifacts.

## 3. Generate tests and implement (four lanes in parallel)

- [ ] 3A.1 Write `tools/test_live_preview.py` and `tools/test_live_pipeline.py` (B1, B4-B11, B13) against the API in `design.md`.
- [ ] 3A.2 Write `tools/test_live_e2e.py` (B1, B4-B7, B9, B10).
- [ ] 3A.3 Validate: run the new tests on the group 1 commit; each must fail (import error for the new module counts), and record the failure lines.
- [ ] 3B.1 Implement `live_preview.py` by porting the eval's `M3-1.0-a3-w15` path (no flags) from `~/code/open-source/capswriter-ab/stream_eval/run_eval.py`.
- [ ] 3B.2 Implement D2, D4, D6 and D7 in the pipeline, work handler, `ws_recv` and `ws_send`.
- [ ] 3C.1 Write `tools/test_live_client.py` (B1-B3, B12) against the API in `design.md`.
- [ ] 3C.2 Validate: run it on the group 1 commit; each case must fail; record the failure lines.
- [ ] 3D.1 Add `dictation_mode = 'hold'` to `config_client.py` with a Chinese comment; set `live` in the recorder's three `AudioMessage` calls.
- [ ] 3D.2 Implement `live_panel.py` (D8) and the `result_processor` branch (D9).

## 4. Merge and validate

- [ ] 4.1 Merge 3A-3D into `feature/live-dictation`.
- [ ] 4.2 Run all new tests and all existing `tools/test_*.py`. A mismatch between a test and the code goes back to the lane that is wrong by the spec, not to whichever is easier to change.

## 5. Review, simplify, mutations, docs (parallel)

- [ ] 5A Opus code review of the diff against `spec.md` and `design.md`: correctness, privacy (no partial text in logs), focus behaviour, hold mode unchanged, and the KISS / Ponytail audit checklist (every line serves a scenario, no one-caller abstraction, no new knob, no impossible-case branch, no touched line outside the task, hold path does no extra work).
- [ ] 5B Simplify pass over the whole diff (the five checks in the user's rules plus the KISS / Ponytail checklist); report the line reduction.
- [ ] 5C Write `mutations.toml` with one row per new production call site (list below) and run `python3 ~/.claude/tools/mutate.py openspec/changes/add-live-dictation-mode/mutations.toml` in the verification worktree after `python3 ~/.claude/tools/test_mutate.py` reports 8/8.
- [ ] 5D Update `readme.md` (the setting, what live mode shows, GPU cost, restart needed) and `CLAUDE.md` (the "流式识别策略" decision row and the task list).

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
- `live_preview`: `AGREE`, `HOLDBACK`, `WINDOW`, `FORCE`, the pause ratio, the consistency check

## 6. Apply findings

- [ ] 6.1 Apply accepted findings from 5A and 5B; rerun only the tests the fixes touch, plus the mutation rows on touched call sites.

## 7. Verify and clean

- [ ] 7.1 All `tools/test_*.py` pass; `test_live_e2e.py` passes; every `mutations.toml` row is CAUGHT; `openspec validate add-live-dictation-mode` passes.
- [ ] 7.2 `git status` shows no stray files; commit on `feature/live-dictation`; no push.

## 8. Acceptance review

- [ ] 8.1 Fable acceptance in a fresh subagent with paths and commands only (`opsx:accept`).

## Acceptance

Items for the user in the running app. Never ticked by an agent.

- [ ] A1 With `dictation_mode = 'live'` and `capswriter restart`, hold Caps Lock in a text field and speak naturally, with fillers and self-corrections: the panel shows text within about 2 s of the first word and updates while speaking; the text field keeps focus and its caret.
- [ ] A2 On release in live mode, the pasted text is the final text and the panel closes.
- [ ] A3 With the default `'hold'`, dictation looks and behaves as before (no panel).
- [ ] A4 A dictation of about one minute in live mode keeps updating to the end.
