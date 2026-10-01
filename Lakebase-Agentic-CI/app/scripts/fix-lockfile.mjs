#!/usr/bin/env node
// ---------------------------------------------------------------------------
// fix-lockfile.mjs
//
// Normalize package-lock.json so committed tarball URLs use the PUBLIC npm
// registry. Developers behind npm-proxy.dev.databricks.com otherwise bake that
// internal host into freshly-resolved URLs, which GitHub-hosted CI runners
// cannot reach — `npm ci` then hangs and eventually fails with ETIMEDOUT.
//
// Only the host in each `resolved` URL changes; integrity hashes are
// content-based, so the tarball contents (and the hashes) are unaffected.
//
// Usage: npm run lockfile:fix   (run after adding/updating dependencies)
// ---------------------------------------------------------------------------
import { readFileSync, writeFileSync } from 'node:fs';

const FILE = 'package-lock.json';
const INTERNAL = 'npm-proxy.dev.databricks.com';
const PUBLIC = 'registry.npmjs.org';

const before = readFileSync(FILE, 'utf8');
const after = before.replaceAll(INTERNAL, PUBLIC);

if (after === before) {
  console.log(`${FILE} already uses ${PUBLIC} — nothing to fix.`);
  process.exit(0);
}

const count = before.split(INTERNAL).length - 1;
writeFileSync(FILE, after);
console.log(`Rewrote ${count} ${INTERNAL} URL(s) -> ${PUBLIC} in ${FILE}.`);
