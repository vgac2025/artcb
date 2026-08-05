import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    // B16 FIX: code-splitting manuel — réduit le bundle initial de 809KB
    // vendor (~200KB), axios (~50KB), cytoscape (~400KB) chargés séparément
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ["react", "react-dom"],
          axios: ["axios"],
          cytoscape: ["cytoscape"],
        },
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/ws": { target: "ws://127.0.0.1:8000", ws: true },
    },
  },
});
