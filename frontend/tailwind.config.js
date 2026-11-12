/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      colors: {
        sand: {
          50: '#FAF9F6',
          100: '#F5F4EF',
          200: '#EAE8DE',
          300: '#DDD9CB',
        },
        obsidian: '#111111',
        paypal: {
          blue: "#003087",
          light: "#0070BA",
          dark: "#001C64",
          gold: "#FFC439",
        },
      },
    },
  },
  plugins: [],
}
