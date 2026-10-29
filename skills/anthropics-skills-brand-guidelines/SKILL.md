---
name: anthropics-skills-brand-guidelines
description: "Applies Anthropic's official brand colors and typography to any sort of artifact that may benefit from having Anthropic's look-and-feel. Use it when brand colors or style guidelines, visual formatting, or company design standards apply."
license: Apache-2.0 per skill
status: review
category: design
upstream: https://github.com/anthropics/skills
upstream-path: skills/brand-guidelines
upstream-commit: ca45fc496a3436251f191354091d557da31c15b5
---

# Provenance

This package is a curated import from [anthropics-skills](https://github.com/anthropics/skills) at commit `ca45fc496a3436251f191354091d557da31c15b5`. Original path: `skills/brand-guidelines`. The package is marked `review` and may require host-specific adaptation. Review the source notice in `third_party/licenses/` before redistribution.

# Anthropic Brand Styling

## Overview

To access Anthropic's official brand identity and style resources, use this skill.

**Keywords**: branding, corporate identity, visual identity, post-processing, styling, brand colors, typography, Anthropic brand, visual formatting, visual design

## Brand Guidelines

### Colors

**Main Colors:**

- Dark: `#141413` - Primary text and dark backgrounds
- Light: `#faf9f5` - Light backgrounds and text on dark
- Mid Gray: `#b0aea5` - Secondary elements
- Light Gray: `#e8e6dc` - Subtle backgrounds

**Accent Colors:**

- Orange: `#d97757` - Primary accent
- Blue: `#6a9bcc` - Secondary accent
- Green: `#788c5d` - Tertiary accent

### Typography

- **Headings**: Poppins (with Arial fallback)
- **Body Text**: Lora (with Georgia fallback)
- **Note**: Fonts should be pre-installed in your environment for best results

## Features

### Smart Font Application

- Applies Poppins font to headings (24pt and larger)
- Applies Lora font to body text
- Automatically falls back to Arial/Georgia if custom fonts unavailable
- Preserves readability across all systems

### Text Styling

- Headings (24pt+): Poppins font
- Body text: Lora font
- Smart color selection based on background
- Preserves text hierarchy and formatting

### Shape and Accent Colors

- Non-text shapes use accent colors
- Cycles through orange, blue, and green accents
- Maintains visual interest while staying on-brand

## Technical Details

### Font Management

- Uses system-installed Poppins and Lora fonts when available
- Provides automatic fallback to Arial (headings) and Georgia (body)
- No font installation required - works with existing system fonts
- For best results, pre-install Poppins and Lora fonts in your environment

### Color Application

- Uses RGB color values for precise brand matching
- Applied via python-pptx's RGBColor class
- Maintains color fidelity across different systems

## Workflow


1. Read the task context and prerequisites.

2. Apply the source workflow only within the host and authorization boundaries.

## Output contract


Return the requested artifact or a concise report of actions, assumptions, and unresolved risks.

## Verification


Check the result against the task requirements and record evidence before reporting completion.

## Failure handling


Stop on missing prerequisites, unsafe instructions, or unverified side effects; explain the blocker and a safe recovery path.
