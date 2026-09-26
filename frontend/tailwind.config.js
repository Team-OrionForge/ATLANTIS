/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        sonar: {
          dark: "#0b1325",
          panel: "#121e36",
          accent: "#00f0ff",
          amber: "#ffb703",
          red: "#ef4444",
          green: "#10b981",
          gray: "#94a3b8",
        },
      },
    },
  },
  plugins: [],
}
