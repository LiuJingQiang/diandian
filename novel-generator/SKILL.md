# Skill: Novel Generator Writing Rules

Use this skill whenever generating or converting prose for the interactive reading game.

## Fixed Dialogue Frame Rule

The frontend restores the Android 点点-style fixed blue dialogue band. The text area is fixed height and must never grow.

### Hard limit

- Every emitted `chat.text` must be **46 Chinese characters or fewer**.
- A single click must show a complete sentence or complete semantic fragment.
- Never write one long paragraph as one chat.

### Writing guidance

When drafting source prose intended for game conversion:

- Prefer short sentences: 18–32 Chinese characters.
- Split long narration into multiple visual beats.
- Put one camera/feeling/action per beat.
- If a sentence must be long, rewrite it into two complete sentences before conversion.

### Conversion behavior

`convert.py` enforces the same rule automatically:

1. Split first by `。！？；`.
2. If still too long, split by `，、：`.
3. If still too long, hard-slice as a last resort.
4. BG tags and handlers remain only on the first slice to avoid repeated triggers.

### Bad

```text
她说这句话时，檐灯巷外的煤车刚好碾过青石路，窗纸被震得发抖。药汤已经凉了，黑褐色一层浮在碗面，苦味混着煤烟味，像烬岚城灰檐区每天醒来都要吞的一口灰。
```

## Character Audit Rule

Before converting a novel into game data, run:

```bash
python3 character_audit.py --project <novel-project>
```

This generates:

```text
<project>/追踪/角色审计报告.md
```

Rules:

- Family members with emotional stakes must be in `book.config.json > roster`.
- Important NPCs that appear in the current volume should be in roster even if they are not romance leads.
- Generic groups such as 钟卫 can be generic roster entries if they affect visual staging.
- Missing high/medium-priority roles must be reviewed before `convert.py`.

## optionTitle Rule

Read `docs/option-title-generation.md` before modifying choice generation.

Rules:

- `optionTitle` must be generated in `novel-generator`, not in `game-frontend`.
- Frontend only displays `node.optionTitle`.
- `choices.json` title has highest priority.
- `contextual_option_title(seg_chats)` is only a temporary fallback.
- Never generate or commit the generic title: `这一步，你怎么应对？`.
- Every `optionTitle` must expose the current story conflict, character pressure, or gate.

### Good

```text
檐灯巷外的煤车碾过青石路。
窗纸被震得发抖。
药汤已经凉了，黑褐色浮在碗面。
苦味混着煤烟味，像每天醒来都要吞的一口灰。
```
