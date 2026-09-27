# Acceptance rounds 4 and 5 (Opus delta reviews after the first real-app check)

These two reports are kept verbatim for reference. `acceptance.md` holds
rounds 1-3 with the user's sign-off; the user chose to archive before round 5
returned. Round 4 (e586500..67efc8b) found FAIL on questions 1, 3 and 4; the
fixes are tasks.md group 9. Round 5 (67efc8b..ca19ece) found no FAIL and left
the Acceptance items to the user; its four non-blocking findings are task 9.8.

---

# Acceptance review, delta round 4: add-live-dictation-mode

- Change: `add-live-dictation-mode`
- Git range: `e586500..67efc8b` (delta round; previous report: `git show e586500:openspec/changes/add-live-dictation-mode/acceptance.md`, round 3, final line `Verdict: NEEDS-HUMAN`)
- Review tree: `/Users/qingyun.yuan/code/open-source/CapsWriter-wt/panel-style`, detached at `67efc8b`
- Date: 2026-09-27
- Reviewer: one fresh reviewer, no history with this work
- Interpreter: `/Users/qingyun.yuan/code/open-source/CapsWriter-for-macOS/.venv/bin/python` (`<py>` below), `PYTHONDONTWRITEBYTECODE=1` on every run; no `__pycache__` in the tree before or after

## What the delta contains

`git diff --stat e586500..67efc8b`: 11 files.

- Production (2 files, +22/-6):
  - `core/client/output/live_panel.py`: tentative text in `systemBlueColor` with `NSUnderlineStyleSingle` (was `secondaryLabelColor`); panel height capped at `edit_panel._MAX_SCREEN_RATIO`; label keeps full height, anchored at the bottom.
  - `core/server/worker/live_preview.py`: new `_join(a, b)` puts one space between two ASCII letters/digits where committed text and a new piece meet; used at the two concatenation sites in `Agreement.update`.
- Tests: `tools/test_live_client.py` (colour/underline asserts, new `test_panel_height_is_capped_for_long_text`), `tools/test_live_preview.py` (new `test_glued_latin_words_across_passes_get_a_space`).
- Docs: `readme.md`, `proposal.md`, `design.md` (D8), `specs/live-dictation/spec.md`, `mutations.toml` (+4 rows, 2 rows edited; 46 rows now), `tasks.md` (A1-A4 ticked, 8.1 note edited, tables realigned), `acceptance.md` (round-3 verdicts edited).

## Commands this round ran

```
cd /Users/qingyun.yuan/code/open-source/CapsWriter-wt/panel-style
git status; git log --oneline -5; git diff --stat e586500..67efc8b
git diff e586500..67efc8b -- core readme.md tools openspec/.../{design,proposal}.md openspec/.../specs openspec/.../mutations.toml
git diff --word-diff=plain e586500..67efc8b -- openspec/.../tasks.md        # semantic changes only
git diff --word-diff=plain e586500..67efc8b -- openspec/.../acceptance.md
git log --format='%h %an %ad %s %b' e586500..67efc8b; git log --graph e586500^..67efc8b
git reflog show --date=iso feature/live-dictation | head -12
git reflog show --date=iso origin/feature/live-dictation | head -5; git remote -v; git worktree list
git show e586500:openspec/.../acceptance.md | tail -30 ; sed -n 278,297p of the same
cat proposal.md design.md specs/live-dictation/spec.md tasks.md
cat -n core/client/output/live_panel.py core/server/worker/live_preview.py
sed -n 118,166p core/server/worker/qwen_mlx_runner_pipeline.py; sed -n 25,75p core/server/connection/ws_send.py
grep -n text_tentative|preview core/protocol.py core/client/output/result_processor.py core/server/schema.py
sed -n 355,385p core/client/output/edit_panel.py; sed -n 215,245p core/client/output/result_processor.py
git grep -nE "(^|[^.A-Za-z])_join\(" -- '*.py'; git grep -n _MAX_SCREEN_RATIO -- '*.py'
grep of tools/test_live_{client,preview,pipeline,e2e}.py for entry calls and Latin text
openspec validate add-live-dictation-mode                   # "Change 'add-live-dictation-mode' is valid"
python3 ~/.claude/tools/test_mutate.py                      # "mutate canary: 8/8 passed"
# whole suite, run 1 of 2 (baseline) and run 2 of 2 (end): every tools/test_*.py -v; e2e with HF_HUB_OFFLINE=1
# previous behaviour: git archive e586500 core tools config_*.py -> scratchpad/prev, HEAD test files copied in, narrow tests run there
python3 ~/.claude/tools/mutate.py scratchpad/accept-r4/delta-rows.toml          # the 6 rows the delta adds or edits, narrowest test each
python3 ~/.claude/tools/mutate.py scratchpad/accept-r4/touched-file-rows.toml   # the other 16 rows on the two touched files
python3 scratchpad/accept-r4/hand_mutate.py                 # 7 hand mutations H1-H7, each restored and sha256-checked
<py> - (read-only probe: show the long text, print panel height, cap and label frame, hide)
```

---

## 1. Entry points

The delta adds no new entry point. It changes behaviour behind two existing ones.

| # | Entry point | What the delta changes there | Test that enters through it | Proof (grep / run) | Row verdict |
|---|---|---|---|---|---|
| E-a | Client event handler `ResultProcessor._handle_message` preview branch (`result_processor.py:224-227`) -> `live_panel.show` -> `_show_on_main` | Tentative text blue + single underline; committed text unchanged (`live_panel.py:106-113`) | `test_live_client.py::LivePanelTests::test_preview_message_updates_real_panel` | `:356` `RecognitionMessage(...).to_json()`, `:357` `from_dict`, `:360` `await processor._handle_message(message)`; real `NSPanel`; asserts `:381-384`. Fakes on path: `_FakeState`, `_FakeHotword`, `_emit_text` (declared in tasks.md; the preview branch returns before any of them). Call-site mutation H1 CAUGHT | PASS |
| E-b | Same handler -> `live_panel.show` | Height cap and bottom anchoring (`live_panel.py:128`, `:132`) | `test_live_client.py::LivePanelTests::test_panel_height_is_capped_for_long_text` | `:429` `self.live_panel.show(long_text, '')`; real panel, real `NSScreen`. It enters one call below `_handle_message`; that one forward is pinned by E-a's test (H1 CAUGHT). Not listed in tasks.md B12 | PASS (note) |
| E-c | Server background worker `WorkHandler.loop` -> `QwenMLXRunnerPipeline.live_tick` (`qwen_mlx_runner_pipeline.py:118-159`) -> `LiveTask.step` (`live_preview.py:133-147`) -> `Agreement.update` | `_join` at `live_preview.py:101` (committed) and `:109` (shown) | None for the new behaviour. The only test of it is `test_live_preview.py::AgreementTests::test_glued_latin_words_across_passes_get_a_space`, which calls `Agreement.update` directly (`:99-113`). Tests that do enter the worker: `test_live_e2e.py` live clips are Chinese only (`:241`, `:297`, `:326`; the one Latin clip `:227` is hold mode); `test_live_pipeline.py` uses the scripted model and has no Latin text (grep) | H2 and H3 MISSED (see question 2): no test that runs through `step` / `live_tick` can see the space. tasks.md B6 row still names only the old tests and `test_live_run_streams_previews`; no gap is declared for the new scenario | FAIL |

