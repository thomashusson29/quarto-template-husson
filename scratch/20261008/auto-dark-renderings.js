/*
 * auto-dark-renderings.js
 *
 * Runs at end of <body> for both HTML documents and RevealJS presentations.
 *
 * Purpose:
 *   For each <img> on the page, probe for a *-auto-dark.* companion image
 *   generated at render time by auto-dark-setup.R via magick.
 *
 *   When a companion exists, keep a single DOM image and swap its src/data-src
 *   between the light and dark files according to the active theme. This avoids
 *   duplicated figures in documents where CSS is not loaded early enough or
 *   when the viewer caches an older stylesheet.
 *
 * Companion URL convention:
 *   "fig-1.png"  -> "fig-1-auto-dark.png"  (primary companion path)
 *   "fig-1.png"  -> "fig-2.png"            (secondary numbered sibling)
 *
 * Opt-out:
 *   Add .auto-dark-no-filter to an image or set chunk option
 *   `class.output = "auto-dark-no-filter"` to skip companion switching.
 *
 * Re-runs on:
 *   DOMContentLoaded, window load, theme class changes, and the
 *   "auto-dark-change" custom event fired by RevealJS theme switching.
 */
(function () {

  /* -- 1. URL helpers ----------------------------------------------------- */

  function source(image) {
    return image.getAttribute("data-src") || image.getAttribute("src") || "";
  }

  function sourceAttribute(image) {
    return image.getAttribute("data-src") ? "data-src" : "src";
  }

  function companionUrls(url) {
    if (!url || /^data:/i.test(url)) return [];

    var autoDark = url.replace(
      /(\.(?:png|jpe?g|webp|svg))(?:([?#].*)?)$/i,
      "-auto-dark$1$2"
    );
    var numbered = url.replace(
      /-1(\.(?:png|jpe?g|webp|svg))(?:([?#].*)?)$/i,
      "-2$1$2"
    );

    var urls = [];
    if (autoDark && autoDark !== url) urls.push(autoDark);
    if (numbered && numbered !== url && !urls.includes(numbered)) urls.push(numbered);
    return urls;
  }


  /* -- 2. Theme detection ------------------------------------------------- */

  function isDarkMode() {
    var body = document.body;
    var html = document.documentElement;

    return (
      body.classList.contains("quarto-dark") ||
      body.classList.contains("auto-dark-theme-dark") ||
      html.classList.contains("auto-dark-theme-dark") ||
      html.getAttribute("data-bs-theme") === "dark" ||
      html.getAttribute("data-auto-dark-theme") === "dark"
    );
  }


  /* -- 3. Single-image source swapping ----------------------------------- */

  function setImageSource(image, url) {
    var attr = sourceAttribute(image);

    image.setAttribute(attr, url);
    if (image.hasAttribute("src")) {
      image.setAttribute("src", url);
    }
    if (image.hasAttribute("data-src")) {
      image.setAttribute("data-src", url);
    }
  }

  function applyTheme(image) {
    if (!image.dataset.autoDarkLightSource ||
        !image.dataset.autoDarkDarkSource) {
      return;
    }

    setImageSource(
      image,
      isDarkMode()
        ? image.dataset.autoDarkDarkSource
        : image.dataset.autoDarkLightSource
    );
  }


  /* -- 4. Companion probing ---------------------------------------------- */

  function probeCompanions(image, urls, index) {
    if (index >= urls.length) return;

    var darkSource = urls[index];
    var probe = new Image();

    probe.onload = function () {
      image.dataset.autoDarkDarkSource = darkSource;
      image.classList.add("auto-dark-no-filter");
      applyTheme(image);
    };
    probe.onerror = function () {
      probeCompanions(image, urls, index + 1);
    };
    probe.src = new URL(darkSource, document.baseURI).href;
  }


  /* -- 5. Per-image setup ------------------------------------------------- */

  function installForImage(image) {
    if (image.dataset.autoDarkRenderingChecked === "true") {
      applyTheme(image);
      return;
    }
    if (image.classList.contains("auto-dark-no-filter")) return;
    if (image.classList.contains("auto-dark-render-light")) return;
    if (image.classList.contains("auto-dark-render-dark")) return;

    var lightSource = source(image);
    var candidates = companionUrls(lightSource);
    if (!candidates.length) return;

    image.dataset.autoDarkRenderingChecked = "true";
    image.dataset.autoDarkLightSource = lightSource;

    probeCompanions(image, candidates, 0);
  }


  /* -- 6. Boot and theme observation ------------------------------------- */

  function boot() {
    document.querySelectorAll("img[src], img[data-src]").forEach(installForImage);
  }

  function observeThemeChanges() {
    var observer = new MutationObserver(boot);

    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class", "data-bs-theme", "data-auto-dark-theme"]
    });

    if (document.body) {
      observer.observe(document.body, {
        attributes: true,
        attributeFilter: ["class", "data-auto-dark-theme"]
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      boot();
      observeThemeChanges();
    });
  } else {
    boot();
    observeThemeChanges();
  }

  window.addEventListener("load", boot);
  window.addEventListener("auto-dark-change", boot);
})();
