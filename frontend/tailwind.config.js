/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#171717",
        paper: "#fafafa",
        flame: "#f97316",
        smoke: "#737373",
        ash: "#a3a3a3",
      },
      fontFamily: {
        sans: ["Montserrat", "Helvetica Neue", "system-ui", "sans-serif"],
      },
      boxShadow: {
        hard: "6px 6px 0 0 #171717",
        "hard-sm": "3px 3px 0 0 #171717",
      },
    },
  },
  plugins: [],
};
