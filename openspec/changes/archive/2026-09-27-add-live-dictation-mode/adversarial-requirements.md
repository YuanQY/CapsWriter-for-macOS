# Adversarial review: requirements stage

- Stage: requirements
- Files reviewed:
  - `openspec/changes/add-live-dictation-mode/proposal.md`
  - `openspec/changes/add-live-dictation-mode/specs/live-dictation/spec.md`
  - `openspec/changes/add-live-dictation-mode/evidence.md` (read because the proposal cites it as its premise; not itself under review)
- Repository root: `/Users/qingyun.yuan/code/open-source/CapsWriter-for-macOS`
- Date: 2026-09-27
- Model: fable
- Not read: `design.md`, `tasks.md`, any `adversarial-*.md`, any `acceptance.md`.

## Commands run to check premises

Each line: the command, then what it printed (one line).

1. `ls -la openspec/changes/add-live-dictation-mode/ …/specs/live-dictation/; ls openspec/changes/ openspec/changes/archive/ openspec/specs/` → change dir holds design.md, evidence.md, proposal.md, tasks.md, specs/; `archive/` and `openspec/specs/` are empty.
2. `git log --oneline -15; git status --short; cat .gitmodules; git submodule status` → HEAD `33eba19` (2026-09-25, "Turn off editor (annotation) mode"); only `openspec/` untracked; submodule `mlx-qwen3-asr` at `f745f5e`.
3. `cat config_client.py` → shortcuts: `caps_lock` with `hold_mode: True`, `x2` mouse (disabled); `editor_mode = False` (line 63); `hot = True`; `log_level = 'DEBUG'`; `udp_broadcast = False`; no `dictation_mode`.
4. `ls -la core/client/output/edit_panel.py; find core -name '*.py'; ls tools/` → edit_panel.py exists (21472 bytes); tools/ has 6 `test_*.py` scripts and 5 probes.
5. `ls -la …/evidence.md …/mutations.toml readme.md README.md CLAUDE.md` → evidence.md present; `mutations.toml: No such file`; `readme.md` and `README.md` both present, same size; CLAUDE.md 78286 bytes.
6. `grep -rln streaming --include=*.py .` → `mlx-qwen3-asr/mlx_qwen3_asr/streaming.py` exists.
7. `grep -rn "partial\|dictation_mode\|live_mode\|preview" --include=*.py .` → no existing live/preview/dictation_mode code (hits are GGUF converter noise).
8. `grep -rn "udp\|diary\|annotation\|save_audio"` → `result_processor.py:25` imports `broadcast_output_udp`; lines 352, 435, 479 save audio and diary.
9. `grep -rn is_final core` → `protocol.py:66` RecognitionMessage.is_final "是否为最终结果"; `ws_recv.py:100-159` legacy path emits non-final work.
10. `which python3 uv pytest; ps aux | grep capswriter; sysctl -n machdep.cpu.brand_string; system_profiler SPHardwareDataType` → Apple M4 Max, 64 GB; `start_server.py` (pid 70500) and `CapsWriter.app` (pid 70516) running since Friday; two `record_d.py` processes running.
11. `cat openspec/changes/add-live-dictation-mode/evidence.md` → D layer a3: first text 0.88 s, shown-then-changed 0.8 %, commit error 1.4 %; "Pre-registered thresholds that a3 did not meet on D: … commit error 0.5 % (1.4 %), commit lag 2 s".
12. `cat -n core/protocol.py` → `AudioMessage` has no live/mode field (lines 29-37); `RecognitionMessage.is_final` (line 78).
13. `cat -n core/server/connection/ws_recv.py` → line 34 `Config.model_type.lower() == 'qwen_asr_mlx'` gates the runner path; lines 194-195 and 222-223: MLX path only adds to `byte_count`, keeps no audio.
14. `cat -n core/server/connection/ws_send.py core/server/schema.py` → `ws_send.py:60` `logger.info(f"麦克风识别结果: {result.text}")`.
15. `cat -n core/server/worker/qwen_mlx_runner_pipeline.py` → line 57 `feed_audio_patch`; 66-67 returns None for non-final; 77 `logger.info(f'模型输出：{raw_text}')`; 81-82 `console.print` of raw and formatted text.
16. `cat -n core/server/worker/worker.py core/server/worker/work_pipeline.py` → one process, one loop; legacy `WorkPipeline.process` returns non-final results (line 126-127).
17. `cat -n mlx-qwen3-asr/mlx_qwen3_asr/capswriter_runner.py` → `self._states` private dict (line 112); `feed_audio` returns None until final (138-140); `transcribe_audio` goes through `feed_audio(is_final=True)` which pops the state (200-202).
18. `sed -n 1,140p core/client/output/edit_panel.py; grep -n "NSPanel\|activateIgnoringOtherApps\|canBecomeKey" …` → line 196 `canBecomeKeyWindow`; 307 `NSApp.activateIgnoringOtherApps_(True)`; 308 `makeKeyAndOrderFront_`.
19. `cat -n core/client/manager/mic_runner.py` → lines 48-49 start UDP control when `Config.udp_control`.
20. `cat -n core/client/audio/recorder.py` → one `AudioMessage(is_final=False)` per mic chunk (165-178); `time_start` is the key-down time.
21. `cat -n core/client/output/result_processor.py` → lines 245-254: non-final message logs `text[:50]` at DEBUG then returns; 256-272 traditional convert + hotword correct + rule substitute; 347 `editor_mode` branch; 390 `present_editor`.
22. `cat -n config_server.py` → line 21 `model_type = 'qwen_asr_mlx' if sys.platform == 'darwin' else 'qwen_asr'`; `format_num = True`, `format_spell = True`.
23. `cat requirements-client.txt requirements-server.txt; ls pyproject.toml pytest.ini setup.cfg tox.ini; .venv/bin/python -c "import AppKit, objc; …"` → no pytest config file; pyobjc 12.2.2 importable from `.venv`; pyobjc absent from `requirements-client.txt`; `mlx_qwen3_asr` importable.
24. `grep -n -i "stage\|阶段状态" CLAUDE.md; grep -n macos_mic_device readme.md; grep -rn tools/test_ CLAUDE.md` → no "stage status" section (file is a dated log "当前阶段同步"); readme line 191 documents a setting; CLAUDE.md:9 runs tests as `tools/test_*.py`.
25. `grep -n "logger\.\(info\|debug\|warning\)" core/server/connection/ws_send.py core/server/worker/*.py; ls -la logs/` → text logged at `ws_send.py:60`, `qwen_mlx_runner_pipeline.py:77`; `logs/server_latest.log` 5.3 MB, `client_latest.log` 1.25 MB.
26. `cat -n core/server/worker/work_handler.py` → `loop()` lines 158-191; `queue_in.get(timeout=1)` when idle (line 105); one `pipeline.process(work)` at a time.
27. `cat -n core/server/worker/audio.py core/server/engines/qwen_asr_mlx/asr_engine.py` → `uses_task_runner = True` (line 77); `feed_audio_patch` wraps `runner.feed_audio` (192-202).
28. `grep -n hold_mode core/client/shortcut/*.py; grep -n "START\|STOP" core/client/udp/udp_control.py` → `event_handler.py:36,53` hold vs click branches; `udp_control.py:108,118` START/STOP.
29. `cat -n core/server/formatter/text_formatter.py` → lines 56-58 `chinese_to_num` when `format_num`; 63-64 `adjust_space`.
30. `grep -n "def transcribe\|lock\|thread" mlx-qwen3-asr/mlx_qwen3_asr/session.py; grep -n "= 30" …/chunking.py` → `MAX_CHUNK_SECONDS = 30.0`; no lock in Session.
31. `sed -n 1,60p tools/test_editor_ui_contract.py; grep -n "patch(" tools/test_editor_*.py` → line 5 "不启动 … AppKit RunLoop"; result_flow tests `patch('core.client.output.edit_panel.present_editor')`.
32. `grep -n "stdout\|Popen" capswriterd.py` → `subprocess.Popen(cmd, cwd=…)` with no stdout redirect (lines 143, 152).
33. `ls models/Qwen3-ASR-MLX/Qwen3-ASR-1.7B-8bit` → `weights.safetensors`, `config.json`, tokenizer files present.
34. `ls ~/code/open-source/capswriter-ab/stream_eval/; ls -la …/results/report.md` → harness present (`run_eval.py`, `metrics.py`, `record_d.py`, `results/`); `report.md` 13599 bytes, 2026-09-27 10:50.
35. `grep -n "34.6\|0.88\|1.4 %\|0.22\|0.46" …/results/report.md` → D M0 34.6 %; D a3 commit error 1.4 %; pass p95 0.22 s / 0.46 s; numbers match evidence.md.
36. `head -12 tools/test_*.py` → all six say they do not open a real device, keyboard, or AppKit.
37. `.venv/bin/python tools/test_worker_scheduling.py; .venv/bin/python tools/test_editor_ui_contract.py` → "Ran 10 tests … OK"; "PASS: editor UI contract". (The other four scripts were not run.)
38. `sed -n 140,175p core/client/connection/websocket_manager.py` → every inbound message goes through `RecognitionMessage.from_dict`; a KeyError becomes `CommunicationError`.
39. `sed -n 25,110p core/client/shortcut/event_handler.py` → line 67: release before `threshold` (0.3 s) → `task.cancel()` and the key is re-emitted.
40. `grep -n capture_frontmost_app core/client/shortcut/task.py; grep -n NSApplication start_client_macos.py` → target app captured at key-down (`task.py:134-139`); NSApp Accessory policy (lines 69-70).
41. `grep -rln "流式\|streaming" docs/; grep -rn "流式识别\|流式显示" docs/*.md; grep -n "流式识别策略" CLAUDE.md` → `docs/Qwen3-ASR_macOS_最小适配规划.md:88` excludes "按住说话时的中间结果流式显示"; `CLAUDE.md:179` "当前阶段不把产品级流式识别/流式显示作为优先目标".
42. `grep StandardOutPath ~/Library/LaunchAgents/com.capswriter.*.plist` → server stdout → `~/.capswriter/logs/server.stdout.log`; client stdout → `client.stdout.log`.
43. `grep -a -c "模型输出" logs/server_latest.log; grep -a -c "接收到识别结果，文本" logs/client_latest.log` → 116 server lines carry transcript text today; 0 client non-final lines (the MLX path never sends non-final today).
44. `ls -la …/stream_eval/results/ | grep D_; python: count CJK lines in D_ideal.log, D_wall.log` → 8 of 10 D files are mode 600; `D_ideal.log` and `D_wall.log` are 644 and contain 0 lines with CJK text.

