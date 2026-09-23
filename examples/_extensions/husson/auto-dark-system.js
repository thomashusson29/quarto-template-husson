/*
 * auto-dark-system.js
 *
 * Runs in <head>, before Quarto's colour-scheme bootstrap script.
 *
 * The HTML format follows the browser/OS colour scheme only. Quarto stores
 * manual theme choices in localStorage under "quarto-color-scheme"; when that
 * value exists, Quarto intentionally stops reacting to prefers-color-scheme
 * changes. Clearing it before Quarto starts restores system-driven behaviour.
 */
(function () {
  var storageKey = "quarto-color-scheme";

  function clearQuartoColorSchemePreference() {
    try {
      window.localStorage.removeItem(storageKey);
    } catch (error) {
      // Ignore unavailable localStorage, e.g. privacy-restricted contexts.
    }
  }

  clearQuartoColorSchemePreference();

  if (!window.matchMedia) return;

  var query = window.matchMedia("(prefers-color-scheme: dark)");

  function onSystemColorSchemeChange() {
    clearQuartoColorSchemePreference();
    window.setTimeout(function () {
      window.dispatchEvent(new Event("auto-dark-change"));
    }, 0);
  }

  if (typeof query.addEventListener === "function") {
    query.addEventListener("change", onSystemColorSchemeChange);
  } else if (typeof query.addListener === "function") {
    query.addListener(onSystemColorSchemeChange);
  }
})();
