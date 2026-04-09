DO
$do$
DECLARE
   _user text := current_setting('saas.app_db_user');
   _schema text;
   _schemas text[] := ARRAY['public', 'platform', 'b2b', 'b2c', 'bank_surveillance', 'b2b_project_management', 'b2c_finance_trader'];
BEGIN
   FOREACH _schema IN ARRAY _schemas
   LOOP
      -- Grant usage on schema
      EXECUTE format('GRANT USAGE ON SCHEMA %I TO %I', _schema, _user);
      
      -- Grant access to all tables in schema
      EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA %I TO %I', _schema, _user);
      
      -- Grant access to all sequences
      EXECUTE format('GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA %I TO %I', _schema, _user);
      
      -- Ensure future tables also get these permissions
      EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA %I GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO %I', _schema, _user);
      
      -- Grant execute on all functions (fixes B2C RLS helpers)
      EXECUTE format('GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA %I TO %I', _schema, _user);

      RAISE NOTICE 'Granted permissions on schema % to %', _schema, _user;
   END LOOP;
END
$do$;