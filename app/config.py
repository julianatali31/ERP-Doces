from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="before")
    @classmethod
    def ignorar_vazias(cls, valores):
        """Trata variavel de ambiente em branco como se nao existisse.

        Paineis de hospedagem criam facilmente uma variavel sem valor - por
        importacao de .env, por exemplo. Sem isto, um PORT='' derruba a
        aplicacao inteira na inicializacao, com erro de validacao dificil de
        entender, mesmo que a aplicacao nunca use aquele campo.
        """
        if isinstance(valores, dict):
            return {
                chave: valor
                for chave, valor in valores.items()
                if not (isinstance(valor, str) and not valor.strip())
            }
        return valores

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/erp_confeitaria"
    database_url_sync: str = ""

    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True
    workers: int = 1

    cors_origins: str = "*"

    environment: str = "development"
    debug: bool = True
    log_level: str = "INFO"

    backup_dir: str = "./backups/json"
    upload_dir: str = "./uploads"
    max_file_size_mb: int = 10

    empresa_nome: str = "Dom Cookies"

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
