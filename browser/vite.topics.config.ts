import {defineConfig} from 'vite-plus';
export default defineConfig({cacheDir:'.cache/topics-vite',build:{outDir:'../build/configurable-topics',rollupOptions:{input:['topics-demo.html','performance-demo.html']}}});
