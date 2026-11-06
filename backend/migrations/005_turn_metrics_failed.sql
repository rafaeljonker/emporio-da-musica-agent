-- Failed turns (the fixed error reply) stay out of the reply p50.
ALTER TABLE turn_metrics ADD COLUMN IF NOT EXISTS failed boolean NOT NULL DEFAULT false;
