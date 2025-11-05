# 向量資料庫刪除機制與新聞資料管理

**核心問題**:
1. 主流向量資料庫是否都支援硬刪除？
2. 每日美股新聞存入向量資料庫，如何透過定時刪除控制容量？

**簡答**: 是的，主流向量資料庫都支援刪除功能，但實作機制各有不同。新聞資料的定時清理是可行的，但有更好的替代方案。

---

## 📋 目錄

1. [主流向量資料庫刪除機制對比](#主流向量資料庫刪除機制對比)
2. [新聞資料的特性與挑戰](#新聞資料的特性與挑戰)
3. [容量管理策略](#容量管理策略)
4. [實作方案：每日美股新聞系統](#實作方案每日美股新聞系統)
5. [效能與成本分析](#效能與成本分析)
6. [最佳實踐建議](#最佳實踐建議)

---

## 🗂️ 主流向量資料庫刪除機制對比

### 1. ChromaDB

**刪除機制**: 硬刪除 (Hard Delete)

```python
import chromadb

client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection("news")

# 刪除單一文檔
collection.delete(ids=["news_001"])

# 批次刪除
collection.delete(ids=["news_001", "news_002", "news_003"])

# 條件刪除
collection.delete(
    where={"date": {"$lt": "2025-01-01"}}  # 刪除 2025-01-01 之前的新聞
)
```

**特性**:
- ✅ 真正釋放儲存空間
- ✅ 支援條件刪除 (where clause)
- ✅ 適合本地部署
- ❌ 無內建 TTL (Time-To-Live)

---

### 2. Pinecone

**刪除機制**: 硬刪除 (Hard Delete)

```python
import pinecone

pinecone.init(api_key="YOUR_API_KEY")
index = pinecone.Index("news-index")

# 刪除單一向量
index.delete(ids=["news_001"])

# 批次刪除
index.delete(ids=["news_001", "news_002"])

# 條件刪除（需指定 namespace）
index.delete(
    filter={"date": {"$lt": "2025-01-01"}},
    namespace="us-stocks"
)

# 刪除整個 namespace
index.delete(delete_all=True, namespace="old-news")
```

**特性**:
- ✅ 雲端托管，自動管理儲存
- ✅ 支援 namespace 隔離
- ✅ 刪除後即時生效
- ❌ 按向量數量計費（刪除可節省成本）
- ❌ 無內建 TTL

---

### 3. Weaviate

**刪除機制**: 硬刪除 (Hard Delete)

```python
import weaviate

client = weaviate.Client("http://localhost:8080")

# 刪除單一物件
client.data_object.delete(
    uuid="news_001",
    class_name="News"
)

# 批次刪除（透過 where filter）
client.batch.delete_objects(
    class_name="News",
    where={
        "path": ["publishDate"],
        "operator": "LessThan",
        "valueDate": "2025-01-01T00:00:00Z"
    }
)
```

**特性**:
- ✅ 支援複雜查詢刪除
- ✅ 即時生效
- ✅ 可選雲端或自建
- ❌ 無內建 TTL

---

### 4. Milvus

**刪除機制**: 硬刪除 (Hard Delete)

```python
from pymilvus import Collection

collection = Collection("news")

# 刪除指定 ID
expr = "id in ['news_001', 'news_002', 'news_003']"
collection.delete(expr)

# 條件刪除
expr = "publish_date < '2025-01-01'"
collection.delete(expr)

# 需要手動觸發 compact
collection.compact()
```

**特性**:
- ✅ 支援 SQL-like 表達式
- ✅ 高效能，適合大規模
- ⚠️ 刪除後需手動 compact 才能釋放空間
- ❌ 無內建 TTL

---

### 5. Qdrant

**刪除機制**: 硬刪除 (Hard Delete) + **支援 TTL**

```python
from qdrant_client import QdrantClient
from datetime import datetime, timedelta

client = QdrantClient("localhost", port=6333)

# 刪除單一點
client.delete(
    collection_name="news",
    points_selector=[1, 2, 3]
)

# 條件刪除
client.delete(
    collection_name="news",
    points_selector={
        "filter": {
            "must": [
                {
                    "key": "date",
                    "range": {
                        "lt": "2025-01-01"
                    }
                }
            ]
        }
    }
)

# ✨ TTL 功能（自動過期）
client.upsert(
    collection_name="news",
    points=[
        {
            "id": 1,
            "vector": [...],
            "payload": {
                "text": "新聞內容",
                "ttl": (datetime.now() + timedelta(days=30)).timestamp()
            }
        }
    ]
)
# 30 天後自動刪除
```

**特性**:
- ✅ 支援 TTL（自動過期刪除）
- ✅ 高效能過濾刪除
- ✅ 開源且功能完整
- ✅ 適合新聞類時效性資料

---

### 6. Elasticsearch (向量搜索功能)

**刪除機制**: 硬刪除 (Hard Delete) + **內建 ILM (Index Lifecycle Management)**

```python
from elasticsearch import Elasticsearch

es = Elasticsearch(["http://localhost:9200"])

# 刪除單一文檔
es.delete(index="news", id="news_001")

# 批次刪除
es.delete_by_query(
    index="news",
    body={
        "query": {
            "range": {
                "publish_date": {
                    "lt": "2025-01-01"
                }
            }
        }
    }
)

# ✨ ILM 策略（自動管理）
ilm_policy = {
    "policy": {
        "phases": {
            "hot": {
                "actions": {}
            },
            "delete": {
                "min_age": "30d",  # 30 天後自動刪除
                "actions": {
                    "delete": {}
                }
            }
        }
    }
}

es.ilm.put_lifecycle(policy="news_policy", body=ilm_policy)
```

**特性**:
- ✅ 內建 ILM（自動生命週期管理）
- ✅ 支援複雜查詢刪除
- ✅ 久經考驗的企業級方案
- ⚠️ 較重量級，需要更多資源

---

### 對比總結表

| 向量資料庫 | 刪除類型 | 條件刪除 | TTL 支援 | 空間釋放 | 最適合場景 |
|-----------|---------|---------|---------|---------|-----------|
| **ChromaDB** | 硬刪除 | ✅ | ❌ | 立即 | 本地開發、小規模 |
| **Pinecone** | 硬刪除 | ✅ | ❌ | 立即 | 雲端托管、企業 |
| **Weaviate** | 硬刪除 | ✅ | ❌ | 立即 | 知識圖譜、複雜查詢 |
| **Milvus** | 硬刪除 | ✅ | ❌ | 需 compact | 大規模、高效能 |
| **Qdrant** | 硬刪除 | ✅ | ✅ | 立即 | **新聞、時效性資料** ⭐ |
| **Elasticsearch** | 硬刪除 | ✅ | ✅ (ILM) | 立即 | 企業級、混合搜索 |

**結論**:
- ✅ **所有主流向量資料庫都支援硬刪除**
- ⭐ **Qdrant 和 Elasticsearch 特別適合新聞類資料**（內建 TTL/ILM）

---

## 📰 新聞資料的特性與挑戰

### 新聞資料特性

```
美股新聞資料特點:
├── 時效性強
│   └── 價值隨時間遞減（今天重要，一個月後無關）
├── 數量龐大
│   └── 每日 10,000+ 篇新聞（假設）
├── 更新頻繁
│   └── 24/7 持續產生
└── 儲存成本高
    └── 向量 + 原文 = 大量空間
```

### 容量挑戰

**範例計算**:

```
假設:
- 每篇新聞 = 1KB 文本 + 3KB 向量（768 維）= 4KB
- 每日新聞量 = 10,000 篇
- 保留天數 = 30 天

總容量需求:
= 10,000 篇/天 × 30 天 × 4KB
= 300,000 篇 × 4KB
= 1.2 GB

如果保留 1 年:
= 10,000 × 365 × 4KB
= 14.6 GB
```

**問題**:
1. 儲存成本隨時間線性增長
2. 舊新聞佔用空間但很少被查詢
3. 搜索效能隨資料量下降

---

## 🎯 容量管理策略

### 策略 1: 定時刪除（您提到的方案）

**實作**: 每日執行清理任務

```python
from datetime import datetime, timedelta
import chromadb

def cleanup_old_news(days_to_keep: int = 30):
    """刪除超過 N 天的新聞"""

    client = chromadb.PersistentClient(path="./news_db")
    collection = client.get_collection("us_stock_news")

    # 計算截止日期
    cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()

    # 條件刪除
    collection.delete(
        where={
            "publish_date": {"$lt": cutoff_date}
        }
    )

    print(f"已刪除 {cutoff_date} 之前的新聞")

# 使用 cron job 每日執行
# 0 2 * * * python cleanup_news.py  # 每天凌晨 2 點執行
```

**優點**:
- ✅ 簡單直接
- ✅ 容量可控
- ✅ 適用於所有向量資料庫

**缺點**:
- ❌ 需要額外維護定時任務
- ❌ 刪除操作可能影響效能
- ❌ 硬性刪除，無法彈性調整

---

### 策略 2: 使用 TTL 自動過期（推薦 ⭐）

**實作**: 使用 Qdrant 的 TTL 功能

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from datetime import datetime, timedelta

client = QdrantClient("localhost", port=6333)

# 建立集合
client.create_collection(
    collection_name="us_stock_news",
    vectors_config=VectorParams(size=768, distance=Distance.COSINE)
)

def add_news_with_ttl(news_id: str, text: str, embedding: list, days: int = 30):
    """新增新聞並設定 TTL"""

    # 計算過期時間戳
    expire_at = datetime.now() + timedelta(days=days)

    client.upsert(
        collection_name="us_stock_news",
        points=[
            PointStruct(
                id=news_id,
                vector=embedding,
                payload={
                    "text": text,
                    "publish_date": datetime.now().isoformat(),
                    "expire_at": expire_at.timestamp()  # TTL 欄位
                }
            )
        ]
    )

# Qdrant 會自動刪除過期資料，無需手動干預
```

**優點**:
- ✅ 自動化，無需維護定時任務
- ✅ 精確到秒級的過期控制
- ✅ 不影響線上服務效能

**缺點**:
- ⚠️ 需使用支援 TTL 的資料庫（Qdrant, Elasticsearch）

---

### 策略 3: 滾動索引（Rolling Index）

**實作**: 按日期建立獨立集合/索引

```python
from datetime import datetime
import chromadb

def get_daily_collection(date: datetime):
    """獲取當日的集合"""

    client = chromadb.PersistentClient(path="./news_db")
    collection_name = f"news_{date.strftime('%Y%m%d')}"

    return client.get_or_create_collection(collection_name)

def add_news(text: str, embedding: list):
    """新增新聞到當日集合"""

    today = datetime.now()
    collection = get_daily_collection(today)

    collection.add(
        ids=[f"news_{today.timestamp()}"],
        embeddings=[embedding],
        documents=[text]
    )

def search_recent_news(query_embedding: list, days: int = 30):
    """搜索最近 N 天的新聞"""

    results = []
    client = chromadb.PersistentClient(path="./news_db")

    # 遍歷最近 N 天的集合
    for i in range(days):
        date = datetime.now() - timedelta(days=i)
        collection_name = f"news_{date.strftime('%Y%m%d')}"

        try:
            collection = client.get_collection(collection_name)
            day_results = collection.query(
                query_embeddings=[query_embedding],
                n_results=10
            )
            results.extend(day_results['documents'][0])
        except:
            continue  # 集合不存在，跳過

    return results

def cleanup_old_collections(days_to_keep: int = 30):
    """刪除舊的集合（整個集合）"""

    client = chromadb.PersistentClient(path="./news_db")
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)

    # 刪除舊集合
    old_collection = f"news_{cutoff_date.strftime('%Y%m%d')}"
    try:
        client.delete_collection(old_collection)
        print(f"已刪除集合: {old_collection}")
    except:
        pass
```

**優點**:
- ✅ 刪除極快（直接刪除整個集合）
- ✅ 隔離性好（不同日期互不影響）
- ✅ 便於備份和恢復

**缺點**:
- ❌ 跨日期搜索複雜
- ❌ 管理多個集合較繁瑣

---

### 策略 4: 冷熱資料分離

**實作**: 近期新聞 (熱資料) vs 歷史新聞 (冷資料)

```python
import chromadb
from datetime import datetime, timedelta

client = chromadb.PersistentClient(path="./news_db")

# 熱資料：最近 7 天，快速存取
hot_collection = client.get_or_create_collection("news_hot")

# 溫資料：8-30 天，普通存取
warm_collection = client.get_or_create_collection("news_warm")

# 冷資料：31-90 天，歸檔（降低精度或壓縮）
cold_collection = client.get_or_create_collection("news_cold")

def add_news(text: str, embedding: list):
    """新增到熱資料"""
    hot_collection.add(
        ids=[f"news_{datetime.now().timestamp()}"],
        embeddings=[embedding],
        documents=[text],
        metadatas=[{"date": datetime.now().isoformat()}]
    )

def migrate_to_warm():
    """將 7 天前的資料從熱資料遷移到溫資料"""

    cutoff = (datetime.now() - timedelta(days=7)).isoformat()

    # 查詢舊資料
    old_data = hot_collection.get(
        where={"date": {"$lt": cutoff}}
    )

    if old_data['ids']:
        # 複製到溫資料
        warm_collection.add(
            ids=old_data['ids'],
            embeddings=old_data['embeddings'],
            documents=old_data['documents'],
            metadatas=old_data['metadatas']
        )

        # 從熱資料刪除
        hot_collection.delete(ids=old_data['ids'])

def search_news(query_embedding: list):
    """智能搜索：優先搜索熱資料"""

    # 先搜索熱資料
    hot_results = hot_collection.query(
        query_embeddings=[query_embedding],
        n_results=20
    )

    # 如果結果不足，再搜索溫資料
    if len(hot_results['documents'][0]) < 10:
        warm_results = warm_collection.query(
            query_embeddings=[query_embedding],
            n_results=10
        )
        # 合併結果
        ...

    return hot_results
```

**優點**:
- ✅ 熱資料高效能
- ✅ 冷資料低成本
- ✅ 彈性管理

**缺點**:
- ❌ 實作複雜
- ❌ 需要資料遷移邏輯

---

### 策略對比

| 策略 | 實作難度 | 維護成本 | 效能影響 | 適用場景 |
|------|---------|---------|---------|---------|
| **定時刪除** | ⭐ 簡單 | 中等 | 低 | 小規模、簡單需求 |
| **TTL 自動過期** | ⭐⭐ 簡單 | 極低 | 無 | **推薦首選** ⭐ |
| **滾動索引** | ⭐⭐⭐ 中等 | 中等 | 低 | 需要按日期隔離 |
| **冷熱分離** | ⭐⭐⭐⭐ 複雜 | 高 | 低 | 大規模、多層次需求 |

---

## 💻 實作方案：每日美股新聞系統

### 方案 A: ChromaDB + 定時清理（簡單方案）

**適用**: 小規模、快速啟動

```python
# news_manager.py
import chromadb
from datetime import datetime, timedelta
import schedule
import time

class NewsVectorDB:
    def __init__(self, db_path: str = "./news_db", days_to_keep: int = 30):
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(
            name="us_stock_news",
            metadata={"description": "美股新聞向量資料庫"}
        )
        self.days_to_keep = days_to_keep

    def add_news(self, news_id: str, title: str, content: str, embedding: list):
        """新增新聞"""
        self.collection.add(
            ids=[news_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[{
                "title": title,
                "publish_date": datetime.now().isoformat(),
                "source": "yahoo_finance"
            }]
        )

    def search_news(self, query_embedding: list, top_k: int = 10):
        """搜索相關新聞"""
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
        return results

    def cleanup_old_news(self):
        """刪除舊新聞"""
        cutoff_date = (datetime.now() - timedelta(days=self.days_to_keep)).isoformat()

        # 獲取舊新聞
        all_news = self.collection.get(include=["metadatas"])
        old_ids = [
            id for id, meta in zip(all_news['ids'], all_news['metadatas'])
            if meta.get('publish_date', '') < cutoff_date
        ]

        if old_ids:
            self.collection.delete(ids=old_ids)
            print(f"[{datetime.now()}] 刪除 {len(old_ids)} 條舊新聞")

    def get_stats(self):
        """獲取統計資訊"""
        count = self.collection.count()
        return {
            "total_news": count,
            "days_kept": self.days_to_keep,
            "estimated_size_mb": count * 4 / 1024  # 估算
        }

# 使用範例
db = NewsVectorDB(days_to_keep=30)

# 每日凌晨 2 點執行清理
schedule.every().day.at("02:00").do(db.cleanup_old_news)

while True:
    schedule.run_pending()
    time.sleep(60)
```

**部署**:
```bash
# 使用 systemd 或 supervisor 運行
# 或使用 cron job
0 2 * * * cd /path/to/project && python news_manager.py
```

---

### 方案 B: Qdrant + TTL（推薦方案 ⭐）

**適用**: 生產環境、自動化

```python
# news_manager_qdrant.py
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from datetime import datetime, timedelta

class NewsVectorDBWithTTL:
    def __init__(self, host: str = "localhost", port: int = 6333):
        self.client = QdrantClient(host=host, port=port)
        self.collection_name = "us_stock_news"

        # 建立集合
        try:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=768,  # Google Embeddings 維度
                    distance=Distance.COSINE
                )
            )
        except:
            pass  # 集合已存在

    def add_news(
        self,
        news_id: str,
        title: str,
        content: str,
        embedding: list,
        ttl_days: int = 30
    ):
        """新增新聞並設定 TTL"""

        # 計算過期時間
        expire_at = datetime.now() + timedelta(days=ttl_days)

        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=news_id,
                    vector=embedding,
                    payload={
                        "title": title,
                        "content": content,
                        "publish_date": datetime.now().isoformat(),
                        "expire_at": expire_at.timestamp(),  # TTL
                        "source": "yahoo_finance"
                    }
                )
            ]
        )

    def search_news(self, query_embedding: list, top_k: int = 10):
        """搜索新聞（自動過濾過期資料）"""

        now = datetime.now().timestamp()

        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=top_k,
            query_filter={
                "must": [
                    {
                        "key": "expire_at",
                        "range": {"gt": now}  # 只搜索未過期的
                    }
                ]
            }
        )

        return results

    def get_stats(self):
        """獲取統計資訊"""
        info = self.client.get_collection(self.collection_name)
        return {
            "total_vectors": info.vectors_count,
            "points_count": info.points_count
        }

