import {defineConfig} from 'vite-plus';
import {playwright} from '@vitest/browser-playwright';
export default defineConfig({
 cacheDir:'../../cache/vite-reporting',
 server:{host:'127.0.0.1'},
 test:{maxWorkers:1,fileParallelism:false,reporters:['verbose'],include:['src/dependency-reporting.browser.test.tsx','src/reconnect-status.browser.test.tsx'],browser:{enabled:true,provider:playwright(),headless:true,instances:[{browser:'chromium',name:'chromium'}]}},
});
