/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // Warm, calm palette — high contrast, elderly-friendly
        cream: {
          50: '#FDFBF7',
          100: '#FAF5EB',
          200: '#F3EAD8',
        },
        ink: {
          900: '#1F1B16',
          700: '#3E372E',
          500: '#6B5F52',
        },
        brand: {
          50: '#EEF7F4',
          100: '#D9EDE6',
          500: '#1F7A64',
          600: '#186551',
          700: '#12503F',
        },
        sun: {
          100: '#FDEFD2',
          400: '#F5B942',
          500: '#EFA31B',
        },
      },
      fontFamily: {
        sans: ['"Atkinson Hyperlegible"', 'system-ui', '-apple-system', '"Segoe UI"', 'Roboto', 'sans-serif'],
      },
      minHeight: {
        touch: '3rem', // 48px minimum touch target
      },
      minWidth: {
        touch: '3rem',
      },
    },
  },
  plugins: [],
}
