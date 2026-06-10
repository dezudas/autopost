# Chordpedia Marketing Site Design System

---

version: 1.0
name: Chordpedia Marketing Design
brand: Chordpedia
-----------------

# Overview

Chordpedia’s marketing site should feel modern, musical, and creator-focused while remaining clean and easy to navigate. The visual language combines a warm golden primary accent with strong readable typography and spacious layouts.

The overall experience should balance:

* Music community energy
* Editorial cleanliness
* Product-focused storytelling
* High readability across desktop and mobile

The design system uses:

* **Primary Brand Color:** `#FFC107`
* **Primary Text Color:** `#333333`
* Minimal shadows
* Soft rounded corners
* Spacious layouts
* Modern sans-serif typography

---

# Colors

colors:
primary: "#FFC107"
primary-active: "#E0A800"
primary-light: "#FFF3CD"

text-primary: "#333333"
text-secondary: "#555555"
text-muted: "#777777"
text-light: "#999999"

background: "#FFFFFF"
background-soft: "#FAFAFA"
surface-card: "#FFFFFF"
surface-alt: "#F5F5F5"

border: "#E5E5E5"
border-strong: "#D6D6D6"

success: "#198754"
warning: "#FFC107"
error: "#DC3545"
info: "#0DCAF0"

on-primary: "#333333"
on-dark: "#FFFFFF"

---

# Typography

typography:
display-xl:
fontSize: 72px
fontWeight: 700
lineHeight: 1.05
letterSpacing: -2px

display-lg:
fontSize: 52px
fontWeight: 700
lineHeight: 1.1
letterSpacing: -1px

heading-lg:
fontSize: 40px
fontWeight: 700
lineHeight: 1.2

heading-md:
fontSize: 32px
fontWeight: 600
lineHeight: 1.25

heading-sm:
fontSize: 24px
fontWeight: 600
lineHeight: 1.3

body-lg:
fontSize: 18px
fontWeight: 400
lineHeight: 1.7

body-md:
fontSize: 16px
fontWeight: 400
lineHeight: 1.6

body-sm:
fontSize: 14px
fontWeight: 400
lineHeight: 1.5

caption:
fontSize: 12px
fontWeight: 500
lineHeight: 1.4
letterSpacing: 0.5px

button:
fontSize: 14px
fontWeight: 600
lineHeight: 1

---

# Font Recommendations

Primary Font:

* Inter
* Poppins
* Manrope

Fallback:

* system-ui
* Arial
* sans-serif

Code / Technical Content:

* JetBrains Mono
* Fira Code

---

# Layout System

spacing:
xxs: 4px
xs: 8px
sm: 12px
md: 16px
lg: 24px
xl: 32px
xxl: 48px
section: 96px

container:
maxWidth: 1280px
contentWidth: 1180px
gutter: 24px

---

# Border Radius

rounded:
xs: 4px
sm: 8px
md: 12px
lg: 16px
xl: 24px
pill: 9999px

---

# Core Components

## Navigation

component: top-nav

* Background: White
* Height: 72px
* Sticky navigation
* Minimal border bottom
* Logo left
* Menu center/right
* CTA button right

Recommended Navigation:

* Home
* Features
* Artists
* Events
* Pricing
* Download App

---

## Primary Button

component: button-primary

* Background: `#FFC107`
* Text: `#333333`
* Height: 44px
* Padding: `0 20px`
* Radius: `12px`
* Font Weight: `600`

Hover:

* Slightly darker yellow (`#E0A800`)
* Smooth transition

---

## Secondary Button

component: button-secondary

* White background
* Dark text
* 1px border
* Soft hover state

---

## Hero Section

component: hero-section

Structure:

* Large heading
* Supporting text
* Primary CTA
* Secondary CTA
* App preview or artist showcase image

Hero Style:

* Bright and clean
* Large typography
* Plenty of whitespace
* Yellow accents used sparingly

Suggested Headline Style:

* Bold
* Music-focused
* Community-driven

Example Layout:

* Left: Copy + CTA
* Right: Mobile app mockup or featured artist card

---

## Feature Cards

component: feature-card

* White card surface
* Thin border
* Radius: 16px
* Padding: 24px
* Optional icon top
* Subtle hover lift

Used For:

* Song requests
* Artist profiles
* Chords library
* Karaoke features
* Events
* Mobile app highlights

---

## Artist Cards

component: artist-card

* Large image
* Artist name
* Genre label
* Social links
* Hover animation

Card Layout:

* Image top
* Details bottom
* Rounded corners
* Minimal border

---

## Event Cards

component: event-card

Include:

* Event banner
* Event title
* Date & location
* CTA button

Visual Style:

* Modern ticket/event layout
* Yellow accent tags
* Strong readable typography

---

## Statistics Section

component: stats-band

Use for:

* Total songs
* Artists
* Monthly users
* Events
* Downloads

Style:

* Large numbers
* Bold typography
* Minimal background
* Equal spacing

---

## Testimonials

component: testimonial-card

* User quote
* Avatar
* Name + role
* Soft card background

---

## Footer

component: footer

Background:

* `#333333`

Text:

* White / light gray

Sections:

* Company
* Product
* Artists
* Community
* Social Links

Include:

* Copyright
* App store links
* Newsletter signup

---

# Visual Style Guidelines

## Do

* Use yellow strategically for emphasis
* Keep layouts spacious
* Use large readable typography
* Prioritize mobile responsiveness
* Maintain strong accessibility contrast
* Use music/community imagery
* Keep cards clean and modern

## Don’t

* Overuse yellow backgrounds
* Use heavy shadows
* Use excessive gradients
* Add too many competing accent colors
* Overcrowd layouts

---

# Responsive Guidelines

## Mobile (<640px)

* Single-column layouts
* Hero text reduced
* Stack buttons vertically
* Collapsed navigation menu

## Tablet (640px–1024px)

* Two-column feature grids
* Reduced spacing
* Medium hero typography

## Desktop (>1024px)

* Full grid layouts
* Large hero sections
* Rich visual storytelling

---

# Animation Guidelines

Use subtle animations only.

Recommended:

* Fade in
* Slide up
* Soft hover transitions
* Card elevation on hover
* Smooth carousel transitions

Avoid:

* Flashy effects
* Fast animations
* Excessive motion

---

# Accessibility

* Maintain WCAG AA contrast
* Use minimum 16px body text
* Ensure button tap area ≥ 44px
* Support keyboard navigation
* Use semantic HTML

---

# Suggested Marketing Sections

1. Hero Banner
2. Trusted by Nepali Musicians
3. Features Overview
4. Artist Showcase
5. Upcoming Events
6. Mobile App Preview
7. Community Statistics
8. Testimonials
9. Download CTA
10. Footer

---

# Chordpedia Brand Personality

Chordpedia should feel:

* Creative
* Community-driven
* Friendly
* Modern
* Music-focused
* Authentic
* Accessible to beginners and professionals alike

The design should represent Nepal’s growing digital music ecosystem while remaining globally modern.