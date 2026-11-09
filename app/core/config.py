import os
from dataclasses import dataclass, field

from dotenv import load_dotenv


load_dotenv()


@dataclass
class Settings:
    DATABASE_URL: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./negotiation.db"))
    SECRET_KEY: str = field(default_factory=lambda: os.getenv("SECRET_KEY", ""))
    SERVICE_SECRET: str = field(default_factory=lambda: os.getenv("SERVICE_SECRET", ""))
    ACCESS_TOKEN_EXPIRE_MINUTES: int = field(default_factory=lambda: int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")))
    GEMINI_API_KEY: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    GEMINI_MODEL: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
    GEMINI_TIMEOUT_SECONDS: float = field(default_factory=lambda: float(os.getenv("GEMINI_TIMEOUT_SECONDS", "30")))
    GEMINI_REQUESTS_PER_MINUTE: int = field(default_factory=lambda: int(os.getenv("GEMINI_REQUESTS_PER_MINUTE", "10")))
    REDIS_URL: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"))
    TWIN_GRPC_TARGET: str = field(default_factory=lambda: os.getenv("TWIN_GRPC_TARGET", "127.0.0.1:50051"))
    ANALYSIS_GRPC_TARGET: str = field(default_factory=lambda: os.getenv("ANALYSIS_GRPC_TARGET", "127.0.0.1:50052"))
    EVENT_GRPC_TARGET: str = field(default_factory=lambda: os.getenv("EVENT_GRPC_TARGET", "127.0.0.1:50053"))
    GRPC_TIMEOUT_SECONDS: float = field(default_factory=lambda: float(os.getenv("GRPC_TIMEOUT_SECONDS", "40")))
    GRPC_TLS_CA: str = field(default_factory=lambda: os.getenv("GRPC_TLS_CA", ""))
    GRPC_TLS_CERT: str = field(default_factory=lambda: os.getenv("GRPC_TLS_CERT", ""))
    GRPC_TLS_KEY: str = field(default_factory=lambda: os.getenv("GRPC_TLS_KEY", ""))
    CORS_ORIGINS: list[str] = field(default_factory=lambda: os.getenv("CORS_ORIGINS", "http://localhost:4200").split(","))

    def validate_security(self) -> None:
        if len(self.SECRET_KEY) < 32 or len(self.SERVICE_SECRET) < 32:
            raise RuntimeError("SECRET_KEY and SERVICE_SECRET must each contain at least 32 characters")
        if self.SECRET_KEY == self.SERVICE_SECRET:
            raise RuntimeError("Access and service signing keys must be different")
        if self.GEMINI_REQUESTS_PER_MINUTE < 1 or self.GRPC_TIMEOUT_SECONDS <= 0:
            raise RuntimeError("Rate and timeout settings must be positive")


settings = Settings()
