// Copies the pinned third-party dist files from node_modules into
// orbit/static/orbit/vendor (and fonts into ../fonts). Versions come from
// package.json; licenses are recorded in orbit/static/orbit/vendor/LICENSES.md.
import { copyFileSync, mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const nm = (p) => resolve(here, 'node_modules', p);
const out = resolve(here, '../orbit/static/orbit');

const files = [
  ['htmx.org/dist/htmx.min.js', 'vendor/htmx.min.js'],
  ['alpinejs/dist/cdn.min.js', 'vendor/alpine.min.js'],
  ['@alpinejs/collapse/dist/cdn.min.js', 'vendor/alpine-collapse.min.js'],
  ['apexcharts/dist/apexcharts.min.js', 'vendor/apexcharts.min.js'],
  // Served as <link id="apexcharts-css">; ApexCharts then skips injecting an inline <style>.
  ['apexcharts/dist/apexcharts.css', 'vendor/apexcharts.css'],
  [
    '@fontsource-variable/inter/files/inter-latin-wght-normal.woff2',
    'fonts/inter-latin-wght-normal.woff2',
  ],
  [
    '@fontsource-variable/jetbrains-mono/files/jetbrains-mono-latin-wght-normal.woff2',
    'fonts/jetbrains-mono-latin-wght-normal.woff2',
  ],
];

for (const [from, to] of files) {
  const dest = resolve(out, to);
  mkdirSync(dirname(dest), { recursive: true });
  copyFileSync(nm(from), dest);
  console.log(`vendored ${to}`);
}
