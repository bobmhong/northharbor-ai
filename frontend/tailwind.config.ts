import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        harbor: {
          50: "#f0f7ff",
          100: "#e0effe",
          200: "#baddfd",
          300: "#7dc2fc",
          400: "#38a3f8",
          500: "#0e87e9",
          600: "#0269c7",
          700: "#0354a1",
          800: "#074885",
          900: "#0c3d6e",
          950: "#082749",
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
