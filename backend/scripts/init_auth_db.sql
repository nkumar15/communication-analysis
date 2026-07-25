-- Create the application user if it doesn't exist
DO
$do$
DECLARE
   _password text := current_setting('saas.app_db_password');
   _user text := current_setting('saas.app_db_user');
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles
      WHERE  rolname = _user) THEN

      EXECUTE format('CREATE ROLE %I WITH LOGIN PASSWORD %L', _user, _password);
      RAISE NOTICE 'Role % created', _user;
   ELSE
      EXECUTE format('ALTER ROLE %I WITH PASSWORD %L', _user, _password);
      RAISE NOTICE 'Role % already exists - password updated', _user;
   END IF;
END
$do$;

-- Grant connect permission
DO
$do$
DECLARE
   _user text := current_setting('saas.app_db_user');
   _dbname text := current_setting('saas.app_db_name');
BEGIN
   EXECUTE format('GRANT CONNECT ON DATABASE %I TO %I', _dbname, _user);
END
$do$;