No CLI path, no new handler, no new worker.

Verdict for question 1: **FAIL**. The Latin-spacing behaviour has no test that enters through the worker (or the pipeline), and tasks.md does not declare the gap. The panel changes do have real-entry tests.

---

## 2. Fails before

Method:

- Previous behaviour: `git archive e586500` of `core`, `tools`, `config_*.py` into `scratchpad/accept-r4/prev`, HEAD's two test files copied in, narrow tests run there. Nothing in the repo changed.
- Mutations: the 6 toml rows the delta adds or edits, each with its narrowest named test; the other 16 toml rows on the two touched files (the files changed, so their rows were re-run), file-level tests; 7 hand mutations, 3 at production call sites outside the function under test (H1 client, H2 and H3 server).

Previous-commit run (e586500 code, HEAD tests):

```
FAIL: test_glued_latin_words_across_passes_get_a_space
AssertionError: 'dessert you know' not found in '我们聊到了dessertyou know 好吃吗还不错'
FAIL: test_preview_message_updates_real_panel
AssertionError: Catalog color: System secondaryLabelColor != Catalog color: System systemBlueColor
FAIL: test_utf16_color_ranges_across_surrogate_pair
AssertionError: Catalog color: System secondaryLabelColor != Catalog color: System systemBlueColor : "尾"应是暂定色
ERROR: test_panel_height_is_capped_for_long_text
AttributeError: module 'core.client.output.live_panel' has no attribute '_MAX_SCREEN_RATIO'
```

The cap test errors instead of failing an assertion (a changed module), so its proof is by mutation below.

Toml rows the delta adds or edits (`delta-rows.toml`, verbatim `old`/`new`, each found exactly once):

```
CAUGHT   committed text drawn blue
CAUGHT   committed Latin words are glued
CAUGHT   shown Latin words are glued
CAUGHT   panel height is not capped
CAUGHT   tentative text drawn in the normal colour
CAUGHT   tentative text has no underline
RESULT mutate caught=6 missed=0 skipped=0 errors=0
```

Other rows on the touched files (`touched-file-rows.toml`: rows 23-29, 30-36, 39-41 of `mutations.toml`): `RESULT mutate caught=16 missed=0 skipped=0 errors=0`. All 46 rows still match their file exactly once (checked by script).

Hand mutations (`hand_mutate.py`; each restored, `restored=True`):

| Id | File:site | Mutation | Test run | Result |
|---|---|---|---|---|
| H1 | `result_processor.py:226` (call site of `live_panel.show`) | `show(message.text, message.text_tentative)` -> `show(message.text + message.text_tentative, '')` | `test_preview_message_updates_real_panel` | CAUGHT: `Catalog color: System labelColor != Catalog color: System systemBlueColor` |
| H2 | `live_preview.py:147` (`LiveTask.step`, call site of `Agreement.update`) | `shown[len(committed):]` -> `shown[len(committed):].lstrip()` | `test_live_preview.py` + `test_live_pipeline.py` (files) | **MISSED**: `Ran 7 ... OK`, `Ran 13 ... OK` |
| H3 | `qwen_mlx_runner_pipeline.py:157` (`live_tick` Result) | `text_tentative=tentative,` -> `text_tentative=tentative.lstrip(),` | `test_live_pipeline.py` (file) | **MISSED**: `Ran 13 ... OK` |
| H4 | `live_panel.py:108` | committed text also underlined | `test_preview_message_updates_real_panel` | CAUGHT: `1 is not false : 已提交文本不应有下划线` |
| H5 | `live_panel.py:128` | `min(text_h + 2*_MARGIN, cap)` -> `min(text_h, cap) + 2*_MARGIN` (20 pt over the cap) | `test_panel_height_is_capped_for_long_text` | **MISSED**: `Ran 1 ... OK` (bound is loose, see question 5) |
| H6 | `live_panel.py:132` | label anchored at the top (`y = content_h - _MARGIN - text_h`) | same | CAUGHT: `-2272.2 != 10 within 0.5 delta ... label 必须仍贴底摆放` |
| H7 | `live_panel.py:128` | `* _MAX_SCREEN_RATIO` -> `* 0.9` | same | CAUGHT: `767.0 not less than or equal to 361.3 : 面板高度必须封顶` |

Scenario table (requirement text and scenarios the delta adds or changes):

| Spec text | Test that pins it | Fails before | Row verdict |
|---|---|---|---|
| Live preview: "tentative text in the system blue colour with an underline" (committed in the normal colour) | `test_preview_message_updates_real_panel`, `test_utf16_color_ranges_across_surrogate_pair` | Previous commit: both FAIL on the colour. Rows "tentative text drawn in the normal colour", "tentative text has no underline", "committed text drawn blue" CAUGHT; H1 (call site) and H4 CAUGHT | PASS |
| Live preview: "When the text is taller than 40 % of the visible screen height, the panel SHALL stop growing and show the newest lines" | `test_panel_height_is_capped_for_long_text` | Previous commit: ERROR (no attribute). Row "panel height is not capped" CAUGHT; H6, H7 CAUGHT; H5 MISSED (a 20 pt overshoot passes) | PASS, with note |
| Commit rule: space between two ASCII letters/digits; scenario "Latin words from different passes do not glue together" | `test_glued_latin_words_across_passes_get_a_space` | Previous commit: FAIL (`dessertyou`). Rows "committed Latin words are glued", "shown Latin words are glued" (the two new call sites) CAUGHT. H2, H3 MISSED: past `Agreement.update` the space is not pinned (question 1 and 3) | PASS for the gate (every new call site caught), with note |

Earlier sections whose evidence the delta touches: round 1/3 question 2 rows on `live_panel.py` and `live_preview.py` (rows 23-44), re-run here, 22/22 CAUGHT; the round-3 B12 production-entry row (its colour assertion changed from grey to blue).

Verdict for question 2: **PASS**. Every added or changed requirement and scenario has a test that fails on the previous behaviour, and every new call site's toml row is CAUGHT. Notes: H2 and H3 MISSED (belongs to questions 1 and 3); H5 MISSED (loose bound, question 5).

---

## 3. Real versus simulated

Bypasses the delta's tests add or rely on:

| # | Where | What is bypassed | Covered elsewhere? |
|---|---|---|---|
| 1 | `test_panel_height_is_capped_for_long_text` calls `live_panel.show()` directly | `ResultProcessor._handle_message` and the protocol round trip | Yes: `test_preview_message_updates_real_panel` enters through `_handle_message`; H1 CAUGHT |
| 2 | Same test takes its expected ratio from `live_panel._MAX_SCREEN_RATIO` (the production constant) | The spec value "40 %" | Partly: the call site is pinned (H7 CAUGHT). The value 0.4 itself is pinned by no test (`git grep _MAX_SCREEN_RATIO tools/` finds only this test). NOTE: an edit of the shared constant for the editor panel (`edit_panel.py:57`) would move the live cap too, and no test would fail |
| 3 | All panel tests pump the main run loop on the test thread (`_pump_main_runloop`) | Production calls `show()` from the asyncio thread; `callAfter` hops to the NSApp run loop | Pre-existing (round 1 row 17). Covered only by the user's A1 in the running app, which was done on e586500 code (question 4). The delta does not change the dispatch |
| 4 | `test_glued_latin_words_across_passes_get_a_space` calls `Agreement.update` directly with scripted text | `LiveTask.step` split (`shown[len(committed):]`, so the tentative part now starts with the space), `live_tick` Result copy, `ws_send` copy, `RecognitionMessage.from_dict`, panel concatenation | **No.** By source reading nothing on that path strips text today (`qwen_mlx_runner_pipeline.py:141-158`, `ws_send.py:31-44`, `protocol.py:128-129`, `result_processor.py:224-227`, `live_panel.py:106-113`), so the code is correct now. But no test covers it: H2 and H3 MISSED |
| 5 | Real engine in live mode with Latin words | The model's real mixed-language output across passes | No: the e2e live clips are Chinese only. Not declared in tasks.md |
| 6 | `_new_result_processor` (`_FakeState`, `_FakeHotword`, `_emit_text` AsyncMock) | Output side | Declared in tasks.md; unchanged by the delta |

