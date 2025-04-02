import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'
import { resolve } from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
    // Exclude Ape directories from build process
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
      },
      // Explicitly tell rollup to ignore these directories
      external: [
        /^\/contracts\//,
        /^\/scripts\//,
        /^\/tests\//
      ],
    }
  },
  // Exclude web3 folders from the build
  optimizeDeps: {
    exclude: ['contracts/**', 'scripts/**', 'tests/**']
  }
})
