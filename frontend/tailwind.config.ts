import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        display: ["var(--font-display)", "serif"],
        body: ["var(--font-body)", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"],
      },
      colors: {
        brand: {
          50:  "#f0f9f4",
          100: "#dcf1e6",
          200: "#bbe3ce",
          300: "#8bcead",
          400: "#55b285",
          500: "#329666",
          600: "#237850",
          700: "#1c6042",
          800: "#184d36",
          900: "#14402d",
          950: "#0a2419",
        },
        ink: {
          50:  "#f6f6f7",
          100: "#e1e2e6",
          200: "#c3c5ce",
          300: "#9c9faf",
          400: "#797d91",
          500: "#5f6377",
          600: "#4c4f61",
          700: "#3e4050",
          800: "#363844",
          900: "#1e1f28",
          950: "#131419",
        },
        saffron: {
          400: "#f5a623",
          500: "#e8960f",
        },
      },
      backgroundImage: {
        "mesh-green": `
          radial-gradient(at 20% 20%, hsla(145,60%,20%,0.9) 0px, transparent 50%),
          radial-gradient(at 80% 0%, hsla(155,55%,15%,0.8) 0px, transparent 50%),
          radial-gradient(at 5% 80%, hsla(150,50%,25%,0.6) 0px, transparent 40%)
        `,
      },
      animation: {
        "fade-in": "fadeIn 0.4s ease forwards",
        "slide-up": "slideUp 0.5s cubic-bezier(0.16,1,0.3,1) forwards",
        "pulse-slow": "pulse 3s cubic-bezier(0.4,0,0.6,1) infinite",
        shimmer: "shimmer 1.6s linear infinite",
      },
      keyframes: {
        fadeIn: {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        slideUp: {
          from: { opacity: "0", transform: "translateY(16px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          from: { backgroundPosition: "-200% 0" },
          to: { backgroundPosition: "200% 0" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
