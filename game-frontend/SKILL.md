# Skill: Diandian-style React Frontend Execution

Use this skill whenever modifying `game-frontend/` UI, runtime flow, story schema consumption, branching, economy, or asset layout.

Before editing UI, read and obey:

```text
docs/ui-development-rules.md
```

## Non-negotiable Product Rules

1. **Not just choices + point deduction**
   - A choice must be able to change future structure: `next`, `diverts`, variables, unlocks, branch memory, ending flags.
   - Paid choices are monetization wrappers around meaningful alternatives, not fake duplicated options.
   - Pseudo-branches may exist only when they alter emotion/variable/economy feedback; otherwise collapse them during generation.

2. **Fixed reader frame**
   - Dialogue text lives inside a fixed-height mobile reader frame.
   - Text length must never resize the game layout.
   - Long text uses generator-side splitting first: each `chat.text` should be <= 46 CJK characters for the current Android-style blue dialogue band.
   - Internal scroll is only an emergency fallback, not the primary solution.
   - Speaker role changes frame treatment: narration, lead, secondary, system/AI.

3. **Options and character art are mutually exclusive**
   - When branch choices are visible, hide standing character art and the speaker/avatar card.
   - Options must appear above the fixed dialogue band with enough margin.
   - Do not layer choices over characters; it creates visual noise and breaks Android-style readability.

4. **Character staging rules live in `src/stageConfig.js`**
   - `characterStage` defines per-character preferred side and art-only exceptions.
   - `stagingRules.alternateDifferentConsecutiveCharacters` enforces: two different consecutive visual characters must not appear on the same side.
   - `zuizhong` must remain `{ position: 'center', artOnly: true }`: standing art only, no avatar/speaker card.

5. **Fixed Android reader controls**
   - Back button must use original `back.webp`; no CSS-drawn arrow/circle fallback.
   - Bottom action bar is icon-only: auto/shop/wardrobe/menu; no extra text under icons.
   - Reward bubble must stay above the dialogue region and not overlap options/dialogue.
   - Auto-read supports 1–10× speed and must pause at options.

6. **Android 点点 layout fidelity**
   - Vertical mobile-first, close to 1080×2400.
   - Full-screen background + character layer + fixed bottom dialogue frame.
   - Top wallet/resource bar must support energy, stardust, wishing star, love.
   - Fixed action icons: back, auto-read, shop, wardrobe, menu, reward/ad energy.
   - Options are horizontal rounded bars with explicit state: free, paid, ad, locked, wardrobe/attribute locked.
   - Prefer APK UI image assets for dialog/name/option/toast/action icons when available; CSS boxes are fallback only.

7. **Theme by novel style**
   - `story.categories` / book theme should select UI variant: userall/default, xiuxian, ai_chat, horror/urban, eastern-steam.
   - Theme changes colors, nameplate, option background, panel texture, icon set, and dialogue frame variant.

8. **Economy is two-layered**
   - Platform layer: energy, stardust, wishing star, love, VIP/virtual coin hooks.
   - Book layer: trust/favorability, moral axis, corruption, battle stats, story items, wardrobe attributes.
   - Gates must define source of friction and relief: energy, ad, free-card, VIP, wardrobe, attribute, chapter unlock.

## Required Components / Systems

- `ChoiceButton`: render free/paid/ad/locked/wardrobe/vip states.
- `WalletBar`: energy + secondary currencies + reward timer.
- `ActionBar`: back / auto / shop / wardrobe / menu fixed icon layout.
- `DialogueFrame`: fixed height; role variants; internal scroll or pagination.
- `BranchRuntime`: choice history, branch id, convergence support.
- `EconomyRuntime`: cost checks, ad reward, free-card consumption, wallet mutation.
- `UnlockRuntime`: chapter visual unlock, wardrobe locks, attribute locks, paid gates.
- `ThemeRuntime`: applies book category/theme to CSS variables and asset variants.
- `TelemetryHooks`: node enter, option show, option select, paywall show, ad reward, energy insufficient.

## Evidence Sources

- `../研究资料/README.md` — root research archive index; treat this as primary.
- `../研究资料/点点游戏架构规范.md` — authoritative product/data/economy model.
- `../研究资料/hbjmtlhbddrz_flow_data.json` — real branch graph data: 49 chapters / 897 paragraphs / 557 options.
- `../研究资料/全站存档/hbjmtlhbddrz-flow.md`
- `../研究资料/apk解析/raw_unzip/assets/flutter_assets/assets/images/` — decompiled APK UI resources.
- `reversed/docs/17-gameplay-and-economy-analysis.md`
- `reversed/docs/14-full-design-chain.md`
- `reversed/docs/05-ui-walkthrough.md`
- `diandian_apk_art_resources/UI_STYLE_GUIDE.md`
- `diandian_apk_art_resources/RESOURCE_CATALOG.md`

If root `研究资料/` and older copied files under a novel project disagree, prefer root `研究资料/`.

## Definition of Done for Frontend Changes

1. `npm run build` passes.
2. LSP diagnostics for `src/` show zero errors.
3. Mobile viewport remains stable while long/short text advances.
4. Speaker role variants are visually distinguishable.
5. Choices visibly encode cost/gate type.
6. Options mode hides character art/avatar card.
7. If adding economy/branching, update `docs/planning-execution.md` and sample story schema notes.
