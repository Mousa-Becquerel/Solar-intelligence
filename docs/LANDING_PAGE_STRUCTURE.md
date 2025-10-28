# Landing Page Structure Documentation

## Overview
This document describes the structure and organization of the Solarintelligence landing page to facilitate understanding and future migrations.

---

## File Structure

```
templates/
  └── landing.html          # Main landing page template
static/
  ├── css/
  │   └── landing.css       # Landing page specific styles
  └── js/
      └── landing.js        # Landing page JavaScript (counters, animations)
```

---

## Page Sections

### 1. Hero Section (`#home`)
**Purpose**: First impression, primary call-to-action, and navigation

**Layout**: Two-column design (Desktop only)

**Components**:
- **Navigation Bar**
  - Logo (left): `new_logo.svg` with subtitle
  - Navigation Links (center): Home, AI Agents, Data Coverage, How It Works
  - Action Buttons (right): Sign In, Contact Us

- **Left Column: Hero Content**
  - Main headline: "THE FUTURE IS SOLAR, AND IT IS INTELLIGENT"
  - Subtitle: "Advanced analytics for solar intelligence..."
  - CTA Buttons: START NOW, EXPLORE

- **Right Column: Animated Agent Showcase** (Desktop only)
  - 3 Rotating agent interaction cards:
    1. **Alex (Market Agent)**: Shows market analysis example
    2. **Maya (Price Agent)**: Shows pricing comparison example
    3. **Emma (News Agent)**: Shows news/policy update example
  - Each card displays:
    - Agent avatar with gradient background
    - Agent name and status
    - User question in gray bubble
    - Agent response in golden gradient bubble
  - Cards fade in/out every 4 seconds with stacked positioning effect

**Key Classes**:
- `.logo-with-subtitle` - Logo container
- `.nav-link` - Navigation link styling with hover effects
- `.btn-primary` - Primary call-to-action button
- `.btn-secondary` - Secondary button
- `.agent-showcase-container` - Container for animated cards
- `.agent-showcase-card` - Individual agent interaction card
- `.user-message` - User question bubble
- `.agent-response` - Agent response bubble

**JavaScript**:
- `initAgentShowcase()` - Cycles through cards with fade animations

---

### 2. Data Statistics Section (`#data`)
**Purpose**: Showcase data coverage and credibility with impressive numbers

**Components**:
- Section Title: "Our Data Coverage"
- Statistics Grid (5 items):
  1. Total Data Records (18K+)
  2. Countries & Regions (38)
  3. Solar Components (9)
  4. Data Timeline (2015-2030)
  5. Price Data Points (16K+)

**Key Features**:
- Animated counters (JavaScript driven)
- Hover effects on statistics
- White background card on gradient

**Key Classes**:
- `.counter` - Animated number counter
- `.stats-number` - Gradient text styling

---

### 3. AI Agents Section (`#agents`)
**Purpose**: Introduce the AI agents and their capabilities

**Components**:
- Section Title: "Meet Your AI Agents"
- Agent Cards (3 agents):
  1. **Alex** - Market Analysis
     - Icon: Chart/Graph
     - Capabilities: Market trends, capacity data, forecasts

  2. **Maya** - Price Analysis
     - Icon: Dollar sign
     - Capabilities: Module pricing, cost breakdowns, comparisons

  3. **Luna** - News Analysis
     - Icon: Newspaper
     - Capabilities: Industry news, policy updates, developments

**Key Classes**:
- `.agent-card` - Glass-morphism card with hover lift effect
- `.agent-icon` - Icon container with gradient background

---

### 4. How It Works Section (`#workflow`)
**Purpose**: Explain the user workflow and process

**Components**:
- Section Title: "How It Works"
- Workflow Steps (4 steps):
  1. **Define Business Case**
     - Icon: Target
     - Description: Outline research objectives

  2. **Ask & Retrieve Data**
     - Icon: Database
     - Description: Natural language queries

  3. **Create & Modify Plots**
     - Icon: Chart
     - Description: Generate visualizations

  4. **Generate Report**
     - Icon: Document
     - Description: Export professional reports

**Key Features**:
- Sequential step numbers (color-coded)
- Icon + title + description format
- White background cards with subtle hover

**Key Classes**:
- `.workflow-step` - Individual step container
- Step numbers: Color gradients (orange → blue → green → purple)

---

### 5. Footer
**Purpose**: Links, copyright, and additional navigation

**Components**:
- Logo
- Links: European PV Data Hub, Becquerel Institute, Market Reports, Contact
- Copyright notice

---

## Design System

### Color Palette

```css
Primary Colors:
- Orange: #f97316 → #ea580c (buttons, accents)
- Golden: #E9A544 → #E8BF4F (highlights, hover states)

Background Gradient:
- Dark blue/purple: #0a1850 → #1e1b4b → #312e81 → #3730a3
- Accent overlays: rgba(251, 191, 36, 0.15), rgba(139, 92, 246, 0.12)

Text Colors:
- White: #ffffff (hero section)
- Dark: #gray-900 (white sections)
- Muted: #gray-400, #gray-600
```

### Typography

