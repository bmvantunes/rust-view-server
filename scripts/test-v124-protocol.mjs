// V13.1: the preserved command runs the expanded actual binary Worker schedules.
import {copyFile} from 'node:fs/promises';
import {resolve} from 'node:path';
process.env.V13_CANDIDATE_ROOT=resolve(import.meta.dirname,'..');
process.env.V13_CODEC='msgpack';
await import('./test-v131-protocol.mjs');
await copyFile(new URL('../evidence/v13.1/protocol-msgpack.json',import.meta.url),new URL('../evidence/v12.4/protocol.json',import.meta.url));