Earlier sections the delta touches: round-3 question 3 rows 6 and 17 (worker process boundary, cross-thread dispatch) were closed by the user's A1-A4; that check ran on the code before this delta.

Verdict for question 3: **FAIL**. Bypass 4 is not covered: a change in `step` or `live_tick` that drops the leading space of the tentative text would bring back "dessertyou" on screen and every test would pass. This is the same gap as question 1; one pipeline-level test fixes both (see Findings).

---

## 4. Open items

Commands: `grep -n '^- \[ \]' tasks.md` (none), word diff of tasks.md and acceptance.md, reflog of the branch and of `origin/feature/live-dictation`.

| Item | State | Evidence |
|---|---|---|
| A1-A4 | `[X]` | Ticked in `a8757c7`. Its message says the user ticked them; the file-wide `[x]` -> `[X]` and table realignment fit an editor re-save. I cannot check a person's action; this is the user's own claim. Timeline (reflog): `e586500` 15:25:41 -> `a8757c7` 15:45:57 "real-app acceptance and **post-acceptance** tweaks" -> code merges 15:45:57 and 15:51:39 -> `67efc8b` 15:56:47. So A1-A4 were checked on e586500 code. The blue/underline text, the height cap and the Latin spacing were never in the app when the user checked, and no Acceptance item covers them |
| 8.1 | `[X]`, note "round 3 Opus at d3217e8: `Verdict: PASS`" | **Claim is false.** `git show e586500:.../acceptance.md | tail -1` -> `Verdict: NEEDS-HUMAN`. Commit `67efc8b` changed round 3's rows 3 and 4 and its final line to PASS with no new review, and left the reviewer's own words in those rows, which still say "still covered only by the user's Acceptance A1-A4" and "A1-A4 plus the F4 quality judgement are open". The round-3 table no longer reads as the reviewer wrote it |
| F4 quality decision (round 3, "What the user must still verify" item 5) | No record | Nothing in the range records the user's decision on the measured preview quality |
| Stale figures and text after the delta | Open (docs) | tasks.md B12 row: "tentative grey"; B6 row does not list the Latin test; 5C: "42 rows" (toml has 46); 7.1: "live_client 13, live_preview 6, mutations 42/42" (now 14, 7, 46 rows; no record anywhere that the 4 new rows were run before hand-off); "Call sites to mutate" lacks `_join` and the cap. `CLAUDE.md:3-10`: "尚未推送", "真机验收（A1–A4）等待用户确认", "live_preview 6 项 … live_client 13 项 … 42/42" |
| Push | Note | `origin/feature/live-dictation` (`git@github.com:YuanQY/CapsWriter-for-macOS.git`) was updated "by push" to `67efc8b` at 15:56:51. Task 7.2 says "no push"; CLAUDE.md says not pushed |

What the user must still verify (plain words):

1. With `dictation_mode = 'live'`, run `capswriter restart` so the app runs the current code (67efc8b). Speak. Words that may still change must be blue and underlined. Settled words must be in the normal text colour. Check that both are easy to read, in light and in dark mode.
2. Dictate long enough that the panel reaches about 40 % of the screen height (one to two minutes). The panel must stop growing. The newest words must stay visible at the bottom.
3. Say a Chinese sentence with an English phrase and a short pause, for example "我们聊到了 dessert, you know, 还不错". The panel must never show two English words stuck together, such as "dessertyou".
4. Re-run A1 and A4 on this code. Your earlier A1-A4 check ran on the code before these changes.
5. Say whether the preview quality is acceptable (F4: about 1.4 % wrong committed text and about 3 s commit lag on your voice). No record of that decision exists.
6. Confirm that the push to origin was intended (task 7.2 says no push).

Verdict for question 4: **FAIL**. A checked task (8.1) states a verdict the round-3 reviewer did not give, and the round-3 report was edited in place. Items 1-6 above are also waiting for the user (NEEDS-HUMAN).

---

## 5. Scope, tolerances and design drift

Files, config, dependencies, ignore rules:

- All 11 files sit in lane ownership in tasks.md: `live_panel.py` (3D), `live_preview.py` (3B), `test_live_client.py` (3C), `test_live_preview.py` (3A), `readme.md` (5D), `openspec/...` (group 1).
- No change to `config_*.py`, `requirements*.txt`, `.gitignore`, `.gitmodules` or the submodule (`git diff --stat`).
- Note: no task in tasks.md names this work. The behaviour is declared in `spec.md`, `design.md` D8 and `proposal.md` (commit `a8757c7`), not in tasks.md.

Tolerances and expected values (`git diff e586500..67efc8b -- tools | grep '^-'` lists only the old colour lines and docstrings; no timeout, threshold or e2e bound changed):

| Where | Before | After | Judgement |
|---|---|---|---|
| `test_live_client.py:382`, `:480`, `:482` tentative colour expected | `NSColor.secondaryLabelColor()` | `NSColor.systemBlueColor()` | Expected value changed with the spec (a8757c7). Declared. Plus 5 new underline asserts (tighter) |
| `mutations.toml` row "committed text drawn grey" | `new` = `secondaryLabelColor` | renamed "committed text drawn blue", `new` = `systemBlueColor` | Follows the new tentative colour. Not loosened. CAUGHT |
| `mutations.toml` row "tentative text drawn in the normal colour" | `old` = the grey line | `old` = the blue line | Follows the code. CAUGHT |
| New: `test_live_client.py:438` cap bound | - | `panel height <= cap + 2 * margin + 0.5` | NOTE. The docstring (`:422`) says "留浮点容差" (float tolerance only). Measured by probe: panel 341.0 pt, cap 340.8 pt, bound 361.3 pt, so the bound is 20 pt looser than needed. Cost: H5 (a panel 20 pt over the 40 % cap) passes. A bound near `cap + 1` would catch it |

(a) Design decisions:

- D8, as updated in this range: "tentative text in `systemBlueColor` with a single underline" -> `live_panel.py:111-113`; "capped at the editor panel's `_MAX_SCREEN_RATIO` (40 %)" -> `:34` import (reuse), `:128`; "the label keeps its full height anchored at the bottom" -> `:132`; clipping by `setMasksToBounds_(True)` at `:78`, `:87`. Same content-height meaning as `edit_panel.py:366-377` (content, margins included, at most 40 %). Matches.
- D5: "It imports `re` and `difflib` (and numpy for the audio chunks) only" still holds. D5's function list does not name `_join`; the spec's Commit rule now requires the space. The docstring says `_join` is ported from the eval harness's `join()`; I did not verify this (outside the review tree). No departure from a stated decision.
- D1-D4, D6, D7, D9: no delta line touches them. Carried from round 3.

