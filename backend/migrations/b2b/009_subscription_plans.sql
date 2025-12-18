-- Add contact_required column to b2b.subscription_plans
ALTER TABLE b2b.subscription_plans ADD COLUMN IF NOT EXISTS contact_required BOOLEAN DEFAULT FALSE;
