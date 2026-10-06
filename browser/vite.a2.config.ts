import {defineConfig} from 'vite-plus';
export default defineConfig({cacheDir:'.cache/a2-vite',build:{outDir:'../build/a2',rollupOptions:{input:['a2-smoke.html','grouped-demo.html']}}});
