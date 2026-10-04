/*
 * navigation-reveal.js
 * Gestionnaire client de la barre de navigation hierarchique Quarto RevealJS
 * Extension Husson (Variante A : fil d'Ariane sobre H1 | H2 › H3)
 */

(function () {
  var navbarId = "husson-reveal-navbar";
  var navbar = null;
  var slideTargets = {
    h1: {},
    crumbs: {}
  };

  function createNavbar() {
    if (document.getElementById(navbarId)) {
      navbar = document.getElementById(navbarId);
      return;
    }
    navbar = document.createElement("div");
    navbar.id = navbarId;
    navbar.className = "husson-reveal-navbar husson-nav-hidden";
    navbar.setAttribute("aria-label", "Navigation hierarchique");

    var container = document.querySelector(".reveal") || document.body;
    container.appendChild(navbar);
  }

  function recordSlideTarget(slide, h, v) {
    var h1 = slide.dataset.navH1;
    if (h1 && !slideTargets.h1[h1]) {
      slideTargets.h1[h1] = { h: h, v: v };
    }

    var active = slide.dataset.navActive;
    if (active && !slideTargets.crumbs[active]) {
      slideTargets.crumbs[active] = { h: h, v: v };
    }

    var innerNavs = slide.querySelectorAll("[data-nav-active]");
    innerNavs.forEach(function (el) {
      var act = el.dataset.navActive;
      if (act && !slideTargets.crumbs[act]) {
        slideTargets.crumbs[act] = { h: h, v: v };
      }
    });
  }

  function indexSlides() {
    if (!window.Reveal) return;
    slideTargets = { h1: {}, crumbs: {} };

    var horizontalSlides = document.querySelectorAll(".reveal .slides > section");
    horizontalSlides.forEach(function (hSection, hIndex) {
      var verticalSlides = hSection.querySelectorAll("section");
      if (verticalSlides.length > 0) {
        verticalSlides.forEach(function (vSection, vIndex) {
          recordSlideTarget(vSection, hIndex, vIndex);
        });
      } else {
        recordSlideTarget(hSection, hIndex, 0);
      }
    });
  }

  function getElementNavData(el) {
    if (!el || !el.dataset || !el.dataset.navH1) return null;
    var bcArray = [];
    if (el.dataset.navBc) {
      try {
        bcArray = JSON.parse(el.dataset.navBc);
      } catch (e) {
        bcArray = [];
      }
    }
    return {
      h1: el.dataset.navH1,
      bc: bcArray,
      active: el.dataset.navActive || "",
      hidden: el.dataset.navHidden === "true"
    };
  }

  function findSlideNavData(slide) {
    var cur = slide;
    while (cur) {
      if (cur.dataset && cur.dataset.navHidden === "true") {
        return { hidden: true };
      }

      var innerNavs = cur.querySelectorAll("[data-nav-bc]");
      if (innerNavs.length > 0) {
        var deepest = innerNavs[innerNavs.length - 1];
        var innerData = getElementNavData(deepest);
        if (innerData) return innerData;
      }

      var selfData = getElementNavData(cur);
      if (selfData) return selfData;

      if (cur.previousElementSibling && cur.previousElementSibling.tagName === "SECTION") {
        cur = cur.previousElementSibling;
      } else if (cur.parentElement && cur.parentElement.tagName === "SECTION" && cur.parentElement.previousElementSibling) {
        cur = cur.parentElement.previousElementSibling;
      } else {
        break;
      }
    }
    return null;
  }

  function updateNavbar(currentSlide) {
    if (!navbar) {
      createNavbar();
    }
    if (!navbar || !currentSlide) return;

    // Masquage sur la diapositive de titre ou les intercalaires explicites
    if (
      currentSlide.id === "title-slide" ||
      currentSlide.classList.contains("title-slide") ||
      currentSlide.classList.contains("nobar")
    ) {
      navbar.classList.add("husson-nav-hidden");
      navbar.innerHTML = "";
      return;
    }

    var navData = findSlideNavData(currentSlide);
    if (!navData || navData.hidden || !navData.h1 || navData.h1 === "") {
      navbar.classList.add("husson-nav-hidden");
      navbar.innerHTML = "";
      return;
    }

    var html = "";

    // 1. Chapitre H1
    var isStandalone = (!navData.bc || navData.bc.length === 0);
    var h1Class = "husson-nav-h1" + (isStandalone ? " husson-nav-standalone" : "");
    var targetH1 = slideTargets.h1[navData.h1];
    if (targetH1) {
      h1Class += " husson-nav-clickable";
    }

    html += '<span class="' + h1Class + '" data-nav-target="h1" data-name="' + escapeAttr(navData.h1) + '">' +
            escapeHtml(navData.h1) + '</span>';

    // 2. Fil d'Ariane si present
    if (!isStandalone) {
      html += '<span class="husson-nav-bar-sep">|</span>';
      html += '<span class="husson-nav-bc">';

      for (var i = 0; i < navData.bc.length; i++) {
        var crumb = navData.bc[i];
        var isLast = (i === navData.bc.length - 1);
        var crumbClass = "husson-nav-crumb" + (isLast ? " husson-nav-active" : "");
        var targetCrumb = slideTargets.crumbs[crumb];
        if (targetCrumb && !isLast) {
          crumbClass += " husson-nav-clickable";
        }

        if (i > 0) {
          html += '<span class="husson-nav-arrow">›</span>';
        }

        html += '<span class="' + crumbClass + '" data-nav-target="crumb" data-name="' + escapeAttr(crumb) + '">' +
                escapeHtml(crumb) + '</span>';
      }

      html += '</span>';
    }

    navbar.innerHTML = html;
    navbar.classList.remove("husson-nav-hidden");

    attachClickHandlers();
  }

  function attachClickHandlers() {
    if (!navbar || !window.Reveal) return;

    var clickables = navbar.querySelectorAll(".husson-nav-clickable");
    clickables.forEach(function (el) {
      el.addEventListener("click", function (e) {
        e.preventDefault();
        var type = el.getAttribute("data-nav-target");
        var name = el.getAttribute("data-name");
        var target = (type === "h1") ? slideTargets.h1[name] : slideTargets.crumbs[name];
        if (target && typeof window.Reveal.slide === "function") {
          window.Reveal.slide(target.h, target.v);
        }
      });
    });
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function escapeAttr(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function init() {
    createNavbar();

    if (window.Reveal) {
      if (typeof window.Reveal.isReady === "function" && window.Reveal.isReady()) {
        indexSlides();
        updateNavbar(window.Reveal.getCurrentSlide());
      }

      window.Reveal.on("ready", function (event) {
        indexSlides();
        updateNavbar(event.currentSlide);
      });

      window.Reveal.on("slidechanged", function (event) {
        updateNavbar(event.currentSlide);
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
