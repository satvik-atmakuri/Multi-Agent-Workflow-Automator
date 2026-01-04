"""
Configuration management using Pydantic Settings.
Loads environment variables and provides type-safe access to configuration.
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    app_env: str = "development"
    log_level: str = "info"
    
    # Database
    database_url: str
    
    # LLM API Keys
    openai_api_key: str
    anthropic_api_key: str = ""
    
    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    
    # LLM Settings
    default_model: str = "gpt-4o-mini"  # Cost-effective default
    temperature: float = 0.7
    max_tokens: int = 2000
    
    # Workflow Settings
    max_retries: int = 3
    max_clarification_questions: int = 5
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins string into list"""
        return [origin.strip() for origin in self.cors_origins.split(",")]


# Global settings instance
settings = Settings()
