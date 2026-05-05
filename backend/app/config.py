# Module cấu hình: đọc biến môi trường để bật/tắt ASR thật và tóm tắt bằng LLM.
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Cho phép đọc file .env ở thư mục backend (không bắt buộc).
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # URL gốc API (https://api.valsea.ai). Nếu để trống nhưng có API key → dùng mặc định chính thức.
    valsea_api_base: str = ""
    # Khóa (tiền tố vl_…); để trống = chế độ transcript mẫu, không gọi mạng.
    valsea_api_key: str = ""
    # Ngôn ngữ ASR theo tài liệu VALSEA (vd: vietnamese, english, english-us).
    valsea_language: str = "vietnamese"
    # Gửi kèm trong form (mặc định bật theo API).
    valsea_enable_correction: bool = True
    valsea_enable_tags: bool = True
    valsea_response_format: str = "json"  # json | verbose_json
    # Các tính năng NLP phụ của VALSEA sau khi có transcript.
    valsea_enable_enrichment: bool = True
    valsea_translate_target: str = "english"
    # CORS: danh sách origin frontend được phép gọi API.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    def valsea_base_resolved(self) -> str:
        """
        Base URL hợp lệ cho httpx (luôn có scheme).
        - Trống hoặc nhầm dán API key (vl_…) → https://api.valsea.ai
        - Chỉ hostname (api.valsea.ai) → tự thêm https://
        """
        b = (self.valsea_api_base or "").strip().rstrip("/")
        if not b or b.startswith("vl_"):
            return "https://api.valsea.ai"
        if b.startswith("http://") or b.startswith("https://"):
            return b
        return f"https://{b.lstrip('/')}"


# Một instance dùng chung trong toàn app (import settings).
settings = Settings()
