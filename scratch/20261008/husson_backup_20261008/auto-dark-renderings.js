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

    if (
      (body && (
        body.classList.contains("quarto-dark") ||
        body.classList.contains("auto-dark-theme-dark")
      )) ||
      html.classList.contains("auto-dark-theme-dark") ||
      html.getAttribute("data-bs-theme") === "dark" ||
      html.getAttribute("data-auto-dark-theme") === "dark"
    ) {
      return true;
    }

    if (
      (body && (
        body.classList.contains("quarto-light") ||
        body.classList.contains("auto-dark-theme-light")
      )) ||
      html.classList.contains("auto-dark-theme-light") ||
      html.getAttribute("data-bs-theme") === "light" ||
      html.getAttribute("data-auto-dark-theme") === "light"
    ) {
      return false;
    }

    return Boolean(
      window.matchMedia &&
      window.matchMedia("(prefers-color-scheme: dark)").matches
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


  /* -- 6. Interactive Plotly (2D & 3D) synchronization -------------------- */

  var ONE_DARK_PALETTE = [
    "#61afef",
    "#98c379",
    "#e06c75",
    "#c678dd",
    "#d19a66",
    "#56b6c2",
    "#e5c07b"
  ];

  var DEFAULT_TRACE_COLOR_RE = /^(?:#636efa|#ef553b|#00cc96|#ab63fa|#ffa15a|#19d3f3|#ff6692|#b6e880|#ff97ff|#fecb52|#1f77b4|#ff7f0e|#2ca02c|#d62728|#9467bd|#8c564b|#e377c2|#7f7f7f|#bcbd22|#17becf|#66c2a5|#fc8d62|#8da0cb|#e78ac3|#a6d854|#ffd92f|#e5c494|#b3b3b3|rgba?\(\s*(?:102\s*,\s*194\s*,\s*165|252\s*,\s*141\s*,\s*98|141\s*,\s*160\s*,\s*203|231\s*,\s*138\s*,\s*195|166\s*,\s*216\s*,\s*84|255\s*,\s*217\s*,\s*47|229\s*,\s*196\s*,\s*148|179\s*,\s*179\s*,\s*179|31\s*,\s*119\s*,\s*180|255\s*,\s*127\s*,\s*14|44\s*,\s*160\s*,\s*44|214\s*,\s*39\s*,\s*40)\b)/i;

  var plotlyRetryCount = 0;
  var plotlyRetryTimer = null;

  function ensureOneDarkTraceColors(el) {
    if (!el || el.dataset.autoDarkPlotlyPalette === "true") return;
    if (!Array.isArray(el.data) || !window.Plotly || typeof window.Plotly.restyle !== "function") return;

    el.dataset.autoDarkPlotlyPalette = "true";

    el.data.forEach(function (trace, idx) {
      if (!trace) return;
      var replacement = ONE_DARK_PALETTE[idx % ONE_DARK_PALETTE.length];
      var restylePatch = {};
      var changed = false;

      if (trace.marker && typeof trace.marker.color === "string" &&
          DEFAULT_TRACE_COLOR_RE.test(trace.marker.color.trim())) {
        restylePatch["marker.color"] = replacement;
        changed = true;
      }
      if (trace.line && typeof trace.line.color === "string" &&
          DEFAULT_TRACE_COLOR_RE.test(trace.line.color.trim())) {
        restylePatch["line.color"] = replacement;
        changed = true;
      }

      if (changed) {
        try {
          window.Plotly.restyle(el, restylePatch, [idx]);
        } catch (e) {}
      }
    });
  }

  function syncPlotlyElement(el) {
    if (!el) return true;
    el.classList.add("auto-dark-no-filter");

    hookPlotlyGlobal();

    if (!window.Plotly || typeof window.Plotly.relayout !== "function") return false;
    if (!el._fullLayout) return false;

    ensureOneDarkTraceColors(el);

    var dark = isDarkMode();
    var themeKey = dark ? "dark" : "light";
    var fg = dark ? "#abb2bf" : "#212529";
    var fgStrong = dark ? "#e6edf3" : "#131516";
    var grid2d = dark ? "rgba(128,128,128,0.25)" : "rgba(128,128,128,0.22)";
    var line2d = dark ? "rgba(128,128,128,0.40)" : "rgba(128,128,128,0.40)";
    var grid3d = dark ? "#5c6370" : "#9aa5b1";
    var line3d = dark ? "#8b949e" : "#57606a";

    if (el.dataset.autoDarkPlotlyTheme === themeKey) return true;
    el.dataset.autoDarkPlotlyTheme = themeKey;

    var update = {
      "colorway": ONE_DARK_PALETTE,
      "paper_bgcolor": "rgba(0,0,0,0)",
      "plot_bgcolor": "rgba(0,0,0,0)",
      "font.color": fg,
      "title.font.color": fgStrong,
      "legend.bgcolor": "rgba(0,0,0,0)",
      "legend.bordercolor": "rgba(0,0,0,0)",
      "legend.font.color": fg,
      "legend.title.font.color": fgStrong
    };

    var fullKeys = Object.keys(el._fullLayout || {});
    var sceneKeys = fullKeys.filter(function (k) { return /^scene\d*$/.test(k); });
    if (sceneKeys.length === 0 && el.layout && el.layout.scene) {
      sceneKeys = ["scene"];
    }

    if (sceneKeys.length > 0) {
      sceneKeys.forEach(function (sc) {
        update[sc + ".bgcolor"] = "rgba(0,0,0,0)";
        ["xaxis", "yaxis", "zaxis"].forEach(function (ax) {
          update[sc + "." + ax + ".backgroundcolor"] = "rgba(0,0,0,0)";
          update[sc + "." + ax + ".showbackground"] = false;
          update[sc + "." + ax + ".showgrid"] = true;
          update[sc + "." + ax + ".showline"] = true;
          update[sc + "." + ax + ".gridcolor"] = grid3d;
          update[sc + "." + ax + ".zerolinecolor"] = line3d;
          update[sc + "." + ax + ".linecolor"] = line3d;
          update[sc + "." + ax + ".tickcolor"] = line3d;
          update[sc + "." + ax + ".tickfont.color"] = fg;
          update[sc + "." + ax + ".title.font.color"] = fgStrong;
        });
      });
    } else {
      var axisKeys = fullKeys.filter(function (k) { return /^[xy]axis\d*$/.test(k); });
      if (axisKeys.length === 0) axisKeys = ["xaxis", "yaxis"];
      axisKeys.forEach(function (ax) {
        update[ax + ".gridcolor"] = grid2d;
        update[ax + ".zerolinecolor"] = line2d;
        update[ax + ".linecolor"] = line2d;
        update[ax + ".tickfont.color"] = fg;
        update[ax + ".title.font.color"] = fgStrong;
      });
    }

    try {
      window.Plotly.relayout(el, update);
    } catch (e) {}
    return true;
  }

  function hookPlotlyGlobal() {
    if (!window.Plotly || window.Plotly._autoDarkHooked) return;
    window.Plotly._autoDarkHooked = true;

    ["newPlot", "react"].forEach(function (method) {
      var orig = window.Plotly[method];
      if (typeof orig !== "function") return;
      window.Plotly[method] = function (gd) {
        var result = orig.apply(this, arguments);
        var target = typeof gd === "string" ? document.getElementById(gd) : gd;
        if (result && typeof result.then === "function") {
          result.then(function (plotEl) {
            var el = plotEl || target;
            if (el) {
              delete el.dataset.autoDarkPlotlyTheme;
              syncPlotlyElement(el);
            }
          });
        } else if (target) {
          setTimeout(function () {
            delete target.dataset.autoDarkPlotlyTheme;
            syncPlotlyElement(target);
          }, 20);
        }
        return result;
      };
    });
  }

  function syncPlotlyWidgets(forceResize) {
    hookPlotlyGlobal();

    var nodes = document.querySelectorAll(".js-plotly-plot, .plotly-graph-div, .plotly.html-widget");
    var pending = false;

    nodes.forEach(function (el) {
      if (forceResize) {
        delete el.dataset.autoDarkPlotlyTheme;
        if (window.Plotly && window.Plotly.Plots && typeof window.Plotly.Plots.resize === "function") {
          try {
            window.Plotly.Plots.resize(el);
          } catch (e) {}
        }
      }
      if (!syncPlotlyElement(el)) {
        pending = true;
      }
    });

    if (pending && plotlyRetryCount < 40) {
      plotlyRetryCount += 1;
      if (plotlyRetryTimer) clearTimeout(plotlyRetryTimer);
      plotlyRetryTimer = setTimeout(function () {
        syncPlotlyWidgets(false);
      }, 100);
    } else if (!pending) {
      plotlyRetryCount = 0;
    }
  }


  /* -- 7. Boot and theme observation ------------------------------------- */

  function boot() {
    hookPlotlyGlobal();
    document.querySelectorAll("img[src], img[data-src]").forEach(installForImage);
    syncPlotlyWidgets(false);
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

    if (window.matchMedia) {
      try {
        var mq = window.matchMedia("(prefers-color-scheme: dark)");
        if (typeof mq.addEventListener === "function") {
          mq.addEventListener("change", boot);
        } else if (typeof mq.addListener === "function") {
          mq.addListener(boot);
        }
      } catch (e) {}
    }

    if (window.HTMLWidgets && typeof window.HTMLWidgets.addPostRenderHandler === "function") {
      window.HTMLWidgets.addPostRenderHandler(function () {
        syncPlotlyWidgets(false);
        setTimeout(function () { syncPlotlyWidgets(false); }, 120);
      });
    }

    if (window.Reveal && typeof window.Reveal.on === "function") {
      window.Reveal.on("ready", function () {
        setTimeout(function () { syncPlotlyWidgets(true); }, 100);
      });
      window.Reveal.on("slidechanged", function () {
        setTimeout(function () { syncPlotlyWidgets(true); }, 60);
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      boot();
      observeThemeChanges();
      setTimeout(function () { syncPlotlyWidgets(false); }, 250);
    });
  } else {
    boot();
    observeThemeChanges();
    setTimeout(function () { syncPlotlyWidgets(false); }, 250);
  }

  window.addEventListener("load", function () {
    boot();
    setTimeout(function () { syncPlotlyWidgets(true); }, 200);
  });
  window.addEventListener("auto-dark-change", boot);
})();