## Angle 1: Ambiguity

Looked for: sentences two engineers would implement differently; numbers without a bound or origin.

Found:

- spec line 21: "In live mode, while Caps Lock is held, the client SHALL show a floating preview panel". The client has three other ways to start a recording: click mode (`hold_mode: False`, `event_handler.py:36-56`), the mouse `x2` shortcut (`config_client.py:26-32`), and UDP START/STOP (`udp_control.py:108,118`). One engineer gates live mode on the Caps Lock hold path only; another gates it on "a recording is running". (F5)
- spec line 28: "shows recognized text within 2 s of speech start". The system has only the key-down time (`recorder.py:116`, `task.py:178`). Evidence measured "first text after speech" separately and notes a median 0.72 s of silence before speech. No VAD is named. One test measures from key-down, another from a hand-marked onset. (F19)
- spec lines 82-84: "a pause (a 20 ms frame whose RMS is at most 0.2 times the segment median) between 7.5 s after the segment start and 3 s before its end". "Segment median" can be the median frame RMS or the median sample amplitude. If several frames qualify, first, last and quietest are three different freeze points and give three different frozen texts. "the quietest frame if there is no pause" does not say whether the same window applies. (F11)
- spec lines 44-47 and 85: "three consecutive partial passes agree on it" and "starts with the committed text". The comparison is not defined. Scenario 1 shows "Cloud" vs "cloud". Evidence computed MER after "NFKC, casefold and punctuation removal" but does not say the commit rule used the same normalisation. Exact-string and casefolded comparisons commit different units. (F12)
- spec line 46: "a numeral run that is still open". Which units are numerals (一二三…十百千万亿零两, digits, 点, 百分之, 元/块) is not stated. (F13)
- spec line 121: "If a partial pass fails or times out". No timeout figure. An MLX model call cannot be interrupted once started, so "times out" also needs to say what happens to the engine. (F14)
- spec line 95: "each partial pass covers at most about 25 s of audio". "About" is not a bound. (F20)
- spec lines 21-22 do not say when the panel opens. Key-down or first text are both readings. A release before 0.3 s cancels the recording and re-emits Caps Lock (`event_handler.py:67-76`), so a panel opened at key-down would flash on every Caps toggle. A silent hold is not covered. (F15)
- proposal line 35: "CLAUDE.md records stage status". CLAUDE.md has no such section; it is a dated log (command 24). LOW, folded into F22.

