import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        harbor: {
          50: "#f0f7f6",
          100: "#dcecea",
          200: "#bbd9d6",
          300: "#8dbfbb",
          400: "#5fa19d",
          500: "#458582",
          600: "#376b69",
          700: "#305756",
          800: "#2a4746",
          900: "#263c3b",
          950: "#122221",
        },
        sage: {
          50: "#f4f7f6",
          100: "#e2eae7",
          200: "#d0deda",
          300: "#b0c7c1",
          400: "#8aaba3",
          500: "#6b9189",
          600: "#557671",
          700: "#46605c",
          800: "#3b4f4c",
          900: "#344341",
          950: "#1b2524",
        },
        slate: {
          850: "#1a2e35",
        },
      },
      boxShadow: {
        soft: "0 2px 8px -2px rgba(38, 60, 59, 0.08), 0 4px 16px -4px rgba(38, 60, 59, 0.12)",
        card: "0 1px 3px rgba(38, 60, 59, 0.06), 0 4px 12px rgba(38, 60, 59, 0.08)",
        elevated: "0 4px 20px -4px rgba(38, 60, 59, 0.15), 0 8px 32px -8px rgba(38, 60, 59, 0.1)",
      },
      backgroundImage: {
        "gradient-subtle": "linear-gradient(135deg, #f4f7f6 0%, #e2eae7 100%)",
        "gradient-header": "linear-gradient(to right, #ffffff, #f4f7f6)",
      },
    },
  },
  plugins: [],
} satisfies Config;
