# UI/UX Design Skill — Dark Cosmic Portfolio System

Runbook for building portfolio/marketing frontends in Juan's brand:
**dark cosmic cyberpunk** (deep-space backgrounds, neon cyan/magenta accents).
Distilled from the o22ugdw213.network v4 redesign (2026-09-17).

## Design tokens

```css
--bg0:#040409; --bg1:#0a0a16;            /* void → cosmic panel */
--cyan:#00e5ff;                          /* primary neon — CTAs, links, key data */
--magenta:#ff2ea6;                       /* secondary neon — tags, social, accents */
--violet:#7b2fff;                        /* tertiary — gradients, gradients only */
--text:#eef2ff; --muted:#9aa3c7; --faint:#5b6285;
```

- **Neon discipline:** cyan = interactive/primary, magenta = social/secondary,
  violet = gradient filler only. Never use all three at full saturation in one
  component; pair cyan+magenta max.
- **Text on dark:** body `#eef2ff` on `#040409` ≈ 15:1. Muted `#9aa3c7` ≈ 7:1 —
  safe for secondary text. Faint `#5b6285` is for metadata only, never body copy.
- **Magenta text rule:** `#ff2ea6` on dark is ~4.5:1 — use only for large/bold/
  short labels (tags, kickers), never paragraphs.

## Glassmorphism layer (v5)

Evolves Dark Cosmic: frosted-glass surfaces floating over the starfield.
Grounded in 226 HF web-design docs (see `knowledge/ui-ux-learnings.md`):
blur 8–20px range, white alpha .05–.10 borders, gradient glass-card fills,
Tailwind `bg-white/10 + backdrop-blur-md` nav pattern.

```css
--glass:rgba(13,16,32,.44);            /* frosted fill — content cards */
--glass-deep:rgba(13,16,32,.60);       /* denser frost — nav, inputs */
--glass-border:rgba(255,255,255,.09);  /* 1px glass edge */
--glass-hi:rgba(255,255,255,.10);      /* top inner highlight */
--glass-shadow:0 18px 50px rgba(0,0,0,.42),0 2px 10px rgba(0,0,0,.30);
--glass-shadow-hover:0 22px 60px rgba(0,0,0,.50),0 0 0 1px rgba(0,229,255,.06),0 12px 44px rgba(0,229,255,.08);
--blur-s:8px; --blur-m:14px; --blur-l:22px;
--saturate:140%;
```

- **Full frost recipe** (hero band, nav, feature/about/skill/connect/ibot cards):
  translucent fill + `backdrop-filter:blur(var(--blur-m)) saturate(140%)`
  (+ `-webkit-` prefix) + 1px `--glass-border` edge +
  `box-shadow:inset 0 1px 0 var(--glass-hi), var(--glass-shadow)`.
  The inner highlight is what sells "glass" — never skip it.
- **Lite glass** (long lists like the 50-row repo index): fill + edge +
  highlight, NO backdrop-filter. Reads as glass, costs nothing on scroll.
- **Hover:** keep the existing lift, swap the glow for `--glass-shadow-hover`
  (deep shadow + faint cyan ring + neon glow). Translate values unchanged.
- **Two-tier opacity:** `.44` for content cards (blur shows the starfield),
  `.60` for nav/inputs where legibility beats atmosphere.
- **Contrast over glass:** effective card bg ≈ `#0b0d1b` (glass over void);
  body `#eef2ff` ≈ 14:1, muted `#9aa3c7` ≈ 6.5:1 — both hold. Rule: never let
  a glass fill drop below `.40` alpha under body copy; faint metadata only.
- **Light theme:** redefine the same tokens
  (`--glass:rgba(255,255,255,.58)`, `--glass-border:rgba(10,20,40,.14)`,
  `--glass-hi:rgba(255,255,255,.65)`, softer `--glass-shadow`). Zero new rules.
- **Perf budget:** full frost on ≤ ~25 surfaces; lite glass beyond that.
  Mobile (`max-width:768px`): drop to `blur(8px) saturate(120%)`.
  `@supports not (backdrop-filter…)` → solid `--card-solid` fallback.
- **Don't:** stack blurred translucents (double-frost muddies), blur text
  containers under 12px type, or use frost on the scroll-progress bar.

## Type scale