## Angle 2: Hidden premises

Looked for: things the text assumes exist, run, or hold. Checked each on this machine.

Held:

- "the model already shipped" (proposal line 12): `models/Qwen3-ASR-MLX/Qwen3-ASR-1.7B-8bit/weights.safetensors` exists (command 33).
- "An offline evaluation (see `evidence.md`)" and its numbers 0.9 s, 1 in 100, 34.6 % vs 3.6 %, p95 0.22-0.46 s: evidence.md exists; the harness exists at `~/code/open-source/capswriter-ab/stream_eval/`; `results/report.md` shows the same figures (commands 34, 35).
- "the runner's existing transcription call is reused" (proposal line 68): `QwenASRRunner.transcribe_audio(audio, task_id=…)` transcribes any array under a fresh task_id (`capswriter_runner.py:142-166`). Held for the call itself.
- "No new dependencies" for the panel: PyObjC 12.2.2 is importable from `.venv` (command 23). Held for the venv; see F24 for the requirements file.
- Server keeps a per-task audio buffer during the hold: yes, in `runner._states[task_id].chunks` (`capswriter_runner.py:133-136`).

Broken or unverified:

- The audio "received so far" lives only in the submodule's private `_states` dict. The server's `AudioCache` on the MLX path keeps a byte count and no audio (`ws_recv.py:194-195, 222-223`); the pipeline hands `work.data` to the runner and drops it (`qwen_mlx_runner_pipeline.py:51-65`). So a partial pass must read a private attribute of the submodule or keep a second copy in the server. The proposal says "Submodule `mlx-qwen3-asr`: none planned" (line 67). INFERRED: I read the sources; the design is not written. (F17)
- The proposal's Why says "keeping the current hold-and-release mode as the default", and the spec's output scenario says "the text pasted into the target app equals the final transcription". With `editor_mode = True` (`config_client.py:63`, a supported setting turned off on 2026-09-25 by commit `33eba19`), the output path shows an editor panel and pastes only on Enter with the user's edits (`result_processor.py:347-392`). The editor panel takes focus by design (`edit_panel.py:196, 307-308`). Two panels and a non-literal paste are unaddressed. (F6)
- "Old clients never receive it because only live tasks request it" (proposal line 69-70): `AudioMessage` has no field to request it (`protocol.py:29-37`). The client→server protocol must change too. The Protocol impact line names only the server→client message. (F21)
- The premise that "logs" means the rotating log files only: launchd redirects server stdout to `~/.capswriter/logs/server.stdout.log` (command 42). Today's pipeline `console.print`s raw and formatted text (`qwen_mlx_runner_pipeline.py:81-82`). A partial path built the same way writes partial text to a file while never calling `logger`. (F10)
- The premise that the client's non-final path is text-free: `result_processor.py:246` logs `text[:50]` of every non-final message at DEBUG, and `log_level = 'DEBUG'`. It has fired 0 times today only because the MLX path sends no non-final messages (command 43). (F9)
- The premise that partial passes can run for every server: the runner path is gated on `model_type == 'qwen_asr_mlx'` (`ws_recv.py:34`), which is the default only on darwin (`config_server.py:21`). Other engines go through `WorkPipeline`, which has no audio-so-far. The spec says "the server SHALL" without naming the engine. (F16)
- evidence.md: "Layer D … its result files are mode 600 and its text was never printed". 8 of 10 D files are 600; `D_ideal.log` and `D_wall.log` are 644. They hold no CJK text (command 44). The mode claim is partly wrong; the privacy outcome holds. (F25)
- "the existing tools/ tests pass" (spec line 139): 2 of 6 run green here; 4 not run. Unverified for those four.

