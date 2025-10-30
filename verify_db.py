import sqlite3

c = sqlite3.connect('backend/data/app.db')
tables = [t[0] for t in c.execute('SELECT name FROM sqlite_master WHERE type="table"').fetchall()]
print('✅ Tables created:', tables)

# 顯示表結構
for table in tables:
    print(f'\n📋 {table}:')
    columns = c.execute(f'PRAGMA table_info({table})').fetchall()
    for col in columns:
        print(f'   - {col[1]}: {col[2]}')

c.close()
