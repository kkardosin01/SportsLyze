import type { Config } from "tailwindcss";
import basePreset from "@sportslyze/config/tailwind.preset.js";

const config: Config = {
  presets: [basePreset as Config],
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
};

export default config;
