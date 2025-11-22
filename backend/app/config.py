from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application configuration"""
    
    # Database
    database_url: str
    
    # Security
    secret_key: str
    algorithm: str = "HS256"
    
    # Firebase
    firebase_project_id: str
    firebase_credentials_path: str = "/app/firebase-credentials.json"
    
    # URLs
    frontend_url: str
    backend_url: str
    
    # CORS
    allowed_origins: str = "http://localhost:3000"
    
    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
