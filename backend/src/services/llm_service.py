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
        memories: Optional[List] = None,
        conversation_history: Optional[List[dict]] = None,
    ) -> str:
        """
        生成 LLM 回應（US2 T039 改進）

        Args:
            user_input: 使用者輸入
            memories: 相關記憶列表（可以是字串或字典列表）
            conversation_history: 對話歷史（選用）

        Returns:
            str: LLM 回應

        Raises:
            LLMError: 如果生成失敗
        """
        try:
            if cls._model is None:
                cls.initialize()

            # 構建系統提示 - 使用簡潔中性的措辭
            system_prompt = """你是一個專業、友善的投資顧問助理。
請根據使用者的需求提供資訊和建議。
使用繁體中文回應，保持簡潔明瞭。
"""

            # 新增記憶上下文（US2 T039）
            # 詳細的記憶診斷日誌
            logger.info(f"[LLM] memories 類型: {type(memories)}, 值: {memories}")
            
            if memories and len(memories) > 0:
                logger.info(f"[LLM] 注入記憶: 共 {len(memories)} 個")
                
                # 提取實際的記憶內容
                memory_contents = []
                for idx, memory in enumerate(memories):
                    # 支援字典格式（新增）或字串格式（舊版本相容）
                    if isinstance(memory, dict):
                        content = memory.get("content", "")
                        logger.info(f"  [{idx+1}] 字典記憶: id={memory.get('id', 'N/A')}, content={content!r}")
                    else:
                        content = str(memory)
                        logger.info(f"  [{idx+1}] 字符記憶: {content!r}")
                    
                    if content:
                        memory_contents.append(content)
                        logger.info(f"      [OK] 記憶內容有效: {content[:50]}...")
                    else:
                        logger.warning(f"      [WARN] 記憶內容為空")
                
                # 只有當有實際記憶內容時，才添加到 system prompt
                if memory_contents:
                    memory_context = "已知的使用者信息與投資偏好：\n"
                    for content in memory_contents:
                        memory_context += f"• {content}\n"
                    memory_context += "\n請基於上述使用者信息提供個人化的投資建議。\n"
                    system_prompt += memory_context
                    logger.info(f"[LLM] 記憶已成功注入到 prompt ({len(memory_contents)} 項)")
                else:
                    logger.warning(f"[LLM] 記憶結果有 {len(memories)} 個但內容全為空")
            else:
                logger.info(f"[LLM] 未找到記憶 (memories 為空或 None), memories={memories!r}")

            # 構建對話歷史上下文
            history_context = ""
            if conversation_history:
                history_context = "\n對話歷史：\n"
                for msg in conversation_history:
                    role = msg.get("role", "unknown")
                    content = msg.get("content", "")
                    if role == "user":
                        history_context += f"使用者: {content}\n"
                    elif role == "assistant":
                        history_context += f"助理: {content}\n"
                
                system_prompt += history_context

            # 構建提示
            full_prompt = f"""{system_prompt}

【對話記錄】
{history_context if history_context else "(首次對話)"}

【當前提問】
{user_input}

【要求】
- 請基於已知的使用者信息（如果提供）來個人化回應
- 避免重複詢問已知的信息
- 提供具體的投資建議而非泛泛而談
- 如果尚缺相關信息，可詢問但要指出已知內容

【回應】
"""

            # 配置安全設定 - 使用寬鬆的安全級別以支援金融/投資內容
            # BLOCK_ONLY_HIGH 只阻擋最嚴重的內容
            safety_settings = [
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

            logger.debug(f"發送 LLM 請求，prompt 長度: {len(full_prompt)} 字元，記憶數: {len(memories) if memories else 0}")

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

            # 取得 finish_reason
            finish_reason = getattr(response, 'finish_reason', None)
            finish_reason_name = finish_reason.name if finish_reason and hasattr(finish_reason, 'name') else str(finish_reason)
            
            logger.debug(f"finish_reason 詳情: {finish_reason} (name={finish_reason_name})")

            # 檢查 finish_reason 以判斷是否因為安全原因被阻擋
            if finish_reason and finish_reason_name == "SAFETY":
                logger.warning(
                    f"LLM 回應因安全原因被阻擋 (finish_reason=SAFETY)，使用備用回應"
                )
                # 返回備用回應而不是拋出異常
                return "感謝您的提問。為了提供更好的服務，請用不同的方式表達您的問題。"

            # 檢查是否有 prompt_feedback 中的阻擋原因
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
                logger.warning(
                    f"LLM 回應被安全過濾器阻擋。"
                    f"Block reason: {response.prompt_feedback.block_reason}，使用備用回應"
                )
                # 返回備用回應而不是拋出異常
                return "感謝您的提問。我們無法處理此請求，請稍後重試或使用不同的方式表達。"

            # 安全地取得回應文本，避免觸發快速訪問器異常
            try:
                text = None
                if response and response.candidates and len(response.candidates) > 0:
                    candidate = response.candidates[0]
                    # 檢查是否有內容和部分
                    if candidate.content and hasattr(candidate.content, 'parts'):
                        parts = candidate.content.parts
                        if parts:  # 檢查 parts 是否不為空
                            text = "".join(part.text for part in parts if hasattr(part, 'text'))
                
                # 如果成功取得文本
                if text:
                    # 計算實際注入的記憶數
                    actual_memories_used = len([m for m in (memories or []) if m and m.get("content", "").strip()]) if memories else 0
                    
                    logger.info(
                        f"[LLM] 回應成功 (tokens: {len(text.split())}, "
                        f"finish_reason: {finish_reason_name}, "
                        f"memories_injected: {actual_memories_used}, "
                        f"memories_searched: {len(memories) if memories else 0})"
                    )
                    return text
                
                # 如果沒有找到有效的回應部分，記錄詳細信息用於調試
                has_candidates = response and response.candidates and len(response.candidates) > 0
                has_content = has_candidates and response.candidates[0].content is not None
                has_parts = has_content and hasattr(response.candidates[0].content, 'parts')
                parts_content = response.candidates[0].content.parts if has_parts else None
                parts_len = len(parts_content) if parts_content else 0
                
                # 檢查安全評級和候選者的阻擋原因
                candidate_finish_reason = None
                safety_ratings = None
                if has_candidates:
                    candidate = response.candidates[0]
                    candidate_finish_reason = getattr(candidate, 'finish_reason', None)
                    safety_ratings = getattr(candidate, 'safety_ratings', None)
                
                logger.warning(
                    f"LLM 回應為空: "
                    f"finish_reason={finish_reason_name}, "
                    f"candidate_finish_reason={candidate_finish_reason}, "
                    f"has_candidates={has_candidates}, "
                    f"has_content={has_content}, "
                    f"has_parts={has_parts}, "
                    f"parts_len={parts_len}"
                )
                
                # 記錄安全評級以便診斷
                if safety_ratings:
                    logger.warning(f"Safety ratings: {safety_ratings}")
                
                # 如果候選者的 finish_reason 是 SAFETY
                if candidate_finish_reason:
                    candidate_finish_reason_name = candidate_finish_reason.name if hasattr(candidate_finish_reason, 'name') else str(candidate_finish_reason)
                    if candidate_finish_reason_name == "SAFETY":
                        logger.warning("候選者因安全原因被阻擋，使用備用回應")
                        return "感謝您的提問。為了提供更好的服務，請用不同的方式表達您的問題。"
                
                # 回應為空，可能是由於內容審核或其他原因，返回備用回應
                logger.warning("LLM 回應為空，返回備用回應")
                return "感謝您的提問。請稍後重試。"
            except ValueError as e:
                # 這通常是由 response.text 快速訪問器拋出的
                logger.error(
                    f"LLM 回應無效 (ValueError): {str(e)}"
                )
                raise LLMError(f"LLM 回應無效: {str(e)}")

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

            # 配置安全設定 - 暫時使用最寬鬆的設定進行測試
            safety_settings = [
                {
                    "category": genai.types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                    "threshold": genai.types.HarmBlockThreshold.BLOCK_NONE,
                },
                {
                    "category": genai.types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    "threshold": genai.types.HarmBlockThreshold.BLOCK_NONE,
                },
                {
                    "category": genai.types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    "threshold": genai.types.HarmBlockThreshold.BLOCK_NONE,
                },
                {
                    "category": genai.types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    "threshold": genai.types.HarmBlockThreshold.BLOCK_NONE,
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

            # 檢查 finish_reason 以判斷是否因為安全原因被阻擋
            finish_reason = getattr(response, 'finish_reason', None)
            if finish_reason and finish_reason.name == "SAFETY":
                logger.warning(
                    f"偏好提取因安全原因被阻擋 (finish_reason=SAFETY)"
                )
                return None

            # 檢查是否有 prompt_feedback 中的阻擋原因
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
                logger.warning(
                    f"偏好提取被安全過濾器阻擋: block_reason={response.prompt_feedback.block_reason}"
                )
                return None

            # 安全地取得回應文本
            try:
                if response and response.candidates and len(response.candidates) > 0:
                    candidate = response.candidates[0]
                    # 檢查是否有內容
                    if candidate.content and hasattr(candidate.content, 'parts'):
                        parts = candidate.content.parts
                        if parts and len(parts) > 0:
                            text = "".join(part.text for part in parts if hasattr(part, 'text'))
                            if text:
                                result = text.strip()
                                if result == "NONE":
                                    logger.debug("用戶消息中未找到投資偏好")
                                    return None
                                logger.info(f"成功提取投資偏好: {result[:100]}")
                                return result
                
                # 如果沒有找到有效的回應部分
                logger.debug(
                    f"偏好提取未返回有效回應，finish_reason: {finish_reason}"
                )
                return None
            except ValueError as e:
                # 這通常是由快速訪問器拋出的
                logger.debug(f"偏好提取回應無效: {str(e)}")
                return None

        except Exception as e:
            logger.error(f"偏好提取失敗: {str(e)}")
            return None
