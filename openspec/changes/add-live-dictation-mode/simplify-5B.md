# Simplify pass (5B) — add-live-dictation-mode

Diff reviewed: `git diff 33eba19 28c89ea -- . ':!openspec'` (17 files, +1615/-5).
Tree: `/Users/qingyun.yuan/code/open-source/CapsWriter-wt/review` (read-only, not modified).
Verification: proposals applied to a scratch copy at
`/private/tmp/.../scratchpad/scratch_repo` and checked against the fast tests
(`test_live_preview.py`, `test_live_pipeline.py`, `test_live_client.py`,
`test_worker_scheduling.py` — 32 tests total, all green before and after both
proposals, applied together). `pyflakes` is not installed in the project venv;
per instructions it was not installed, so unused-import/variable checks were
done by manual read of every new/changed file instead (see item 3 below).

## Proposals

### 1. `core/client/output/result_processor.py:224-237` — dedupe the `live_panel` import

Check: #2 (shorter form the file itself already uses) / general duplication.
`_handle_message` imports the same module twice, once per branch that uses it;
only one branch ever runs per call (the `preview` branch returns early), so the
second import statement is redundant text, not redundant work.

Current (in the diff, `28c89ea`):
```python
        # live 预览：只更新悬浮面板，不进日志/日记/剪贴板/UDP，不消耗 last_case
        if message.preview:
            from core.client.output import live_panel
            live_panel.show(message.text, message.text_tentative)
            return
        ...
        if message.is_final:
            from core.client.output import live_panel
            live_panel.hide()  # 最终结果到达，收起预览面板（从未 show() 过也是空操作）
```

Replacement:
```python
        # live 预览：只更新悬浮面板，不进日志/日记/剪贴板/UDP，不消耗 last_case
        from core.client.output import live_panel
        if message.preview:
            live_panel.show(message.text, message.text_tentative)
            return
        ...
        if message.is_final:
            live_panel.hide()  # 最终结果到达，收起预览面板（从未 show() 过也是空操作）
```

Why behaviour is unchanged: Python caches modules in `sys.modules`, so hoisting
the import above the `if message.preview:` check does not change what gets
imported or when the module's top-level code runs (it already ran on the first
call). The only behavioural difference is that the import statement itself now
executes for every message instead of only for preview/final ones — an
attribute lookup against an already-imported module, not a new side effect.
Verified: applied in the scratch copy, `test_live_client.py` (8 tests,
including `ResultProcessorLoggingTests` and the three `LivePanelTests` that
exercise `_handle_message` through the real panel) still passes.

Line delta: **-1** (611 → 610 lines).

### 2. `core/server/connection/ws_send.py:61-64` — merge the nested `if`

Check: #2 (shorter form the file itself already uses) — the rest of the
function uses flat `if/elif` on `result.source`; this is the only nested `if`
the diff introduces.

Current:
```python
            if result.source == 'mic':
                if not result.preview:
                    # 预览文本只用于屏显，不能落进任何日志（哪怕是这一条info）。
                    logger.info(f"麦克风识别结果: {result.text}")
            elif result.source == 'file':
```

Replacement:
```python
            if result.source == 'mic' and not result.preview:
                # 预览文本只用于屏显，不能落进任何日志（哪怕是这一条info）。
                logger.info(f"麦克风识别结果: {result.text}")
            elif result.source == 'file':
```