## Angle 3: Mutually exclusive constraints

Looked for: two sentences that cannot both hold.

Found:

- proposal line 33: "Partial passes never delay or change the final pass." spec lines 65-67: "Partial passes SHALL NOT delay the start of the final pass by more than one partial pass already running". On one engine in one worker loop (`work_handler.py:177`) a running pass cannot be pre-empted, so "never" cannot hold; the spec's bound can. The two texts disagree. (F2)
- spec lines 44-46 (Commit rule): a unit is committed only when "it is not among the last four units of any of those passes". spec lines 58-60 (scenario): "WHEN '你好世界' is committed and later passes read '你好啊世界今天' THEN the committed text becomes '你好世界今天'". "你好啊世界今天" is 7 units; the last four are 世界今天; so 今 and 天 cannot be committed by the rule, yet the THEN commits them. A test written to the scenario cannot pass under the rule as written. (F1)
- spec lines 131-135 (TDD gate): "For each new behaviour at least one test SHALL enter through the real production entry point without replacing a real dependency". spec lines 22-23, 28-29: the panel "SHALL NOT take keyboard focus", "shows recognized text within 2 s". The repository's own UI tests refuse to start AppKit (`test_editor_ui_contract.py:5`) and patch `present_editor` (`test_editor_result_flow.py:156`). A real-entry test of focus needs a running NSApp, a frontmost app and the model. The gate and the practice conflict unless some behaviours are moved to the user Acceptance list. (F7)
- spec lines 36-40 vs 87-90: committed text "SHALL" not change, except at the forced freeze which "replaces the committed text of the segment". The spec names the exception, so this holds. The proposal does not mention that black text can be replaced; folded into F18.

