import sqlite3
import bcrypt

conn = sqlite3.connect('hospital_rehab.db')
cursor = conn.cursor()

# 生成 hash
hashed = bcrypt.hashpw(b"123456", bcrypt.gensalt()).decode('utf-8')
cursor.execute("INSERT INTO doctors (name, department, login_name, password_hash) VALUES (?, ?, ?, ?)",
               ("演示医生", "内科", "demo_doctor", hashed))
conn.commit()
conn.close()
print("演示医生插入成功")
