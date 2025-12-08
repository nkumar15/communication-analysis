# UI Design Specification

**ID**: `SPEC-DESIGN-01`
**Status**: Draft
**Scope**: Web Admin, Tenant Dashboard, Mobile App

## 1. Overview
This specification defines the **visual language** and **design tokens** for the SaaS platform. All implementations (Web & Mobile) must strictly adhere to these values to ensure brand consistency.

## 2. Design Tokens
Tokens are abstract values that represent design decisions. They must be implemented as constants in code (e.g., JS constants, Swift structs, XML resources), **not** just CSS variables.

### 2.1. Color Palette

**Primary Actions**
- `Primary Blue`: `#4F46E5` (Main actions, Links)
- `Secondary Purple`: `#8B5CF6` (Platform Admin actions)

**Feedback / State**
- `Success Green`: `#10B981` (Success messages, valid states)
- `Warning Orange`: `#F59E0B` (Warnings, pending actions)
- `Error Red`: `#EF4444` (Destructive actions, validation errors)

**Neutrals**
- `Text Primary`: `#111827` (Main content)
- `Text Secondary`: `#6B7280` (Subtitles, placeholders)
- `Border`: `#E5E7EB` (Dividers, input borders)
- `Background`: `#F9FAFB` (Page background)
- `Surface`: `#FFFFFF` (Card/Modal background)

### 2.2. Domain-Specific Colors

**Role Badges**
- `Role Admin`: `#7C3AED` (Purple)
- `Role Manager`: `#D97706` (Orange)
- `Role Member`: `#2563EB` (Blue)

**Status Indicators**
- `Status Active`: `#059669` (Green)
- `Status Inactive`: `#6B7280` (Gray)
- `Status Pending`: `#D97706` (Orange)
- `Status Expired`: `#DC2626` (Red)

## 3. Typography

**Constraint**: Use system fonts where possible for performance, but fallback to Inter.

### 3.1. Scale (Web / Mobile)

| Token | Web Size (px) | Mobile Size (pt) | Weight | Usage |
|-------|---------------|------------------|--------|-------|
| `Heading 1` | 30px | 28pt | Bold (700) | Page Titles |
| `Heading 2` | 24px | 22pt | Semibold (600) | Section Headers |
| `Heading 3` | 20px | 18pt | Medium (500) | Card Titles |
| `Body Large` | 16px | 16pt | Regular (400) | Primary Text |
| `Body Small` | 14px | 14pt | Regular (400) | Secondary Text |
| `Caption`    | 12px | 12pt | Regular (400) | Labels, Badges |

## 4. Layout Guidelines

**Constraint**: Strict separation of layouts for distinct platforms.

### 4.1. Web Layout (Admin Desktop)
- **Grid**: 12-column fluid grid.
- **Sidebar**: Fixed width `250px`.
- **Header**: Fixed height `64px`.
- **Content Padding**: `32px` (2rem).

### 4.2. Mobile Layout (App Flow)
- **Grid**: Single column fluid.
- **Navigation**: Bottom Tab Bar or Stack Navigation.
- **Touch Targets**: Minimum `44x44` points.
- **Safe Area**: Must respect notch/home indicator areas.

## 5. Spacing System
Use these unitless multipliers. Base unit = `4px`.
- `Space-1`: 4px
- `Space-2`: 8px
- `Space-4`: 16px
- `Space-6`: 24px
- `Space-8`: 32px
