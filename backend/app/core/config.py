from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    app_debug: bool = False
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173"

    db_server: str = "localhost"
    db_name: str = "DevTeamAI"
    db_driver: str = "ODBC Driver 18 for SQL Server"
    db_trusted_connection: bool = True
    db_user: str = ""
    db_password: SecretStr = SecretStr("")
    db_trust_server_certificate: bool = True
    db_test_name: str = "DevTeamAI_Test"

    workspaces_root: Path = Field(default=Path("../workspaces"))

    # Authentication. ADMIN_* creates the first account when the users table is empty.
    admin_username: str = "admin"
    admin_password: SecretStr = SecretStr("")
    session_hours: int = 12
    # true when served over HTTPS (e.g. behind a tunnel); keeps the cookie off plain HTTP
    cookie_secure: bool = False

    llm_base_url: str = ""
    llm_api_key: SecretStr = SecretStr("")
    openai_api_key: SecretStr = SecretStr("")

    @property
    def llm_key(self) -> str:
        return self.llm_api_key.get_secret_value() or self.openai_api_key.get_secret_value()

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def workspaces_path(self) -> Path:
        root = self.workspaces_root
        if not root.is_absolute():
            root = BACKEND_DIR / root
        return root.resolve()

    def database_url(self, database: str | None = None) -> str:
        """Build a SQLAlchemy mssql+pyodbc URL from an ODBC connection string."""
        parts = [
            f"DRIVER={{{self.db_driver}}}",
            f"SERVER={self.db_server}",
            f"DATABASE={database or self.db_name}",
            f"TrustServerCertificate={'yes' if self.db_trust_server_certificate else 'no'}",
        ]
        if self.db_trusted_connection:
            parts.append("Trusted_Connection=yes")
        else:
            parts.append(f"UID={self.db_user}")
            parts.append(f"PWD={self.db_password.get_secret_value()}")
        return "mssql+pyodbc:///?odbc_connect=" + quote_plus(";".join(parts))


@lru_cache
def get_settings() -> Settings:
    return Settings()
