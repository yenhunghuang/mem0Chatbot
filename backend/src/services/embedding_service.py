"""
嵌入服務模組：Google Embeddings API 整合

此模組提供文本向量化功能，用於語義搜索。
"""

from typing import List

import google.generativeai as genai

from ..config import settings
from ..utils.logger import get_logger
from ..utils.exceptions import LLMError

logger = get_logger(__name__)


class EmbeddingService:
    """嵌入服務"""

    _client = None

    @classmethod
    def initialize(cls) -> None:
        """初始化 Google Embeddings 客戶端"""
        try:
            genai.configure(api_key=settings.google_api_key)
            logger.info("Google Embeddings 客戶端已初始化")
        except Exception as e:
            logger.error(f"Google Embeddings 初始化失敗: {str(e)}")
            raise LLMError(f"無法初始化嵌入服務: {str(e)}")

    @classmethod
    def embed_text(cls, text: str) -> List[float]:
        """
        將文本轉換為向量

        Args:
            text: 要嵌入的文本

        Returns:
            List[float]: 向量表示

        Raises:
            LLMError: 如果嵌入失敗
        """
        try:
            response = genai.embed_content(
                model=f"models/{settings.mem0_embedder_model}",
                content=text,
            )
            if "embedding" in response:
                return response["embedding"]
            else:
                raise LLMError("嵌入回應不包含向量")

        except Exception as e:
            logger.error(f"文本嵌入失敗: {str(e)}")
            raise LLMError(f"無法嵌入文本: {str(e)}")

    @classmethod
    def embed_batch(cls, texts: List[str]) -> List[List[float]]:
        """
        批量嵌入文本

        Args:
            texts: 文本列表

        Returns:
            List[List[float]]: 向量列表

        Raises:
            LLMError: 如果嵌入失敗
        """
        try:
            embeddings = []
            for text in texts:
                embedding = cls.embed_text(text)
                embeddings.append(embedding)
            return embeddings

        except LLMError:
            raise
        except Exception as e:
            logger.error(f"批量嵌入失敗: {str(e)}")
            raise LLMError(f"無法批量嵌入文本: {str(e)}")
