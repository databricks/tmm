// Drizzle schema — the single source of truth for the database structure.
//
// Schema changes are made HERE, then turned into an ordered SQL migration with
// `npm run db:generate` (which writes to ./migrations). Migrations are applied
// to a database branch by `npm run migrate` — never by the app at startup.
//
// The app itself does not run DDL; it connects with a least-privilege role and
// only issues DML. See server/routes/lakebase/todo-routes.ts.

import { pgSchema, serial, text, boolean, timestamp } from 'drizzle-orm/pg-core';

// The app owns a dedicated `app` schema (kept out of `public`).
export const appSchema = pgSchema('app');

export const todos = appSchema.table('todos', {
  id: serial('id').primaryKey(),
  title: text('title').notNull(),
  completed: boolean('completed').notNull().default(false),
  url: text('url'),
  createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
});

// Inferred row types — import these instead of hand-writing shapes, so the
// application code stays in lockstep with the schema above.
export type Todo = typeof todos.$inferSelect;
export type NewTodo = typeof todos.$inferInsert;
