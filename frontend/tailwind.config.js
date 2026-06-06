/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#030712", // Slate 950
        card: "#0f172a", // Slate 900
        border: "#1e293b", // Slate 800
        primary: {
          DEFAULT: "#e11d48", // Rose 600 (Crimson red)
          hover: "#be123c", // Rose 700
          light: "#fda4af", // Rose 300
        },
        accent: {
          DEFAULT: "#3b82f6", // Blue 500
          success: "#10b981", // Emerald 500
          warning: "#f59e0b", // Amber 500
          danger: "#ef4444", // Red 500
        },
        text: {
          primary: "#f8fafc", // Slate 50
          secondary: "#94a3b8", // Slate 400
          muted: "#64748b", // Slate 500
        }
      },
      fontFamily: {
        sans: ["Inter", "sans-serif"],
        heading: ["Outfit", "sans-serif"],
      },
      boxShadow: {
        glass: "0 8px 32px 0 rgba(0, 0, 0, 0.37)",
        "glass-primary": "0 8px 32px 0 rgba(225, 29, 72, 0.15)",
      }
    },
  },
  plugins: [],
}
