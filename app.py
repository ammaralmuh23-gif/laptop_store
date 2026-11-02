from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
import mysql.connector
from functools import wraps
import os
from werkzeug.utils import secure_filename
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import csv
import io
from flask import Response
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
import arabic_reshaper
from bidi.algorithm import get_display

# إعدادات البريد الإلكتروني
SENDER_EMAIL = "ammaralmuh23@gmail.com"
SENDER_PASSWORD = "aeso dnbm cihf huzr"
ADMIN_EMAIL = "ammaralmuh23@gmail.com"

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_laptop_store'

# إعدادات قاعدة البيانات (تقرأ من متغيرات البيئة)
def get_db():
    return mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', 3306)),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', ''),
        database=os.getenv('DB_NAME', 'laptop_store'),
        ssl_verify_cert=False,
        ssl_disabled=False,
        charset='utf8mb4'
    )

# إعدادات رفع الملفات
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def send_notification(subject, body):
    try:
        admin_email = get_admin_email()
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = admin_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"✅ تم إرسال الإشعار إلى: {admin_email}")
    except Exception as e:
        print(f"❌ فشل إرسال الإشعار: {e}")

def get_whatsapp_number():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT whatsapp_number FROM settings WHERE id = 1")
    setting = cursor.fetchone()
    conn.close()
    return setting['whatsapp_number'] if setting else '966500000000'

