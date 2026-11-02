import os
import sys

path = os.path.dirname(os.path.abspath(__file__))
if path not in sys.path:
    sys.path.append(path)

from app import app, get_db

application = app

# محاولة إنشاء الجداول تلقائياً عند التشغيل
try:
    # الاتصال بقاعدة البيانات باستخدام الدالة get_db
    conn = get_db()
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

