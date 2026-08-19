import "@testing-library/jest-dom";

// jsdom doesn't implement the Blob URL APIs — used by CSV download actions
// (BatchPredictionPanel, ReportsPage) via `URL.createObjectURL`.
if (typeof window !== "undefined") {
  if (!window.URL.createObjectURL) {
    window.URL.createObjectURL = jest.fn(() => "blob:mock-url");
  }
  if (!window.URL.revokeObjectURL) {
    window.URL.revokeObjectURL = jest.fn();
  }
}

// jsdom doesn't implement IntersectionObserver — framer-motion's
// `whileInView` (used by `components/marketing/Reveal.tsx`) constructs one
// unconditionally on mount, so without this stub any test that renders a
// marketing page throws `ReferenceError: IntersectionObserver is not
// defined`. A no-op stub is enough since these tests don't assert on scroll
// behavior.
if (typeof window !== "undefined" && !window.IntersectionObserver) {
  class MockIntersectionObserver implements IntersectionObserver {
    readonly root: Element | Document | null = null;
    readonly rootMargin: string = "";
    readonly thresholds: ReadonlyArray<number> = [];
    observe() {}
    unobserve() {}
    disconnect() {}
    takeRecords(): IntersectionObserverEntry[] {
      return [];
    }
  }
  window.IntersectionObserver = MockIntersectionObserver as unknown as typeof IntersectionObserver;
  global.IntersectionObserver = window.IntersectionObserver;
}

// jsdom doesn't implement matchMedia — the theme resolver
// (`lib/theme/ThemeProvider.tsx`) reads it to fall back to OS preference.
if (typeof window !== "undefined" && !window.matchMedia) {
  window.matchMedia = (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }) as unknown as MediaQueryList;
}
