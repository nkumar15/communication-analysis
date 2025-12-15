-- B2C Subscriptions - Add Missing RLS INSERT/UPDATE Policies
-- Migration: 004_subscription_rls_policies.sql
-- Description: Add INSERT and UPDATE policies for subscriptions, invoices, coupons, and related tables
-- These policies allow proper testing while respecting RLS constraints

-- ============================================================================
-- SUBSCRIPTIONS - Add INSERT and UPDATE policies
-- ============================================================================

-- Allow users to insert subscriptions for their own user_id
CREATE POLICY subscriptions_insert_own ON b2c.subscriptions
    FOR INSERT
    WITH CHECK (user_id::TEXT = current_setting('app.current_user_id', true));

-- Allow updates to own subscriptions
CREATE POLICY subscriptions_update_own ON b2c.subscriptions
    FOR UPDATE
    USING (user_id::TEXT = current_setting('app.current_user_id', true))
    WITH CHECK (user_id::TEXT = current_setting('app.current_user_id', true));

-- ============================================================================
-- INVOICES - Add INSERT and UPDATE policies
-- ============================================================================

-- Allow invoice insertion for own user_id (webhooks and system operations)
CREATE POLICY invoices_insert_own ON b2c.invoices
    FOR INSERT
    WITH CHECK (user_id::TEXT = current_setting('app.current_user_id', true));

-- Allow updates to own invoices
CREATE POLICY invoices_update_own ON b2c.invoices
    FOR UPDATE
    USING (user_id::TEXT = current_setting('app.current_user_id', true))
    WITH CHECK (user_id::TEXT = current_setting('app.current_user_id', true));

-- ============================================================================
-- COUPONS - Add INSERT and UPDATE policies
-- ============================================================================

-- Coupons are global resources created by admins/system
-- Allow inserts without user restriction (typically done by admins or migrations)
CREATE POLICY coupons_insert_all ON b2c.coupons
    FOR INSERT
    WITH CHECK (true);

-- Allow updates to coupons (for redemption count and status changes)
CREATE POLICY coupons_update_all ON b2c.coupons
    FOR UPDATE
    USING (true)
    WITH CHECK (true);

-- ============================================================================
-- COUPON REDEMPTIONS - Add INSERT policy
-- ============================================================================

-- Allow users to insert their own coupon redemptions
CREATE POLICY coupon_redemptions_insert_own ON b2c.coupon_redemptions
    FOR INSERT
    WITH CHECK (user_id::TEXT = current_setting('app.current_user_id', true));

-- ============================================================================
-- SUBSCRIPTION EVENTS - Add INSERT policy
-- ============================================================================

-- Allow inserting events for subscriptions owned by current user
CREATE POLICY subscription_events_insert_own ON b2c.subscription_events
    FOR INSERT
    WITH CHECK (
        subscription_id IN (
            SELECT id FROM b2c.subscriptions
            WHERE user_id::TEXT = current_setting('app.current_user_id', true)
        )
    );

-- ============================================================================
-- PAYMENT METHODS - Update policy was missing
-- ============================================================================

-- Allow updates to own payment methods (for default status changes)
CREATE POLICY payment_methods_update_own ON b2c.payment_methods
    FOR UPDATE
    USING (user_id::TEXT = current_setting('app.current_user_id', true))
    WITH CHECK (user_id::TEXT = current_setting('app.current_user_id', true));
