/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      screens: {
        'xs': '475px',   // Extra small devices (large phones)
        'sm': '640px',   // Small devices (tablets in portrait)
        'md': '768px',   // Medium devices (tablets in landscape)
        'lg': '1024px',  // Large devices (desktops)
        'xl': '1280px',  // Extra large devices
        '2xl': '1536px', // 2X Extra large devices
        // Custom breakpoints for better device flexibility
        'mobile': {'max': '639px'},
        'tablet': {'min': '640px', 'max': '1023px'},
        'desktop': {'min': '1024px'},
        // Orientation
        'portrait': {'raw': '(orientation: portrait)'},
        'landscape': {'raw': '(orientation: landscape)'},
      },
      spacing: {
        'safe-top': 'env(safe-area-inset-top)',
        'safe-bottom': 'env(safe-area-inset-bottom)',
        'safe-left': 'env(safe-area-inset-left)',
        'safe-right': 'env(safe-area-inset-right)',
      },
    },
  },
  darkMode: 'class', // Enable class-based dark mode - Tailwind will look for 'dark' class by default
  plugins: [],
}

