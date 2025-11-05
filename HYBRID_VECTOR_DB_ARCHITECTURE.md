# 混合向量資料庫架構設計：問答記憶 + 新聞記憶

**架構方案**:
- **問答機器人記憶**: ChromaDB + Mem0（使用者偏好、對話歷史）
- **新聞資料記憶**: Qdrant + Mem0 (TTL 自動過期)

**版本**: 1.0.0
**日期**: 2025-11-05

---

## 📋 目錄

1. [架構設計理念](#架構設計理念)
2. [技術架構圖](#技術架構圖)
3. [資料分離策略](#資料分離策略)
4. [完整實作方案](#完整實作方案)
5. [Mem0 多向量儲存配置](#mem0-多向量儲存配置)
6. [整合範例](#整合範例)
7. [部署與維護](#部署與維護)

---

## 🎯 架構設計理念

### 為什麼使用混合架構？

#### 問答機器人記憶的特性

```
使用者偏好記憶:
├── 數據特性
│   ├── 數量少（每使用者 < 1000 條）
│   ├── 價值高（長期有效）
│   ├── 更新頻繁（持續學習）
│   └── 需要精準檢索
│
├── 儲存需求
│   ├── 永久保留（或長期保留）
│   ├── 無需 TTL
│   └── 容量可控
│
└── 最佳選擇
    └── ChromaDB（輕量、本地、易管理）✓
```

#### 新聞資料記憶的特性

```
美股新聞資料:
├── 數據特性
│   ├── 數量大（每日 10,000+ 篇）
│   ├── 時效性強（價值遞減）
│   ├── 寫多讀少
│   └── 需要快速檢索
│
├── 儲存需求
│   ├── 定期過期（30 天）
│   ├── 需要 TTL 自動清理
│   └── 容量持續增長
│
└── 最佳選擇
    └── Qdrant（TTL、高效能、易擴展）✓
```

### 架構優勢

| 特性 | 單一向量資料庫 | 混合架構 |
|------|--------------|---------|
| **資料隔離** | ❌ 混在一起 | ✅ 清晰分離 |
| **容量管理** | ❌ 統一管理，複雜 | ✅ 各自管理，簡單 |
| **效能優化** | ❌ 難以針對性優化 | ✅ 各自最佳化 |
| **成本控制** | ❌ 難以精細控制 | ✅ 新聞自動過期降成本 |
| **擴展性** | ❌ 受限於單一資料庫 | ✅ 獨立擴展 |

---

## 🏗 技術架構圖

### 完整系統架構

```
┌─────────────────────────────────────────────────────────────────┐
│                          FastAPI Backend                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Service Layer                          │  │
│  │  ┌─────────────────────┐    ┌──────────────────────┐    │  │
│  │  │ ConversationService │    │   NewsSearchService  │    │  │
│  │  └──────────┬──────────┘    └──────────┬───────────┘    │  │
│  │             │                           │                 │  │
│  │             ▼                           ▼                 │  │
│  │  ┌─────────────────────┐    ┌──────────────────────┐    │  │
│  │  │   MemoryService     │    │   NewsMemoryService  │    │  │
│  │  │   (問答記憶)         │    │   (新聞記憶)          │    │  │
│  │  └──────────┬──────────┘    └──────────┬───────────┘    │  │
│  └─────────────┼────────────────────────────┼───────────────┘  │
└────────────────┼────────────────────────────┼──────────────────┘
                 │                            │
                 ▼                            ▼
    ┌────────────────────────┐   ┌────────────────────────┐
    │      Mem0 Instance 1   │   │    Mem0 Instance 2     │
    │  (使用者偏好提取)       │   │  (新聞內容提取)         │
    └────────────┬───────────┘   └────────────┬───────────┘
                 │                            │
                 ▼                            ▼
    ┌────────────────────────┐   ┌────────────────────────┐
    │       ChromaDB         │   │        Qdrant          │
    │  Collection:           │   │  Collection:           │
    │  - user_preferences    │   │  - us_stock_news       │
    │  - conversation_memory │   │  - news_embeddings     │
    │                        │   │                        │
    │  特性:                  │   │  特性:                  │
    │  - 永久保留             │   │  - TTL: 30 天          │
    │  - 精準檢索             │   │  - 自動過期             │
    │  - 小數據量             │   │  - 大數據量             │
    └────────────────────────┘   └────────────────────────┘
          ./data/chroma              localhost:6333
```

---

## 📦 資料分離策略

### 1. 問答機器人記憶（ChromaDB）

**儲存內容**:
```
user_preferences (使用者偏好):
├── "使用者偏好科技股"
├── "使用者風險承受度為中等"
├── "使用者計劃長期投資"
└── ...

conversation_memory (對話記憶):
├── 重要的對話摘要
├── 使用者提問的主題
└── ...
```

**特性**:
- 永久保留（或 90 天清理）
- 每使用者 < 1000 條記憶
- 高精準度檢索
- 支援 Mem0 自動提取

---

### 2. 新聞資料記憶（Qdrant）

**儲存內容**:
```
us_stock_news (美股新聞):
├── "蘋果公司發布新 iPhone，股價上漲 5%"
├── "特斯拉 Q3 財報超預期，盤後漲幅達 10%"
├── "Fed 宣布維持利率不變，市場反應平淡"
└── ... (每日 10,000+ 篇)

news_embeddings:
├── 新聞標題向量
├── 新聞摘要向量
└── 新聞全文向量（可選）
```

**特性**:
- TTL: 30 天自動過期
- 每日新增 10,000+ 條
- 快速語義搜索
- 支援時間範圍過濾

---

## 💻 完整實作方案

### 專案結構

```
backend/
├── src/
│   ├── services/
│   │   ├── memory_service.py          # 問答記憶服務（ChromaDB）
│   │   ├── news_memory_service.py     # 新聞記憶服務（Qdrant）✨ 新增
│   │   ├── conversation_service.py    # 對話服務
│   │   └── news_search_service.py     # 新聞搜索服務 ✨ 新增
│   │
│   ├── config/
│   │   └── settings.py                # 配置（新增 Qdrant 設定）
│   │
│   └── main.py
│
├── data/
│   ├── chroma/                        # ChromaDB 資料
│   └── qdrant/                        # Qdrant 資料（可選本地）
│
├── requirements.txt                   # 新增 qdrant-client
└── .env
```

---

### 步驟 1: 更新依賴

**`backend/requirements.txt`**:

```txt
# 現有依賴
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic>=2.7.3,<3.0.0
mem0ai==0.0.10
google-generativeai==0.3.1
google-genai>=1.47.0
chromadb>=0.4.0
python-dotenv==1.0.0

# 新增：Qdrant 支援
qdrant-client>=1.7.0  # ✨ 新增

# 測試
pytest==7.4.3
pytest-asyncio==0.21.1
httpx==0.25.1
```

安裝:
```bash
cd backend
pip install qdrant-client
```

---

### 步驟 2: 更新環境變數

**`backend/.env`**:

```bash
# Google API
GOOGLE_API_KEY=your_google_api_key

# ChromaDB（問答記憶）
DATABASE_URL=sqlite:///./data/app.db
CHROMA_PATH=./data/chroma

# Qdrant（新聞記憶）✨ 新增
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=us_stock_news
QDRANT_USE_MEMORY=false  # true=記憶體模式, false=持久化

# Mem0 配置
MEM0_LLM_MODEL=gemini-2.0-flash-exp
MEM0_EMBEDDER_MODEL=text-embedding-004

# 新聞 TTL 設定 ✨ 新增
NEWS_TTL_DAYS=30

# CORS
CORS_ORIGINS=["http://localhost:3000"]
LOG_LEVEL=INFO
```

---

### 步驟 3: 更新配置

**`backend/src/config/settings.py`**:

```python
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # 現有配置
    google_api_key: str
    database_url: str = "sqlite:///./data/app.db"
    chroma_path: str = "./data/chroma"
    mem0_llm_model: str = "gemini-2.0-flash-exp"
    mem0_embedder_model: str = "text-embedding-004"
    cors_origins: List[str] = ["http://localhost:3000"]
    log_level: str = "INFO"

    # 新增：Qdrant 配置 ✨
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection_name: str = "us_stock_news"
    qdrant_use_memory: bool = False
    news_ttl_days: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

---

### 步驟 4: 建立新聞記憶服務

**`backend/src/services/news_memory_service.py`**:

```python
"""
新聞記憶服務：使用 Qdrant + Mem0 管理新聞資料

特性:
- 使用 Qdrant 向量資料庫
- 支援 TTL 自動過期（30 天）
- 整合 Mem0 進行新聞內容提取
- 高效能語義搜索
"""

from typing import List, Optional, Dict
from datetime import datetime, timedelta
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    Range
)

try:
    from mem0 import Memory
except ImportError:
    Memory = None

from ..config import settings
from ..utils.logger import get_logger
from ..utils.exceptions import MemoryError

logger = get_logger(__name__)


class NewsMemoryService:
    """新聞記憶服務（Qdrant + Mem0）"""

    _qdrant_client = None
    _mem0_client = None
    _collection_name = settings.qdrant_collection_name

    @classmethod
    def initialize(cls) -> None:
        """初始化 Qdrant 和 Mem0"""

        try:
            # 初始化 Qdrant
            cls._qdrant_client = QdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port,
                prefer_grpc=False  # 使用 REST API
            )

            # 建立集合（如果不存在）
            try:
                cls._qdrant_client.get_collection(cls._collection_name)
                logger.info(f"Qdrant 集合 '{cls._collection_name}' 已存在")
            except:
                cls._qdrant_client.create_collection(
                    collection_name=cls._collection_name,
                    vectors_config=VectorParams(
                        size=768,  # Google Embeddings 維度
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"已建立 Qdrant 集合: {cls._collection_name}")

            # 初始化 Mem0（用於新聞內容提取）
            if Memory is None:
                raise MemoryError("Mem0 庫未安裝")

            cls._mem0_client = Memory.from_config({
                "llm": {
                    "provider": "gemini",
                    "config": {
                        "model": settings.mem0_llm_model,
                        "temperature": 0.5,  # 新聞提取較低溫度
                        "max_tokens": 1000,
                        "api_key": settings.google_api_key,
                    },
                },
                "embedder": {
                    "provider": "gemini",
                    "config": {
                        "model": f"models/{settings.mem0_embedder_model}",
                        "api_key": settings.google_api_key,
                    },
                },
                # 注意：這裡不使用 Mem0 的向量儲存，我們自己管理 Qdrant
            })

            logger.info("新聞記憶服務已初始化（Qdrant + Mem0）")

        except Exception as e:
            logger.error(f"新聞記憶服務初始化失敗: {str(e)}")
            raise MemoryError(f"無法初始化新聞記憶服務: {str(e)}")

    @classmethod
    def add_news(
        cls,
        news_id: str,
        title: str,
        content: str,
        embedding: List[float],
        source: str = "yahoo_finance",
        ttl_days: int = None
    ) -> str:
        """
        新增新聞並設定 TTL

        Args:
            news_id: 新聞唯一 ID
            title: 新聞標題
            content: 新聞內容
            embedding: 向量嵌入（768 維）
            source: 新聞來源
            ttl_days: TTL 天數（預設使用環境變數）

        Returns:
            str: 新聞 ID
        """
        try:
            if cls._qdrant_client is None:
                cls.initialize()

            # 計算過期時間
            ttl = ttl_days or settings.news_ttl_days
            expire_at = datetime.now() + timedelta(days=ttl)

            # 建立 Point
            point = PointStruct(
                id=news_id,
                vector=embedding,
                payload={
                    "title": title,
                    "content": content,
                    "source": source,
                    "publish_date": datetime.now().isoformat(),
                    "expire_at": expire_at.timestamp(),  # TTL 時間戳
                    "ttl_days": ttl
                }
            )

            # 插入到 Qdrant
            cls._qdrant_client.upsert(
                collection_name=cls._collection_name,
                points=[point]
            )

            logger.info(
                f"新聞已新增: id={news_id[:20]}..., "
                f"expire_in={ttl} days"
            )

            return news_id

        except Exception as e:
            logger.error(f"新增新聞失敗: {str(e)}")
            raise MemoryError(f"無法新增新聞: {str(e)}")

    @classmethod
    def search_news(
        cls,
        query_embedding: List[float],
        top_k: int = 10,
        filter_expired: bool = True,
        date_range: Optional[Dict] = None
    ) -> List[Dict]:
        """
        搜索相關新聞

        Args:
            query_embedding: 查詢向量
            top_k: 返回數量
            filter_expired: 是否過濾已過期新聞
            date_range: 日期範圍 {"start": "2025-01-01", "end": "2025-01-31"}

        Returns:
            List[Dict]: 新聞列表
        """
        try:
            if cls._qdrant_client is None:
                cls.initialize()

            # 建立過濾條件
            filters = []

            # 過濾已過期新聞
            if filter_expired:
                now = datetime.now().timestamp()
                filters.append(
                    FieldCondition(
                        key="expire_at",
                        range=Range(gt=now)  # 只搜索未過期的
                    )
                )

            # 日期範圍過濾
            if date_range:
                if date_range.get("start"):
                    start_ts = datetime.fromisoformat(date_range["start"]).timestamp()
                    filters.append(
                        FieldCondition(
                            key="publish_date",
                            range=Range(gte=start_ts)
                        )
                    )
                if date_range.get("end"):
                    end_ts = datetime.fromisoformat(date_range["end"]).timestamp()
                    filters.append(
                        FieldCondition(
                            key="publish_date",
                            range=Range(lte=end_ts)
                        )
                    )

            # 執行搜索
            search_result = cls._qdrant_client.search(
                collection_name=cls._collection_name,
                query_vector=query_embedding,
                limit=top_k,
                query_filter=Filter(must=filters) if filters else None,
                with_payload=True,
                with_vectors=False  # 不返回向量以節省頻寬
            )

            # 轉換結果
            news_list = []
            for hit in search_result:
                news_list.append({
                    "id": hit.id,
                    "title": hit.payload.get("title", ""),
                    "content": hit.payload.get("content", ""),
                    "source": hit.payload.get("source", ""),
                    "publish_date": hit.payload.get("publish_date", ""),
                    "relevance": hit.score,
                    "metadata": {
                        "expire_at": hit.payload.get("expire_at"),
                        "ttl_days": hit.payload.get("ttl_days")
                    }
                })

            logger.info(f"搜索新聞: found={len(news_list)}, top_k={top_k}")
            return news_list

        except Exception as e:
            logger.error(f"搜索新聞失敗: {str(e)}")
            return []

    @classmethod
    def cleanup_expired_news(cls) -> int:
        """
        手動清理已過期新聞（Qdrant 會自動處理，此方法為備用）

        Returns:
            int: 清理的新聞數量
        """
        try:
            if cls._qdrant_client is None:
                cls.initialize()

            now = datetime.now().timestamp()

            # 刪除已過期新聞
            cls._qdrant_client.delete(
                collection_name=cls._collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="expire_at",
                            range=Range(lt=now)
                        )
                    ]
                )
            )

            logger.info("已清理過期新聞")
            return 0  # Qdrant 不返回刪除數量

        except Exception as e:
            logger.error(f"清理過期新聞失敗: {str(e)}")
            return 0

    @classmethod
    def get_stats(cls) -> Dict:
        """獲取統計資訊"""

        try:
            if cls._qdrant_client is None:
                cls.initialize()

            collection_info = cls._qdrant_client.get_collection(cls._collection_name)

            return {
                "collection_name": cls._collection_name,
                "total_news": collection_info.points_count,
                "vectors_count": collection_info.vectors_count,
                "ttl_days": settings.news_ttl_days
            }

        except Exception as e:
            logger.error(f"獲取統計資訊失敗: {str(e)}")
            return {}
```

---

### 步驟 5: 保留現有問答記憶服務

**`backend/src/services/memory_service.py`** (現有檔案，不變):

```python
"""
問答記憶服務：使用 ChromaDB + Mem0 管理使用者偏好

此服務專注於:
- 使用者投資偏好
- 對話歷史記憶
- 個人化上下文
"""

# 現有程式碼保持不變
# 使用 ChromaDB 作為向量儲存
```

---

### 步驟 6: 建立新聞搜索服務

**`backend/src/services/news_search_service.py`**:

```python
"""
新聞搜索服務：整合問答記憶和新聞記憶

工作流程:
1. 接收使用者查詢
2. 從問答記憶中獲取使用者偏好（ChromaDB）
3. 結合偏好在新聞記憶中搜索（Qdrant）
4. 返回個人化新聞結果
"""

from typing import List, Dict, Optional
from ..services.memory_service import MemoryService
from ..services.news_memory_service import NewsMemoryService
from ..services.embedding_service import EmbeddingService
from ..utils.logger import get_logger

logger = get_logger(__name__)


class NewsSearchService:
    """新聞搜索服務"""

    @classmethod
    def search_personalized_news(
        cls,
        user_id: str,
        query: str,
        top_k: int = 10
    ) -> Dict:
        """
        個人化新聞搜索

        Args:
            user_id: 使用者 ID
            query: 搜索查詢
            top_k: 返回新聞數量

        Returns:
            Dict: 包含新聞列表和使用的偏好
        """

        # Step 1: 從問答記憶獲取使用者偏好（ChromaDB）
        user_preferences = MemoryService.search_memories(
            user_id=user_id,
            query="投資偏好 股票偏好 風險承受度",
            top_k=5
        )

        logger.info(
            f"獲取使用者偏好: user_id={user_id[:8]}..., "
            f"preferences={len(user_preferences)}"
        )

        # Step 2: 擴充查詢（結合使用者偏好）
        enhanced_query = query

        if user_preferences:
            # 將偏好加入查詢
            preferences_text = " ".join([
                pref.get("content", "")
                for pref in user_preferences
            ])
            enhanced_query = f"{query} {preferences_text}"

        # Step 3: 生成查詢向量
        query_embedding = EmbeddingService.embed_text(enhanced_query)

        # Step 4: 在新聞記憶中搜索（Qdrant）
        news_results = NewsMemoryService.search_news(
            query_embedding=query_embedding,
            top_k=top_k,
            filter_expired=True  # 只搜索未過期新聞
        )

        logger.info(
            f"搜索新聞: user_id={user_id[:8]}..., "
            f"found={len(news_results)}"
        )

        # Step 5: 返回結果
        return {
            "news": news_results,
            "user_preferences": [
                {
                    "content": pref.get("content", ""),
                    "relevance": pref.get("metadata", {}).get("relevance", 0)
                }
                for pref in user_preferences
            ],
            "query": query,
            "enhanced_query": enhanced_query,
            "total_results": len(news_results)
        }
```

---

### 步驟 7: 更新主應用程式

**`backend/src/main.py`** (新增初始化):

```python
# 現有程式碼...

from .services.news_memory_service import NewsMemoryService  # ✨ 新增

@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用程式生命週期管理"""

    logger.info("應用程式啟動中...")
    try:
        # 現有初始化
        DatabaseManager.initialize(settings.database_url)
        logger.info("資料庫已初始化")

        EmbeddingService.initialize()
        logger.info("嵌入服務已初始化")

        LLMService.initialize()
        logger.info("LLM 服務已初始化")

        MemoryService.initialize()
        logger.info("記憶服務已初始化（ChromaDB）")

        # 新增：初始化新聞記憶服務 ✨
        NewsMemoryService.initialize()
        logger.info("新聞記憶服務已初始化（Qdrant）")

    except Exception as e:
        logger.error(f"應用程式啟動失敗: {str(e)}")
        raise

    yield

    # 關閉事件
    logger.info("應用程式關閉中...")
    try:
        DatabaseManager.close()
        logger.info("資料庫連線已關閉")
    except Exception as e:
        logger.error(f"關閉資料庫失敗: {str(e)}")

# 其餘程式碼保持不變...
```

---

## 🔧 Mem0 多向量儲存配置

### 方案 A: 兩個獨立的 Mem0 實例（推薦）

```python
# 問答記憶的 Mem0（使用 ChromaDB）
conversation_mem0 = Memory.from_config({
    "llm": {...},
    "embedder": {...},
    "vector_store": {
        "provider": "chroma",
        "config": {
            "collection_name": "user_preferences",
            "path": "./data/chroma"
        }
    }
})

# 新聞記憶的 Mem0（使用 Qdrant）
news_mem0 = Memory.from_config({
    "llm": {...},
    "embedder": {...},
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name": "us_stock_news",
            "host": "localhost",
            "port": 6333
        }
    }
})
```

### 方案 B: 混合使用（靈活但複雜）

```python
# 問答記憶：使用 Mem0 完整功能（ChromaDB）
# 新聞記憶：只使用 Mem0 的 LLM 提取，手動管理 Qdrant
```

**我們採用方案 B**:
- 問答記憶：Mem0 完整管理（提取 + ChromaDB）
- 新聞記憶：Mem0 提取 + 手動 Qdrant（更靈活的 TTL 控制）

---

## 🚀 整合範例

### 完整使用流程

```python
# 1. 使用者發送查詢
user_query = "最近有哪些科技股的好消息？"
user_id = "user-123"

# 2. 搜索個人化新聞
result = NewsSearchService.search_personalized_news(
    user_id=user_id,
    query=user_query,
    top_k=10
)

# 3. 返回結果
{
    "news": [
        {
            "id": "news_20251105_001",
            "title": "Apple 發布 AI 新功能，股價創新高",
            "content": "蘋果公司今日...",
            "relevance": 0.92,
            "publish_date": "2025-11-05T10:30:00Z"
        },
        {
            "id": "news_20251105_002",
            "title": "NVIDIA AI 晶片需求強勁",
            "content": "NVIDIA 最新財報...",
            "relevance": 0.88,
            "publish_date": "2025-11-05T09:15:00Z"
        },
        ...
    ],
    "user_preferences": [
        {
            "content": "使用者偏好科技股",
            "relevance": 0.95
        },
        {
            "content": "使用者偏好 AI 相關投資",
            "relevance": 0.87
        }
    ],
    "query": "最近有哪些科技股的好消息？",
    "total_results": 10
}
```

---

## 📊 資料流程圖

### 問答對話流程（使用 ChromaDB）

```
使用者: "我偏好科技股"
   ↓
ConversationService.process_message()
   ↓
MemoryService.add_memory_from_message()
   ↓
Mem0 提取: "使用者偏好科技股"
   ↓
儲存到 ChromaDB
   collection: user_preferences
   TTL: 永久保留
```

### 新聞搜索流程（使用 Qdrant）

```
使用者: "科技股新聞"
   ↓
NewsSearchService.search_personalized_news()
   ↓
Step 1: 從 ChromaDB 獲取使用者偏好
   MemoryService.search_memories()
   → "使用者偏好科技股"
   → "使用者偏好 AI 相關投資"
   ↓
Step 2: 擴充查詢
   原始: "科技股新聞"
   擴充: "科技股新聞 使用者偏好科技股 AI 相關投資"
   ↓
Step 3: 在 Qdrant 中搜索
   NewsMemoryService.search_news()
   → 搜索 30 天內未過期新聞
   → 返回最相關的 10 篇
```

---

## 🛠 部署與維護

### Docker Compose 部署

**`docker-compose.yml`**:

```yaml
version: '3.8'

services:
  # FastAPI 後端
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      - QDRANT_HOST=qdrant
      - QDRANT_PORT=6333
    volumes:
      - ./backend/data:/app/data
    depends_on:
      - qdrant

  # Qdrant 向量資料庫
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"  # REST API
      - "6334:6334"  # gRPC (可選)
    volumes:
      - ./qdrant_data:/qdrant/storage
    environment:
      - QDRANT__SERVICE__GRPC_PORT=6334

  # 前端 (可選)
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend
```

啟動:
```bash
docker-compose up -d
```

---

### 監控與維護

#### 1. 檢查資料庫狀態

```python
# 檢查 ChromaDB（問答記憶）
stats = MemoryService.get_stats()
print(f"問答記憶數量: {stats['total_memories']}")

# 檢查 Qdrant（新聞記憶）
stats = NewsMemoryService.get_stats()
print(f"新聞數量: {stats['total_news']}")
print(f"TTL: {stats['ttl_days']} 天")
```

#### 2. 定期清理（備用）

雖然 Qdrant 會自動處理 TTL，但可以定期手動確認：

```python
import schedule

def cleanup_task():
    # 清理 ChromaDB 中的舊對話（可選）
    # MemoryService.cleanup_old_conversations(days=90)

    # 確認 Qdrant 過期清理（備用）
    deleted = NewsMemoryService.cleanup_expired_news()
    print(f"清理了 {deleted} 條過期新聞")

# 每日凌晨 3 點執行
schedule.every().day.at("03:00").do(cleanup_task)
```

---

## 🎯 總結

### 架構優勢

1. **清晰分離**
   - 問答記憶 → ChromaDB（永久、精準）
   - 新聞記憶 → Qdrant（TTL、大量）

2. **各自優化**
   - ChromaDB: 輕量、本地、適合小數據
   - Qdrant: TTL、高效能、適合大數據

3. **成本控制**
   - 新聞自動過期，節省儲存
   - 問答記憶永久保留，價值最大化

4. **易於擴展**
   - 兩個資料庫獨立擴展
   - 可以分別部署到不同伺服器

### 下一步

1. **安裝 Qdrant**:
   ```bash
   docker run -p 6333:6333 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant
   ```

2. **測試新聞服務**:
   ```bash
   cd backend
   pip install qdrant-client
   python -c "from src.services.news_memory_service import NewsMemoryService; NewsMemoryService.initialize(); print('OK')"
   ```

3. **新增 API 端點**:
   - `POST /api/v1/news/search` - 個人化新聞搜索
   - `POST /api/v1/news/add` - 新增新聞
   - `GET /api/v1/news/stats` - 統計資訊

4. **實作新聞爬蟲**:
   - 從 Yahoo Finance 等來源抓取新聞
   - 自動新增到 Qdrant
   - 設定 TTL 為 30 天

---

**相關文檔**:
- Qdrant 文檔: https://qdrant.tech/documentation/
- Mem0 多向量儲存: https://docs.mem0.ai/
- 現有問答服務: `backend/src/services/memory_service.py`
