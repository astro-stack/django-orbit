// Builds a small Lucide bundle containing only the icons Orbit uses, exposed as
// the global `lucide` (API subset: createIcons). Add an icon name to `ICONS`
// whenever a template, JS file or OrbitEntry.TYPE_ICONS references a new one.
import { build } from 'esbuild';
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const ICONS = [
  "activity",
  "alert-circle",
  "alert-triangle",
  "align-left",
  "archive",
  "arrow-left",
  "arrow-right",
  "bar-chart",
  "bar-chart-2",
  "book-open",
  "bot",
  "box",
  "bug",
  "check",
  "check-circle",
  "chevron-down",
  "chevron-left",
  "chevron-right",
  "chevron-up",
  "circle",
  "clipboard-check",
  "clock",
  "code",
  "copy",
  "database",
  "download",
  "eye",
  "file-code",
  "file-text",
  "filter",
  "gauge",
  "git-branch",
  "globe",
  "hard-drive",
  "heart-pulse",
  "help-circle",
  "inbox",
  "layers",
  "layout-dashboard",
  "link",
  "loader-2",
  "lock",
  "log-in",
  "mail",
  "mouse-pointer-click",
  "orbit",
  "pause",
  "pause-circle",
  "play",
  "refresh-cw",
  "route",
  "search",
  "search-code",
  "send",
  "server",
  "shield",
  "shield-check",
  "tag",
  "terminal",
  "trash-2",
  "trending-up",
  "user",
  "x",
  "x-circle",
  "zap"
];

const pascal = (n) =>
  n.split('-').map((s) => s[0].toUpperCase() + s.slice(1)).join('');

const entry = `
import { createIcons } from 'lucide';
import { ${ICONS.map(pascal).join(', ')} } from 'lucide';
const icons = { ${ICONS.map(pascal).join(', ')} };
export function createOrbitIcons(options) {
  return createIcons({ icons, ...(options || {}) });
}
export { icons };
export { createOrbitIcons as createIcons };
`;

const outfile = resolve(here, '../orbit/static/orbit/vendor/lucide.min.js');
mkdirSync(dirname(outfile), { recursive: true });
const result = await build({
  stdin: { contents: entry, resolveDir: here, loader: 'js' },
  bundle: true,
  minify: true,
  format: 'iife',
  globalName: 'lucide',
  target: 'es2018',
  legalComments: 'none',
  banner: { js: '/*! lucide (ISC) - Orbit icon subset; see LICENSES.md */' },
  write: false,
});
writeFileSync(outfile, result.outputFiles[0].text);
console.log(`built ${outfile}`);