(b) Abstractions the delta adds:

| Name | Callers (`git grep`) | Verdict |
|---|---|---|
| `_join(a, b)` (`live_preview.py:50`) | 2: `live_preview.py:101`, `:109` | OK |
| `_MAX_SCREEN_RATIO` | Existing constant, reused as D8 says; production users now `edit_panel.py:366`, `live_panel.py:128` | OK (reuse) |
| `underline_at` (test-local helper) | 3 uses in its test | OK |

No new module, config key or class.

Earlier sections the delta touches: round-3 question 5 D8 row ("labelColor/secondaryLabelColor") is superseded by the new D8 text, which the code matches.

Verdict for question 5: **PASS**. No undeclared file, dependency, config or ignore change; no existing tolerance loosened; code matches D8 as updated. Notes: the work is not a task in tasks.md; the new cap bound is looser than its docstring says.

---

## Test runs (commands tasks.md names)

`openspec validate add-live-dictation-mode`: "Change 'add-live-dictation-mode' is valid".

| File | Run 1 (baseline) | Run 2 (end) |
|---|---|---|
| test_editor_annotation | rc 0, 8 PASS, 0 FAIL | rc 0, 8 PASS, 0 FAIL |
| test_editor_result_flow | rc 0, 16 PASS, 0 FAIL | rc 0, 16 PASS, 0 FAIL |
| test_editor_ui_contract | `PASS: editor UI contract` | `PASS: editor UI contract` |
| test_live_client | Ran 14, OK | Ran 14, OK |
| test_live_e2e (real model, `HF_HUB_OFFLINE=1`) | Ran 4 in 62.6 s, OK (no skip) | Ran 4 in 62.3 s, OK (no skip) |
| test_live_pipeline | Ran 13, OK | Ran 13, OK |
| test_live_preview | Ran 7, OK | Ran 7, OK |
| test_mic_shortcut_lifecycle | Ran 9, OK | Ran 9, OK |
| test_mlx_model_resolution | Ran 4, OK | Ran 4, OK |
| test_stream_stop_leak | Ran 14, OK | Ran 14, OK |
| test_worker_scheduling | Ran 10, OK | Ran 10, OK |

Totals per run: 75 unittest cases + 24 editor script cases + the UI contract check, 0 failures. Mutations run this round: 22 toml rows (6 delta + 16 on touched files), 22 CAUGHT; 7 hand mutations, 4 CAUGHT, 3 MISSED (H2, H3, H5). The e2e writes to the worktree's ignored `logs/` by design; I did not open it. `git status --porcelain` was empty after every mutation run and at the end.

## Findings and smallest fixes

1. (Q1, Q3) Latin spacing is pinned only inside `Agreement.update`. Fix: one test in `tools/test_live_pipeline.py` that feeds the "dessert" passes through the real `WorkHandler.loop` / `live_tick` with the declared scripted model and asserts `result.text + result.text_tentative` contains "dessert you"; add H2 and H3 as toml rows; in tasks.md B6, declare that the real-engine entry for this scenario is a gap and why (TTS cannot make the model drop a comma on demand).
2. (Q4) Restore round 3's rows and final line as the reviewer wrote them (`git show e586500:.../acceptance.md`), record the user's A1-A4 sign-off as its own dated line, and correct the 8.1 note.
3. (Q4) Add Acceptance items for the new visuals (user items 1-3 above), or have the user re-run A1 and A4 on 67efc8b.
4. (Q4, docs) Update tasks.md B12 ("grey"), B6, 5C, 7.1 and the call-site list, and CLAUDE.md:3-10, or point them to the tool output instead of copying numbers.
5. (Q5, note) Tighten the cap bound in `test_panel_height_is_capped_for_long_text` to about `cap + 1` so H5 fails.

## Summary table

| Question | Verdict | One line |
|---|---|---|
| 1. Entry points | FAIL | Panel colour/underline enters through the real `_handle_message` and the cap through the real `show()`, but the Latin-spacing change has no test through the worker or pipeline and tasks.md declares no gap. |
| 2. Fails before | PASS | All three changed spec items fail on e586500 code or under their toml rows (6/6 delta rows and 16/16 other rows on touched files CAUGHT; call-site H1 CAUGHT); notes: H2/H3 (space dropped after `Agreement.update`) and H5 (20 pt over the cap) MISSED. |
| 3. Real versus simulated | FAIL | The Latin test calls `Agreement.update` directly; nothing covers the space surviving `step`, `live_tick` and transport (H2, H3 MISSED), and the e2e live clips are Chinese only. |
| 4. Open items | FAIL | 8.1 claims round 3 gave PASS, but that reviewer wrote NEEDS-HUMAN and 67efc8b edited the report; the user's A1-A4 ran on pre-delta code, so the new visuals, the cap, Latin spacing, F4 and the push still wait for the user. |
| 5. Scope, tolerances and design drift | PASS | Only lane-owned files, no config/dependency/ignore change, no existing tolerance loosened, code matches D8 as updated; notes: the work is not a task in tasks.md, and the new cap bound is 20 pt looser than its docstring says. |

Verdict: FAIL

---

# Acceptance review, delta round 5: add-live-dictation-mode

- Change: `add-live-dictation-mode`
- Git range: `67efc8b..ca19ece` (delta round; previous report: `scratchpad/accept-r4/delta.md`, round 4 over `e586500..67efc8b`, final line `Verdict: FAIL`)
- Review tree: `/Users/qingyun.yuan/code/open-source/CapsWriter-wt/panel-style`, detached at `ca19ece`, clean before and after
- Date: 2026-09-27
- Reviewer: one fresh reviewer, no history with this work
- Interpreter: `/Users/qingyun.yuan/code/open-source/CapsWriter-for-macOS/.venv/bin/python` (`<py>` below), `PYTHONDONTWRITEBYTECODE=1` on every run; no `__pycache__` in the tree after the runs

## What the delta contains

`git diff --stat 67efc8b..ca19ece`: 13 files, +364/-199. Commits: `3af0dea` (spec, design, evidence, tasks, acceptance restore, docs), `6c9b5e9` (code and tests, Sonnet lane), `5b79557` (merge), `ca19ece` (tasks: declared expected values).

- Production (1 file, +8/-1): `core/server/worker/live_preview.py`. New pause branch in `Agreement.update` (`:95-100`): when the last `AGREE` tails are equal, `limit = len(tail_keys)` minus trailing punctuation, so `HOLDBACK` does not apply. Docstring updated.
- Tests:
  - `tools/test_live_preview.py`: 3 new tests (`test_pause_commits_the_tail`, `test_numeral_at_a_pause_still_waits`, `test_speech_after_a_pause_loses_nothing`); expected values changed in 2 tests.
  - `tools/test_live_pipeline.py`: 2 new tests (`test_latin_word_spacing_through_the_production_path`, `test_pause_through_the_production_path_commits_the_tail`).
  - `tools/test_live_e2e.py`: 1 new test (`test_pause_after_speech_leaves_no_tentative_text`).
  - `tools/test_live_client.py`: cap bound tightened.