## Angle 4: What would make it useless

Looked for: every SHALL met, user still not helped.

Found:

- The preview shows one text; the paste shows another. The final passes server `TextFormatter` (punctuation model, `chinese_to_num`, `adjust_space`: `text_formatter.py:47-64`, `format_num = True`), then client traditional conversion, phoneme hotword correction and rule substitution (`result_processor.py:256-272`, `hot = True`), then `trash_punc`. The spec never says which layer the preview shows. The numeral scenario ("一万" stays tentative) implies raw model text. The user will read "价格是一万" and paste "价格是10000"; hotword fixes for tech terms never appear in the preview, which is the case the Why ("cannot tell whether the words are being heard correctly") is about. (F3)
- Black text can be wrong and the spec allows any rate. evidence.md, Known limits: "Pre-registered thresholds that a3 did not meet on D: … commit error 0.5 % (1.4 %), commit lag 2 s"; commit lag measured "about 2.8-3.2 s". No SHALL bounds commit error or commit lag. The proposal's Why cites 0.9 s, "1 in 100", and "exactly as accurate as today" and omits the missed thresholds. If every SHALL is met, 1 in 70 committed units is wrong and only the silent final paste corrects it. (F4)
- evidence.md: "The user's spontaneous speech with fillers and self-corrections was not recorded". The Why targets "longer dictation", which is spontaneous. INFERRED that spontaneous speech behaves differently. (F23)

## Angle 5: Overlap with existing capability

Looked for: something that already does this, in `openspec/specs/`, the code, docs and archive.

- `openspec/specs/` and `openspec/changes/archive/` are empty (command 1). Held.
- No existing live/preview/dictation_mode code (command 7). Held.
- `RecognitionMessage.is_final` already carries "final vs not final" (`protocol.py:66`), the legacy pipeline already sends non-final results, and the client already receives and drops them (`result_processor.py:252-254`). The proposal adds "one new server-to-client message type" (line 69). Not a duplicate, but an existing carrier the text does not weigh. (F21)
- Two recorded decisions say the opposite of this proposal: `CLAUDE.md:179` "流式识别策略 | 当前阶段不把产品级流式识别/流式显示作为优先目标" and `docs/Qwen3-ASR_macOS_最小适配规划.md:88` "不把按住说话时的中间结果流式显示纳入首版必做范围". The proposal cites neither. (F22)

## Angle 6: Scenario coverage

Looked for: failure path, empty input, concurrent case per requirement.

- Dictation mode setting: default, unknown value. Held.
- Live preview while speaking: only happy paths. Missing: release under 0.3 s (cancel + key re-emit, `event_handler.py:67`), a silent hold, server that never sends a partial (old server, non-MLX engine), WebSocket drop mid-hold (panel left open?). (F15, F16)
- Commit rule: three scenarios; two are satisfied by never committing (see Angle 8). (F8)
- Final result unchanged: two scenarios. Missing: a second recording starting while the first panel is still closing. LOW, folded into F26.
- Long utterances: 16 s with and without prefix match, 60 s. Missing: the >25 s forced freeze that "replaces the committed text" (lines 87-90), which is the one case where black text changes in front of the user. (F18)
- Partial failures: exception only; "times out" has no scenario and no figure. (F14)
- Partial text stays private: logs only; the other five sinks (diary, recordings archive, annotation files, clipboard, UDP) have no scenario. LOW; a single requirement can still be tested per sink. Folded into F9/F10.
- Concurrent clients: one worker loop serves every socket (`work_handler.py:20-45`). Partial passes for client A delay client B's file transcription. No scenario. (F26)

## Angle 7: Testability

Looked for: a SHALL with no observable outcome.

