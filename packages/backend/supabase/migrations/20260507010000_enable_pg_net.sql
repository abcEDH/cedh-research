-- Enable pg_net so cron-triggered SQL wrappers can call Edge Functions.

CREATE EXTENSION IF NOT EXISTS pg_net;
