---
name: DevTeam AI Platform System
colors:
  surface: '#0f131c'
  surface-dim: '#0f131c'
  surface-bright: '#353942'
  surface-container-lowest: '#0a0e16'
  surface-container-low: '#181c24'
  surface-container: '#1c2028'
  surface-container-high: '#262a33'
  surface-container-highest: '#31353e'
  on-surface: '#dfe2ee'
  on-surface-variant: '#c2c6d6'
  inverse-surface: '#dfe2ee'
  inverse-on-surface: '#2c3039'
  outline: '#8c909f'
  outline-variant: '#424754'
  surface-tint: '#adc6ff'
  primary: '#adc6ff'
  on-primary: '#002e6a'
  primary-container: '#4d8eff'
  on-primary-container: '#00285d'
  inverse-primary: '#005ac2'
  secondary: '#c0c1ff'
  on-secondary: '#1000a9'
  secondary-container: '#3131c0'
  on-secondary-container: '#b0b2ff'
  tertiary: '#4cd7f6'
  on-tertiary: '#003640'
  tertiary-container: '#009eb9'
  on-tertiary-container: '#002f38'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#d8e2ff'
  primary-fixed-dim: '#adc6ff'
  on-primary-fixed: '#001a42'
  on-primary-fixed-variant: '#004395'
  secondary-fixed: '#e1e0ff'
  secondary-fixed-dim: '#c0c1ff'
  on-secondary-fixed: '#07006c'
  on-secondary-fixed-variant: '#2f2ebe'
  tertiary-fixed: '#acedff'
  tertiary-fixed-dim: '#4cd7f6'
  on-tertiary-fixed: '#001f26'
  on-tertiary-fixed-variant: '#004e5c'
  background: '#0f131c'
  on-background: '#dfe2ee'
  surface-variant: '#31353e'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 2.25rem
    fontWeight: '600'
    lineHeight: 2.75rem
    letterSpacing: -0.025em
  headline-xl:
    fontFamily: Inter
    fontSize: 1.75rem
    fontWeight: '600'
    lineHeight: 2.25rem
    letterSpacing: -0.02em
  headline-xl-mobile:
    fontFamily: Inter
    fontSize: 1.5rem
    fontWeight: '600'
    lineHeight: 2rem
    letterSpacing: -0.015em
  headline-lg:
    fontFamily: Inter
    fontSize: 1.25rem
    fontWeight: '600'
    lineHeight: 1.75rem
    letterSpacing: -0.015em
  headline-sm:
    fontFamily: Inter
    fontSize: 1rem
    fontWeight: '600'
    lineHeight: 1.5rem
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 1rem
    fontWeight: '400'
    lineHeight: 1.5rem
    letterSpacing: 0em
  body-md:
    fontFamily: Inter
    fontSize: 0.875rem
    fontWeight: '400'
    lineHeight: 1.375rem
    letterSpacing: -0.005em
  body-sm:
    fontFamily: Inter
    fontSize: 0.75rem
    fontWeight: '400'
    lineHeight: 1.125rem
    letterSpacing: 0em
  code-md:
    fontFamily: JetBrains Mono
    fontSize: 0.8125rem
    fontWeight: '400'
    lineHeight: 1.25rem
    letterSpacing: -0.01em
  code-sm:
    fontFamily: JetBrains Mono
    fontSize: 0.6875rem
    fontWeight: '400'
    lineHeight: 1rem
    letterSpacing: 0em
  label-md:
    fontFamily: Inter
    fontSize: 0.8125rem
    fontWeight: '500'
    lineHeight: 1.125rem
    letterSpacing: 0em
  label-sm:
    fontFamily: Inter
    fontSize: 0.6875rem
    fontWeight: '600'
    lineHeight: 0.875rem
    letterSpacing: 0.03em
  label-mono:
    fontFamily: JetBrains Mono
    fontSize: 0.6875rem
    fontWeight: '500'
    lineHeight: 0.875rem
    letterSpacing: 0.02em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-desktop: 1.5rem
  margin: 1rem
  margin-desktop: 1.5rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1rem
  space-xl: 1.5rem
  space-2xl: 2rem
---