- Docs: `spec.md` (pause sentence, 2 new scenarios, 1 scenario changed), `design.md` (D5), `evidence.md` ("Pause rule"), `mutations.toml` (+5 rows, 51 now), `tasks.md` (group 9, A1/A4 reopened, A5-A9 added, pointers instead of copied figures), `acceptance.md` (restored to the round-3 text), `readme.md`, `CLAUDE.md`.

## Commands this round ran

```
cd /Users/qingyun.yuan/code/open-source/CapsWriter-wt/panel-style
git status; git log --oneline -8; git diff --stat 67efc8b..ca19ece
git diff 67efc8b..ca19ece -- core tools readme.md CLAUDE.md
git diff 67efc8b..ca19ece -- openspec/.../{design,evidence}.md openspec/.../mutations.toml openspec/.../specs openspec/.../tasks.md
git diff e586500 ca19ece -- openspec/.../acceptance.md          # empty: round 3 restored byte for byte
git log --format='%h %an %ad %s %b' 67efc8b..ca19ece; git log --graph --oneline 67efc8b^..ca19ece
git reflog show --date=iso origin/feature/live-dictation | head -4; git reflog show --date=iso feature/live-dictation | head -6
git log --oneline ca19ece..a2384aa; git show --stat a2384aa        # after the range, reported only
cat proposal.md design.md evidence.md specs/live-dictation/spec.md tasks.md
cat -n core/server/worker/live_preview.py; sed -n 100,175p core/server/worker/qwen_mlx_runner_pipeline.py
sed -n 95,140p core/client/output/live_panel.py; grep -n live_panel.show|strip() core/client/output/result_processor.py
grep -n entry calls in tools/test_live_{pipeline,e2e,client,preview}.py
openspec validate add-live-dictation-mode                       # "Change 'add-live-dictation-mode' is valid"
python3 ~/.claude/tools/test_mutate.py                          # "mutate canary: 8/8 passed"
scratchpad/accept-r5/run_suite.sh run1 ; ... run2               # whole suite, run 1 of 2 (baseline) and 2 of 2 (end)
# previous behaviour: git archive 67efc8b core tools config_*.py hot*.txt -> scratchpad/accept-r5/prev,
#   HEAD's 4 test files copied in, models symlinked to the worktree's models; narrow tests run there
# pre-_join behaviour: git archive e586500 ... -> scratchpad/accept-r5/prev0, HEAD test_live_pipeline.py copied in
python3 scratchpad/accept-r5/make_rows.py                       # builds 2 scratch specs, old/new copied verbatim, round trip checked
python3 ~/.claude/tools/mutate.py scratchpad/accept-r5/delta-rows.toml          # the 5 rows the delta adds, narrowest test each
python3 ~/.claude/tools/mutate.py scratchpad/accept-r5/touched-file-rows.toml   # the 11 other rows on live_preview.py + 2 cap rows
python3 scratchpad/accept-r5/hand_mutate.py                     # H1-H7, each restored and sha256-checked
python3 scratchpad/accept-r5/hand_mutate2.py                    # H8 (unit files, then the e2e pause test)
python3 - (all 51 rows of mutations.toml match their file exactly once)   # "51 rows; not matching exactly once: []"
```

---

## Round-4 findings: closed or not

| # | Round-4 finding | State at ca19ece | Evidence |
|---|---|---|---|
| 1 | (Q1, Q3) Latin spacing pinned only inside `Agreement.update`; H2/H3 (`.lstrip()` in `LiveTask.step` / `live_tick`) MISSED; no gap declared | **Closed** at the pipeline level. Real-engine part declared and left to A7 | New `test_live_pipeline.py::test_latin_word_spacing_through_the_production_path` (`:291`). Toml rows "step strips the space before tentative text" and "live_tick strips the space before tentative text" (round-4 H2, H3) both CAUGHT with that test alone. On `e586500` code (before `_join`) it fails: `'dessert you' not found in '我们聊到了dessertyou know 好吃吗还不错'`. Gap declared in tasks.md B6 and 9.4. Two notes: the test calls `pipeline.process()` / `pipeline.live_tick()` directly, not `WorkHandler.loop` as 9.4 says; the client hop is still not pinned (H4 below) |
| 2 | (Q4) 8.1 claimed round 3 gave PASS; round 3's rows edited in place | **Closed at ca19ece**. Reopened after the range (see "After the range") | `git diff e586500 ca19ece -- acceptance.md` is empty; `tail -1` is `Verdict: NEEDS-HUMAN`. 8.1 now reads "round 3 Opus at d3217e8: `Verdict: NEEDS-HUMAN` ... round 4 Opus delta at 67efc8b: FAIL, fixed in group 9" |
| 3 | (Q4) No Acceptance items for the new visuals; A1-A4 ran on pre-delta code | **Closed** | tasks.md Acceptance: A1 and A4 reopened with the reason; A5 (colour), A6 (cap), A7 (Latin), A8 (pause), A9 (F4 decision) added, all `[ ]` |
| 4 | (Q4, docs) Stale figures in tasks.md and CLAUDE.md | **Mostly closed** | B12 now says "system blue with an underline, height capped"; B6 lists the new tests; 5C and 7.1 point to acceptance.md; CLAUDE.md no longer copies counts and says A1, A4-A9 are open. Still open: the "Call sites to mutate (5C)" list (`tasks.md:127-141`) does not name `_join`, the cap, the pause branch or the two `.lstrip()` sites; and acceptance.md at ca19ece holds rounds 1-3 only, so the pointers lead to no current figures until 9.7 is written |
| 5 | (Q5, note) Cap bound 20 pt looser than its docstring | **Closed** | `test_live_client.py:440` now `cap + 1`. Toml row "panel height cap overshoots by 20 pt" CAUGHT; H5 (+2 pt) CAUGHT: `343.0 not less than or equal to 341.8` |
| - | (Q4) Push to origin against task 7.2 | **Declared** | 7.2 now says "Push only to `origin` ... only when the user asks ... (Pushed at the user's request on 2026-09-27.)". Reflog: `origin/feature/live-dictation` updated by push to `ca19ece` at 16:53:43. The user's request itself I cannot check |

Earlier evidence the delta touches:

- Rows 31-41 of `mutations.toml` (on `live_preview.py`, and caught by `test_live_preview.py`, whose expected values changed): re-run, 11/11 CAUGHT.
- Round-4 Q2 H5 (cap overshoot MISSED): now CAUGHT.
- Round-4 Q3 bypass 4: closed for `step` and `live_tick`; the client part stays open as a note (H4).
- Round-3/4 "A1-A4 done by the user": tasks.md now reopens A1 and A4 and keeps A2 and A3. The delta's production change is inside `Agreement.update` only, so the final path (A2) and the hold path (A3) are not touched by this range.

---

## 1. Entry points

| # | Entry point | What the delta changes there | Test that enters through it | Proof | Row verdict |
|---|---|---|---|---|---|
| E1 | Server background worker `WorkHandler.loop` -> `QwenMLXRunnerPipeline.live_tick` -> `LiveTask.step` -> `Agreement.update` | Pause branch (`live_preview.py:95-100`) | `test_live_e2e.py::test_pause_after_speech_leaves_no_tentative_text` (`:317`) | `:323` `_record(self.harness.uri, audio, task_id, live=True, ...)`: real `websockets` socket, real `ws_recv`/`ws_send`, real `WorkHandler.loop` in a thread, real `qwen_asr_mlx` engine (`ServerHarness`, `:88-138`). Passes at HEAD (runs 1 and 2). On `67efc8b` code it fails: `AssertionError: '到这里' != ''` | PASS |
| E2 | Same worker, Latin spacing (round-4 carry) | None in this range (`_join` came in the previous range) | No test enters through the real worker with Latin text. `test_latin_word_spacing_through_the_production_path` enters at `pipeline.process()` / `pipeline.live_tick()` (`test_live_pipeline.py:301-302`) with the declared scripted model | tasks.md B6 and 9.4: "Declared gap: the real-model e2e has no mixed Chinese-English clip ... so Latin spacing on the real engine is left to A7" | NEEDS-HUMAN (A7) |

