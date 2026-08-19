Redesign the existing ChurnAI frontend using the **attached Figma/reference images as the primary visual design reference**.

### IMPORTANT — TWO SEPARATE THEMES

The reference images represent **two separate visual designs**:

* **Dark Mode reference image → implement the Dark Mode design**
* **Light Mode reference image → implement the Light Mode design**

Do NOT simply invert the dark theme into light mode. Both themes should be individually designed and visually polished while keeping the same layout, components, and content.

### Visual Style

Match the reference images with a premium **Figma-quality AI SaaS UI**:

* Beautiful layered gradients
* Soft purple / blue / cyan accent colors
* Subtle background glow and gradients
* Professional shadows and depth
* Glass/soft-surface card treatment where appropriate
* Gradient borders and highlights
* Strong typography hierarchy
* Clean spacing and alignment
* Modern rounded cards and buttons
* Visually rich but not cluttered

The UI should feel like a **real production SaaS product**, not plain HTML/text placed inside boxes.

### Cards

Redesign existing cards according to the reference:

* Layered shading/depth
* Soft shadow
* Subtle gradient highlight
* Gradient border on hover
* Smooth lift animation on hover
* Slight glow on hover
* Cards should **drop/fade smoothly from the top when they enter the viewport**
* Keep animation subtle and professional.

### Background

Add the same type of visual depth shown in the reference:

* Subtle gradient blobs/glows
* Very light animated flowing lines
* Soft ambient lighting
* Section-to-section visual transitions

Do NOT make the background distracting or heavy.

### Public Pages

Apply the same visual design system consistently to the existing:

* Home
* About
* Features
* FAQ
* Privacy
* Terms
* Contact

Do not add new pages or invented content.

### Dark Mode

Use the attached **Dark Mode reference image** as the visual source of truth.

Dark mode should have:

* Deep navy/near-black background
* Purple/blue/cyan accent gradients
* Soft illuminated cards
* Proper contrast
* Subtle shadows/glows
* Professional dark SaaS appearance

### Light Mode

Use the attached **Light Mode reference image** as the visual source of truth.

Light mode should have:

* Clean light background
* Soft tinted gradient sections
* Purple/blue/cyan accents
* Elegant card shadows
* Clear borders
* Excellent text contrast
* Same premium visual quality as Dark Mode

Do NOT make Light Mode look like a simple white version of Dark Mode.

### Authentication-aware CTA

Keep the existing authentication behavior:

* Logged out → existing `Sign Up Free` / login CTA
* Logged in → `Go to Dashboard`
* Never show `Sign Up Free` to an already authenticated user.

Do not create or modify the authentication architecture.

### Footer

Redesign the existing footer to match the Figma visual style with proper spacing, columns, hierarchy, subtle gradients and hover states.

Use the real contact information:

* Email: `khanbahawal2004@gmail.com`
* LinkedIn: `https://www.linkedin.com/in/bahawal-khan-9b1124313`
* GitHub: `https://github.com/bahawal-khan`

Remove all placeholder contact information such as `hello@example.com`.

### Strict Constraints

* Use the attached reference images as visual guidance.
* Do not add features that do not already exist.
* Do not invent statistics, testimonials, pricing, customers, integrations, or product capabilities.
* Do not change backend functionality.
* Do not change existing routes.
* Do not replace existing content with invented content.
* Improve ONLY the frontend presentation, UX, animations, responsiveness, and visual design.
* Keep the implementation responsive on mobile, tablet, laptop, and desktop.

### Acceptance Criteria

* [ ] Dark Mode closely follows the Dark Mode reference image.
* [ ] Light Mode closely follows the Light Mode reference image.
* [ ] Both themes are individually designed, not simple color inversion.
* [ ] Figma-quality gradients, shades, shadows and visual depth are present.
* [ ] Existing cards have polished hover/lift/glow effects.
* [ ] Cards smoothly drop/fade from the top when entering the viewport.
* [ ] Background visual effects are subtle and performant.
* [ ] Home page has strong visual hierarchy and minimal unnecessary empty space.
* [ ] All public pages share the same professional design system.
* [ ] Footer is properly arranged and visually polished.
* [ ] Real GitHub, LinkedIn and Email are used.
* [ ] Logged-in users see `Go to Dashboard`, not `Sign Up Free`.
* [ ] Fully responsive.
* [ ] No hydration errors.
* [ ] No console errors.
* [ ] Existing functionality remains unchanged.
* [ ] `npm test` passes.
* [ ] `npm run build` succeeds.

**Do not treat the reference images as optional inspiration. Use them as the primary visual direction for the implementation while preserving ChurnAI's existing content and functionality.**
