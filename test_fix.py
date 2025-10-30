import sqlite3
import sys
sys.path.insert(0, 'backend')

# 初始化資料庫
from src.storage.database import DatabaseManager
from src.storage.storage_service import StorageService
import uuid

# 初始化資料庫
DatabaseManager.initialize()

# 建立測試對話
test_user_id = str(uuid.uuid4())
print(f"建立測試對話，使用者 ID: {test_user_id}")

conversation = StorageService.create_conversation(test_user_id)
print(f"✅ 對話已建立: ID={conversation.conversation_id}")

# 儲存測試訊息
message = StorageService.save_message(conversation.conversation_id, "user", "你好，這是測試訊息")
print(f"✅ 訊息已儲存: ID={message.message_id}")

# 驗證資料庫
print("\n" + "=" * 60)
print("📊 資料庫驗證")
print("=" * 60)

c = sqlite3.connect('backend/data/app.db')

# 查詢對話
cursor = c.execute('SELECT id, user_id, message_count FROM conversations')
convs = cursor.fetchall()
print(f"\n✅ 對話記錄: {len(convs)} 個")
for conv in convs:
    print(f"   ID: {conv[0][:8]}... | 訊息數: {conv[2]}")

# 查詢訊息
cursor = c.execute('SELECT id, conversation_id, role, content FROM messages')
msgs = cursor.fetchall()
print(f"\n✅ 訊息記錄: {len(msgs)} 個")
for msg in msgs:
    print(f"   ID: {msg[0]} | 對話: {msg[1][:8]}... | 角色: {msg[2]}")

c.close()
print("\n" + "=" * 60)
print("✅ 修復驗證完成！")
print("=" * 60)
