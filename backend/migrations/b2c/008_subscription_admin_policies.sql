-- Allow admins/system to manage invoices (needed for webhooks)
-- This policy uses the app.is_platform_admin setting set by rls_service.set_platform_admin_context()

CREATE POLICY invoices_all_admin ON b2c.invoices
    FOR ALL
    USING (current_setting('app.is_platform_admin', true) = 'true')
    WITH CHECK (current_setting('app.is_platform_admin', true) = 'true');

-- Allow admins/system to manage subscriptions (update status etc)
CREATE POLICY subscriptions_all_admin ON b2c.subscriptions
    FOR ALL
    USING (current_setting('app.is_platform_admin', true) = 'true')
    WITH CHECK (current_setting('app.is_platform_admin', true) = 'true');
