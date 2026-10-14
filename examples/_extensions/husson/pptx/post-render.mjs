#!/usr/bin/env node
// Quarto project post-render hook for the husson-pptx format.
import { existsSync, readdirSync } from 'node:fs';
import { resolve, dirname, basename, extname } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

if (process.env.HUSSON_PPTX_NESTED !== '1') {
  const outputs = (process.env.QUARTO_PROJECT_OUTPUT_FILES || '').split(/\r?\n/).filter(x => x.endsWith('.pptx'));
  const extensionDir = dirname(fileURLToPath(import.meta.url));
  for (const outputName of outputs) {
    const pptx = resolve(outputName);
    const stem = basename(outputName, extname(outputName));
    const candidates = [resolve(dirname(outputName), stem + '.qmd'), resolve(stem + '.qmd')];
    const findSources = dir => readdirSync(dir, {withFileTypes:true}).flatMap(entry => {
      if (entry.isDirectory() && !['.git','_extensions','node_modules','output','scratch'].includes(entry.name)) return findSources(resolve(dir,entry.name));
      return entry.isFile() && entry.name === stem + '.qmd' ? [resolve(dir,entry.name)] : [];
    });
    const found = [...new Set(candidates.filter(existsSync))];
    const matches = found.length ? found : findSources(process.cwd());
    if (matches.length > 1) throw new Error(`Plusieurs sources .qmd pour ${outputName}: ${matches.join(', ')}`);
    const qmd = matches[0];
    if (!qmd) throw new Error(`Source .qmd introuvable pour ${outputName}`);
    const quarto = process.env.QUARTO_PATH || 'quarto';
    const reveal = spawnSync(quarto, ['render', qmd, '--to', 'husson-revealjs'], {
      stdio: 'inherit', env: {...process.env, HUSSON_PPTX_NESTED: '1'}
    });
    if (reveal.status !== 0) throw new Error(`Rendu RevealJS échoué (${reveal.status ?? reveal.error})`);
    const htmlCandidates = [resolve(dirname(pptx), stem + '.html'), resolve(dirname(qmd), stem + '.html')];
    const html = htmlCandidates.find(existsSync);
    if (!existsSync(html)) throw new Error(`RevealJS absent : ${html}`);
    const converted = spawnSync(process.execPath, [resolve(extensionDir, 'export.mjs'), html, pptx], {stdio:'inherit'});
    if (converted.status !== 0) throw new Error(`Export PPTX échoué (${converted.status ?? converted.error})`);
  }
}
