"""Provision the restricted application role; run only with the migration owner's connection."""

import os

import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.db import make_engine
from app.services.law import ingest
from app.services.llm import OllamaProvider


def main():
    options = Settings()
    password = os.environ.get("APP_DATABASE_PASSWORD", "")
    if len(password) < 24:
        raise SystemExit("APP_DATABASE_PASSWORD must contain at least 24 random URL-safe characters")
    url = make_url(options.database_url).set(drivername="postgresql")
    role = sql.Identifier("casetrace_app")
    with psycopg.connect(url.render_as_string(hide_password=False)) as connection:
        with connection.cursor() as cursor:
            exists = cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = 'casetrace_app'").fetchone()
            operation = "ALTER" if exists else "CREATE"
            cursor.execute(sql.SQL(operation + " ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD {}").format(role, sql.Literal(password)))
            cursor.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(sql.Identifier(url.database), role))
            cursor.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
            cursor.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(role))
            cursor.execute(sql.SQL("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {}").format(role))
            cursor.execute(sql.SQL("GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA public TO {}").format(role))
            for table in ("users", "cases", "extracted_entities", "law_sections", "law_pages", "plan_steps", "notices", "transactions", "deadlines", "auth_sessions", "login_buckets"):
                cursor.execute(sql.SQL("GRANT UPDATE ON {} TO {}").format(sql.Identifier(table), role))
            for table in ("auth_sessions", "login_buckets", "deadlines"):
                cursor.execute(sql.SQL("GRANT DELETE ON {} TO {}").format(sql.Identifier(table), role))
            cursor.execute(sql.SQL("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {}").format(role))
    engine = make_engine(options.database_url)
    with Session(engine) as db:
        ingest(db, options.corpus_path, OllamaProvider(options))
    engine.dispose()
    print("Restricted application role and section reference catalog provisioned; no sample accounts or cases were created.")


if __name__ == "__main__":
    main()
