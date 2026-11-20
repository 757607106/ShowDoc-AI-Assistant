\getenv platform_password POSTGRES_PLATFORM_PASSWORD
\getenv agent_password POSTGRES_AGENT_PASSWORD
\getenv async_password POSTGRES_ASYNC_PASSWORD
\getenv sandbox_password POSTGRES_SANDBOX_PASSWORD

SELECT format('CREATE ROLE showdoc_platform LOGIN NOINHERIT PASSWORD %L', :'platform_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'showdoc_platform')
\gexec
SELECT format('CREATE ROLE showdoc_agent LOGIN NOINHERIT PASSWORD %L', :'agent_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'showdoc_agent')
\gexec
SELECT 'CREATE DATABASE showdoc_agent'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'showdoc_agent')
\gexec

SELECT format('CREATE ROLE %I LOGIN NOINHERIT PASSWORD %L', name, password)
FROM (VALUES ('showdoc_async_agent_app', :'async_password'),
             ('opensandbox_control', :'sandbox_password')) AS config(name, password)
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = config.name)
\gexec
SELECT format('CREATE DATABASE %I', name)
FROM (VALUES ('showdoc_async_agent'), ('opensandbox_control')) AS config(name)
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = config.name)
\gexec

REVOKE ALL ON DATABASE showdoc_knowledge FROM PUBLIC;
GRANT CONNECT ON DATABASE showdoc_knowledge TO showdoc_platform;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE, CREATE ON SCHEMA public TO showdoc_platform;

\connect showdoc_agent
REVOKE ALL ON DATABASE showdoc_agent FROM PUBLIC;
GRANT CONNECT ON DATABASE showdoc_agent TO showdoc_agent;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE, CREATE ON SCHEMA public TO showdoc_agent;

\connect showdoc_async_agent
REVOKE ALL ON DATABASE showdoc_async_agent FROM PUBLIC;
GRANT CONNECT ON DATABASE showdoc_async_agent TO showdoc_async_agent_app;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE, CREATE ON SCHEMA public TO showdoc_async_agent_app;

\connect opensandbox_control
REVOKE ALL ON DATABASE opensandbox_control FROM PUBLIC;
GRANT CONNECT ON DATABASE opensandbox_control TO opensandbox_control;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE, CREATE ON SCHEMA public TO opensandbox_control;