Why behaviour is unchanged: the `elif` branch is keyed only on `result.source`,
never on the outcome of the inner check, so folding `not result.preview` into
the outer condition cannot change which branch of the `if/elif` fires. Checked
by exhaustive truth table over `source ∈ {mic, file, other, None}` × `preview
∈ {True, False}` × `is_final ∈ {True, False}` (16 cases, 0 mismatches; script
kept at `scratchpad/verify_ws_send_logic.py`). No fast test exercises this
function directly (only `tools/test_live_e2e.py` does, and that needs the
local model, out of scope per the task's constraints), so it was verified by
the truth-table script rather than a unit test; applying it in the scratch
copy left all 32 fast tests green (this file isn't imported by any of them).

Line delta: **-1** (76 → 75 lines).

## Total

**-2 lines** if both proposals are applied (both verified independently and
together in the scratch copy; no other file needs to change).

## Checked, no finding (for the record)

- **Unused imports / dead code (check #3):** read every new file in full
  (`live_preview.py`, `live_panel.py`) and every changed file's diff hunks.
  All imports in both new files are used (verified by hand; `pyflakes` is not
  installed in `.venv` and was not installed per the task's constraint).
- **Single-caller helpers (check #4):** `LiveTask.duration`, `.due()`,
  `live_panel._ensure_panel/_attributed_text/_resize_panel`,
  `live_preview.is_numeral` each have one or two call sites, but each either
  hides a private field behind a documented accessor, isolates a genuinely
  long block of one-time AppKit setup, or is exercised directly by the pure
  rule tests (`test_live_preview.py`). None are seams copied from a neighbour
  "for consistency" with no caller of their own — removing any would either
  break encapsulation or bloat one function. No proposal.
- **Defensive branch for a config that can't exist today (check #1 /
  KISS #4):** `live_panel.py`'s `try/except` around the AppKit import mirrors
  `edit_panel.py`'s existing, already-merged pattern byte-for-byte (guards the
  non-macOS / PyObjC-missing case, needed so `result_processor.py` — shared
  with `start_client.py` — still imports on CI). Not new speculative code;
  matches an established, justified idiom. No proposal.
- **Hold-path blast radius (KISS #8):** `WorkHandler.loop()`'s new
  `hasattr(self.pipeline, 'live_tick')` check runs on the hold path too (same
  as the pre-existing `hasattr(self.pipeline, 'cleanup_tasks')` guard a few
  lines below in `cleanup()`), and `QwenMLXRunnerPipeline.process()` always
  does one `self.live.pop(work.task_id, None)` on every final regardless of
  mode. Both are O(1) on an always-empty dict in hold mode and reuse the
  codebase's existing optional-hook idiom (D2 in design.md) rather than
  introducing a new one. Not flagged.
- **Duplicated privacy checks (explicitly allowed to stay):** the "no partial
  text in logs" property is checked three times at three layers —
  `PipelineLiveTests.test_preview_is_not_logged` (tools/test_live_pipeline.py),
  `ResultProcessorLoggingTests.test_preview_is_not_logged`
  (tools/test_live_client.py), and the fragment-leak scan in
  `test_live_run_streams_previews` (tools/test_live_e2e.py). These are
  redundant with each other but each guards a path where a failure would leak
  preview text (server log, client log, and the full wire path respectively) —
  kept, per the task's own carve-out, not proposed for removal.
- **Cross-file test duplication (considered, not proposed):**
  `tools/test_live_client.py`'s `_FakeCorrector`/`_FakeHotword` are
  byte-identical to the ones in the pre-existing `tools/test_editor_result_flow.py`
  (whose docstring even says "与 test_editor_result_flow 同构" — deliberately
  mirrored, not imported). Importing them from that file would touch a file
  outside this diff's scope for a ~10-line saving, and would couple two
  otherwise-independent test files (a change to the editor-panel fakes could
  silently break the live-dictation tests). Given Ponytail's bias toward
  minimal blast radius and test-file independence, this was not turned into a
  proposal.
- **Idiom nit, not proposed as a line-reduction (zero delta):**
  `core/server/worker/qwen_mlx_runner_pipeline.py:134`,
  `_run_live_pass`'s inner `transcribe()` closure hardcodes
  `sample_rate=16000` where `process()` a few lines above uses
  `sample_rate=work.samplerate` for the exact same call. `Work.samplerate`
  always defaults to 16000 today (no caller in `ws_recv.py` ever sets it), so
  behaviour is identical either way — this is a same-line-count idiom match
  (check #2), not a size reduction, so it isn't counted in the total above.
  Swap is: `sample_rate=16000,` → `sample_rate=work.samplerate,`. Not applied
  to the scratch copy since it changes no line count and the task's goal is
  less code.

## Not touched

`live_preview.py`'s `Agreement.update()`/`_tail_start()` (the LocalAgreement-3 +
holdback + numeral-hold + content-alignment core) is already dense — no
redundant branch or shorter existing idiom found. `readme.md`/`CLAUDE.md`
changes are prose, not code, and were left out of scope.