- "SHALL NOT change its result" (line 67): observable by comparing final text with and without live mode on the same audio. Held.
- "Any other value SHALL be treated as 'hold'": observable. Held.
- "SHALL NOT delay the start of the final pass by more than one partial pass already running": observable with a fake clock. Held.
- "within 2 s of speech start": observable only once "speech start" is defined. (F19)
- "SHALL NOT take keyboard focus": observable via `NSWorkspace.frontmostApplication`, but not under the gate's "real production entry point" rule without a GUI test. (F7)
- "updates about once per second": "about" makes the test threshold a guess. LOW, folded into F20.

## Angle 8: Wording that can be gamed

Looked for: a SHALL a lazy implementation meets without doing the useful thing.

- Lazy implementation: never commit anything; show all text grey. It passes "A tail word is not committed early" (two passes, rule needs three), "An open numeral run waits" ("一万" sits in the last four units of "价格是一万", so the tail rule holds it without any numeral logic), "Committed text does not change during the utterance", and "the client SHALL show a floating preview panel with the text recognized so far". The only scenario that forces a commit is the insertion scenario, which contradicts the rule (F1). (F8)
- "SHALL NOT be written to logs": met while `console.print` writes partial text to `server.stdout.log` via launchd (command 42). (F10)
- "no log file receives partial text; logs may record counts and timings": met by the existing `logger.debug(f"接收到识别结果，文本: {text[:50]}…")` only if that line is removed or bypassed; the spec does not say it is in scope. (F9)

## Findings