- The client side has no changed entry point. The only client change is the cap test bound.
- No CLI path, handler or worker is added.
- Note: tasks.md 9.4 says the two new pipeline tests run "through the real `WorkHandler.loop` / `live_tick`". Grep of `test_live_pipeline.py:291-319` finds no `WorkHandler`; the class docstring (`:124`) says the class calls `process()`/`live_tick()` directly. The forward `WorkHandler.loop` -> `live_tick` -> `queue_out` is pinned elsewhere (`WorkHandlerLiveTests`, toml row "work handler never ticks", and the e2e). So the claim overstates the entry, but no behaviour is left without a test.

Verdict for question 1: **NEEDS-HUMAN**. The pause rule has a real-entry test that fails on the previous code. Latin spacing through the real worker is declared manual (A7).

---

## 2. Fails before

Previous-commit run (`67efc8b` code, HEAD tests, in `scratchpad/accept-r5/prev`):

```
FAIL: test_commits_on_third_agreeing_pass       AssertionError: '今天下午三点开会' != '今天下午三点开会讨论方案'
FAIL: test_insertion_does_not_duplicate_tail    AssertionError: '你好世界' != '你好世界今天天气'
FAIL: test_pause_commits_the_tail               AssertionError: '我要把代码推送到远' != '我要把代码推送到远程仓库'
FAIL: test_speech_after_a_pause_loses_nothing   AssertionError: '我要把代码推送到远' != '我要把代码推送到远程仓库'
ok:   test_numeral_at_a_pause_still_waits       (property kept from before; proven by H1)
Ran 10 tests ... FAILED (failures=4)
FAIL: test_pause_through_the_production_path_commits_the_tail   AssertionError: '我要把代码推送到远' != '我要把代码推送到远程仓库'
ok:   test_latin_word_spacing_through_the_production_path       (_join exists at 67efc8b; see e586500 run)
Ran 15 tests ... FAILED (failures=1)
FAIL: test_pause_after_speech_leaves_no_tentative_text (real model)   AssertionError: '到这里' != ''
ok:   test_panel_height_is_capped_for_long_text (only the bound changed; proven by row and H5)
```

`e586500` code (before `_join`), HEAD `test_live_pipeline.py`:
`FAIL: test_latin_word_spacing_through_the_production_path  AssertionError: 'dessert you' not found in '我们聊到了dessertyou know 好吃吗还不错'`.

Toml rows the delta adds (`delta-rows.toml`, verbatim `old`/`new`, narrowest test each):

```
CAUGHT   live_tick strips the space before tentative text   (test_latin_word_spacing_through_the_production_path)
CAUGHT   step strips the space before tentative text        (same test)
CAUGHT   pause keeps the holdback                           (test_pause_commits_the_tail)
CAUGHT   pause commits trailing punctuation                 (test_speech_after_a_pause_loses_nothing)
CAUGHT   panel height cap overshoots by 20 pt               (test_panel_height_is_capped_for_long_text)
RESULT mutate caught=5 missed=0 skipped=0 errors=0
```

Other rows the delta touches (`touched-file-rows.toml`: the 11 other rows on `live_preview.py` with `test_live_preview.py && test_live_pipeline.py`; "panel height is not capped" with the cap test; "label height ignores the wrapped text" with `test_live_client.py`): `RESULT mutate caught=13 missed=0 skipped=0 errors=0`. All 51 rows match their file exactly once.

Hand mutations (each restored, sha256 equal, `git status` clean after):

| Id | File:site | Mutation | Test run | Result |
|---|---|---|---|---|
| H1 | `live_preview.py:106` | numeral back-off skipped at a pause (`... and not all(t == tail_keys for t in tails)`) | `test_numeral_at_a_pause_still_waits` | CAUGHT: `'价格是一万五千' != '价格是'` |
| H2 | `live_preview.py:95` | pause detected on the last two passes only (`tails[1:]`) | `test_live_preview.py` + `test_live_pipeline.py` | CAUGHT, but only by `IndexError` in `test_insertion_does_not_duplicate_tail`, not by an assertion (note) |
| H3 | `live_preview.py:153-154` (`LiveTask.step`, **call site** of `Agreement.update`) | read `committed` before calling `update` | `test_pause_through_the_production_path_commits_the_tail` | CAUGHT: `'' != '我要把代码推送到远程仓库'` |
| H4 | `result_processor.py:226` (**call site** of `live_panel.show`) | `message.text_tentative` -> `message.text_tentative.lstrip()` | `test_live_client.py` (file) | **MISSED**: `Ran 14 ... OK` (see question 3) |
| H5 | `live_panel.py:128` | cap overshoots by 2 pt | `test_panel_height_is_capped_for_long_text` | CAUGHT: `343.0 not less than or equal to 341.8` |
| H6 | `live_preview.py:85` | no content alignment (row 35), changed test only | `test_insertion_does_not_duplicate_tail` | CAUGHT: `'你好世界今天天气气很好' != '你好世界今天天气很好'` |
| H7 | `live_preview.py:29` | `AGREE = 2` (row 31), changed test only | `test_commits_on_third_agreeing_pass` | CAUGHT: `'今天下午三点开会讨论方案' != ''` |
| H8 | `live_preview.py:99` | drop the `limit and` guard | `test_live_preview.py` + `test_live_pipeline.py`; then the e2e pause test | **MISSED** in both. The e2e logged `ERROR 实时预览 pass 失败: task=e2e-paus, ...` twice and still passed (note) |

Scenario table (spec text the delta adds or changes):

| Spec text | Test that pins it | Fails before | Row verdict |
|---|---|---|---|
| Commit rule: "When the uncommitted text of the last three passes is the same ... the last-four-units rule SHALL NOT apply" | `test_pause_commits_the_tail`, `test_pause_through_the_production_path_commits_the_tail`, e2e `test_pause_after_speech_leaves_no_tentative_text` | All three FAIL on 67efc8b; row "pause keeps the holdback" CAUGHT; H3 (call site) CAUGHT | PASS |
| "... every unit except trailing punctuation SHALL be committed" | `test_speech_after_a_pause_loses_nothing`, `test_pause_commits_the_tail` | FAIL on 67efc8b; row "pause commits trailing punctuation" CAUGHT | PASS |
| "... subject to the numeral rule"; scenario "A numeral at a pause still waits" | `test_numeral_at_a_pause_still_waits` | Passes on 67efc8b (kept property); H1 CAUGHT | PASS |
| Scenario "A pause commits the tail" (both halves) | `test_pause_commits_the_tail`, `test_speech_after_a_pause_loses_nothing` | FAIL on 67efc8b; both new rows CAUGHT | PASS |
| Scenario "An insertion inside committed text does not duplicate the tail" (changed precondition and result) | `test_insertion_does_not_duplicate_tail` | FAIL on 67efc8b (pause part); H6 shows it still pins the alignment | PASS |
| Commit rule "three partial passes agree" (test expected value changed) | `test_commits_on_third_agreeing_pass` | FAIL on 67efc8b; H7 CAUGHT | PASS |
| Round-4 carry: "the shown and committed text read 'dessert you'" past `Agreement.update` | `test_latin_word_spacing_through_the_production_path` | FAIL on e586500; both `.lstrip()` rows CAUGHT | PASS (client hop: note, question 3) |

