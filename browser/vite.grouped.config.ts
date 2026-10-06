import {defineConfig} from 'vite-plus';
export default defineConfig({cacheDir:'.cache/grouped-vite',build:{outDir:'../build/grouped',rollupOptions:{input:['grouped-demo.html']}}});
