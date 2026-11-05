# GSP Design Exports

> Load this file first, then load only the chunks needed for your task.

## Usage

This file is the entry point for coding agents consuming GSP design output.

1. Read this file to find chunk paths for your task
2. Load only the chunks relevant to your current screen or component
3. Each chunk is self-contained — follow `## Related` links for cross-references

## Quick Reference

- Building a screen? → Design table → load screen chunk + referenced components
- Need a component spec? → Components table (in brand system)
- Need color/type/spacing? → Foundations table (in brand system)
- Need project scope? → Brief table
- Need UX patterns or reference specs? → Research table

## Design System (Brand-Level)

<!-- BEGIN:system -->
| Section | Chunk | Lines |
|---------|-------|-------|
| _(populated by /gsp-brand-system — lives in brand directory)_ | | |

### Foundations

| Foundation | File | Tokens |
|------------|------|--------|
| | | |

### Components

| Component | File | States | Variants |
|-----------|------|--------|----------|
| | | | |
<!-- END:system -->

## Project Brief

<!-- BEGIN:brief -->
| Section | File |
|---------|------|
| Scope | [scope.md](../brief/scope.md) |
| Target Adaptations | [target-adaptations.md](../brief/target-adaptations.md) |
| Install Manifest | [install-manifest.md](../brief/install-manifest.md) |
<!-- END:brief -->

## Project Research

<!-- BEGIN:research -->
| Section | File |
|---------|------|
| _(populated by /gsp-project-research)_ | |
<!-- END:research -->

## Design

<!-- BEGIN:design -->
### Screens

| # | Screen | File | Components Used |
|---|--------|------|-----------------|
| 01 | Chat | [screen-01-chat.md](../design/screen-01-chat.md) | WoodRailHeader, DemoStrip, CustomerSelector, MetricsDetails, MetricsPanel, LocalModeNotice, ChatTranscript, ChatBubble, TypingIndicator, HandoffBubble, ProductCard, Composer |
| 02 | Warm-up (chat body state) | [screen-02-warmup.md](../design/screen-02-warmup.md) | WarmupStatus, WoodRailHeader, DemoStrip, ChatTranscript, Composer, Button |
| 03 | Demo login | [screen-03-login.md](../design/screen-03-login.md) | Card, Label, Input, Button |

### Shared

| Section | File |
|---------|------|
| Personas | [personas.md](../design/shared/personas.md) |
| Information architecture | [information-architecture.md](../design/shared/information-architecture.md) |
| Navigation | [navigation.md](../design/shared/navigation.md) |
| Micro-interactions | [micro-interactions.md](../design/shared/micro-interactions.md) |
| Responsive | [responsive.md](../design/shared/responsive.md) |
| Component plan | [component-plan.md](../design/shared/component-plan.md) |
| Mockups (HTML gallery) | [mockups/index.html](../design/mockups/index.html) |
<!-- END:design -->

## Design Critique

<!-- BEGIN:critique -->
| Section | File |
|---------|------|
| _(populated by /gsp-project-critique)_ | |
<!-- END:critique -->

## Build

<!-- BEGIN:build -->
| Section | File |
|---------|------|
| _(populated by /gsp-project-build)_ | |
<!-- END:build -->

## QA Review

<!-- BEGIN:review -->
| Section | File |
|---------|------|
| _(populated by /gsp-project-review)_ | |
<!-- END:review -->
