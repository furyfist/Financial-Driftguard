/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ["Bricolage Grotesque", "sans-serif"],
        mono: ["DM Mono", "monospace"],
        body: ["Bricolage Grotesque", "sans-serif"],
      },
      colors: {
        canvas: "#F7F6F3",
        surface: "#FFFFFF",
        border: "#E8E6E0",
        "border-subtle": "#EEECE8",
        ink: "#1A1916",
        "ink-muted": "#6B6860",
        "ink-faint": "#A8A49E",
        accent: "#D4450C",
        "accent-soft": "#FBF0EC",
        stable: "#1A6B3C",
        "stable-soft": "#EDFAF3",
        warning: "#B45309",
        "warning-soft": "#FEF7EC",
        critical: "#C0200F",
        "critical-soft": "#FEF0EE",
      },
    },
  },
  plugins: [],
}