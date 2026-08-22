import { defineConfig } from "vite";

// Build-only: output lands inside the Python package, which serves the dist
// statically (`src/zuaef_agent/web/server.py`). Node never participates in
// the runtime; no dev-server/proxy config on purpose.
export default defineConfig({
  base: "./",
  build: {
    outDir: "../src/zuaef_agent/web/static/dist",
    emptyOutDir: true,
    sourcemap: false,
    target: "es2022",
  },
});