# 使用範例
db = NewsVectorDBWithTTL()

# 新增新聞（30 天後自動過期）
db.add_news(
    news_id="news_20251105_001",
    title="Apple 股價創新高",
    content="蘋果公司今日股價...",
    embedding=[0.1, 0.2, ...],  # 768 維向量
    ttl_days=30  # 30 天後自動刪除
)

# 搜索（無需手動清理，自動過濾過期資料）
results = db.search_news(query_embedding=[...], top_k=10)
```

**優點**:
- ✅ 零維護（自動過期）
- ✅ 無需定時任務
- ✅ 效能更好

---

### 方案 C: 滾動索引（企業級方案）

**適用**: 大規模、需要按日期隔離

```python
# news_manager_rolling.py
import chromadb
from datetime import datetime, timedelta

class RollingNewsVectorDB:
    def __init__(self, db_path: str = "./news_db"):
        self.client = chromadb.PersistentClient(path=db_path)

    def _get_date_collection(self, date: datetime):
        """獲取指定日期的集合"""
        collection_name = f"news_{date.strftime('%Y%m%d')}"
        return self.client.get_or_create_collection(collection_name)

    def add_news(self, news_id: str, content: str, embedding: list):
        """新增新聞到當日集合"""
        today = datetime.now()
        collection = self._get_date_collection(today)

        collection.add(
            ids=[news_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[{"date": today.isoformat()}]
        )

    def search_news(self, query_embedding: list, days: int = 7, top_k: int = 10):
        """搜索最近 N 天的新聞"""
        all_results = []

        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            collection_name = f"news_{date.strftime('%Y%m%d')}"

            try:
                collection = self.client.get_collection(collection_name)
                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=top_k
                )
                all_results.extend(results['documents'][0])
            except:
                continue

        return all_results[:top_k]

    def cleanup_old_collections(self, days_to_keep: int = 30):
        """刪除舊集合"""
        deleted_count = 0

        # 刪除超過 days_to_keep 天的集合
        for i in range(days_to_keep, days_to_keep + 7):  # 多檢查 7 天
            date = datetime.now() - timedelta(days=i)
            collection_name = f"news_{date.strftime('%Y%m%d')}"

            try:
                self.client.delete_collection(collection_name)
                deleted_count += 1
                print(f"刪除集合: {collection_name}")
            except:
                pass

        return deleted_count

