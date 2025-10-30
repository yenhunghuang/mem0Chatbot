import sqlite3

c = sqlite3.connect('backend/data/app.db')

# 查詢原始 conversations 資料
print("=" * 60)
print("🔍 原始 conversations 資料")
print("=" * 60)

cursor = c.execute('SELECT * FROM conversations LIMIT 5')
columns = [description[0] for description in cursor.description]
print(f"\n欄位名稱: {columns}")

cursor = c.execute('SELECT * FROM conversations LIMIT 5')
rows = cursor.fetchall()
print(f"\n前 5 個對話記錄:")
for row in rows:
    print(row)

# 查詢 messages 與 conversations 的關聯
print("\n" + "=" * 60)
print("🔍 訊息與對話的關聯")
print("=" * 60)

cursor = c.execute('''
    SELECT c.id, c.user_id, COUNT(m.id) as msg_count
    FROM conversations c
    LEFT JOIN messages m ON c.id = m.conversation_id
    GROUP BY c.id
    ORDER BY c.created_at DESC
    LIMIT 5
''')
print(f"\n對話 ID | 使用者 ID | 訊息數:")
for row in cursor.fetchall():
    print(f"{row[0]} | {row[1][:20]}... | {row[2]}")

c.close()
