import {defineConfig} from 'vite-plus';
export default defineConfig({cacheDir:'.cache/symbols-vite',build:{outDir:'../build/codegen-symbols',rollupOptions:{input:['codegen-symbols.html']}}});
