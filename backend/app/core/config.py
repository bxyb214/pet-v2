"""应用配置：全部从环境变量读取，密钥不入 git。"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="PET_", extra="ignore")

    app_name: str = "PET v2 API"
    # 生产必须通过环境变量注入强随机值
    jwt_secret: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"
    access_token_hours: int = 2
    refresh_token_days: int = 60

    database_url: str = "sqlite:///./data/pet.db"

    # Qwen Realtime Key（口语），只存服务端，接口仅回尾号
    qwen_api_key: str = ""
    qwen_sdp_endpoint: str = "https://dashscope.aliyuncs.com/api/v1/services/aigc/realtime"

    # 初始化 claim：库内无任何账号时允许用邀请码创建首个账号
    allow_claim: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
