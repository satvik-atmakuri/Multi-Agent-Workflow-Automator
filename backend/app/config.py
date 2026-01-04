import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Core
    OPENAI_API_KEY: str
    DATABASE_URL: str
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000"
    
    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    # Search Configuration
    SEARCH_PROVIDER: str = "brave"  # brave, ddg, mock
    BRAVE_SEARCH_API_KEY: str = ""
    ENABLE_WEB_SEARCH: bool = True
    
    # Model Configuration
    # Model Configuration
    DEFAULT_MODEL: str = "gpt-4o-mini"
    MAX_TOKENS: int = 4096
    
    # Caching
    CACHE_ENABLED: bool = True
    CACHE_THRESHOLD: float = 0.95
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
