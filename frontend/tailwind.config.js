/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg:      '#030912',
        surface: '#060e1b',
        card:    '#0c1525',
        border:  'rgba(148,163,184,0.08)',
        accent:  '#0ea5e9',
        success: '#10b981',
        warning: '#f59e0b',
        danger:  '#ef4444',
        muted:   '#64748b',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"Fira Code"', 'Consolas', 'monospace'],
      },
    },
  },
  plugins: [],
}
