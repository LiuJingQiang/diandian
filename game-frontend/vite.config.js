import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { readFileSync } from 'node:fs';

const appVersion = readFileSync(new URL('./VERSION', import.meta.url), 'utf8').trim();

export default defineConfig({
  plugins: [react()],
  base: process.env.BASE_PATH || './',
  define: {
    'import.meta.env.VITE_APP_VERSION': JSON.stringify(appVersion),
  },
});
