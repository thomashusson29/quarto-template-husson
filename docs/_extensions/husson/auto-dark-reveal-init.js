/*
 * auto-dark-reveal-init.js
 *
 * IMPORTANT: This script runs synchronously in <head> (via include-in-header),
 * BEFORE the page body is painted. It must stay small and fast.
 *
 * Purpose:
 *   Read the user's preferred theme (URL param → localStorage → OS setting)
 *   and set the matching CSS class on <html> immediately, preventing a
 *   flash-of-wrong-theme (FOUT) when the page loads.
 *
 * Execution order (do not change):
 *   1. auto-dark-reveal-init.js  — runs synchronously in <head> (this file)
 *   2. auto-dark-reveal.js       — runs at end of <body>, installs button
 *   3. auto-dark-renderings.js   — runs at end of <body>, swaps figure sources
 *
 * Classes added to <html>:
 *   .auto-dark-theme-dark   when dark mode is active
 *   .auto-dark-theme-light  when light mode is active
 *
 * Also sets data-auto-dark-theme attribute for later scripts to read.
 */
(function () {
  var storageKey = "quarto-auto-dark-theme";
  var root = document.documentElement;

  /* -- Determine the preferred theme ------------------------------------ */

  function preferredTheme() {
    try {
      // 1. Allow URL parameter override: ?theme=dark or ?theme=light
      var params = new URLSearchParams(window.location.search);
      var queryTheme = params.get("theme");
      if (queryTheme === "dark" || queryTheme === "light") {
        return queryTheme;
      }

      // 2. Use persisted preference from previous visit.
      var saved = window.localStorage.getItem(storageKey);
      if (saved === "dark" || saved === "light") {
        return saved;
      }

      // 3. Fall back to OS-level prefers-color-scheme.
      if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
        return "dark";
      }
    } catch (error) {
      // localStorage may be blocked in some environments — fail silently.
    }

    return "light";
  }

  /* ── Apply theme class immediately ───────────────────────────────────── */

  var theme = preferredTheme();
  root.classList.add(theme === "dark" ? "auto-dark-theme-dark" : "auto-dark-theme-light");
  root.setAttribute("data-auto-dark-theme", theme);
})();