## Brand & Style

The design system establishes a high-performance, dark-mode developer canvas built for coordinating autonomous multi-agent engineering workflows. The interface balances high-density technical telemetry with immediate cognitive parsing, prioritizing utilitarian precision, deterministic state representation, and silent efficiency over decorative flair.

### Brand Personality
- **Deterministic & Methodical:** Every visual element serves an operational purpose. State changes, agent handoffs, and verification diffs are presented with structural clarity.
- **Architectural & Technical:** Inspired by high-end engineering cockpits (Linear, Vercel, GitHub Actions), the platform treats code, agent prompts, log streams, and git diffs as primary visual primitives.
- **Sovereign & Dependable:** Multi-agent autonomous software delivery introduces parallel execution risks; the UI conveys safety through explicit boundaries, discrete visual checkpoints, and rigorous human-in-the-loop audit gates.

### Target Audience
Senior software architects, technical leads, autonomous agent engineers, and engineering managers operating across distributed development environments and multilingual teams with seamless Vietnamese technical localization.

### Visual Style
- **Disciplined Dark Minimalism:** Deep charcoal and navy foundations with hairline surface delineation (`1px` borders with microscopic inner highlights).
- **Functional Typography:** Tight sans-serif hierarchy built on Inter, integrated seamlessly with tabular monospace numerals and code identifiers.
- **Information-Dense Surface Architecture:** Monolithic dashboards broken into compartmentalized cards, telemetry chips, state monitors, and unified action bars without gratuitous whitespace.

## Colors

The color system is engineered for dark-mode contrast governance (WCAG AAA for primary content, AA for metadata) across long engineering sessions.

### Core Canvas & Surfaces
- **Canvas Base (`#0B0F17`):** Deep navy void grounding root application windows and canvas viewports.
- **Sub-canvas / Shell Panels (`#0F172A`):** Navigation rails, execution timelines, and collapsed sidebars.
- **Surface Elevation 1 (`#111827`):** Primary workspace container, agent chat streams, and code viewports.
- **Surface Elevation 2 (`#1E293B`):** Modular Kanban task units, node graph panels, code review split-views.
- **Surface Elevation 3 / Hover (`#283548`):** Active card states, interactive list highlights, dropdown menus.

### Accent & Semantics
- **Primary Electric Blue (`#3B82F6`):** Active selections, focused execution nodes, primary deployment commits, command shortcuts.
- **Secondary Indigo/Violet (`#6366F1`):** Autonomous AI agent orchestration markers, agent prompt generators, pipeline links.
- **Tertiary Cyber Cyan (`#06B6D4`):** Real-time streaming tokens, runtime metrics (TPS, latency), dynamic telemetry charts.
- **Success Emerald (`#10B981`):** Passed CI/CD checks, verified test suites, state "Hoàn thành" (Completed).
- **Warning / Action Amber (`#F59E0B`):** Human gate intervention required, policy exceptions, state "Chờ duyệt" (Pending Review).
- **Destructive / Error Rose (`#EF4444`):** Syntax crashes, failed test builds, token run-out, state "Lỗi" (Failed / Error).
- **Processing Blue-Violet Pulse (`#818CF8`):** Active agent reasoning, state "Đang xử lý" (In Progress / Executing).

### Text & Hairline Tokens
- **Foreground Pure (`#F8FAFC`):** Primary headings, execution code, active diff text.
- **Foreground Muted (`#94A3B8`):** Descriptive labels, file paths, branch references.
- **Foreground Sub-meta (`#64748B`):** Commit hashes, timestamps, token consumption counters.
- **Border Structural (`#334155`):** Explicit panel separation.
- **Border Subtle (`rgba(255, 255, 255, 0.08)`): In-card row boundaries and nested node sockets.

## Typography

The typographic system utilizes **Inter** as the foundational sans-serif for UI layout, headings, and interactive elements, complemented by **JetBrains Mono** for technical data structures (execution IDs, Git hashes, CLI streams, JSON payloads, and token consumption).

