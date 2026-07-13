import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// IonityEdge · K10 installer — Vite config. © Ionity (Pty) Ltd · Policy 986 AED
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, host: true },
  build: { outDir: "dist", target: "es2020" },
});