| Finding | Verdict | One line | Disposition |
|---|---|---|---|
| F1 Commit rule vs insertion scenario | FIXED | HIGH EVIDENCED In "你好啊世界今天" the units 今天 are among the last four, so the rule at spec lines 44-46 forbids committing them while the scenario at lines 58-60 requires "你好世界今天"; which is right, the four-unit hold-back or the scenario's expected text? | Scenario now: "你好世界" committed, then three passes "你好啊世界今天天气很好"; ran the eval Agreement (a3, holdback 4): committed "你好世界今天", tentative "天气很好". |
| F2 Never delay vs at most one pass | FIXED | MEDIUM EVIDENCED Proposal line 33 says partial passes "never delay" the final pass; spec lines 65-67 allow a delay of one running pass; which sentence is the requirement? | Proposal now says partial passes delay the final start by at most one running pass, matching the spec. |
| F3 Preview text layer | FIXED | MEDIUM EVIDENCED The final text passes server ITN/punctuation/spacing and client hotword and rule substitution (`text_formatter.py:47-64`, `result_processor.py:256-272`) but the spec never says which layer the preview shows; should the preview show raw model text, server-formatted text, or the hotword-corrected text that will be pasted? | Spec: the preview shows raw model text; only the final gets server formatting and client hotword substitution. |
| F4 Commit error and lag unbounded | ACCEPTED | MEDIUM EVIDENCED evidence.md reports commit error 1.4 % and commit lag 2.8-3.2 s on the user's voice, both missing the pre-registered thresholds, and no SHALL bounds either while the proposal's Why omits the miss; is 1.4 % wrong black text and a 3 s commit lag accepted, or should the spec state a bound? | The user reviewed the results and chose an optional mode; the proposal Why now states the four missed thresholds; the user judges the feel in Acceptance. |
| F5 Which recording starts are live | FIXED | MEDIUM EVIDENCED Spec line 21 says "while Caps Lock is held" but recordings also start from click mode (`event_handler.py:36-56`), the mouse x2 shortcut and UDP START (`udp_control.py:108`); does live mode apply to every recording start or only to a held Caps Lock? | Spec: live mode applies to every microphone recording, whichever shortcut started it. |
| F6 editor_mode interplay | FIXED | MEDIUM EVIDENCED With `editor_mode = True` (`config_client.py:63`) the final goes to a focus-taking editor panel and pastes only on Enter with edits (`result_processor.py:347-392`, `edit_panel.py:307`), which breaks the "pasted text equals the final transcription" scenario and shows two panels; what should happen when both `editor_mode` and `dictation_mode='live'` are set? | Spec: the final goes to the same output as hold mode (paste, or the editor panel when editor_mode is on); the panel closes before the output. |
| F7 TDD gate vs GUI and model behaviours | FIXED | MEDIUM EVIDENCED Spec lines 131-135 demand a real-entry-point test for every new behaviour, but the panel focus and 2 s scenarios need a live NSApp and model, and the repo's own UI tests refuse AppKit (`test_editor_ui_contract.py:5`); which behaviours may be verified by a user Acceptance item instead of an automated real-entry test? | TDD gate allows gaps declared with a reason in tasks.md; behaviours needing the app and a person are also Acceptance items. |
| F8 Commit scenarios satisfied by never committing | FIXED | MEDIUM EVIDENCED The tail-word scenario uses two passes (rule needs three) and "一万" is inside the last four units of "价格是一万", so an implementation that never commits passes both; should each commit-rule scenario include a pass sequence in which the unit is committed? | Each commit scenario now states the pass after which the unit is committed; all three checked with the eval Agreement. |
| F9 Existing DEBUG line logs non-final text | FIXED | MEDIUM EVIDENCED `result_processor.py:246` logs `text[:50]` of every non-final message at DEBUG and `log_level = 'DEBUG'`, so a partial carried by the existing receive path lands in `client_latest.log`; is changing or bypassing that existing line in scope? | Design D9 puts the preview branch before result_processor.py:246; the client test captures DEBUG records and asserts no preview text. |
| F10 "Logs" and launchd stdout | FIXED | MEDIUM EVIDENCED launchd writes server stdout to `~/.capswriter/logs/server.stdout.log` and today's pipeline `console.print`s transcript text (`qwen_mlx_runner_pipeline.py:81-82`); does "no log file receives partial text" include stdout and stderr files captured by launchd? | Spec now covers every log level, console output and the launchd stdout/stderr files; the preview path has no console.print. |
| F11 Pause definition | FIXED | MEDIUM EVIDENCED Spec lines 82-84 do not say whether "segment median" is median frame RMS or median sample amplitude, nor which pause (first, last, quietest) wins when several qualify, nor whether "the quietest frame" uses the same window; which choice is intended for each? | Spec defines the threshold as 0.2 x median 20 ms frame RMS, the quietest frame in the window, and the same window for the forced freeze. |
| F12 Agreement and prefix comparison | FIXED | MEDIUM EVIDENCED "agree on it" (line 45) and "starts with the committed text" (line 85) name no comparison while scenario 1 shows "Cloud" vs "cloud"; is agreement exact-string, casefolded, or NFKC+casefold as the MER metric used? | Spec: units compare ignoring letter case, all punctuation equal (the evaluated rule; no NFKC). |
| F13 Numeral unit undefined | FIXED | MEDIUM EVIDENCED "a numeral run that is still open" (line 46) never lists which units are numerals; which characters count (Chinese numerals, digits, 点, 百分之, 元/块)? | Spec lists the numeral characters and the exact commit condition for a numeral unit. |
| F14 Timeout without figure | FIXED | MEDIUM INFERRED "fails or times out" (line 121) gives no timeout and an MLX call cannot be interrupted once started; what is the timeout and what happens to the running engine call when it fires? | Removed "or times out": an MLX call is not interrupted; only a raised exception is handled. |
| F15 Panel open timing, short press, silence | FIXED | MEDIUM EVIDENCED The spec does not say whether the panel opens at key-down or at first text, and a release under 0.3 s cancels and re-emits Caps Lock (`event_handler.py:67-76`); does the panel open at key-down or at first text, and does it appear for a silent hold? | Spec: the panel opens at the first non-empty partial and closes at the final or 5 s after the last partial; short-press scenario added. |
| F16 Engine scope and no-partial server | FIXED | MEDIUM EVIDENCED Partial passes are possible only on the `qwen_asr_mlx` runner path (`ws_recv.py:34`, default only on darwin per `config_server.py:21`) and no scenario covers a server that never sends a partial; is live mode `qwen_asr_mlx`-only, and what does the client show when no partial arrives? | Spec states qwen_asr_mlx only and adds a scenario for another engine (no panel, hold behaviour). |
| F17 Audio-so-far only in runner private state | FIXED | MEDIUM INFERRED The buffered audio exists only in `runner._states` (`capswriter_runner.py:112,133-136`) and the server keeps no copy (`ws_recv.py:194-195`), yet the proposal plans no submodule change; is reading a private attribute or keeping a second copy acceptable, or is a small public runner method in scope? | Design D4: the pipeline keeps its own copy of live audio; no private runner attribute, no submodule change. |
| F18 No scenario for the 25 s forced replacement | FIXED | MEDIUM EVIDENCED Lines 87-90 let a forced freeze replace committed text, the one case where black text changes in front of the user, and no scenario covers it; should a scenario be added, and should the panel signal the replacement? | Scenario added for the forced freeze replacing disagreeing committed text; no extra panel signal (KISS). |
| F19 "Speech start" undefined | FIXED | MEDIUM EVIDENCED "within 2 s of speech start" (line 28) has no origin the client can observe (only key-down exists, `recorder.py:116`) and evidence notes a median 0.72 s pre-speech silence; is the 2 s measured from key-down or from a VAD-detected onset, and which VAD? | Spec measures from the first spoken word; the e2e clip starts with speech; the user checks the feel in Acceptance A1. |
| F20 "At most about 25 s" | FIXED | LOW EVIDENCED "at most about 25 s" (line 95) is not a bound; is the bound 25 s plus one pass interval? | Bound now: 25 s plus the audio received since the previous pass. |
| F21 Protocol change is two-way; existing is_final carrier | FIXED | LOW EVIDENCED `AudioMessage` has no field to request live (`protocol.py:29-37`) so the client→server message changes too, and `RecognitionMessage.is_final=False` already exists as a non-final carrier (`protocol.py:66`); is the change a new message type or an extension of the existing one? | Proposal Impact lists both optional fields (client-to-server live, server-to-client preview and text_tentative). |
| F22 Reverses recorded decisions; "stage status" | FIXED | LOW EVIDENCED `CLAUDE.md:179` and `docs/Qwen3-ASR_macOS_最小适配规划.md:88` record a decision not to build streaming display, the proposal cites neither, and CLAUDE.md has no "stage status" section; should the decision row be updated and what does "records stage status" mean? | Proposal cites the CLAUDE.md 流式识别策略 row; the docs task updates it. |
| F23 Spontaneous speech not evaluated | FIXED | LOW INFERRED evidence.md says the user's spontaneous speech with fillers was not recorded while the Why targets long dictation; is a spontaneous-dictation check part of acceptance? | Acceptance A1 asks for natural speech with fillers and self-corrections. |
| F24 pyobjc undeclared | ACCEPTED | LOW EVIDENCED PyObjC is importable from `.venv` but absent from `requirements-client.txt`, so "no new dependencies" rests on an undeclared one; is declaring it in scope? | Pre-existing; declaring PyObjC in requirements-client.txt is outside this change (Ponytail). |
| F25 evidence.md mode claim | FIXED | LOW EVIDENCED evidence.md says layer-D result files are mode 600 but `D_ideal.log` and `D_wall.log` are 644 (they contain no CJK text); should the sentence say ".jsonl files" or should the two logs be chmod 600? | chmod 600 on every results/D_* file; the evidence sentence now holds. |
| F26 Concurrent clients | ACCEPTED | LOW EVIDENCED One worker loop serves every socket (`work_handler.py:20-45,177`) so partial passes for one client delay another client's work, and no scenario covers two clients or two back-to-back recordings; is single-client use an accepted assumption? | Single local client is the product's use; noted in design Risks. |

