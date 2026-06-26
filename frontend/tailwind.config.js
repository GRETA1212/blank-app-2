/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        studio: {
          950: '#11100e',
          900: '#181613',
          800: '#24201b',
          700: '#342d25',
          amber: '#d6a84b',
          parchment: '#eee5d1',
          slate: '#9b958d',
          teal: '#55b7aa'
        }
      },
      fontFamily: {
        display: ['Georgia', 'serif'],
        sans: ['Inter', 'ui-sans-serif', 'system-ui'],
        mono: ['ui-monospace', 'SFMono-Regular', 'monospace']
      }
    }
  },
  plugins: []
};
