-- Create the application user if it doesn't exist
DO
$do$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles
      WHERE  rolname = 'sso_app') THEN

      CREATE ROLE sso_app WITH LOGIN PASSWORD 'sso_app_password';
      RAISE NOTICE 'Role sso_app created';
   ELSE
      RAISE NOTICE 'Role sso_app already exists';
   END IF;
END
$do$;

-- Grant connect permission
GRANT CONNECT ON DATABASE sso_db TO sso_app;
