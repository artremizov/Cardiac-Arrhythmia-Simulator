/** @type {import('tailwindcss').Config} */
// Only Tailwind's base reset is used; the app's styles are in src/index.css.
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: { extend: {} },
  plugins: [],
}
