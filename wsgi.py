import os
import sys
import mysql.connector

path = os.path.dirname(os.path.abspath(__file__))
if path not in sys.path:
    sys.path.append(path)

from app import app, db_config, get_db

application = app

# محاولة إنشاء الجداول تلقائياً عند التشغيل
try:
    # الاتصال بقاعدة البيانات
    conn = mysql.connector.connect(
        host=os.getenv('DB_HOST', db_config['host']),
        port=int(os.getenv('DB_PORT', db_config.get('port', 3306))),
        user=os.getenv('DB_USER', db_config['user']),
        password=os.getenv('DB_PASSWORD', db_config['password']),
        database=os.getenv('DB_NAME', db_config['database'])
    )
    cursor = conn.cursor()
    
    # قراءة ملف database.sql
    sql_file = os.path.join(path, 'database.sql')
    if os.path.exists(sql_file):
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_commands = f.read().split(';')
            
        for command in sql_commands:
            if command.strip():
                try:
                    cursor.execute(command)
                except Exception:
                    pass # تجاهل الأخطاء إذا كانت الجداول موجودة مسبقاً
        
        conn.commit()
        print("✅ تم التحقق من الجداول بنجاح")
    conn.close()
except Exception as e:
    print(f"⚠️ خطأ في إنشاء الجداول: {e}")
