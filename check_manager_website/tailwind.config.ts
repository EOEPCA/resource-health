import type { Config } from "tailwindcss";
// const defaultTheme = require("tailwindcss/defaultTheme");

/** @type {import('tailwindcss').Config} */

export default {
  content: [
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
} satisfies Config;
