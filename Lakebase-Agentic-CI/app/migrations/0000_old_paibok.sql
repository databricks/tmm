-- Baseline migration.
--
-- This is made idempotent (IF NOT EXISTS) on purpose: the `app` schema and
-- `app.todos` table already exist on the production branch (they were
-- previously created by the app at startup), and every preview branch is a
-- clone of production. Making the baseline safe to re-run lets us adopt
-- migrations over the existing database without a manual journal backfill:
-- Drizzle records it as applied, and it is a no-op where the objects exist.
-- Subsequent migrations are ordinary drizzle-kit output.
CREATE SCHEMA IF NOT EXISTS "app";
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "app"."todos" (
	"id" serial PRIMARY KEY NOT NULL,
	"title" text NOT NULL,
	"completed" boolean DEFAULT false NOT NULL,
	"url" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