Verdict for question 2: **PASS**. Every added or changed scenario has a test that fails on the previous code or under a mutation, including two call-site mutations I ran (H3 CAUGHT; the two `.lstrip()` rows CAUGHT). Notes: H8 (the guard 9.6 kept) and H4 (client hop) are MISSED; H2 is caught only by a crash.

---

## 3. Real versus simulated

| # | Where | What is bypassed | Covered elsewhere? |
|---|---|---|---|
| 1 | The two new pipeline tests: `ScriptedRecognizer`, direct `pipeline.process()` / `live_tick()` | The model (declared fake); `WorkHandler.loop`, `queue_out`, `ws_send`, socket, client | Yes for the loop and transport: `WorkHandlerLiveTests` (real `WorkHandler.loop`) and the e2e (`test_live_run_streams_previews`, `test_pause_after_speech_leaves_no_tentative_text`) |
| 2 | The new `Agreement` unit tests call `update()` directly | `LiveTask.step` split and `live_tick` Result | Yes: pipeline pause test (H3 CAUGHT) and the e2e pause test |
| 3 | e2e pause test: TTS speech plus `np.zeros(int(4.5 * SR))` (`test_live_e2e.py:320`) | Real microphone silence has room noise; the model's output may keep changing (no pause detected) or add words | No automated test. Covered by user item A8 (declared in tasks.md) -> NEEDS-HUMAN |
| 4 | Latin spacing on the real engine | The model's real mixed-language output across passes | No. Declared gap (B6, 9.4) -> A7, NEEDS-HUMAN |
| 5 | Latin spacing across `ws_send` (`:44`), `RecognitionMessage.from_dict` (`protocol.py:129`), `result_processor.py:226`, `live_panel.py:106-113` | The leading space of the tentative text reaching the screen | Partly. Rows "ws_send drops text_tentative" and "RecognitionMessage.from_dict drops text_tentative" pin that the field is carried; nothing on this hop strips today (source reading). But H4 (`.lstrip()` at the client call site) is MISSED: no client test uses a tentative text with a leading space. Only A7 covers it -> NEEDS-HUMAN. NOTE cost: `result_processor.py:583` already uses `(panel_text or '').strip()`; a similar clean-up copied into the preview branch would bring "dessertyou" back on screen with every test green. One client test case (tentative `' you know'` through `test_preview_message_updates_real_panel`) would pin it |
| 6 | Evidence for the pause rule | The user's own voice (layer D not rerun, `evidence.md:117`) | Declared; user item A9 |
| 7 | Cap test takes the ratio from `_MAX_SCREEN_RATIO` (round-4 note) | The spec value 40 % | Unchanged by this delta; carried note |

Verdict for question 3: **NEEDS-HUMAN**. Round-4's uncovered bypass (step and `live_tick`) is closed. What automation does not reach (real mic silence, real mixed-language speech, the client hop for Latin spacing) is covered only by user items A7 and A8.

---

## 4. Open items

Command: `grep -n '^- \[ \]' tasks.md`, then read every `[X]` note in groups 7-9.

| Item | State | Evidence / judgement |
|---|---|---|
| 9.7 (this review) | `[ ]` | Open |
| A1, A4 | `[ ]` | Reopened: "confirmed on e586500 code and must be checked again" |
| A5-A9 | `[ ]` | New user items |
| A2, A3 | `[X]` | "stay confirmed". This range changes only `Agreement.update`; the final path and the hold path are not touched. The confirmation itself is the user's claim |
| 9.4 note | `[X]` | Partly inaccurate: "tested through the real `WorkHandler.loop`". The tests enter at the pipeline (question 1). The listed rows exist and are CAUGHT; the bound change is as stated |
| 9.6 note | `[X]` | "the `limit and` guard kept because an all-punctuation tail would index out of range": true (H8 raises `IndexError` in the e2e), but no test pins the guard (H8 MISSED). I did not verify "-16 changed lines" (lane worktree history) |
| 5C / 7.1 notes | `[X]` | Point to acceptance.md, which at ca19ece holds rounds 1-3 only. The current figures (51 rows; 10/15/14/5 live tests) are recorded nowhere in the tree until 9.7 is written |
| "Call sites to mutate (5C)" | Stale | Lacks `_join`, the cap, the pause branch and the two `.lstrip()` sites |
| 7.2 | `[X]` | Task changed from "no push" to "push only to origin when the user asks". `ca19ece` was pushed to origin at 16:53:43. The request is the user's to confirm |

After the range (outside `67efc8b..ca19ece`, not judged): `feature/live-dictation` is at `a2384aa` (16:58:33), "Record the user's sign-off: open acceptance rows marked PASS by the user, archive before round 5". It changes `acceptance.md` again (164+/144-): round 3's rows 3 and 4 and its final line go from NEEDS-HUMAN to PASS. Its 9.7 note says the user confirmed group 9 in the app and chose to archive before this round returned. A1 and A4-A9 are still `[ ]` in that commit. If the user made these edits, that is the user's decision; I only note that round 3's report is again not as its reviewer wrote it.

What the user must still verify (plain words):

1. A1: set `dictation_mode = 'live'`, run `capswriter restart`, hold Caps Lock in a text field and speak. Text shows within about 2 s. The text field keeps focus and its caret.
2. A4: dictate for about one minute. The panel keeps updating to the end.
3. A5: words that may still change are blue and underlined, settled words are the normal colour, both easy to read in light and dark mode.
4. A6: dictate one to two minutes. The panel stops growing at about 40 % of the screen height; the newest words stay visible.
5. A7: say a Chinese sentence with an English phrase and a pause, for example "我们聊到了 dessert, you know, 还不错". Two English words never appear stuck together.
6. A8: stop speaking in a normal room (real microphone noise, not digital silence) and keep holding Caps Lock for about 3 s. The blue tail turns to the normal colour. A sentence that ends in a number keeps the number blue.
7. A9: decide whether the preview quality is acceptable on your own voice (about 1.4 % wrong committed text, about 3 s commit lag; the pause rule was not re-measured on your recordings).
8. Confirm that pushing `ca19ece` to `origin` was intended.

Verdict for question 4: **NEEDS-HUMAN**. No checked task hides undone work. The false 8.1 claim from round 4 is fixed. Items 1-8 wait for the user; 9.7 is this review.

---

## 5. Scope, tolerances and design drift

Files, config, dependencies, ignore rules:

- All 13 files are named by tasks.md: `live_preview.py` (9.3), the four test files (9.3, 9.4, B6), `mutations.toml` (9.4), `evidence.md` (9.5), `spec.md`/`design.md` (9.3), `readme.md`/`CLAUDE.md` (group 9 "doc edits (orchestrator)"), `acceptance.md` (restore, 8.1/9.7), `tasks.md`.
- No change to `config_*.py`, `requirements*.txt`, `.gitignore`, `.gitmodules` or the submodule (`git diff --stat`).
- `mutations.toml`: 5 rows added, none edited or removed (diff has `+` lines only).
- Process change, declared in tasks.md: 7.2 now allows a push to origin on request; the roles line now says acceptance is Opus from round 3.

