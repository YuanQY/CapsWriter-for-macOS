## ADDED Requirements

### Requirement: Dictation mode setting

The client SHALL read a `dictation_mode` setting from `config_client.py` with the
values `'hold'` and `'live'`. The default SHALL be `'hold'`. Any other value SHALL
be treated as `'hold'`. Live mode SHALL apply to every microphone recording,
whichever shortcut started it. Live mode SHALL work only with the `qwen_asr_mlx`
server engine; with any other engine the server sends no partial message and
dictation behaves as in hold mode.

#### Scenario: Default keeps today's behaviour
- **WHEN** `dictation_mode` is not changed from its default
- **THEN** no preview panel is shown, the server runs no partial pass, no partial
  message is sent, and the final text and its output path are the same as before
  this change

#### Scenario: Unknown value falls back to hold
- **WHEN** `dictation_mode` is set to `'stream'`
- **THEN** the client behaves as in hold mode

#### Scenario: Another engine sends no partials
- **WHEN** the client is in live mode and the server engine is not `qwen_asr_mlx`
- **THEN** no preview panel opens and the final text is output as in hold mode

### Requirement: Live preview while speaking

In live mode, while a recording is in progress, the client SHALL show a floating
preview panel with the text recognized so far. The panel SHALL open with the
first partial message whose text is not empty, and SHALL close when the final
message arrives or 5 s after the last partial message, whichever comes first.
The panel SHALL NOT take keyboard focus from the app that had focus when
recording started. Committed text SHALL be shown in the normal text colour and
tentative text in a secondary (grey) colour. The preview SHALL show the model's
text before server formatting and client hotword substitution; only the final
text is formatted and substituted.

#### Scenario: First words appear while speaking
- **WHEN** the user starts a recording in live mode and starts speaking
- **THEN** the panel shows recognized text within 2 s of the first spoken word
  and updates about once per second while the user speaks (for recordings
  longer than about 45 s one pass takes longer than 1 s, and updates follow
  the pass time)

#### Scenario: Focus stays in the target app
- **WHEN** the panel is shown or updated
- **THEN** the app that was frontmost when recording started stays frontmost and
  keeps keyboard focus

#### Scenario: Committed text does not change during the utterance
- **WHEN** a unit of text has been shown as committed
- **THEN** later updates during the same recording keep it unchanged, and only
  the tentative part may change

#### Scenario: A short press or a cancelled recording
- **WHEN** a recording ends with no final message, or before any partial text
- **THEN** no panel stays on screen longer than 5 s after the last partial

### Requirement: Commit rule

The text of a partial pass SHALL be split into units: one CJK character, one
Latin or digit word, or one punctuation mark. Units SHALL be compared ignoring
letter case, and all punctuation marks SHALL compare equal. A unit SHALL be
committed only when the last three partial passes agree on it and on every unit
before it, and it is not among the last four units of any of those passes. A
numeral unit is one whose characters are all in
`零〇一二三四五六七八九十百千万亿两点0123456789`. A numeral unit SHALL NOT be
committed unless the next unit of the pass is a non-numeral unit that is also
outside the last four units of those passes. The uncommitted tail of a new pass SHALL
be located by content alignment against the committed units. Tentative text
SHALL NOT end with punctuation.

#### Scenario: A tail word is not committed early
- **WHEN** the passes are "我刚用Cloud", "我刚用cloud code把这个" and
  "我刚用cloud code把这个脚本重构"
- **THEN** nothing is committed, and after a fourth pass
  "我刚用Cloud Code把这个脚本重构了一下" the committed units are 我, 刚, 用 and
  Cloud (a Latin word keeps the space after it, so the committed text is
  "我刚用Cloud ")

#### Scenario: An open numeral run waits
- **WHEN** the passes are "价格是一万五千块钱左右", "价格是一万五千块钱左右吧" and
  "价格是一万五千块钱左右吧我觉得"
- **THEN** "价格是" is committed and "一万五千" is tentative, and after a fourth
  pass "价格是一万五千块钱左右吧我觉得可以" the committed text is "价格是一万五千块"

#### Scenario: An insertion inside committed text does not duplicate the tail
- **WHEN** "你好世界" is committed and the next three passes read
  "你好啊世界今天天气很好"
- **THEN** the committed text becomes "你好世界今天", not "你好世界界今天", and
  "天气很好" is tentative

### Requirement: Final result is unchanged by live mode

On release, the client SHALL receive and output the final transcription produced
by the same path as hold mode, to the same output as hold mode (paste, or the
editor panel when `editor_mode` is on). The preview text SHALL NOT be pasted.
Partial passes SHALL NOT delay the start of the final pass by more than one
partial pass already running, and SHALL NOT change its result.

#### Scenario: The output is the final text
- **WHEN** the user releases the shortcut in live mode
- **THEN** the text output to the target app equals the final transcription of
  the whole recording, the preview panel closes before the output, and no later
  partial message for that task reaches the client

#### Scenario: Final is not queued behind several partials
- **WHEN** the user releases the shortcut while a partial pass is running
- **THEN** no new partial pass starts for that task and the final pass starts as
  soon as the running one ends

### Requirement: Each partial pass reads the whole recording

Each partial pass SHALL transcribe all audio of the recording received so far.
A new pass SHALL start only after at least 1 s of new audio has arrived since
the previous pass started.

#### Scenario: A one-minute dictation
- **WHEN** the user dictates for 60 s in live mode
- **THEN** previews keep coming until release, committed text never changes,
  and the final text covers the whole recording

### Requirement: Partial text stays private and transient

Partial text SHALL exist only in memory. It SHALL NOT be written to logs at any
level (including the stdout and stderr files that launchd captures), the diary,
the recordings archive, annotation files, the clipboard or the UDP broadcast.

#### Scenario: No partial text in logs
- **WHEN** a live recording produces partial messages
- **THEN** no log record and no console output on client or server contains
  partial text before the final result; logs may record counts and timings

### Requirement: Partial failures do not break dictation

If a partial pass raises an exception, the server SHALL skip that update and
keep the recording, the final pass and the output path working.

#### Scenario: A failing partial pass
- **WHEN** a partial pass raises an exception
- **THEN** the preview keeps the last good text, the error is logged without
  text, and the final text is output as in hold mode

### Requirement: TDD quality gate

Every new behaviour in this capability SHALL be covered by an automated test that
fails before the change and passes after it. For each new behaviour at least one
test SHALL enter through the real production entry point without replacing a real
dependency, except where `tasks.md` declares the gap and its reason. A mutation
at every new production call site SHALL make at least one test fail. Behaviours
that need the running app and a person (focus in a real target app, timing while
the user speaks) SHALL also be listed as Acceptance items for the user.

#### Scenario: Gate before hand-off
- **WHEN** the change is handed to acceptance review
- **THEN** all new tests pass, the existing tools/ tests pass, and every row in
  `mutations.toml` reports CAUGHT