## What I could not break

- Evidence numbers: 0.9 s first text, "1 in 100" changed, 34.6 % vs 3.6 %, p95 0.22-0.46 s all match `results/report.md` (commands 11, 35).
- Model presence: `models/Qwen3-ASR-MLX/Qwen3-ASR-1.7B-8bit/weights.safetensors` exists (command 33).
- Evidence harness presence: `~/code/open-source/capswriter-ab/stream_eval/` with `run_eval.py`, `metrics.py`, `results/report.md` (command 34).
- The runner can transcribe an arbitrary array under a fresh task_id without a submodule change: `transcribe_audio` (`capswriter_runner.py:142-166`).
- The server holds the per-task audio during the hold: `_TaskAudioState.chunks` (`capswriter_runner.py:133-136`).
- PyObjC is importable from the client venv, so a native panel needs no new package in the venv (command 23).
- No existing live/preview code and no existing spec in `openspec/specs/` (commands 1, 7).
- "Final result unchanged" and "final not queued behind several partials" are each falsifiable by one test.
- "Any other value SHALL be treated as 'hold'" is falsifiable by one test.
- The non-goal on `mlx_qwen3_asr.streaming` is grounded: the module exists and evidence shows M0 final MER 34.6-34.8 % (commands 6, 11).
- `tools/test_worker_scheduling.py` (10 OK) and `tools/test_editor_ui_contract.py` (PASS) run green on this machine (command 37).
- Layer-D log files at mode 644 contain no CJK text, so the privacy outcome the evidence claims holds even where the mode claim does not (command 44).

Author note (2026-09-27): round two was not run. The user asked to spend Fable sparingly and to start coding after this review; the HIGH fix (F1) and the rewritten commit scenarios (F8) were checked by running the evaluated Agreement code instead.

Verdict: RESOLVED