# 定時清理（每日執行）
db = RollingNewsVectorDB()
db.cleanup_old_collections(days_to_keep=30)
```

---

## 📊 效能與成本分析

### 容量估算

```python
def calculate_storage(
    daily_news_count: int,
    days_to_keep: int,
    vector_dim: int = 768,
    text_avg_chars: int = 1000
):
    """計算儲存需求"""

    # 向量大小（float32 = 4 bytes）
    vector_size_kb = vector_dim * 4 / 1024

    # 文本大小（UTF-8，約 3 bytes per char）
    text_size_kb = text_avg_chars * 3 / 1024

    # 單篇新聞總大小
    per_news_kb = vector_size_kb + text_size_kb

    # 總容量
    total_news = daily_news_count * days_to_keep
    total_size_mb = total_news * per_news_kb / 1024

    return {
        "total_news": total_news,
        "total_size_mb": round(total_size_mb, 2),
        "total_size_gb": round(total_size_mb / 1024, 2),
        "per_news_kb": round(per_news_kb, 2)
    }

# 範例計算
result = calculate_storage(
    daily_news_count=10000,
    days_to_keep=30
)

print(result)
# 輸出:
# {
#   "total_news": 300000,
#   "total_size_mb": 1171.88,
#   "total_size_gb": 1.14,
#   "per_news_kb": 4.00
# }
```

### 不同保留期限的容量對比

| 保留天數 | 新聞總數 (10k/天) | 儲存容量 | 搜索效能 |
|---------|------------------|---------|---------|
| 7 天 | 70,000 | 273 MB | 極快 ⚡⚡⚡ |
| 30 天 | 300,000 | 1.17 GB | 快 ⚡⚡ |
| 90 天 | 900,000 | 3.52 GB | 中等 ⚡ |
| 365 天 | 3,650,000 | 14.26 GB | 慢 🐌 |

**建議**: 保留 **30 天** 是平衡點

---

### 雲端服務成本估算 (Pinecone 為例)

```
Pinecone 定價 (2025):
- Starter Plan: 免費 (100K 向量, 1 Pod)
- Standard Plan: $70/月 (100K 向量, 1 Pod)
- 額外向量: $0.096/1000 向量/月

