/*
 * auto-dark-reveal.js
 *
 * Runs at end of <body> for RevealJS presentations.
 *
 * Responsibilities:
 *   1. Read the persisted theme and apply it (dark/light classes + button state).
 *   2. Install the ☾/☀ toggle button in the top-right corner.
 *   3. Persist the chosen theme to localStorage on toggle.
 *   4. Synchronize Reveal's light/dark background contrast classes.
 *   5. Trigger Reveal.layout() after theme change to fix slide sizing.
 *   6. Notify auto-dark-renderings.js after theme changes.
 *
 * Execution order:
 *   1. auto-dark-reveal-init.js  — runs synchronously in <head>
 *   2. auto-dark-reveal.js       — this file, runs at end of <body>
 *   3. auto-dark-renderings.js   — runs at end of <body>, swaps figure sources
 *
 * Theme classes managed:
 *   html / body:
 *     .auto-dark-theme-dark  / .auto-dark-theme-light
 *     .quarto-dark           / .quarto-light
 *   data-auto-dark-theme attribute: "dark" | "light"
 */
(function () {
  var storageKey = "quarto-auto-dark-theme";
  var root       = document.documentElement;
  var buttonId   = "auto-dark-switch";


  /* ── 1. Theme persistence helpers ───────────────────────────────────────── */

  function storedTheme() {
    try {
      var saved = window.localStorage.getItem(storageKey);
      if (saved === "dark" || saved === "light") {
        return saved;
      }
    } catch (error) {}

    // Fall back to the class already set by auto-dark-reveal-init.js.
    return root.getAttribute("data-auto-dark-theme") === "dark" ? "dark" : "light";
  }

  function persistTheme(theme) {
    try {
      window.localStorage.setItem(storageKey, theme);
    } catch (error) {}
  }


  /* ── 2. DOM class helpers ───────────────────────────────────────────────── */

  function setClass(element, theme) {
    if (!element) return;
    element.classList.toggle("auto-dark-theme-dark",  theme === "dark");
    element.classList.toggle("auto-dark-theme-light", theme === "light");
    element.classList.toggle("quarto-dark",           theme === "dark");
    element.classList.toggle("quarto-light",          theme === "light");
    element.setAttribute("data-auto-dark-theme", theme);
  }

  /* Reveal adds has-dark-background / has-light-background at startup.
   * Those classes control inherited text colour. They otherwise remain stale
   * after a runtime theme switch and can produce white text on a light slide.
   * Preserve slides that declare their own explicit background. */
  function hasExplicitBackground(slide) {
    return [
      "data-background-color",
      "data-background-image",
      "data-background-video",
      "data-background-iframe",
      "data-background-gradient"
    ].some(function (attribute) {
      return slide.hasAttribute(attribute);
    });
  }

  function syncRevealContrastClasses(theme) {
    var isDark = theme === "dark";
    var reveal = document.querySelector(".reveal");

    if (reveal) {
      reveal.classList.toggle("has-dark-background", isDark);
      reveal.classList.toggle("has-light-background", !isDark);
    }

    document.querySelectorAll(".reveal .slides section").forEach(function (slide) {
      if (hasExplicitBackground(slide)) return;
      slide.classList.toggle("has-dark-background", isDark);
      slide.classList.toggle("has-light-background", !isDark);
    });
  }


  /* ── 3. Reveal.js layout trigger ───────────────────────────────────────── */

  // Call after theme changes that may shift slide dimensions.
  function revealLayout() {
    if (window.Reveal && typeof window.Reveal.layout === "function") {
      window.setTimeout(function () {
        window.Reveal.layout();
      }, 60);
    }
  }


  /* ── 4. Apply theme ─────────────────────────────────────────────────────── */

  function setTheme(theme, persist) {
    var safeTheme = theme === "dark" ? "dark" : "light";
    setClass(root, safeTheme);
    setClass(document.body, safeTheme);
    syncRevealContrastClasses(safeTheme);

    // Update button state.
    var button = document.getElementById(buttonId);
    if (button) {
      var isDark = safeTheme === "dark";
      button.dataset.autoDarkTarget = isDark ? "light" : "dark";
      button.title = isDark ? "Switch to light mode" : "Switch to dark mode";
      button.setAttribute("aria-label",   button.title);
      button.setAttribute("aria-pressed", String(isDark));
    }

    if (persist) {
      persistTheme(safeTheme);
    }

    revealLayout();

    // Notify auto-dark-renderings.js and any other listeners.
    window.dispatchEvent(
      new CustomEvent("auto-dark-change", { detail: { theme: safeTheme } })
    );
  }


  /* ── 5. Install ☾/☀ toggle button ──────────────────────────────────────── */

  function installButton() {
    if (!document.querySelector(".reveal") || document.getElementById(buttonId)) {
      return;
    }

    var button = document.createElement("button");
    button.id        = buttonId;
    button.className = "auto-dark-switch";
    button.type      = "button";
    button.innerHTML = '<span class="auto-dark-switch-icon" aria-hidden="true"></span>';

    button.addEventListener("click", function () {
      var nextTheme = root.getAttribute("data-auto-dark-theme") === "dark" ? "light" : "dark";
      setTheme(nextTheme, true);
    });

    document.body.appendChild(button);
  }


  /* ── Boot ────────────────────────────────────────────────────────────────── */

  function boot() {
    installButton();
    setTheme(storedTheme(), false);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
