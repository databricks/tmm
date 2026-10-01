import { defineConfig } from 'drizzle-kit';

// Used by `drizzle-kit generate` to diff server/db/schema.ts against the last
// snapshot and emit an ordered SQL migration into ./migrations. This step is
// offline — it needs no database connection. Migrations are applied separately
// by scripts/migrate.ts (`npm run migrate`).
export default defineConfig({
  schema: './server/db/schema.ts',
  out: './migrations',
  dialect: 'postgresql',
});
