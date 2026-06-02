/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./cv_tailor/templates/**/*.html"],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "Helvetica",
          "Arial",
          "sans-serif",
        ],
      },
      colors: {
        accent: {
          DEFAULT: "#4f46e5",
          hover: "#4338ca",
        },
      },
    },
  },
  plugins: [],
};