### Implementation Rules
- **Numerical Alignment:** Monospace fonts and `font-variant-numeric: tabular-nums` must be enforced across all telemetry widgets, execution counters, and progress percentages to prevent layout jitter.
- **Vietnamese Language Optimization:** Diacritical marks in Vietnamese technical strings (e.g., *Đang xử lý*, *Kiểm tra tính tương thích*, *Chờ phê duyệt mã*) require calibrated line-heights (`1.375rem` minimum on `body-md`) to ensure zero clipping.
- **Micro-Labels:** Use `label-sm` with slight uppercase letter tracking (`0.03em`) for table metadata keys, status chips, and agent role tags (e.g., `ARCHITECT`, `CODER_AGENT`, `QA_RUNNER`).

## Layout & Spacing

The layout is grounded in a modular, flexible density model. Rather than sparse marketing whitespace, the system adopts a high-efficiency layout designed to display multi-pane agent orchestrations, pipeline dependency trees, and real-time diff logs concurrently.

### Layout Philosophy
- **Fluid Structural Canvas:** A split-pane architecture utilizing fixed-width collapsible navigation bars (`240px`), flexible main viewport panels, and dockable side-drawers (`380px` - `480px`) for execution telemetry and agent reasoning traces.
- **12-Column Flexible Grid:** When rendering card matrices, a 12-column grid is deployed with `1rem` gutters on mobile/tablet and `1.5rem` gutters on desktop.
- **Adaptive Density System:**
  - **Compact Mode:** Default across diffs, terminal outputs, and execution trees (`space-xs` and `space-sm` for row spacing).
  - **Standard Mode:** Applied to configuration forms, project settings, and Kanban workflow views (`space-md` to `space-lg`).

### Responsive Adaptation
- **Mobile (< 768px):** Navigation collapses to a top app bar with command palette trigger. Multi-agent side-by-side node trees collapse into sequential timeline step views. Outer margins reduce to `margin: 1rem`.
- **Tablet (768px - 1199px):** Split-view layouts switch to overlay inspectors; Kanban lanes display with horizontal swipe snapping.
- **Desktop (≥ 1200px):** Full multi-column viewports enabled with side-by-side terminal, live editor diff, and agent chat logs. Margins scale to `1.5rem`.

## Elevation & Depth

This design system avoids heavy drop shadows and blur gimmicks, relying instead on **tonal surface stacking** and **crisp micro-borders** to express z-index hierarchy in deep dark environments.

### Elevation Tiers
- **Tier 0 (Root Level):** `#0B0F17` background. Flat, zero elevation. Hosts the canvas grid and base docking panel.
- **Tier 1 (Surface Canvas):** `#111827` panels with a subtle border: `1px solid rgba(255, 255, 255, 0.08)`. No shadow.
- **Tier 2 (Interactive Floating Modules & Cards):** `#1E293B` backgrounds. Paired with `1px solid #334155` borders. Adds subtle directional top highlight: `box-shadow: inset 0 1px 0 0 rgba(255, 255, 255, 0.05)`.
- **Tier 3 (Modals, Command K Palettes, Flyouts):** `#1A2234` solid surface. Elevated with ambient, low-spread dark shadow: `box-shadow: 0 16px 32px -8px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(255, 255, 255, 0.12)`.
- **Active Agent Focus (Glow Accent):** When an agent is actively streaming code or waiting for confirmation, the card receives a focused outline: `box-shadow: 0 0 0 1px #3B82F6, 0 0 16px -4px rgba(59, 130, 246, 0.3)`.

## Shapes

With `roundedness: 1`, the system executes with disciplined, modern precision. Sharpness communicates rigor, while mild radii prevent visual strain across high-density layouts.

### Geometry Specifications
- **Micro Radii (`0.25rem` / `4px`):** Status badges, inline code spans, filter chips, radio indicators, and telemetry labels.
- **Component Radii (`0.375rem` - `0.5rem` / `6px` - `8px`):** Input fields, standard action buttons, dropdown items, tooltips, and tab triggers.
- **Container Radii (`0.5rem` / `8px`):** Workflow cards, Kanban task blocks, diff windows, node blocks, and interactive modals.
- **Strictly Disallowed:** Organic pill-shaped capsules (`rounded-full`) are prohibited except for miniature agent avatar pips and circular counter badges.

