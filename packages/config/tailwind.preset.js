/** Preset Tailwind compartilhado entre web e (futuramente) mobile via nativewind. */
/** @type {import('tailwindcss').Config} */
module.exports = {
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eefcf3",
          100: "#d6f7e2",
          500: "#0fa968",
          600: "#0b8a54",
          700: "#0a6f45",
          900: "#0a4a30",
        },
      },
    },
  },
  plugins: [],
};