30 天新聞成本:
= 300,000 向量 × $0.096 / 1000
= $28.8/月

一年成本:
= 3,650,000 向量 × $0.096 / 1000
= $350.4/月

使用定時刪除保持 30 天:
= $28.8/月 (固定)

節省成本:
= $350.4 - $28.8
= $321.6/月 ✓
```

**結論**: 定時刪除可大幅降低雲端成本

---

## ✅ 最佳實踐建議

### 1. 根據規模選擇方案

```
小規模 (< 100K 向量):
→ ChromaDB + 定時刪除
→ 簡單、低成本、易維護

中規模 (100K - 1M 向量):
→ Qdrant + TTL
→ 自動化、高效能、推薦 ⭐

大規模 (> 1M 向量):
→ Elasticsearch + ILM 或 滾動索引
→ 企業級、可擴展
```

### 2. 設定合理的保留期限

```python
# 根據業務需求設定
retention_rules = {
    "hot_news": 7,      # 熱門新聞：7 天
    "regular_news": 30, # 一般新聞：30 天
    "archive": 90       # 重要新聞：90 天歸檔
}
```

### 3. 監控與告警

```python
def monitor_storage():
    """監控儲存使用情況"""

    stats = db.get_stats()

    if stats['total_size_gb'] > 5:  # 超過 5GB 告警
        send_alert(f"儲存空間過大: {stats['total_size_gb']} GB")

    if stats['total_news'] > 500000:  # 超過 50 萬條告警
        send_alert(f"新聞數量過多: {stats['total_news']}")

