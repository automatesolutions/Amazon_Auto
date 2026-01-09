/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f0f7f4',
          100: '#d4e8dd',
          200: '#a8d5ba',
          300: '#7fb069',
          400: '#6b8e5a',
          500: '#5a7c4a',
          600: '#4a6741',
          700: '#3d5535',
          800: '#2f4229',
          900: '#1f2c1b',
        },
        matcha: {
          light: '#c8e6d3',
          base: '#7fb069',
          dark: '#4a6741',
          deep: '#2f4229',
        },
        genx: {
          cream: '#f5f1e8',
          tan: '#d4c5a9',
          brown: '#8b6f47',
          charcoal: '#3a3a3a',
        },
      },
      fontFamily: {
        sans: ['var(--font-inter)', 'system-ui', 'sans-serif'],
        display: ['var(--font-poppins)', 'Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        'genx': '6px 6px 0px 0px rgba(26, 45, 23, 0.3)',
        'genx-lg': '8px 8px 0px 0px rgba(26, 45, 23, 0.35)',
      },
      backdropBlur: {
        xs: '2px',
      },
      borderWidth: {
        '3': '3px',
      },
    },
  },
  plugins: [],
}

