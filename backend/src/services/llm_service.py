"""
LLM 服務模組：Google Gemini 2.5 Flash 整合

此模組提供大型語言模型的對話功能。
"""

from typing import List, Optional

import google.generativeai as genai

from ..config import settings
from ..utils.logger import get_logger
from ..utils.exceptions import LLMError

logger = get_logger(__name__)


class LLMService:
    """LLM 服務"""

    _model = None

    @classmethod
    def initialize(cls) -> None:
        """初始化 Google Gemini 客戶端"""
        try:
            genai.configure(api_key=settings.google_api_key)
            cls._model = genai.GenerativeModel(settings.mem0_llm_model)
            logger.info(f"Google Gemini 客戶端已初始化: {settings.mem0_llm_model}")
        except Exception as e:
            logger.error(f"Google Gemini 初始化失敗: {str(e)}")
            raise LLMError(f"無法初始化 LLM 服務: {str(e)}")

    @classmethod
    def generate_response(
        cls,
        user_input: str,
        memories: Optional[List[str]] = None,
        conversation_history: Optional[List[dict]] = None,
    ) -> str:
        """
        生成 LLM 回應

        Args:
            user_input: 使用者輸入
            memories: 相關記憶列表（選用）
            conversation_history: 對話歷史（選用）

        Returns:
            str: LLM 回應

        Raises:
            LLMError: 如果生成失敗
        """
        try:
            if cls._model is None:
                cls.initialize()

            # 構建系統提示
            system_prompt = """你是一個友善的投資顧問助理。
你的職責是根據使用者的投資偏好和風險承受度提供個人化的投資建議。
所有回應必須使用繁體中文。
回應應該簡潔明了，避免過度技術性的術語。
"""

            # 新增記憶上下文
            if memories:
                memory_context = "以下是使用者的已知偏好和信息：\n"
                for memory in memories:
                    memory_context += f"- {memory}\n"
                system_prompt += f"\n{memory_context}"

            # 構建提示
            full_prompt = f"{system_prompt}\n使用者：{user_input}\n助理："

            # 配置安全設定（Google Gemini 支持的 5 個類別）
            # 使用 BLOCK_ONLY_HIGH 平衡安全性和可用性
            safety_settings = [
                {
                    "category": genai.types.HarmCategory.HARM_CATEGORY_UNSPECIFIED,
                    "threshold": genai.types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                },
                {
                    "category": genai.types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                    "threshold": genai.types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                },
                {
                    "category": genai.types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    "threshold": genai.types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                },
                {
                    "category": genai.types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    "threshold": genai.types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                },
                {
                    "category": genai.types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    "threshold": genai.types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                },
            ]

            logger.debug(f"發送 LLM 請求，prompt 長度: {len(full_prompt)} 字元")

            # 呼叫模型
            response = cls._model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=500,
                ),
                safety_settings=safety_settings,
            )

            logger.debug(f"LLM 回應狀態: finish_reason={getattr(response, 'finish_reason', 'unknown')}")

            # 檢查是否因為安全過濾器被阻擋
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
                logger.error(
                    f"LLM 回應被安全過濾器阻擋。"
                    f"Block reason: {response.prompt_feedback.block_reason}, "
                    f"Safety ratings: {response.prompt_feedback.safety_ratings}"
                )
                raise LLMError(
                    "您的查詢被安全過濾器識別為不適當的內容。請用不同的方式表達您的問題。"
                )

            # 檢查回應內容是否有效
            if response and hasattr(response, 'text') and response.text:
                logger.info(
                    f"LLM 回應成功 (tokens: {len(response.text.split())}, "
                    f"finish_reason: {getattr(response, 'finish_reason', 'STOP')})"
                )
                return response.text
            else:
                # 記錄完整的回應以便調試
                finish_reason = getattr(response, 'finish_reason', 'unknown')
                logger.error(
                    f"LLM 未返回有效回應。"
                    f"finish_reason: {finish_reason}, "
                    f"has_text: {hasattr(response, 'text')}"
                )
                
                # 如果有安全評級信息，也記錄下來
                if hasattr(response, 'safety_ratings'):
                    logger.error(f"Safety ratings: {response.safety_ratings}")
                
                # 根據 finish_reason 提供更具體的錯誤訊息
                if finish_reason == "SAFETY":
                    raise LLMError("回應因安全考慮被阻擋。請用不同的方式表達您的問題。")
                elif finish_reason == "MAX_TOKENS":
                    raise LLMError("回應過長，已被截斷。")
                else:
                    raise LLMError(f"LLM 未返回有效回應 (reason: {finish_reason})")

        except Exception as e:
            logger.error(f"LLM 生成失敗: {str(e)}")
            raise LLMError(f"無法生成回應: {str(e)}")

    @classmethod
    def extract_preferences(cls, text: str) -> Optional[str]:
        """
        從文本中提取投資偏好

        Args:
            text: 使用者輸入

        Returns:
            Optional[str]: 提取的偏好文本

        Raises:
            LLMError: 如果提取失敗
        """
        try:
            if cls._model is None:
                cls.initialize()

            extraction_prompt = f"""分析以下文本，提取任何投資相關的偏好、目標或風險偏好。
如果沒有投資相關信息，返回 'NONE'。
只返回提取的信息，不要加入任何其他解釋。

文本: {text}

提取的偏好:"""

            # 配置安全設定（Google Gemini 支持的 5 個類別）
            safety_settings = [
                {
                    "category": genai.types.HarmCategory.HARM_CATEGORY_UNSPECIFIED,
                    "threshold": genai.types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                },
                {
                    "category": genai.types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                    "threshold": genai.types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                },
                {
                    "category": genai.types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    "threshold": genai.types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                },
                {
                    "category": genai.types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    "threshold": genai.types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                },
                {
                    "category": genai.types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    "threshold": genai.types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                },
            ]

            response = cls._model.generate_content(
                extraction_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=200,
                ),
                safety_settings=safety_settings,
            )

            # 檢查回應是否被安全過濾器阻擋
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
                logger.warning(
                    f"偏好提取被安全過濾器阻擋: block_reason={response.prompt_feedback.block_reason}"
                )
                return None

            if response and hasattr(response, 'text') and response.text:
                result = response.text.strip()
                if result == "NONE":
                    logger.debug("用戶消息中未找到投資偏好")
                    return None
                logger.info(f"成功提取投資偏好: {result[:100]}")
                return result
            else:
                finish_reason = getattr(response, 'finish_reason', 'unknown')
                logger.warning(
                    f"偏好提取未返回有效回應，finish_reason: {finish_reason}"
                )
                if hasattr(response, 'safety_ratings'):
                    logger.warning(f"Safety ratings: {response.safety_ratings}")
                return None

        except Exception as e:
            logger.error(f"偏好提取失敗: {str(e)}")
            return None
