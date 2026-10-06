"""Record actual runtime versions used by the pinned gate scripts."""
from pathlib import Path
import json, os, platform, subprocess, sys
rustc = subprocess.check_output(['rustup', 'which', '--toolchain', '1.96.1', 'rustc'], text=True).strip()
os.environ['PATH'] = str(Path(rustc).parent) + os.pathsep + os.environ.get('PATH', '')
node_version = subprocess.check_output(['node', '--version'], text=True).strip()
assert tuple(map(int, node_version.lstrip('v').split('.'))) >= (24, 21, 0), 'Node >=24.21.0 required, found ' + node_version
commands = [['rustup', 'run', '1.96.1', 'rustc', '-Vv'],
            ['rustup', 'run', '1.96.1', 'cargo', '-V'],
            ['rustup', 'run', '1.96.1', 'cargo', 'clippy', '-V'], ['node', '--version'],
            ['browser/node_modules/.bin/tsc', '--version'],
            ['browser/node_modules/.bin/playwright', '--version']]
for command in commands:
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print(json.dumps(dict(command=command, exit=result.returncode, output=result.stdout)))
    result.check_returncode()
print(json.dumps(dict(python=sys.version, platform=platform.platform())))
subprocess.run(['node', '--input-type=module', '-e', '''
import fs from 'node:fs'; import {createRequire} from 'node:module';
const require = createRequire(process.cwd() + '/browser/package.json');
const expected = JSON.parse(fs.readFileSync('browser/package.json'));
for (const [name, version] of Object.entries(expected.devDependencies)) {
  const p = JSON.parse(fs.readFileSync(require.resolve(name + '/package.json')));
  if (p.version !== version.split('@').at(-1)) throw Error(name + ' pin mismatch: ' + p.version);
  console.log(JSON.stringify({package:name,version:p.version}));
}
const {chromium} = require('playwright'); console.log(JSON.stringify({chromiumExecutable:chromium.executablePath()}));
'''], check=True)
