/**
 * Test Setup
 *
 * This file is run before all tests to set up the test environment.
 */

import { config } from "dotenv";

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
