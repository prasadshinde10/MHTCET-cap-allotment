/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Core Institutional Palette
        navy: {
          deep: '#0B2545',     // Deep Navy
          primary: '#123B66',  // Primary Navy
          dark: '#081D36',
          light: '#1B4D82',
        },
        brand: {
          blue: '#1769D2',     // Primary Blue
          light: '#EAF3FF',    // Light Blue
          hover: '#1358B3',
        },
        surface: {
          bg: '#F7F9FC',       // Canvas Background
          card: '#FFFFFF',     // White
          border: '#D9E2EC',   // Border
          subtle: '#F0F4F8',   // Subtle Surface
        },
        ink: {
          primary: '#172B4D',   // Primary Text
          secondary: '#5B6B7F', // Secondary Text
          muted: '#8292A2',     // Muted Text
        },
        status: {
          success: '#16845B',          // Success
          'success-bg': '#EAF7EE',
          'success-border': '#B7E4C7',
          warning: '#B7791F',          // Warning
          'warning-bg': '#FEF7E6',
          'warning-border': '#F7D070',
          error: '#C53030',            // Error
          'error-bg': '#FDF2F2',
          'error-border': '#F8B4B4',
        },
        // Backward-compatible primary aliases mapped to our institutional palette
        primary: {
          50: '#EAF3FF',
          100: '#D5E7FF',
          200: '#ADCFFF',
          300: '#80B3FF',
          400: '#4791FA',
          500: '#1769D2',
          600: '#123B66',
          700: '#0B2545',
          800: '#081D36',
          900: '#051324',
        },
      },
      boxShadow: {
        'subtle': '0 1px 2px 0 rgba(11, 37, 69, 0.04)',
        'card': '0 1px 3px 0 rgba(11, 37, 69, 0.05), 0 1px 2px -1px rgba(11, 37, 69, 0.03)',
        'elevated': '0 4px 6px -1px rgba(11, 37, 69, 0.07), 0 2px 4px -2px rgba(11, 37, 69, 0.04)',
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'Helvetica Neue', 'Arial', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
