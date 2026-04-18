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
          50: '#ecfdf5',
          100: '#d1fae5',
          200: '#a7f3d0',
          300: '#6ee7b7',
          400: '#34d399',
          500: '#10b981', // Emerald Green - Primary
          600: '#059669',
          700: '#047857',
          800: '#065f46',
          900: '#064e3b',
        },
        secondary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#1e40af', // Navy Blue - Secondary
          700: '#1e3a8a',
          800: '#1e3a8a',
          900: '#1e3a8a',
        },
        accent: {
          50: '#fffbeb',
          100: '#fef3c7',
          200: '#fde68a',
          300: '#fcd34d',
          400: '#fbbf24',
          500: '#f59e0b', // Gold - Accent
          600: '#d97706',
          700: '#b45309',
          800: '#92400e',
          900: '#78350f',
        },
        matcha: {
          light: '#ecfdf5',
          base: '#10b981',
          dark: '#059669',
          deep: '#047857',
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
        'genx': '6px 6px 0px 0px rgba(6, 95, 70, 0.3)',
        'genx-lg': '8px 8px 0px 0px rgba(6, 95, 70, 0.35)',
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

