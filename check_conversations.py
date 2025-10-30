import sqlite3

c = sqlite3.connect('backend/data/app.db')

# 查看對話
print("=" * 60)
print("📋 對話列表")
print("=" * 60)
convs = c.execute('SELECT id, user_id, created_at, message_count FROM conversations').fetchall()
if convs:
    for conv in convs:
        print(f"\n🆔 ID: {conv[0]}")
        print(f"👤 使用者: {conv[1]}")
        print(f"📅 建立時間: {conv[2]}")
        print(f"💬 訊息數: {conv[3]}")
else:
    print("\n❌ 尚無對話記錄")

# 查看訊息
print("\n" + "=" * 60)
print("💬 訊息內容")
print("=" * 60)
msgs = c.execute('SELECT id, role, content, timestamp FROM messages ORDER BY timestamp').fetchall()
if msgs:
    for msg in msgs:
        content = msg[2][:100] + "..." if len(msg[2]) > 100 else msg[2]
        print(f"\n📨 ID: {msg[0]}")
        print(f"   角色: [{msg[1]}]")
        print(f"   內容: {content}")
        print(f"   時間: {msg[3]}")
else:
    print("\n❌ 尚無訊息記錄")

# 查看記憶
print("\n" + "=" * 60)
print("🧠 記憶記錄")
print("=" * 60)
memories = c.execute('SELECT memory_id, user_id, content, category, created_at FROM memory_metadata ORDER BY created_at DESC').fetchall()
if memories:
    for mem in memories:
        content = mem[2][:100] + "..." if len(mem[2]) > 100 else mem[2]
        print(f"\n🆔 ID: {mem[0]}")
        print(f"   使用者: {mem[1]}")
        print(f"   分類: {mem[3]}")
        print(f"   內容: {content}")
        print(f"   建立時間: {mem[4]}")
else:
    print("\n❌ 尚無記憶記錄")

c.close()
print("\n" + "=" * 60)