```css
Font Family: 'Inter', sans-serif
Font Weights: 300, 400, 500, 600, 700, 800

Headings:
- H1 (Hero): 4xl → 7xl (responsive)
- H2 (Sections): 3xl → 4xl
- H3 (Cards): xl → 2xl

Body Text: base → lg
```

### Spacing

```css
Section Padding:
- Hero: pb-12 lg:pb-20
- Content Sections: py-24 (96px vertical)
- Compact Sections: py-12 (48px vertical)

Container: max-w-7xl (1280px)
Grid Gap: gap-6 (24px)
```

---

## JavaScript Functionality

### Counter Animation
**File**: `landing.js` (inline in template)

**Purpose**: Animate statistics numbers on page load/scroll

**Implementation**:
```javascript
// Targets elements with .counter class
// Reads data-target attribute for final value
// Reads data-suffix attribute for units (K+, etc.)
// Animates from 0 to target over ~2 seconds
```

**Usage**:
```html
<span class="counter" data-target="18" data-suffix="K+">0</span>
```

---

## Responsive Breakpoints

```css
Mobile: < 768px
  - Hide tagline
  - Reduce logo size
  - Stack elements vertically
  - Simplify navigation

Tablet: 768px - 1024px
  - 2-column grids
  - Show most content

Desktop: > 1024px
  - Full layout
  - 3-column grids for agents
  - All features visible
```

---

## Migration Guide

### To React/Next.js

1. **Component Breakdown**:
   ```
   LandingPage
   ├── Navigation
   │   ├── Logo
   │   ├── NavLinks
   │   └── ActionButtons
   ├── HeroSection
   ├── DataStatsSection
   │   └── StatCard (x5)
   ├── AgentsSection
   │   └── AgentCard (x3)
   ├── WorkflowSection
   │   └── WorkflowStep (x4)
   └── Footer
   ```

2. **State Management**:
   - No complex state needed
   - Counter animations: Use `useState` + `useEffect`
   - Scroll effects: Use `IntersectionObserver` API

3. **Styling**:
   - Keep Tailwind CSS classes
   - Move custom CSS to CSS modules or styled-components
   - Maintain color variables in theme config

### To Vue/Nuxt

1. **Component Structure**: Similar to React
2. **Data**: Use `ref()` for counters
3. **Lifecycle**: Use `onMounted()` for animations
4. **Styling**: Scoped styles or CSS modules

### To Static Site Generator (Eleventy, Hugo, etc.)

1. **Templates**: Convert Jinja2 syntax to target templating language
2. **Partials**: Break into includes/partials
3. **Static Assets**: Keep CSS/JS as-is
4. **Build**: Configure asset pipeline

---

## Assets Required

### Images
- `logos/new_logo.svg` - Main application logo
- `logos/bec_logo.svg` - Becquerel Institute logo

### External Dependencies
- Tailwind CSS: `https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css`
- Google Fonts: `Inter` font family
- No other external JavaScript libraries required

---

## Performance Considerations

1. **Image Optimization**:
   - Use SVG for logos (scalable, small file size)
   - Consider lazy loading for below-fold content

2. **CSS**:
   - Separate landing.css file (~10KB)
   - Tailwind CSS via CDN (consider self-hosting for production)

3. **JavaScript**:
   - Minimal vanilla JS for counter animations
   - No heavy frameworks on landing page

4. **Fonts**:
   - Google Fonts with `display=swap` for better loading

---

## Accessibility

### Implemented
- Semantic HTML5 elements (`<nav>`, `<section>`, `<footer>`)
- Alt text for logos
- Proper heading hierarchy (H1 → H2 → H3)
- Color contrast meets WCAG AA standards
- Focus states on interactive elements

### To Improve
- Add ARIA labels for icon-only buttons
- Ensure keyboard navigation for all interactive elements
- Add skip-to-content link
- Test with screen readers

---

## Browser Support

**Tested/Supported**:
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

**CSS Features Used**:
- CSS Grid
- Flexbox
- CSS Gradients
- CSS Transforms
- Backdrop-filter (with fallbacks)

---

## Maintenance Notes

### Common Updates

1. **Adding New Agent**:
   - Add agent card in AI Agents section
   - Update grid columns if needed (currently 3-column)
   - Add agent icon (SVG recommended)

2. **Changing Statistics**:
   - Update `data-target` in counter spans
   - Update description text

3. **Updating CTA**:
   - Modify href in button links
   - Update button text

4. **Color Theme**:
   - Update CSS variables in landing.css
   - Maintain gradient consistency

### Testing Checklist

- [ ] Test all navigation links
- [ ] Verify counter animations work
- [ ] Check responsive behavior (mobile, tablet, desktop)
- [ ] Validate hover states on all interactive elements
- [ ] Test form submissions (Contact Us)
- [ ] Verify external links open in new tabs
- [ ] Check loading performance
- [ ] Validate HTML/CSS
- [ ] Test accessibility with keyboard navigation

---

## Version History

- **v1.0** - Initial landing page with hero, stats, agents, workflow
- **v1.1** - Removed company logos slider
- **v1.2** - Updated navigation layout (full-width)
- **v1.3** - New logo integration
- **v1.4** - Extracted CSS to separate file, added documentation

---

## Contact

For questions about this structure or migration assistance:
- Technical Documentation: See `/docs` folder
- Code Repository: [Add repository URL]
- Development Team: [Add contact]
