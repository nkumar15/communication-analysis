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
    firebase_api_key: Optional[str] = None # Web API Key for client-side emulation
    firebase_credentials_path: Optional[str] = None
    
    # Auth Provider (firebase, keycloak, auth0, etc.)
    # Controls both runtime authentication and tenant provisioning
    auth_provider: str = "firebase"
    
    # Monitoring Provider (prometheus, datadog, none)
    monitoring_provider: str = "prometheus"
    
    # Tracing Provider (otlp, console, none)
    tracing_provider: str = "otlp"
    
    # URLs
    frontend_url: str
    frontend_url_b2c: Optional[str] = None  # B2C frontend (port 3001), falls back to frontend_url
    backend_url: str
    
    # Mobile Deep Links
    mobile_app_domain: Optional[str] = "app.example.com"  # Must match AndroidManifest.xml
    mobile_package_name: Optional[str] = "com.saas.b2b"   # Android package name
    

    # Email (Resend)
    resend_api_key: Optional[str] = None
    email_provider: str = "mailhog"
    email_from: str = "Enterprise SSO <noreply@localhost>"
    mailhog_host: str = "mailhog"
    mailhog_port: int = 1025

    # Redis (for Celery task queue)
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    
    # Celery (defaults to Redis, can be overridden for SQS/GCP)
    celery_broker_url: Optional[str] = None
    celery_result_backend: Optional[str] = None
    
    @property
    def celery_broker_url_resolved(self) -> str:
        if self.celery_broker_url:
            return self.celery_broker_url
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
        
    @property
    def celery_result_backend_resolved(self) -> str:
        if self.celery_result_backend:
            return self.celery_result_backend
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    # Payment Provider Configuration
    payment_provider: str = "stripe"  # 'stripe' | 'razorpay' | 'xendit'
    
    # Stripe
    stripe_secret_key: Optional[str] = None
    stripe_publishable_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None
    
    # Stripe Price IDs (B2C - from Stripe Dashboard)
    stripe_price_premium_monthly: Optional[str] = None
    stripe_price_premium_yearly: Optional[str] = None
    stripe_price_ultimate_monthly: Optional[str] = None
    stripe_price_ultimate_yearly: Optional[str] = None
    
    # B2B Stripe (separate keys for B2B billing)
    stripe_b2b_secret_key: Optional[str] = None
    stripe_b2b_publishable_key: Optional[str] = None
    stripe_b2b_webhook_secret: Optional[str] = None
    
    # B2B Stripe Price IDs (per-seat pricing tiers)
    stripe_b2b_price_starter_monthly: Optional[str] = None
    stripe_b2b_price_starter_yearly: Optional[str] = None
    stripe_b2b_price_professional_monthly: Optional[str] = None
    stripe_b2b_price_professional_yearly: Optional[str] = None
    stripe_b2b_price_enterprise_monthly: Optional[str] = None
    stripe_b2b_price_enterprise_yearly: Optional[str] = None
    
    # Future providers (not implemented yet)
    razorpay_key_id: Optional[str] = None
    razorpay_key_secret: Optional[str] = None
    xendit_secret_key: Optional[str] = None
    
    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:3001,http://localhost:3002,http://localhost:8000,http://localhost:8001"
    
    # Logging Configuration
    log_environment: str = "local"  # local, gcp, aws, production
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    log_json_indent: Optional[int] = 2  # Pretty print JSON in local, None for production
    sentry_dsn: Optional[str] = None
    otel_exporter_otlp_endpoint: Optional[str] = None

    # Cloud Provider Configuration (for logging)
    gcp_project_id: Optional[str] = None
    aws_region: Optional[str] = None
    
    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    @property
    def firebase_credentials_path_resolved(self) -> str:
        """Resolve Firebase credentials path for Docker or local environment"""
        if self.firebase_credentials_path and Path(self.firebase_credentials_path).exists():
            return self.firebase_credentials_path
        
        # Try Docker path
        docker_path = Path("/app/firebase-credentials.json")
        if docker_path.exists():
            return str(docker_path)
        
        # Try local path (relative to backend directory - e.g. backend/secrets)
        local_backend_secrets = Path(__file__).parent.parent / "secrets" / "firebase-credentials.json"
        if local_backend_secrets.exists():
            return str(local_backend_secrets)

        # Try project root (up one more level - e.g. enterprisesso/secrets)
        project_root_secrets = Path(__file__).parent.parent.parent / "secrets" / "firebase-credentials.json"
        if project_root_secrets.exists():
            return str(project_root_secrets)
        
        # Fallback to default Docker path (will fail if not exists, but that's okay)
        return "/app/firebase-credentials.json"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
