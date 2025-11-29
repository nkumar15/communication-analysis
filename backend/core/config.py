from pydantic_settings import BaseSettings
from typing import List, Optional
from pathlib import Path


class Settings(BaseSettings):
    """Application configuration"""
    
    # Database
    database_url: str
    
    # Security
    secret_key: str
    algorithm: str = "HS256"
    
    # Firebase
    firebase_project_id: str
    firebase_credentials_path: Optional[str] = None
    
    # URLs
    frontend_url: str
    backend_url: str
    
    # Email (Resend)
    resend_api_key: Optional[str] = None
    
    # CORS
    allowed_origins: str = "http://localhost:3000"
    
    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",")]
    
    @property
    def firebase_credentials_path_resolved(self) -> str:
        """Resolve Firebase credentials path for Docker or local environment"""
        if self.firebase_credentials_path and Path(self.firebase_credentials_path).exists():
            return self.firebase_credentials_path
        
        # Try Docker path
        docker_path = Path("/app/firebase-credentials.json")
        if docker_path.exists():
            return str(docker_path)
        
        # Try local path (relative to backend directory)
        local_path = Path(__file__).parent.parent / "secrets" / "firebase-credentials.json"
        if local_path.exists():
            return str(local_path)
        
        # Fallback to default Docker path (will fail if not exists, but that's okay)
        return "/app/firebase-credentials.json"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
