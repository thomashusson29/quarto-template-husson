const fs = require('fs');

// Charger le HTML produit
const html = fs.readFileSync('output/tests/test_reveal_navigation.html', 'utf8');

// Extraire les sections
const sectionRegex = /<section\b([^>]*)>([\s\S]*?)<\/section>/gi;
let match;
const slides = [];

// Helper simple pour extraire les attributs
function parseAttrs(attrStr) {
  const attrs = {};
  const regex = /([a-z0-9\-]+)="([^"]*)"/gi;
  let m;
  while ((m = regex.exec(attrStr)) !== null) {
    attrs[m[1]] = m[2];
  }
  const idMatch = attrStr.match(/id="([^"]*)"/i);
  if (idMatch) attrs.id = idMatch[1];
  const classMatch = attrStr.match(/class="([^"]*)"/i);
  if (classMatch) attrs.className = classMatch[1];
  return attrs;
}

// Extraction des sections
const rawSections = html.match(/<section\b[^>]*>[\s\S]*?<\/section>/gi) || [];

console.log(`Nombre total de balises <section> : ${rawSections.length}`);

// Verifions la presence des attributs data-nav dans les sections de contenu
let navSlidesCount = 0;
for (const sec of rawSections) {
  if (sec.includes('data-nav-h1')) {
    navSlidesCount++;
    const h1Match = sec.match(/data-nav-h1="([^"]*)"/);
    const bcMatch = sec.match(/data-nav-bc="([^"]*)"/);
    const activeMatch = sec.match(/data-nav-active="([^"]*)"/);
    console.log(`Slide: H1=[${h1Match ? h1Match[1] : ''}] BC=[${bcMatch ? bcMatch[1].replace(/&quot;/g, '"') : ''}] Active=[${activeMatch ? activeMatch[1] : ''}]`);
  }
}
console.log(`Diapositives avec navigation : ${navSlidesCount}`);