## Components

### 1. Action Buttons
- **Primary:** Solid `#3B82F6` background with white text (`#F8FAFC`), `0.25rem` border-radius, font `label-md`. Hover: `#2563EB`. Active: `#1D4ED8`. Focus: `2px` offset outline `#3B82F6`.
- **Secondary / Outline:** Background `#1E293B`, border `1px solid #334155`, text `#F8FAFC`. Hover: `#283548`, border `rgba(255, 255, 255, 0.2)`.
- **Destructive:** Background `rgba(239, 68, 68, 0.12)`, border `1px solid rgba(239, 68, 68, 0.3)`, text `#EF4444`. Hover: `#EF4444`, text `#FFFFFF`.
- **Agent Action (Approve / "Phê duyệt"):** Emerald tint `#10B981` background, crisp dark text `#0B0F17`, semibold weight, instant keybind hint chip `⌘↵` displayed inline.

### 2. Status Badges & Telemetry Chips
Badges use `0.25rem` radius, padding `0.125rem 0.375rem`, font `label-mono`, accompanied by a `6px` status dot:
- **Đang xử lý (Executing):** Blue-violet background `rgba(99, 102, 241, 0.15)`, text `#818CF8`, dot animated with a subtle radar pulse.
- **Chờ duyệt (Pending Approval):** Amber background `rgba(245, 158, 11, 0.15)`, text `#F59E0B`, static dot.
- **Hoàn thành (Completed):** Emerald background `rgba(16, 185, 129, 0.15)`, text `#10B981`, static dot.
- **Lỗi (Error):** Rose background `rgba(239, 68, 68, 0.15)`, text `#EF4444`, static dot.
- **Agent Identity Badges:** Text `#94A3B8`, border `1px solid #334155`, background `#111827`, e.g., `[AGENT: QA-AUTOMATION]`.

### 3. Workflow Kanban Cards
- Container: `#1E293B`, border `1px solid rgba(255, 255, 255, 0.08)`, corner radius `0.5rem`, padding `0.75rem`.
- Header: Monospace ticket key (`DEV-4028`), status badge, and assigned agent avatar.
- Body: Task title in `headline-sm`, summary in `body-sm` (`#94A3B8`).
- Footer: Git branch link, active PR status, token cost meter (e.g., `14.2k tokens`), and Vietnamese status marker.

### 4. Input Fields & Code Prompts
- Background: `#0F172A`, border `1px solid #334155`, text `#F8FAFC`, placeholder `#64748B`.
- State Focus: Border `#3B82F6`, background `#111827`, box-shadow `0 0 0 1px #3B82F6`.
- Code Editor Inputs: Integrated JetBrains Mono, line number column in `#334155`, active line marked with background `rgba(59, 130, 246, 0.08)`.

### 5. Selection Elements (Checkbox & Radio)
- Checkbox: `16px x 16px`, `0.25rem` radius, border `1px solid #475569`, background `#0F172A`. Checked: `#3B82F6` with sharp checkmark icon.
- Radio: `16px x 16px`, circular, border `1px solid #475569`, checked state reveals a centered `6px` solid dot in `#3B82F6`.

### 6. Node-Based Workflow Canvas Components
- Nodes represent agent roles (Planner, Architect, Coder, Tester, Deployer).
- Canvas background `#0B0F17` overlaid with dot matrix grid (color `rgba(255, 255, 255, 0.05)`, spacing `16px`).
- Node Cards: `#1A2234` with border `1px solid #334155`. Ports/Sockets: `8px x 8px` rounded squares with hover state `#06B6D4`. Connection splines rendered in `#334155` (idle) or glowing `#3B82F6` (data transmitting).

### 7. Approval Diff Container ("Hộp phê duyệt thay đổi")
- Split-view container with red/green line gutters. Additions tinted `rgba(16, 185, 129, 0.1)` with marker `+`, deletions tinted `rgba(239, 68, 68, 0.1)` with marker `-`.
- Sticky footer toolbar containing: "Từ chối" (Reject), "Yêu cầu sửa đổi" (Request Changes), and "Chấp thuận & Triển khai" (Approve & Deploy).