import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Vite = the dev server and build tool. The React plugin adds JSX support
// and fast refresh (the page updates as soon as you save a file).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173, // must match CORS_ORIGINS in the backend's .env
  },
});
