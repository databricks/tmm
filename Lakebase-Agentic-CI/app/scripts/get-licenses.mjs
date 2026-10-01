import { readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';

const root = process.argv[2];
const pkg = JSON.parse(readFileSync(join(root, 'package.json'), 'utf8'));

function parseLicense(p) {
  const lic = p?.license ?? p?.licenses;
  if (!lic) return '';
  if (typeof lic === 'string') return lic.trim();
  if (Array.isArray(lic)) return lic.map(x => typeof x === 'string' ? x : x?.type).filter(Boolean).join(' OR ');
  if (typeof lic === 'object' && lic.type) return String(lic.type).trim();
  return '';
}
function nmPath(name) {
  const parts = name.startsWith('@') ? name.split('/') : [name];
  return join(root, 'node_modules', ...parts, 'package.json');
}

const rows = [];
for (const [type, obj] of [['dependency', pkg.dependencies ?? {}], ['devDependency', pkg.devDependencies ?? {}]]) {
  for (const [name, requested] of Object.entries(obj)) {
    let resolved = '', license = '';
    const p = nmPath(name);
    if (existsSync(p)) {
      try { const dp = JSON.parse(readFileSync(p, 'utf8')); resolved = dp.version ?? ''; license = parseLicense(dp); } catch {}
    }
    rows.push({ name, type, requested: String(requested), resolved, license });
  }
}
rows.sort((a, b) => (a.type === b.type ? a.name.localeCompare(b.name) : a.type < b.type ? -1 : 1));

console.log('| Package | Type | Requested | Resolved | License |');
console.log('| --- | --- | --- | --- | --- |');
for (const r of rows) console.log(`| \`${r.name}\` | ${r.type} | ${r.requested} | ${r.resolved} | ${r.license || '**?**'} |`);

// license summary
const counts = {};
for (const r of rows) counts[r.license || 'UNKNOWN'] = (counts[r.license || 'UNKNOWN'] || 0) + 1;
console.log('\nLicense summary: ' + Object.entries(counts).sort((a,b)=>b[1]-a[1]).map(([k,v])=>`${k}: ${v}`).join(', '));