def get_admin_email():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT admin_email FROM settings WHERE id = 1")
    setting = cursor.fetchone()
    conn.close()
    return setting['admin_email'] if setting and setting['admin_email'] else 'ammaralmuh23@gmail.com'

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            flash('يجب تسجيل الدخول أولاً', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ==========================================
# --- 1. الواجهة العامة والمتجر (للزبائن) ---
# ==========================================
@app.route('/')
def index():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM laptops ORDER BY created_at DESC")
    laptops = cursor.fetchall()
    
    cart_count = 0
    if 'customer_id' in session:
        cursor.execute("SELECT SUM(quantity) as total FROM cart WHERE customer_id = %s", (session['customer_id'],))
        result = cursor.fetchone()
        if result and result['total']:
            cart_count = result['total']
            
    conn.close()
    return render_template('index.html', laptops=laptops, whatsapp_number=get_whatsapp_number(), cart_count=cart_count)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM laptops WHERE name LIKE %s OR specs LIKE %s", (f'%{query}%', f'%{query}%'))
    laptops = cursor.fetchall()
    conn.close()
    return render_template('index.html', laptops=laptops, search_query=query, whatsapp_number=get_whatsapp_number())

@app.route('/product/<int:id>')
def product_detail(id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM laptops WHERE id = %s", (id,))
    laptop = cursor.fetchone()
    conn.close()
    if not laptop:
        return "المنتج غير موجود", 404
    return render_template('product.html', laptop=laptop, whatsapp_number=get_whatsapp_number())

# ==========================================
# --- 2. حسابات الزبائن (تسجيل، دخول، خروج) ---
# ==========================================
@app.route('/customer/register', methods=['GET', 'POST'])
def customer_register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM customers WHERE username = %s", (username,))
        if cursor.fetchone():
            flash('اسم المستخدم موجود بالفعل', 'error')
        else:
            cursor.execute("INSERT INTO customers (username, password) VALUES (%s, %s)", (username, password))
            conn.commit()
            send_notification("🆕 زبون جديد في متجرك", f"تم تسجيل زبون جديد باسم: {username}")
            flash('تم إنشاء الحساب، يمكنك تسجيل الدخول الآن', 'success')
            return redirect(url_for('customer_login'))
        conn.close()
    return render_template('customer_register.html')

@app.route('/customer/login', methods=['GET', 'POST'])
def customer_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM customers WHERE username = %s AND password = %s", (username, password))
        customer = cursor.fetchone()
        conn.close()
        if customer:
            session['customer_id'] = customer['id']
            session['customer_name'] = customer['username']
            flash('مرحباً بك!', 'success')
            return redirect(url_for('index'))
        else:
            flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'error')
    return render_template('customer_login.html')

@app.route('/customer/logout')
def customer_logout():
    session.pop('customer_id', None)
    session.pop('customer_name', None)
    return redirect(url_for('index'))

# ==========================================
# --- 3. سلة المشتريات (لكل زبون سلة خاصة) ---
# ==========================================
@app.route('/add_to_cart/<int:laptop_id>')
def add_to_cart(laptop_id):
    if 'customer_id' not in session:
        flash('يجب تسجيل الدخول أولاً لإضافة المنتجات إلى السلة', 'error')
        return redirect(url_for('customer_login'))
    
    customer_id = session['customer_id']
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM cart WHERE customer_id = %s AND laptop_id = %s", (customer_id, laptop_id))
    existing = cursor.fetchone()
    
    if existing:
        cursor.execute("UPDATE cart SET quantity = quantity + 1 WHERE customer_id = %s AND laptop_id = %s", (customer_id, laptop_id))
    else:
        cursor.execute("INSERT INTO cart (customer_id, laptop_id) VALUES (%s, %s)", (customer_id, laptop_id))
    
    conn.commit()
    conn.close()
    flash('تمت إضافة المنتج إلى السلة', 'success')
    return redirect(url_for('index'))

@app.route('/cart')
def view_cart():
    if 'customer_id' not in session:
        flash('يجب تسجيل الدخول أولاً لعرض السلة', 'error')
        return redirect(url_for('customer_login'))
    
    customer_id = session['customer_id']
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT laptops.*, cart.quantity FROM cart 
        JOIN laptops ON cart.laptop_id = laptops.id 
        WHERE cart.customer_id = %s
    """, (customer_id,))
    laptops = cursor.fetchall()
    conn.close()
    
    total = sum(laptop['price'] * laptop['quantity'] for laptop in laptops)
    return render_template('cart.html', laptops=laptops, total=total, whatsapp_number=get_whatsapp_number())

# ==========================================
# --- 4. لوحة تحكم المدير (إضافة وحذف) ---
# ==========================================
@app.route('/admin')
@login_required
def admin_dashboard():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM laptops ORDER BY created_at DESC")
    laptops = cursor.fetchall()
    conn.close()
    return render_template('admin/dashboard.html', laptops=laptops)

@app.route('/admin/add', methods=['GET', 'POST'])
@login_required
def add_laptop():
    if request.method == 'POST':
        name = request.form['name']
        specs = request.form['specs']
        price = request.form['price']
        
        file = request.files['image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_url = f'/uploads/{filename}'
        else:
            flash('الرجاء اختيار صورة صالحة (png, jpg, jpeg, gif)', 'error')
            return redirect(request.url)

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO laptops (name, specs, price, image_url) VALUES (%s, %s, %s, %s)", (name, specs, price, image_url))
        conn.commit()
        conn.close()
        
        flash('تمت إضافة اللابتوب بنجاح', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('admin/add_laptop.html')

@app.route('/admin/delete/<int:id>')
@login_required
def delete_laptop(id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM laptops WHERE id = %s", (id,))
    conn.commit()
    conn.close()
    flash('تم حذف اللابتوب بنجاح', 'success')
    return redirect(url_for('admin_dashboard'))

# ==========================================
# --- 5. إعدادات المتجر (للمدير) ---
# ==========================================
@app.route('/admin/settings', methods=['GET', 'POST'])
@login_required
def admin_settings():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        new_number = request.form.get('whatsapp_number')
        if new_number:
            cursor.execute("UPDATE settings SET whatsapp_number = %s WHERE id = 1", (new_number,))
            conn.commit()
            flash('تم تحديث رقم الواتساب بنجاح', 'success')
        
        new_email = request.form.get('admin_email')
        if new_email:
            cursor.execute("UPDATE settings SET admin_email = %s WHERE id = 1", (new_email,))
            conn.commit()
            flash('تم تحديث البريد الإلكتروني بنجاح', 'success')

        new_password = request.form.get('new_password')
        if new_password:
            cursor.execute("UPDATE admins SET password = %s WHERE username = 'admin'", (new_password,))
            conn.commit()
            flash('تم تغيير كلمة مرور المدير بنجاح', 'success')
            
        conn.close()
        return redirect(url_for('admin_settings'))
        
    cursor.execute("SELECT whatsapp_number, admin_email FROM settings WHERE id = 1")
    setting = cursor.fetchone()
    conn.close()
    
    return render_template('admin/settings.html', whatsapp_number=setting['whatsapp_number'] if setting else '', admin_email=setting['admin_email'] if setting else '')

# ==========================================
# --- 6. تسجيل دخول المدير ---
# ==========================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM admins WHERE username = %s AND password = %s", (username, password))
        admin = cursor.fetchone()
        conn.close()
        
        if admin:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))

# ==========================================
# --- 7. عرض الصور وتشغيل التطبيق ---
# ==========================================
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/checkout', methods=['POST'])
def checkout():
    if 'customer_id' not in session:
        return redirect(url_for('customer_login'))
    
    customer_id = session['customer_id']
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT laptops.id as laptop_id, laptops.name, laptops.price, cart.quantity 
        FROM cart JOIN laptops ON cart.laptop_id = laptops.id 
        WHERE cart.customer_id = %s
    """, (customer_id,))
    items = cursor.fetchall()
    
    if not items:
        flash('السلة فارغة', 'error')
        return redirect(url_for('index'))

    total = sum(item['price'] * item['quantity'] for item in items)
    
    cursor.execute("INSERT INTO orders (customer_id, total_price, status) VALUES (%s, %s, 'pending')", (customer_id, total))
    order_id = cursor.lastrowid
    
    for item in items:
        cursor.execute(
            "INSERT INTO order_items (order_id, laptop_id, quantity, price) VALUES (%s, %s, %s, %s)",
            (order_id, item['laptop_id'], item['quantity'], item['price'])
        )
    
    body = f"طلب جديد رقم #{order_id} من الزبون: {session['customer_name']}\n\n"
    for item in items:
        body += f"- {item['name']} (الكمية: {item['quantity']}) - السعر: {item['price']}$\n"
    body += f"\nالإجمالي: {total}$"
    send_notification(f"🛒 طلب شراء جديد #{order_id}", body)
    
    cursor.execute("DELETE FROM cart WHERE customer_id = %s", (customer_id,))
    conn.commit()
    conn.close()
    
    flash('تم إرسال طلبك بنجاح، يمكنك متابعة حالته من صفحة "طلباتي"', 'success')
    return redirect(url_for('my_orders'))

