/**
 * Test Setup
 *
 * This file is run before all tests to set up the test environment.
 */

import { vi } from "vitest";
import { config } from "dotenv";

vi.mock("server-only", () => ({}));

// Load environment variables from .env.local
config({ path: ".env.local" });

// Verify required env vars are present
const requiredEnvVars = [
  "NEXT_PUBLIC_SUPABASE_URL",
  "NEXT_PUBLIC_SUPABASE_ANON_KEY",
];

for (const envVar of requiredEnvVars) {
  if (!process.env[envVar]) {
    console.warn(`Warning: ${envVar} is not set. Contract tests may fail.`);
  }
}
