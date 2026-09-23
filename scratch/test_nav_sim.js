const fs = require('fs');

// Charger navigation-reveal.js
const jsCode = fs.readFileSync('_extensions/husson/navigation-reveal.js', 'utf8');

// Creer un environnement minimal simulant le DOM
class MockElement {
  constructor(tagName = 'div') {
    this.tagName = tagName.toUpperCase();
    this.id = '';
    this.className = '';
    this.classList = {
      _classes: new Set(),
      add: (c) => this.classList._classes.add(c),
      remove: (c) => this.classList._classes.delete(c),
      contains: (c) => this.classList._classes.has(c)
    };
    this.dataset = {};
    this.attributes = {};
    this.children = [];
    this.parentElement = null;
    this.previousElementSibling = null;
    this.innerHTML = '';
  }

  setAttribute(k, v) { this.attributes[k] = v; }
  getAttribute(k) { return this.attributes[k] || null; }
  appendChild(child) {
    child.parentElement = this;
    if (this.children.length > 0) {
      child.previousElementSibling = this.children[this.children.length - 1];
    }
    this.children.push(child);
  }
  querySelectorAll(selector) {
    const res = [];
    function walk(el) {
      for (const ch of el.children) {
        if (selector === '[data-nav-bc]' && ch.dataset.navBc) res.push(ch);
        if (selector === '[data-nav-active]' && ch.dataset.navActive) res.push(ch);
        if (selector === '.reveal .slides > section' && ch.classList.contains('slide')) res.push(ch);
        walk(ch);
      }
    }
    walk(this);
    return res;
  }
}

// Testons la fonction updateNavbar sur les differentes diapositives
const slidesData = [
  { id: "title-slide", isTitle: true },
  { h1: "Introduction", bc: "[]", active: "Introduction" },
  { h1: "MÉTHODES", bc: "[]", active: "MÉTHODES" },
  { h1: "MÉTHODES", bc: '["Design"]', active: "Design" },
  { h1: "MÉTHODES", bc: '["Transporteurs"]', active: "Transporteurs" },
  { isContinuation: true }, // Continuation slide (---)
  { h1: "MÉTHODES", bc: '["Biologie","Inflammation","Cytokines","IL-6"]', active: "IL-6" },
  { h1: "RÉSULTATS", bc: "[]", active: "RÉSULTATS" },
  { h1: "RÉSULTATS", bc: '["Hémodynamique"]', active: "Hémodynamique" },
  { navHidden: "true" }, // nav="false"
  { h1: "CONCLUSION", bc: "[]", active: "CONCLUSION" }
];

console.log("=== SIMULATION DES RENDUS DE LA BARRE PAR DIAPOSITIVE ===");

// Reproduisons la logique de updateNavbar
function renderBar(slide, prevSlide) {
  if (slide.isTitle) return "[BARRE MASQUÉE - Diapositive de titre]";
  if (slide.navHidden === "true") return "[BARRE MASQUÉE - {nav='false'}]";

  let data = slide;
  if (slide.isContinuation) {
    data = prevSlide;
  }

  if (!data || !data.h1) return "[BARRE MASQUÉE - Sans données]";

  const bc = JSON.parse(data.bc || "[]");
  if (bc.length === 0) {
    return `[H1 seul] : ${data.h1}`;
  } else {
    const crumbsStr = bc.map((c, i) => i === bc.length - 1 ? `**${c}**` : c).join(" › ");
    return `[Fil d'Ariane] : ${data.h1} | ${crumbsStr}`;
  }
}

let prev = null;
slidesData.forEach((s, idx) => {
  const rendered = renderBar(s, prev);
  console.log(`Diapo ${idx + 1}: ${rendered}`);
  if (!s.isContinuation) prev = s;
});
