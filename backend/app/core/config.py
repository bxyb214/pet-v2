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
    # 数学课程视频的媒体令牌（放 URL 查询串，供 <video>/AirPlay 取流）
    media_token_hours: int = 6

    database_url: str = "sqlite:///./data/pet.db"

    # 开发/测试环境：右上角显示 DEV，AI 接口返回确定性模拟结果，不调用任何外部服务
    dev_mode: bool = False

    # Qwen Realtime Key（口语），只存服务端，接口仅回尾号
    qwen_api_key: str = ""
    qwen_sdp_endpoint: str = "https://dashscope.aliyuncs.com/api/v1/services/aigc/realtime"

    # 初始化 claim：库内无任何账号时允许用邀请码创建首个账号
    allow_claim: bool = True


def require_production_secret(settings: Settings) -> None:
    """生产模式必须显式注入强随机 JWT secret，避免默认值被带上线。

    只在应用启动时调用（main.py），不要放进 Settings 校验：
    Alembic 迁移只需要数据库地址，不应被 JWT 配置拦住。
    """
    if not settings.dev_mode and (
        settings.jwt_secret == "dev-only-change-me" or len(settings.jwt_secret) < 32
    ):
        raise RuntimeError("生产环境必须设置至少 32 字符的 PET_JWT_SECRET")


@lru_cache
def get_settings() -> Settings:
    return Settings()
