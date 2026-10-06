// The two check scopes must use the same exact project-local compiler.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {spawnSync} from 'node:child_process';

const expected = '7.0.2';
const browser = fileURLToPath(new URL('../browser/', import.meta.url));
const mode = process.argv[2];
if (!['browser', 'contracts', 'all'].includes(mode) || process.argv.length !== 3) {
  console.error('Usage: node scripts/typecheck.mjs browser|contracts|all');
  process.exit(2);
}
let executable;
try {
  const project = JSON.parse(fs.readFileSync(path.join(browser, 'package.json'), 'utf8'));
  if (project.devDependencies?.typescript !== expected) throw Error(`browser/package.json must pin typescript to ${expected}`);
  const packagePath = fs.realpathSync(path.join(browser, 'node_modules/typescript/package.json'));
  const installed = JSON.parse(fs.readFileSync(packagePath, 'utf8'));
  if (installed.name !== 'typescript' || installed.version !== expected) throw Error(`installed package is ${installed.name}@${installed.version}; expected typescript@${expected}`);
  // This is the resolver used by this pinned package's bin/tsc launcher.
  const {default: getExePath} = await import(pathToFileURL(path.join(path.dirname(packagePath), 'lib/getExePath.js')).href);
  executable = fs.realpathSync(getExePath());
  const version = spawnSync(executable, ['--version'], {cwd: browser, encoding: 'utf8', timeout: 10000});
  if (version.error || version.status !== 0 || version.stdout.trim() !== `Version ${expected}`) {
    throw Error(`compiler ${executable} reported ${JSON.stringify(version.stdout?.trim())} (exit ${version.status}); expected Version ${expected}${version.error ? ': ' + version.error.message : ''}`);
  }
} catch (error) {
  console.error(`TypeScript guard: ${error.message}\nRestore the project-local browser dependencies from browser/pnpm-lock.yaml using the documented setup. This check requires TypeScript ${expected}; no global compiler or download fallback is used.`);
  process.exit(1);
}
console.error(`TypeScript ${expected}: ${executable}`);
for (const scope of mode === 'all' ? ['browser', 'contracts'] : [mode]) {
  const result = spawnSync(executable, ['--noEmit', '-p', scope === 'browser' ? 'tsconfig.json' : 'tsconfig.contracts.json'], {cwd: browser, stdio: 'inherit'});
  if (result.error) console.error(`TypeScript check failed: ${result.error.message}`);
  if (result.error || result.status !== 0) process.exit(result.status || 1);
}
