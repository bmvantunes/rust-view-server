import {defineConfig} from 'vite-plus';
export default defineConfig({cacheDir:'.cache/a1-vite',build:{outDir:'../build/a1',rollupOptions:{input:['a1-smoke.html','grouped-demo.html']}}});