- Display: **Space Grotesk** 700, `clamp(2.6rem,7vw,4.8rem)` hero,
  `clamp(1.7rem,3.4vw,2.4rem)` section titles, letter-spacing `-0.015em`.
- Body: **Inter** 400/500, `0.86–1.02rem`, line-height 1.6–1.7.
- Labels/code: **JetBrains Mono** 400/600, `0.62–0.72rem`, letter-spacing
  `0.08–0.24em` uppercase for kickers/tags.
- Gradient headlines: `linear-gradient(100deg, cyan 10%, violet 55%, magenta 95%)`
  with background-clip:text. One per viewport max.

## Layout & spacing

- 8pt base. Section: `max-width:1140px`, padding `5.5rem 1.5rem` (4rem mobile).
- Cards: `--radius:16px`, `1px` borders (`rgba(0,229,255,.12)` default,
  `rgba(255,255,255,.07)` soft), glassy `rgba(255,255,255,.028)` fills.
- Grids: `repeat(auto-fill,minmax(320px,1fr))` for feature cards;
  `repeat(auto-fit,minmax(250px,1fr))` for stat/skill tiles.
- Hero: `min-height:100svh`, centered, max-width 860px content.

## Component patterns

- **Nav:** fixed, transparent → blur+border after 40px scroll (`backdrop-filter:
  blur(18px)`, `rgba(4,4,9,.82)`). Active link: cyan + 2px gradient underline.
  Mobile: hamburger → full-width dropdown panel.
- **Hero:** canvas starfield (≤220 stars, twinkle via sine, occasional meteor
  streak every ~7s) + static CSS nebula gradients. Kicker pill (mono, uppercase,
  pulsing dot). Animated counters via IntersectionObserver + easeOutCubic.
- **Section header:** mono uppercase tag (magenta) + display title + one-line
  muted description. Never a bare title.
- **Work card:** 16:9 cover art top (SVG/PNG, `loading="lazy"`), body with
  lang chip + stars row, title, 2–3 sentence case-study blurb
  (**what it does / what was hard / what it proves**), mono tech tags,
  meta footer with repo link. Hover: `translateY(-6px)` + cyan glow shadow.
- **Repo index:** toolbar (search input + sort select + hide-forks toggle)
  rendering from a committed `data/repos.json`; rows = name / truncated
  description / lang / stars / updated. Client-side filter+sort, no framework.
- **Scroll progress:** 2px fixed top bar, cyan→magenta gradient.
- **Theme toggle:** dark-first; light theme redefines the same tokens
  (never a separate stylesheet). Persist in localStorage.

## Motion rules

- Reveal: `.reveal` → opacity/translateY(26px) → visible, `cubic-bezier(.22,.8,.28,1)`,
  stagger ≤210ms across siblings, unobserve after first reveal.
- Hover lifts: `-2px` buttons, `-4px` social cards, `-6px` work cards.
- `prefers-reduced-motion: reduce` → kill all animation, show content statically,
  hide canvas. Non-negotiable.

## Accessibility checklist

- Skip link, `<main>` landmark, one `<h1>`, semantic sections with aria-labels.
- `:focus-visible` 2px cyan outline everywhere.
- `alt` on every cover image; `aria-hidden` on decorative canvases/icons.
- Color never the only signal (icons + text labels on badges).
- Contrast: body ≥7:1, muted ≥4.5:1, faint metadata exempt but never essential.

## Portfolio-specific patterns

- **Live data:** generate `data/repos.json` from `gh repo list ... --json`
  at build time; render counts and the full index from it. Hero metrics must
  match the JSON totals — never hardcode divergent numbers.
- **Cover art:** procedural SVG per featured project (seeded starfield +
  nebula + one geometric motif + title bar), ~7KB each, committed under
  `assets/covers/`. Regenerable via `tools/generate_covers.py`.
- **Case-study blurbs:** 2–3 sentences, concrete (name the hard part, name the
  proof). No "leveraging synergies".
- **Keep shippable:** zero JS frameworks, zero build step. CDN fonts/icons only.
  Total page weight target < 500KB excluding fonts.
- **Don't break:** keep existing URLs/anchors (`#home #projects #skills #ibot
  #connect`, `404.html`, `bg.mp4`, `.nojekyll`, `_config.yml`) working.