Tolerances and expected values:

| Where | Before | After | Judgement |
|---|---|---|---|
| `test_live_client.py:440` cap bound | `cap + 2 * margin + 0.5` | `cap + 1` | Tightened. Declared (9.4). H5 (+2 pt) now CAUGHT |
| `test_live_preview.py:73` setup committed | `'你好世界'` | `'你好世界今天天气'` | Declared (9.3); follows the pause rule. H6 shows the test still pins content alignment |
| same test, final committed / tentative | `'你好世界今天'` / `'天气很好'` | `'你好世界今天天气很好'` / `''` | Declared (9.3) |
| `test_live_preview.py:152` committed after 3rd pass | `'今天下午三点开会'` | `'今天下午三点开会讨论方案'` | Declared (9.3). The test no longer pins `HOLDBACK`; row "holdback of three units" is still CAUGHT by other tests |
| `spec.md` scenario "An insertion inside committed text ..." | "你好世界" committed; result "你好世界今天", "天气很好" tentative | "你好世界今天天气" committed; result "你好世界今天天气很好" | Declared (9.3) |
| New e2e test timeout | - | `len(audio) / SR + 20` | Same value as the other e2e cases (`:231`, `:249`, `:303`) |

No timeout, threshold or e2e bound was loosened.

(a) Design decisions:

- D5, as updated: "When the uncommitted text of the last `AGREE` passes is the same ... `HOLDBACK` does not apply and the whole tail is committed except trailing punctuation" -> `live_preview.py:95` `if all(t == tail_keys for t in tails):`, `:98` `limit = len(tail_keys)`, `:99-100` trailing `'P'` trimmed. "Numeral hold and content alignment are always on" -> `:106` still runs after the pause branch (H1 CAUGHT). "It imports `re` and `difflib` (and numpy) only" still holds. Match.
- The comparison is on unit keys (case folded, all punctuation equal), not raw text. This follows the spec's own comparison rule ("Units SHALL be compared ignoring letter case, and all punctuation marks SHALL compare equal"). Not a departure.
- "Patterns and size": "No new config beyond `dictation_mode`. Interval, agreement and holdback are module constants". The pause rule reuses `AGREE`; no new constant or setting. Match.
- D1-D4, D6-D9: no line in this range touches them. Carried from round 3/4.

(b) Abstractions the delta adds: none. No new function, class, module, constant or config key. The new tests use existing helpers (`make_pipeline`, `ScriptedRecognizer`, `make_work`, `synth`, `_record`, `next_task_id`).

Verdict for question 5: **PASS**. Every file and every changed expected value is declared; the one changed tolerance is tighter; the code matches D5 as updated; no abstraction is added.

---

## Test runs (commands tasks.md names)

`openspec validate add-live-dictation-mode`: "Change 'add-live-dictation-mode' is valid". Canary `test_mutate.py`: 8/8.

| File | Run 1 (baseline) | Run 2 (end) |
|---|---|---|
| test_editor_annotation | rc 0, 8 PASS, 0 FAIL | rc 0, 8 PASS, 0 FAIL |
| test_editor_result_flow | rc 0, 16 PASS, 0 FAIL | rc 0, 16 PASS, 0 FAIL |
| test_editor_ui_contract | `PASS: editor UI contract` | `PASS: editor UI contract` |
| test_live_client | Ran 14, OK | Ran 14, OK |
| test_live_e2e (real model, `HF_HUB_OFFLINE=1`) | Ran 5 in 69.8 s, OK, no skip, 0 "实时预览 pass 失败" lines | Ran 5 in 71.9 s, OK, no skip, 0 such lines |
| test_live_pipeline | Ran 15, OK | Ran 15, OK |
| test_live_preview | Ran 10, OK | Ran 10, OK |
| test_mic_shortcut_lifecycle | Ran 9, OK | Ran 9, OK |
| test_mlx_model_resolution | Ran 4, OK | Ran 4, OK |
| test_stream_stop_leak | Ran 14, OK | Ran 14, OK |
| test_worker_scheduling | Ran 10, OK | Ran 10, OK |

Totals per run: 81 unittest cases + 24 editor script cases + the UI contract check, 0 failures. Mutations this round: 18 toml rows (5 new + 13 on touched code or tests), 18 CAUGHT; 8 hand mutations, 6 CAUGHT (H2 only by a crash), 2 MISSED (H4, H8). The e2e runs in the worktree write to its ignored `logs/`; I did not open it. `git status --porcelain` was empty after every mutation run and at the end.

## Findings and smallest fixes

1. (Q2/Q4, note) The `limit and` guard at `live_preview.py:99` is needed (without it every pass in a held silence after a pause commit raises `IndexError`), but no test pins it (H8 MISSED, and the e2e passed while logging the error). Cost: a later simplify pass can delete it with all tests green. Fix: in `test_pause_commits_the_tail`, feed the same text once more and assert no exception and an empty tentative; or have the e2e pause test assert no "实时预览 pass 失败" record.
2. (Q3, note) The client hop for Latin spacing is not pinned (H4 MISSED). Fix: one client case with tentative `' you know'` through `test_preview_message_updates_real_panel`, asserting the label string contains "dessert you".
3. (Q1/Q4, doc) Correct 9.4: the two new pipeline tests enter at `pipeline.process()`/`live_tick()`, not `WorkHandler.loop`.
4. (Q4, doc) Add `_join`, the cap, the pause branch and the two `.lstrip()` sites to "Call sites to mutate (5C)"; write rounds 4 and 5 into acceptance.md so the 5C/7.1 pointers lead to current figures.
5. (Q2, note) H2 is caught only by an `IndexError`. Optional: one unit case with passes A, B, B (A different) asserting the holdback still applies.

## Summary table

| Question | Verdict | One line |
|---|---|---|
| 1. Entry points | NEEDS-HUMAN | The pause rule enters through the real socket, worker and engine (e2e fails on 67efc8b with `'到这里' != ''`); Latin spacing through the real worker is declared manual (A7); 9.4 overstates the pipeline tests' entry. |
| 2. Fails before | PASS | Every added or changed scenario fails on 67efc8b or under a mutation; 5/5 new rows and 13/13 touched rows CAUGHT; call-site H3 CAUGHT; notes: H8 (guard) and H4 (client hop) MISSED, H2 caught only by a crash. |
| 3. Real versus simulated | NEEDS-HUMAN | Round-4's step/`live_tick` bypass is closed; real mic silence (A8), real mixed-language speech (A7) and the client hop for Latin spacing (H4 MISSED) are covered only by user items. |
| 4. Open items | NEEDS-HUMAN | Round-4's false 8.1 claim is fixed and round 3 restored at ca19ece; A1 and A4-A9, the push, and 9.7 are open; after the range `a2384aa` edits round 3 to PASS again (not judged). |
| 5. Scope, tolerances and design drift | PASS | All 13 files declared, no config/dependency/ignore change, changed expected values declared, the cap bound tightened, code matches D5 as updated, no new abstraction. |

Verdict: NEEDS-HUMAN
