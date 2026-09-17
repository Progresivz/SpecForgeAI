"""Print production diagnostics without exposing secrets."""
from sqlalchemy import text
from app.core.config import settings
from app.database.session import engine


def main():
    print(f"service={settings.APP_NAME}")
    print(f"version={settings.VERSION}")
    print(f"environment={settings.ENVIRONMENT}")
    print(f"database_backend={engine.url.get_backend_name()}")
    print(f"migration_mode={settings.MIGRATION_MODE}")
    print(f"ai_provider={settings.AI_PROVIDER}")
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("database=ok")


if __name__ == "__main__":
    main()
