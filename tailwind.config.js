/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#0070f3',
          50: '#f0f7ff',
          100: '#e0eefe',
          200: '#b9ddfd',
          300: '#7cc2fc',
          400: '#36a1f8',
          500: '#0c84eb',
          600: '#0070f3',
          700: '#015ccb',
          800: '#0550a6',
          900: '#0a4585',
          950: '#072b57',
        },
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
  ],
} 