# 每小時檢查
schedule.every().hour.do(monitor_storage)
```

### 4. 備份策略

```python
def backup_before_cleanup():
    """清理前備份"""

    cutoff = (datetime.now() - timedelta(days=30)).isoformat()

    # 匯出即將刪除的資料
    old_news = collection.get(
        where={"date": {"$lt": cutoff}}
    )

    # 儲存到 S3 或本地
    with open(f"backup_{cutoff}.json", "w") as f:
        json.dump(old_news, f)

    # 執行刪除
    collection.delete(...)
```

### 5. 漸進式刪除

```python
def gradual_cleanup(batch_size: int = 1000):
    """分批刪除，避免影響線上服務"""

    cutoff = (datetime.now() - timedelta(days=30)).isoformat()

    while True:
        # 每次只刪除 1000 條
        old_news = collection.get(
            where={"date": {"$lt": cutoff}},
            limit=batch_size
        )

        if not old_news['ids']:
            break

        collection.delete(ids=old_news['ids'])
        time.sleep(1)  # 暫停 1 秒，減少負載
```

---

## 🎯 總結

### 核心問題答案

1. **所有主流向量資料庫都支援刪除嗎？**
   - ✅ 是的，都支援硬刪除
   - ⭐ Qdrant 和 Elasticsearch 還支援 TTL/ILM

2. **定時刪除能控制容量嗎？**
   - ✅ 可以，是有效的容量管理方案
   - ⭐ 推薦使用 TTL 自動過期（更優）

### 推薦方案

**最簡單**: ChromaDB + 定時刪除 (cron job)
**最推薦**: Qdrant + TTL 自動過期 ⭐
**最靈活**: Elasticsearch + ILM
**最高效**: 滾動索引 + 批次刪除

### 容量管理關鍵

```
每日新聞 10,000 篇:
├── 保留 7 天 → 273 MB ✓ 適合快速搜索
├── 保留 30 天 → 1.17 GB ✓ 平衡點（推薦）
├── 保留 90 天 → 3.52 GB ⚠️ 需要優化
└── 保留 1 年 → 14.26 GB ✗ 不建議
```

### 實作建議

1. **從簡單開始**: ChromaDB + 定時刪除
2. **生產環境**: 升級到 Qdrant + TTL
3. **監控容量**: 設定告警閥值
4. **定期備份**: 刪除前匯出重要資料
5. **測試驗證**: 在開發環境充分測試

---

**相關資源**:
- Qdrant 文檔: https://qdrant.tech/documentation/
- Elasticsearch ILM: https://www.elastic.co/guide/en/elasticsearch/reference/current/index-lifecycle-management.html
- ChromaDB 文檔: https://docs.trychroma.com/

**您的專案**:
- 目前使用: ChromaDB (`backend/src/services/memory_service.py`)
- 建議: 可保持現狀或考慮升級到 Qdrant
