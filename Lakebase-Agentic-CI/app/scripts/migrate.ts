// Apply pending Drizzle migrations to a Lakebase branch.
//
// Run by `npm run migrate` in CI (Deploy Lakebase Preview against pr-<n>, and
// Migrate Lakebase Production against production on merge). Uses
// @databricks/lakebase's `createLakebasePool`, which resolves the connection
// from PGHOST / PGDATABASE / LAKEBASE_ENDPOINT / PGUSER and refreshes the
// short-lived OAuth database token automatically.
//
// Drizzle records applied migrations in a journal table, so re-running is a
// no-op once everything is applied.

import { drizzle } from 'drizzle-orm/node-postgres';
import { migrate } from 'drizzle-orm/node-postgres/migrator';
import { createLakebasePool } from '@databricks/lakebase';

async function main(): Promise<void> {
  const pool = createLakebasePool();
  try {
    const db = drizzle({ client: pool });
    await migrate(db, { migrationsFolder: './migrations' });
    console.log('Migrations applied successfully.');
  } finally {
    await pool.end();
  }
}

main().catch((err) => {
  console.error('Migration failed:', err);
  process.exit(1);
});
