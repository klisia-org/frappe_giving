import path from 'path';
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

// Widget build — emits a self-contained IIFE bundle that can be dropped
// onto any Frappe-hosted page to mount Campaign Forms. See ./src/widget.js
// for the staff embed snippet.
export default defineConfig({
  plugins: [vue()],
  // Vue's runtime code references `process.env.NODE_ENV` for dev warnings.
  // Vite's HTML builds replace it automatically; library builds don't, so
  // we define it here to avoid a browser-side `ReferenceError: process is
  // not defined` when the widget is loaded on a non-Vite host page.
  define: {
    'process.env.NODE_ENV': JSON.stringify('production'),
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  build: {
    lib: {
      entry: path.resolve(__dirname, 'src/widget.js'),
      name: 'FrappeGiving',
      formats: ['iife'],
      fileName: () => 'widget.js',
    },
    outDir: '../frappe_giving/public/widget',
    emptyOutDir: true,
    cssCodeSplit: false,
    target: 'es2015',
    rollupOptions: {
      output: {
        // Single CSS file with a predictable name.
        assetFileNames: (asset) =>
          asset.name && asset.name.endsWith('.css') ? 'widget.css' : '[name][extname]',
      },
    },
  },
});
