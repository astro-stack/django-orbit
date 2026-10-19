/** @type {import('tailwindcss').Config} */
// Reproduces the configuration that used to live inline in base.html
// (Tailwind Play CDN). Keep in sync with DESIGN.md.
const typeColors = [
  'cyan', 'emerald', 'slate', 'rose', 'amber', 'violet', 'orange', 'blue',
  'pink', 'lime', 'fuchsia', 'yellow', 'red', 'indigo', 'teal', 'sky', 'purple',
];

module.exports = {
  darkMode: 'class',
  content: [
    '../orbit/templates/**/*.html',
    '../orbit/static/orbit/js/**/*.js',
    // Python helpers return class names (templatetags, views).
    '../orbit/templatetags/*.py',
    '../orbit/views.py',
  ],
  // Entry-type colors are interpolated by templates
  // (bg-{{ color }}-500/10, text-{{ color }}-400) from OrbitEntry.TYPE_COLORS.
  safelist: [
    {
      pattern: new RegExp(`^(text-(${typeColors.join('|')})-400|bg-(${typeColors.join('|')})-500/10)$`),
    },
  ],
  theme: {
    extend: {
      colors: {
        orbit: {
          bg: {
            primary: '#020617',   /* slate-950 */
            secondary: '#0f172a', /* slate-900 */
            tertiary: '#1e293b',  /* slate-800 */
          },
          border: '#334155',        /* slate-700 */
          text: {
            primary: '#f1f5f9',   /* slate-100 */
            secondary: '#94a3b8', /* slate-400 */
            muted: '#64748b',     /* slate-500 */
          },
          accent: {
            cyan: '#22d3ee',
            amber: '#fbbf24',
            rose: '#fb7185',
            emerald: '#34d399',
            violet: '#a78bfa',
          },
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        glow: {
          '0%': { boxShadow: '0 0 5px rgba(34, 211, 238, 0.3)' },
          '100%': { boxShadow: '0 0 20px rgba(34, 211, 238, 0.6)' },
        },
      },
    },
  },
};