# --- 8. عرض طلبات الزبون ---
@app.route('/my_orders')
def my_orders():
    if 'customer_id' not in session:
        flash('يجب تسجيل الدخول أولاً', 'error')
        return redirect(url_for('customer_login'))
    
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM orders WHERE customer_id = %s AND is_hidden = 0 ORDER BY created_at ASC", (session['customer_id'],))   
    orders = cursor.fetchall()
    
    for order in orders:
        cursor.execute("""
            SELECT laptops.name, order_items.quantity, order_items.price 
            FROM order_items JOIN laptops ON order_items.laptop_id = laptops.id 
            WHERE order_items.order_id = %s
        """, (order['id'],))
        order['products'] = cursor.fetchall()
    
    conn.close()
    return render_template('my_orders.html', orders=orders)

# --- 9. إدارة الطلبات (للمدير) ---
@app.route('/admin/orders')
@login_required
def admin_orders():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT orders.*, customers.username 
        FROM orders JOIN customers ON orders.customer_id = customers.id 
        ORDER BY orders.created_at ASC
    """)
    orders = cursor.fetchall()
    conn.close()
    return render_template('admin/orders.html', orders=orders)

@app.route('/admin/orders/<int:order_id>/status', methods=['POST'])
@login_required
def update_order_status(order_id):
    new_status = request.form['status']
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status = %s WHERE id = %s", (new_status, order_id))
    conn.commit()
    conn.close()
    flash('تم تحديث حالة الطلب', 'success')
    return redirect(url_for('admin_orders'))    

@app.route('/order/hide/<int:order_id>')
def hide_order(order_id):
    if 'customer_id' not in session:
        return redirect(url_for('customer_login'))
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET is_hidden = 1 WHERE id = %s AND customer_id = %s", (order_id, session['customer_id']))
    conn.commit()
    conn.close()
    
    flash('تم إخفاء الطلب من سجلك', 'success')
    return redirect(url_for('my_orders'))

# ==========================================
# --- 10. تقارير المبيعات (للمدير) ---
# ==========================================
@app.route('/admin/reports')
@login_required
def admin_reports():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT COUNT(*) as count, COALESCE(SUM(total_price), 0) as total FROM orders WHERE DATE(created_at) = CURDATE()")
    today_report = cursor.fetchone()
    
    cursor.execute("SELECT COUNT(*) as count, COALESCE(SUM(total_price), 0) as total FROM orders WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)")
    week_report = cursor.fetchone()
    
    cursor.execute("SELECT COUNT(*) as count, COALESCE(SUM(total_price), 0) as total FROM orders WHERE MONTH(created_at) = MONTH(CURDATE()) AND YEAR(created_at) = YEAR(CURDATE())")
    month_report = cursor.fetchone()
    
    cursor.execute("SELECT COUNT(*) as count, COALESCE(SUM(total_price), 0) as total FROM orders WHERE YEAR(created_at) = YEAR(CURDATE())")
    year_report = cursor.fetchone()
    
    conn.close()
    
    return render_template('admin/reports.html', 
                           today_report=today_report,
                           week_report=week_report,
                           month_report=month_report,
                           year_report=year_report)

@app.route('/admin/reports/export/<period>')
@login_required
def export_reports(period):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    if period == 'today':
        query = "SELECT * FROM orders WHERE DATE(created_at) = CURDATE()"
        title = "تقرير اليوم"
    elif period == 'week':
        query = "SELECT * FROM orders WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)"
        title = "تقرير الأسبوع"
    elif period == 'month':
        query = "SELECT * FROM orders WHERE MONTH(created_at) = MONTH(CURDATE()) AND YEAR(created_at) = YEAR(CURDATE())"
        title = "تقرير الشهر"
    elif period == 'year':
        query = "SELECT * FROM orders WHERE YEAR(created_at) = YEAR(CURDATE())"
        title = "تقرير السنة"
    else:
        return "فترة غير صالحة", 400
    
    cursor.execute(query)
    orders = cursor.fetchall()
    conn.close()
    
    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.writer(output)
    
    writer.writerow([title])
    writer.writerow(["رقم الطلب", "التاريخ", "الإجمالي", "الحالة"])
    
    total_sum = 0
    for order in orders:
        status_ar = {
            'pending': 'قيد المعالجة',
            'shipped': 'تم الشحن',
            'delivered': 'تم التوصيل',
            'cancelled': 'ملغي'
        }.get(order['status'], order['status'])
        
        writer.writerow([order['id'], order['created_at'], order['total_price'], status_ar])
        total_sum += float(order['total_price'])
    
    writer.writerow([])
    writer.writerow(["الإجمالي", "", total_sum, ""])
    
    csv_data = output.getvalue()
    output.close()
    
    filename = f"report_{period}.csv"
    return Response(
        csv_data,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@app.route('/admin/reports/pdf/<period>')
@login_required
def export_reports_pdf(period):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    if period == 'today':
        query = "SELECT * FROM orders WHERE DATE(created_at) = CURDATE()"
        title = "تقرير اليوم"
    elif period == 'week':
        query = "SELECT * FROM orders WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)"
        title = "تقرير الأسبوع"
    elif period == 'month':
        query = "SELECT * FROM orders WHERE MONTH(created_at) = MONTH(CURDATE()) AND YEAR(created_at) = YEAR(CURDATE())"
        title = "تقرير الشهر"
    elif period == 'year':
        query = "SELECT * FROM orders WHERE YEAR(created_at) = YEAR(CURDATE())"
        title = "تقرير السنة"
    else:
        return "فترة غير صالحة", 400
    
    cursor.execute(query)
    orders = cursor.fetchall()
    conn.close()
    
    total_sum = sum(float(order['total_price']) for order in orders)
    
    pdfmetrics.registerFont(TTFont('Arabic', 'arial.ttf'))
    
    def ar(text):
        reshaped = arabic_reshaper.reshape(str(text))
        return get_display(reshaped)
    
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    p.setFont("Arabic", 22)
    p.setFillColor(colors.HexColor('#1a252f'))
    p.drawCentredString(width / 2, height - 50, ar(title))
    
    p.setStrokeColor(colors.HexColor('#1a252f'))
    p.setLineWidth(2)
    p.line(50, height - 60, width - 50, height - 60)
    
    y = height - 100
    col_x = [520, 380, 230, 80]  
    
    p.setFillColor(colors.HexColor('#1a252f'))
    p.rect(50, y - 5, width - 100, 25, fill=1, stroke=0)
    
    p.setFillColor(colors.white)
    p.setFont("Arabic", 12)
    p.drawString(col_x[0], y, ar("رقم الطلب"))
    p.drawString(col_x[1], y, ar("التاريخ"))
    p.drawString(col_x[2], y, ar("الإجمالي ($)"))
    p.drawString(col_x[3], y, ar("الحالة"))
    
    y -= 30
    p.setFont("Arabic", 9)
    p.setFillColor(colors.black)
    
    for idx, order in enumerate(orders):
        if idx % 2 == 0:
            p.setFillColor(colors.HexColor('#f4f6f9'))
            p.rect(50, y - 5, width - 100, 20, fill=1, stroke=0)
        
        p.setFillColor(colors.black)
        
        status_ar = {
            'pending': 'قيد المعالجة',
            'shipped': 'تم الشحن',
            'delivered': 'تم التوصيل',
            'cancelled': 'ملغي'
        }.get(order['status'], order['status'])
        
        p.drawString(col_x[0], y, f"#{order['id']}")
        p.drawString(col_x[1], y, str(order['created_at']))
        p.drawString(col_x[2], y, str(order['total_price']))
        p.drawString(col_x[3], y, ar(status_ar))
        
        y -= 20
        
        p.setStrokeColor(colors.HexColor('#e0e0e0'))
        p.setLineWidth(0.5)
        p.line(50, y + 5, width - 50, y + 5)
    
    p.setStrokeColor(colors.HexColor('#1a252f'))
    p.setLineWidth(1)
    table_height = (len(orders) * 20) + 30
    p.rect(50, height - 105 - table_height, width - 100, table_height, fill=0, stroke=1)
    
    y -= 30
    p.setFont("Arabic", 14)
    p.setFillColor(colors.HexColor('#2ecc71'))
    p.drawString(50, y, ar(f"الإجمالي الكلي: {total_sum} $"))
    
    p.save()
    buffer.seek(0)
    
    return Response(
        buffer.getvalue(),
        mimetype='application/pdf',
        headers={'Content-Disposition': f'attachment; filename="report_{period}.pdf"'}
    )

@app.route('/admin/laptop/<int:id>')
@login_required
def admin_view_laptop(id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM laptops WHERE id = %s", (id,))
    laptop = cursor.fetchone()
    conn.close()
    if not laptop:
        flash('المنتج غير موجود', 'error')
        return redirect(url_for('admin_dashboard'))
    return render_template('admin/view_laptop.html', laptop=laptop)

@app.route('/admin/laptop/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_laptop(id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM laptops WHERE id = %s", (id,))
    laptop = cursor.fetchone()
    
    if not laptop:
        flash('المنتج غير موجود', 'error')
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        name = request.form['name']
        specs = request.form['specs']
        price = request.form['price']
        
        image_url = laptop['image_url']
        file = request.files.get('image')
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_url = f'/uploads/{filename}'
        
        cursor.execute(
            "UPDATE laptops SET name = %s, specs = %s, price = %s, image_url = %s WHERE id = %s",
            (name, specs, price, image_url, id)
        )
        conn.commit()
        conn.close()
        
        flash('تم تحديث المنتج بنجاح', 'success')
        return redirect(url_for('admin_dashboard'))
    
    conn.close()
    return render_template('admin/edit_laptop.html', laptop=laptop)

if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)
