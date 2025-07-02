from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
from datetime import datetime
import re
import json
import shutil
from werkzeug.utils import secure_filename
import pytz
import threading
import time
import asyncio
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
import logging

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# إعداد التسجيل للبوت
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# متغيرات البوت
telegram_bot = None
telegram_app = None

# Middleware للتحقق من وضع الصيانة
@app.before_request
def check_maintenance_mode():
    # استثناء صفحات الإدارة والترحيب من وضع الصيانة
    if request.endpoint and (request.endpoint.startswith('admin_') or 
                           request.endpoint == 'login' or 
                           request.endpoint == 'logout' or
                           request.endpoint == 'register' or
                           request.endpoint == 'welcome' or
                           request.endpoint == 'save_settings'):
        return

    # التحقق من وضع الصيانة
    try:
        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()

        # التأكد من وجود جدول الإعدادات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS site_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key TEXT UNIQUE NOT NULL,
                setting_value TEXT,
                description TEXT,
                category TEXT DEFAULT 'general'
            )
        ''')

        cursor.execute('SELECT setting_value FROM site_settings WHERE setting_key = ?', ('maintenance_mode',))
        result = cursor.fetchone()
        conn.close()

        if result and result[0] == '1':
            # إذا كان المستخدم إداري، السماح له بالدخول
            if session.get('is_admin'):
                return

            # السماح بصفحات تسجيل الدخول للإداريين
            if request.endpoint in ['login']:
                return

            # عرض صفحة الصيانة للمستخدمين العاديين
            return '''
                <!DOCTYPE html>
                <html lang="ar" dir="rtl">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>الموقع تحت الصيانة</title>
                    <style>
                        body { font-family: 'Cairo', sans-serif; 
                               background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                               min-height: 100vh; display: flex; align-items: center; justify-content: center; margin: 0; }
                        .container { background: white; padding: 50px; border-radius: 20px; text-align: center; 
                                   box-shadow: 0 20px 40px rgba(0,0,0,0.1); max-width: 500px; }
                        h1 { color: #333; margin-bottom: 20px; font-size: 2.5em; }
                        p { color: #666; font-size: 1.2em; line-height: 1.6; }
                        .icon { font-size: 4em; color: #ffc107; margin-bottom: 20px; }
                        .admin-link { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                    color: white; padding: 12px 25px; border-radius: 25px; 
                                    text-decoration: none; font-weight: bold; display: inline-block; margin-top: 20px; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="icon">🔧</div>
                        <h1>الموقع تحت الصيانة</h1>
                        <p>نعتذر عن الإزعاج، الموقع حالياً تحت الصيانة للتحسين والتطوير.</p>
                        <p>سنعود قريباً بشكل أفضل!</p>
                        <a href="/login" class="admin-link">تسجيل دخول الإدارة</a>
                    </div>
                </body>
                </html>
            ''', 503
    except Exception as e:
        print(f"خطأ في التحقق من وضع الصيانة: {e}")
        pass

# Context processor لإضافة الصيدليات المناوبة لجميع الصفحات
@app.context_processor
def inject_today_pharmacy():
    try:
        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()
        # استخدام التوقيت الحالي مع إضافة 3 ساعات لتوقيت دمشق
        from datetime import timezone, timedelta
        damascus_tz = timezone(timedelta(hours=3))  # دمشق UTC+3
        damascus_time = datetime.now(damascus_tz)
        
        # تحديد التاريخ بناءً على الساعة 1:30 صباحاً
        if damascus_time.hour < 1 or (damascus_time.hour == 1 and damascus_time.minute < 30):
            # إذا كان الوقت قبل 1:30 صباحاً، استخدم تاريخ اليوم السابق
            display_date = (damascus_time - timedelta(days=1)).date()
        else:
            # إذا كان الوقت بعد 1:30 صباحاً، استخدم تاريخ اليوم الحالي
            display_date = damascus_time.date()
        
        today = display_date.strftime('%Y-%m-%d')
        
        print(f"التوقيت الحالي بدمشق: {damascus_time}")
        print(f"تاريخ اليوم (مع تطبيق قاعدة 1:30 ص): {today}")
        
        # جلب جميع الصيدليات المناوبة لهذا اليوم
        cursor.execute('SELECT * FROM duty_pharmacies WHERE duty_date = ? ORDER BY id', (today,))
        today_pharmacies = cursor.fetchall()
        
        # للتوافق مع الكود القديم، نحتفظ بـ today_pharmacy كأول صيدلية
        today_pharmacy = today_pharmacies[0] if today_pharmacies else None
        
        conn.close()
        return dict(
            today_pharmacy=today_pharmacy, 
            today_pharmacies=today_pharmacies,
            damascus_time=damascus_time
        )
    except Exception as e:
        print(f"خطأ في تحميل الصيدليات المناوبة: {e}")
        return dict(
            today_pharmacy=None, 
            today_pharmacies=[],
            damascus_time=None
        )

# إنشاء قاعدة البيانات
def init_db():
    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # جدول المستخدمين
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            is_admin BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # جدول التصنيفات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT
        )
    ''')

    # جدول المحلات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category_id INTEGER,
            address TEXT NOT NULL,
            phone TEXT,
            description TEXT,
            image_url TEXT,
            user_id INTEGER,
            is_approved BOOLEAN DEFAULT 0,
            visits_count INTEGER DEFAULT 0,
            search_count INTEGER DEFAULT 0,
            rating_avg REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # إضافة عمود search_count إذا لم يكن موجوداً
    try:
        cursor.execute('ALTER TABLE stores ADD COLUMN search_count INTEGER DEFAULT 0')
    except:
        pass

    # جدول التقييمات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id INTEGER,
            user_id INTEGER,
            rating INTEGER CHECK (rating >= 1 AND rating <= 5),
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (store_id) REFERENCES stores (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # إضافة عمود التعليق إذا لم يكن موجوداً
    try:
        cursor.execute('ALTER TABLE ratings ADD COLUMN comment TEXT')
    except:
        pass
    
    # إضافة عمود updated_at إذا لم يكن موجوداً
    try:
        cursor.execute('ALTER TABLE ratings ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
    except:
        pass
    
    # تحديث القيم الفارغة في updated_at
    try:
        cursor.execute('UPDATE ratings SET updated_at = created_at WHERE updated_at IS NULL')
        conn.commit()
    except:
        pass

    # جدول الصيدليات المناوبة
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS duty_pharmacies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT NOT NULL,
            phone TEXT NOT NULL,
            duty_date DATE NOT NULL
        )
    ''')

    # جدول الخدمات الهامة
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS important_services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            description TEXT,
            category TEXT
        )
    ''')

    # جدول تصنيفات الخدمات الهامة
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS service_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            icon TEXT,
            color TEXT DEFAULT '#007bff'
        )
    ''')

    # لا نضيف أي تصنيفات افتراضية - سيتم إدارتها من لوحة الإدارة فقط

    # جدول الإشعارات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            type TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP
        )
    ''')

    # جدول الشريط المتحرك
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ticker_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT NOT NULL,
            type TEXT,
            priority INTEGER DEFAULT 1,
            is_active BOOLEAN DEFAULT 1,
            direction TEXT DEFAULT 'right',
            speed INTEGER DEFAULT 50,
            background_color TEXT DEFAULT '#11998e',
            text_color TEXT DEFAULT '#ffffff',
            font_size INTEGER DEFAULT 16,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # إضافة الأعمدة المفقودة إذا لم تكن موجودة
    try:
        cursor.execute('ALTER TABLE ticker_messages ADD COLUMN direction TEXT DEFAULT "right"')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE ticker_messages ADD COLUMN speed INTEGER DEFAULT 50')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE ticker_messages ADD COLUMN background_color TEXT DEFAULT "#11998e"')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE ticker_messages ADD COLUMN text_color TEXT DEFAULT "#ffffff"')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE ticker_messages ADD COLUMN font_size INTEGER DEFAULT 16')
    except:
        pass

    # جدول إعدادات النقاط
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS points_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            setting_key TEXT UNIQUE NOT NULL,
            setting_value INTEGER DEFAULT 0,
            description TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # إدراج الإعدادات الافتراضية للنقاط
    default_points_settings = [
        ('points_add_store', 10, 'نقاط إضافة محل جديد'),
        ('points_rate_store', 5, 'نقاط تقييم محل'),
        ('points_daily_login', 2, 'نقاط الدخول اليومي')
    ]

    for setting in default_points_settings:
        cursor.execute('''
            INSERT OR IGNORE INTO points_settings (setting_key, setting_value, description) 
            VALUES (?, ?, ?)
        ''', setting)

    # جدول نقاط المستخدمين
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_points (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            total_points INTEGER DEFAULT 0,
            available_points INTEGER DEFAULT 0,
            spent_points INTEGER DEFAULT 0,
            last_daily_login DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')

    # جدول سجل النقاط
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS points_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            points INTEGER NOT NULL,
            activity_type TEXT NOT NULL,
            activity_description TEXT,
            related_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')

    # جدول الهدايا
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gifts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            points_cost INTEGER NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            stock_quantity INTEGER DEFAULT -1,
            image_url TEXT,
            category TEXT DEFAULT 'عام',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # جدول طلبات استبدال الهدايا
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gift_redemptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            gift_id INTEGER NOT NULL,
            points_spent INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            admin_notes TEXT,
            requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed_at TIMESTAMP,
            processed_by INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (gift_id) REFERENCES gifts (id) ON DELETE CASCADE,
            FOREIGN KEY (processed_by) REFERENCES users (id)
        )
    ''')

    # إضافة عمود النقاط للمستخدمين الحاليين
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN total_points INTEGER DEFAULT 0')
    except:
        pass

    conn.commit()
    conn.close()

# التحقق من صحة رقم الهاتف السوري
def validate_syrian_phone(phone):
    pattern = r'^09\d{8}$'
    return bool(re.match(pattern, phone))

# تحسين وظائف إرسال الإشعارات
async def send_telegram_message_safely(chat_id, message):
    """إرسال رسالة تليجرام بشكل آمن"""
    if not telegram_bot:
        return False
    
    try:
        await telegram_bot.send_message(chat_id=chat_id, text=message)
        return True
    except Exception as e:
        print(f"خطأ في إرسال رسالة تليجرام: {e}")
        return False

# وظيفة للتحقق التلقائي من انتهاء صلاحية الإشعارات
def check_expired_notifications():
    """تشغيل مهمة تلقائية للتحقق من انتهاء صلاحية الإشعارات كل 30 ثانية"""
    while True:
        try:
            conn = sqlite3.connect('hussainiya_stores.db')
            cursor = conn.cursor()
            
            # الحصول على التوقيت الحالي بتوقيت دمشق مع إضافة 3 ساعات
            from datetime import timezone, timedelta
            damascus_tz = timezone(timedelta(hours=3))  # دمشق UTC+3
            damascus_time = datetime.now(damascus_tz)
            current_time_str = damascus_time.strftime('%Y-%m-%d %H:%M:%S')
            
            # البحث عن الإشعارات المنتهية الصلاحية والنشطة
            cursor.execute('''
                SELECT id, title, expires_at FROM notifications 
                WHERE is_active = 1 AND expires_at IS NOT NULL AND expires_at <= ?
            ''', (current_time_str,))
            expired_notifications = cursor.fetchall()
            
            expired_count = 0
            
            if expired_notifications:
                # تعطيل الإشعارات المنتهية الصلاحية
                cursor.execute('''
                    UPDATE notifications 
                    SET is_active = 0 
                    WHERE is_active = 1 AND expires_at IS NOT NULL AND expires_at <= ?
                ''', (current_time_str,))
                conn.commit()
                expired_count += len(expired_notifications)
                
                # طباعة معلومات الإشعارات المعطلة
                for notification in expired_notifications:
                    print(f"✅ تم تعطيل الإشعار تلقائياً: {notification[1]} (ID: {notification[0]}) - انتهى في: {notification[2]}")
            
            # التحقق من الإشعارات المتقدمة أيضاً
            try:
                cursor.execute('''
                    SELECT id, title, expires_at FROM advanced_notifications 
                    WHERE is_active = 1 AND expires_at IS NOT NULL AND expires_at <= ?
                ''', (current_time_str,))
                expired_advanced = cursor.fetchall()
                
                if expired_advanced:
                    cursor.execute('''
                        UPDATE advanced_notifications 
                        SET is_active = 0 
                        WHERE is_active = 1 AND expires_at IS NOT NULL AND expires_at <= ?
                    ''', (current_time_str,))
                    conn.commit()
                    expired_count += len(expired_advanced)
                    
                    for notification in expired_advanced:
                        print(f"✅ تم تعطيل الإشعار المتقدم تلقائياً: {notification[1]} (ID: {notification[0]}) - انتهى في: {notification[2]}")
                        
            except Exception as advanced_error:
                # إنشاء جدول الإشعارات المتقدمة إذا لم يكن موجوداً
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS advanced_notifications (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        message TEXT NOT NULL,
                        type TEXT,
                        target_users TEXT DEFAULT 'all',
                        priority INTEGER DEFAULT 1,
                        is_popup BOOLEAN DEFAULT 0,
                        is_active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP,
                        read_by TEXT DEFAULT ''
                    )
                ''')
                conn.commit()
            
            # طباعة رسالة تلقائية فقط إذا تم تعطيل إشعارات
            if expired_count > 0:
                print(f"🔄 [النظام التلقائي] تم تعطيل {expired_count} إشعار منتهي الصلاحية في {current_time_str}")
            
            conn.close()
            
        except Exception as e:
            print(f"❌ خطأ في النظام التلقائي للإشعارات: {e}")
        
        # انتظار 30 ثانية قبل التحقق مرة أخرى
        time.sleep(30)

# بدء المهمة التلقائية في خيط منفصل
def start_notification_checker():
    """بدء مهمة التحقق من انتهاء صلاحية الإشعارات"""
    checker_thread = threading.Thread(target=check_expired_notifications, daemon=True)
    checker_thread.start()
    print("تم بدء النظام التلقائي للتحقق من انتهاء صلاحية الإشعارات")

# Context processor للإشعارات والشريط المتحرك وإعدادات الموقع
@app.context_processor
def inject_notifications_and_ticker():
    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # الحصول على التوقيت الحالي بتوقيت دمشق مع إضافة 3 ساعات
    from datetime import timezone, timedelta
    damascus_tz = timezone(timedelta(hours=3))  # دمشق UTC+3
    damascus_time = datetime.now(damascus_tz)
    current_time_str = damascus_time.strftime('%Y-%m-%d %H:%M:%S')
    
    # تعطيل الإشعارات المنتهية الصلاحية تلقائياً في الإشعارات العادية
    cursor.execute('''
        SELECT id, title FROM notifications 
        WHERE is_active = 1 AND expires_at IS NOT NULL AND expires_at <= ?
    ''', (current_time_str,))
    expired_regular = cursor.fetchall()
    
    if expired_regular:
        cursor.execute('''
            UPDATE notifications 
            SET is_active = 0 
            WHERE is_active = 1 AND expires_at IS NOT NULL AND expires_at <= ?
        ''', (current_time_str,))
        
        for notif in expired_regular:
            print(f"🔄 [context] تعطيل إشعار عادي: {notif[1]} (ID: {notif[0]})")

    # تعطيل الإشعارات المتقدمة المنتهية أيضاً
    try:
        # إنشاء جدول الإشعارات المتقدمة إذا لم يكن موجوداً
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS advanced_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                type TEXT,
                target_users TEXT DEFAULT 'all',
                priority INTEGER DEFAULT 1,
                is_popup BOOLEAN DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                read_by TEXT DEFAULT ''
            )
        ''')
        
        cursor.execute('''
            SELECT id, title FROM advanced_notifications 
            WHERE is_active = 1 AND expires_at IS NOT NULL AND expires_at <= ?
        ''', (current_time_str,))
        expired_advanced = cursor.fetchall()
        
        if expired_advanced:
            cursor.execute('''
                UPDATE advanced_notifications 
                SET is_active = 0 
                WHERE is_active = 1 AND expires_at IS NOT NULL AND expires_at <= ?
            ''', (current_time_str,))
            
            for notif in expired_advanced:
                print(f"🔄 [context] تعطيل إشعار متقدم: {notif[1]} (ID: {notif[0]})")
                
    except Exception as e:
        print(f"تحذير في معالجة الإشعارات المتقدمة: {e}")

    # حفظ التغييرات
    conn.commit()

    # الإشعارات النشطة (فقط التي لم تنته بعد أو بدون تاريخ انتهاء)
    cursor.execute('''
        SELECT * FROM notifications 
        WHERE is_active = 1 AND (expires_at IS NULL OR expires_at > ?)
        ORDER BY created_at DESC
    ''', (current_time_str,))
    notifications = cursor.fetchall()

    # التأكد من وجود عمود pages في جدول ticker_messages
    try:
        cursor.execute('ALTER TABLE ticker_messages ADD COLUMN pages TEXT DEFAULT "all"')
        conn.commit()
    except:
        pass

    # الحصول على رسائل الشريط المتحرك مع معالجة عمود pages
    try:
        cursor.execute('''SELECT id, message, type, priority, is_active, direction, speed, 
                          background_color, text_color, font_size, created_at, pages 
                          FROM ticker_messages WHERE is_active = 1 ORDER BY priority DESC, created_at DESC''')
        ticker_messages = cursor.fetchall()
    except:
        # في حالة عدم وجود عمود pages، نضيف قيمة افتراضية
        cursor.execute('''SELECT id, message, type, priority, is_active, direction, speed, 
                          background_color, text_color, font_size, created_at, 'all' as pages 
                          FROM ticker_messages WHERE is_active = 1 ORDER BY priority DESC, created_at DESC''')
        ticker_messages = cursor.fetchall()

    # إعدادات الموقع
    site_settings = get_site_settings()

    conn.close()
    return dict(notifications=notifications, ticker_messages=ticker_messages, site_settings=site_settings)

# البحث الشامل - مع التسجيل الإجباري
@app.route('/search')
def search():
    # التحقق من تسجيل الدخول
    if 'user_id' not in session:
        flash('يجب تسجيل الدخول للبحث', 'warning')
        return redirect(url_for('login'))
    
    query = request.args.get('q', '')
    category_id = request.args.get('category', '')
    service_category = request.args.get('service_category', '')
    search_type = request.args.get('type', 'all')  # all, stores, services

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    store_results = []
    service_results = []

    # البحث في المحلات
    if search_type in ['all', 'stores']:
        search_conditions = ['s.is_approved = 1']
        search_params = []

        if query:
            search_conditions.append('(s.name LIKE ? OR s.description LIKE ? OR s.address LIKE ? OR s.phone LIKE ?)')
            search_params.extend([f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%'])

        if category_id:
            search_conditions.append('s.category_id = ?')
            search_params.append(category_id)

        where_clause = ' AND '.join(search_conditions)

        cursor.execute(f'''
            SELECT s.*, c.name as category_name, COUNT(r.id) as ratings_count
            FROM stores s 
            LEFT JOIN categories c ON s.category_id = c.id 
            LEFT JOIN ratings r ON s.id = r.store_id
            WHERE {where_clause}
            GROUP BY s.id
            ORDER BY s.search_count DESC, COUNT(r.id) DESC, s.rating_avg DESC
        ''', search_params)

        store_results = cursor.fetchall()

        # تحديث عداد البحث للمحلات
        if store_results and query:
            store_ids = [str(result[0]) for result in store_results]
            if store_ids:
                cursor.execute(f'''
                    UPDATE stores 
                    SET search_count = search_count + 1 
                    WHERE id IN ({','.join(['?' for _ in store_ids])})
                ''', store_ids)
                conn.commit()

    # البحث في الخدمات الهامة
    if search_type in ['all', 'services']:
        service_conditions = []
        service_params = []

        if query:
            service_conditions.append('(s.name LIKE ? OR s.description LIKE ? OR s.phone LIKE ? OR s.category LIKE ?)')
            service_params.extend([f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%'])

        if service_category:
            service_conditions.append('s.category = ?')
            service_params.append(service_category)

        service_where_clause = ' AND '.join(service_conditions) if service_conditions else '1=1'

        cursor.execute(f'''
            SELECT s.*, sc.name as category_name, sc.color, sc.icon
            FROM important_services s 
            LEFT JOIN service_categories sc ON s.category = sc.name
            WHERE {service_where_clause}
            ORDER BY 
                CASE 
                    WHEN s.category = 'طوارئ' THEN 1
                    WHEN s.category = 'صحة' THEN 2
                    WHEN s.category = 'أمن' THEN 3
                    ELSE 4
                END, s.name
        ''', service_params)

        service_results = cursor.fetchall()

    # الحصول على جميع التصنيفات للفلترة (بغض النظر عن إعدادات الصفحة الرئيسية)
    cursor.execute('SELECT * FROM categories ORDER BY name')
    categories = cursor.fetchall()

    # الحصول على تصنيفات الخدمات
    cursor.execute('SELECT * FROM service_categories ORDER BY name')
    service_categories = cursor.fetchall()

    # حساب إجمالي النتائج
    total_results = len(store_results) + len(service_results)

    conn.close()

    return render_template('search_results.html', 
                         store_results=store_results,
                         service_results=service_results, 
                         categories=categories,
                         service_categories=service_categories,
                         query=query,
                         selected_category=category_id,
                         selected_service_category=service_category,
                         search_type=search_type,
                         total_results=total_results)

# الصفحة الرئيسية - مع التسجيل الإجباري
@app.route('/')
def index():
    # التحقق من تسجيل الدخول
    if 'user_id' not in session:
        flash('يجب تسجيل الدخول لمشاهدة المحتوى', 'warning')
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # الحصول على إعدادات الموقع
    settings = get_site_settings()

    latest_stores = []
    popular_stores = []
    top_rated_stores = []
    featured_stores = []

    # أحدث المحلات المضافة
    if settings.get('show_latest_stores', '1') == '1':
        limit = int(settings.get('latest_stores_count', '6'))
        cursor.execute('''
            SELECT s.*, c.name as category_name 
            FROM stores s 
            LEFT JOIN categories c ON s.category_id = c.id 
            WHERE s.is_approved = 1 
            ORDER BY s.created_at DESC 
            LIMIT ?
        ''', (limit,))
        latest_stores = cursor.fetchall()

    # أكثر المحلات بحثاً
    if settings.get('show_most_searched_stores', '1') == '1':
        limit = int(settings.get('most_searched_stores_count', '6'))
        cursor.execute('''
            SELECT s.*, c.name as category_name 
            FROM stores s 
            LEFT JOIN categories c ON s.category_id = c.id 
            WHERE s.is_approved = 1 AND s.search_count > 0
            ORDER BY s.search_count DESC 
            LIMIT ?
        ''', (limit,))
        popular_stores = cursor.fetchall()

    # أكثر المحلات تقييماً
    if settings.get('show_top_rated_stores', '1') == '1':
        limit = int(settings.get('top_rated_stores_count', '6'))
        cursor.execute('''
            SELECT s.*, c.name as category_name, COUNT(r.id) as ratings_count
            FROM stores s 
            LEFT JOIN categories c ON s.category_id = c.id 
            LEFT JOIN ratings r ON s.id = r.store_id
            WHERE s.is_approved = 1 AND s.rating_avg > 0
            GROUP BY s.id
            ORDER BY COUNT(r.id) DESC, s.rating_avg DESC 
            LIMIT ?
        ''', (limit,))
        top_rated_stores = cursor.fetchall()

    # المحلات المميزة
    if settings.get('show_featured_stores', '1') == '1':
        limit = int(settings.get('featured_stores_count', '4'))
        cursor.execute('''
            SELECT s.*, c.name as category_name 
            FROM stores s 
            LEFT JOIN categories c ON s.category_id = c.id 
            WHERE s.is_approved = 1 AND s.rating_avg >= 4.0
            ORDER BY s.rating_avg DESC, s.search_count DESC
            LIMIT ?
        ''', (limit,))
        featured_stores = cursor.fetchall()

    # التصنيفات لشبكة العرض في الصفحة الرئيسية
    categories_grid = []
    if settings.get('show_categories_grid', '1') == '1':
        limit = int(settings.get('categories_grid_count', '8'))
        cursor.execute('SELECT * FROM categories LIMIT ?', (limit,))
        categories_grid = cursor.fetchall()

    # جميع التصنيفات لصندوق البحث
    cursor.execute('SELECT * FROM categories ORDER BY name')
    all_categories = cursor.fetchall()

    conn.close()

    return render_template('index.html', 
                         latest_stores=latest_stores,
                         popular_stores=popular_stores,
                         top_rated_stores=top_rated_stores,
                         featured_stores=featured_stores,
                         categories=categories_grid,
                         all_categories=all_categories,
                         site_settings=settings)

# تسجيل مستخدم جديد
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        phone = request.form['phone']
        password = request.form['password']

        # التحقق من صحة البيانات
        if not validate_syrian_phone(phone):
            flash('رقم الهاتف يجب أن يكون سوري ويبدأ بـ 09 ويتكون من 10 أرقام', 'error')
            return render_template('register.html')

        # التحقق من عدم وجود المستخدم مسبقاً
        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE phone = ?', (phone,))
        if cursor.fetchone():
            flash('رقم الهاتف مسجل مسبقاً', 'error')
            conn.close()
            return render_template('register.html')

        # إنشاء المستخدم الجديد
        password_hash = generate_password_hash(password)
        cursor.execute('INSERT INTO users (full_name, phone, password_hash) VALUES (?, ?, ?)',
                      (full_name, phone, password_hash))
        conn.commit()
        conn.close()

        flash('تم إنشاء الحساب بنجاح! يمكنك الآن تسجيل الدخول', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

# صفحة ترحيب للزوار غير المسجلين
@app.route('/welcome')
def welcome():
    # إذا كان المستخدم مسجل دخول، توجيهه للصفحة الرئيسية
    if 'user_id' in session:
        return redirect(url_for('index'))
    
    return render_template('welcome.html')

# تسجيل الدخول
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form['phone']
        password = request.form['password']

        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id, full_name, password_hash, is_active, is_admin FROM users WHERE phone = ?', (phone,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[2], password):
            if user[3]:  # is_active
                session['user_id'] = user[0]
                session['user_name'] = user[1]
                session['is_admin'] = user[4]
                
                # منح نقاط الدخول اليومي
                if award_daily_login_points(user[0]):
                    flash('مرحباً بك! تم منحك نقاط الدخول اليومي', 'success')
                else:
                    flash('مرحباً بك!', 'success')
                
                return redirect(url_for('dashboard'))
            else:
                flash('حسابك معطل، تواصل مع الإدارة', 'error')
        else:
            flash('رقم الهاتف أو كلمة المرور غير صحيحة', 'error')

    return render_template('login.html')

# تسجيل الخروج
@app.route('/logout')
def logout():
    session.clear()
    flash('تم تسجيل الخروج بنجاح', 'success')
    return redirect(url_for('index'))

# عرض تفاصيل الهدية للمستخدمين
@app.route('/gift-details/<int:gift_id>')
def gift_details(gift_id):
    if 'user_id' not in session:
        flash('يجب تسجيل الدخول للوصول لهذه الصفحة', 'error')
        return redirect(url_for('login'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM gifts 
        WHERE id = ? AND is_active = 1
    ''', (gift_id,))
    gift = cursor.fetchone()
    
    if not gift:
        flash('الهدية غير موجودة أو غير متاحة', 'error')
        conn.close()
        return redirect(url_for('user_points'))
    
    # التحقق من نقاط المستخدم
    points_summary = get_user_points_summary(session['user_id'])
    
    conn.close()
    
    return render_template('gift_details.html', 
                         gift=gift,
                         points_summary=points_summary)

# صفحة النقاط والهدايا
@app.route('/points')
def user_points():
    if 'user_id' not in session:
        flash('يجب تسجيل الدخول للوصول لهذه الصفحة', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    points_summary = get_user_points_summary(user_id)
    
    # الحصول على الهدايا المتاحة
    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM gifts 
        WHERE is_active = 1 AND (stock_quantity > 0 OR stock_quantity = -1)
        ORDER BY points_cost ASC
    ''')
    available_gifts = cursor.fetchall()
    
    # الحصول على طلبات الاستبدال السابقة
    cursor.execute('''
        SELECT gr.*, g.name as gift_name, g.points_cost
        FROM gift_redemptions gr
        LEFT JOIN gifts g ON gr.gift_id = g.id
        WHERE gr.user_id = ?
        ORDER BY gr.requested_at DESC
        LIMIT 10
    ''', (user_id,))
    redemption_history = cursor.fetchall()
    
    conn.close()
    
    return render_template('user_points.html', 
                         points_summary=points_summary,
                         available_gifts=available_gifts,
                         redemption_history=redemption_history)

# استبدال هدية
@app.route('/redeem-gift/<int:gift_id>', methods=['POST'])
def redeem_gift(gift_id):
    if 'user_id' not in session:
        return jsonify({'error': 'يجب تسجيل الدخول أولاً'}), 401
    
    user_id = session['user_id']
    
    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()
    
    # التحقق من وجود الهدية وتوفرها
    cursor.execute('SELECT * FROM gifts WHERE id = ? AND is_active = 1', (gift_id,))
    gift = cursor.fetchone()
    
    if not gift:
        conn.close()
        return jsonify({'error': 'الهدية غير موجودة أو غير متاحة'}), 400
    
    gift_points_cost = gift[3]
    gift_stock = gift[5]
    
    # التحقق من المخزون
    if gift_stock == 0:
        conn.close()
        return jsonify({'error': 'الهدية غير متوفرة في المخزون'}), 400
    
    # التحقق من نقاط المستخدم
    points_summary = get_user_points_summary(user_id)
    if points_summary['available_points'] < gift_points_cost:
        conn.close()
        return jsonify({'error': 'نقاطك غير كافية لاستبدال هذه الهدية'}), 400
    
    # خصم النقاط مؤقتاً وإنشاء طلب الاستبدال
    try:
        cursor.execute('''
            UPDATE user_points 
            SET available_points = available_points - ?, 
                spent_points = spent_points + ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (gift_points_cost, gift_points_cost, user_id))
        
        # إنشاء طلب الاستبدال
        cursor.execute('''
            INSERT INTO gift_redemptions (user_id, gift_id, points_spent, status) 
            VALUES (?, ?, ?, 'pending')
        ''', (user_id, gift_id, gift_points_cost))
        
        # إضافة سجل النقاط
        cursor.execute('''
            INSERT INTO points_history 
            (user_id, points, activity_type, activity_description, related_id) 
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, -gift_points_cost, 'gift_redemption', f'استبدال هدية: {gift[1]}', gift_id))
        
        # تقليل المخزون إذا لم يكن لا نهائي
        if gift_stock > 0:
            cursor.execute('UPDATE gifts SET stock_quantity = stock_quantity - 1 WHERE id = ?', (gift_id,))
        
        conn.commit()
        
        # إرسال إشعار للإدارة عبر التليجرام
        try:
            if telegram_bot:
                send_redemption_notification_sync(user_id, gift[1], gift_points_cost)
        except Exception as e:
            print(f"خطأ في إرسال إشعار التليجرام: {e}")
        
        conn.close()
        return jsonify({'success': True, 'message': 'تم إرسال طلب الاستبدال بنجاح'})
        
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': f'خطأ في العملية: {str(e)}'}), 500

# لوحة التحكم الشخصية
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('يجب تسجيل الدخول للوصول لهذه الصفحة', 'error')
        return redirect(url_for('login'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # محلات المستخدم
    cursor.execute('''
        SELECT s.*, c.name as category_name 
        FROM stores s 
        LEFT JOIN categories c ON s.category_id = c.id 
        WHERE s.user_id = ?
        ORDER BY s.created_at DESC
    ''', (session['user_id'],))
    user_stores = cursor.fetchall()

    # الحصول على تاريخ انضمام المستخدم
    cursor.execute('SELECT created_at FROM users WHERE id = ?', (session['user_id'],))
    user_data = cursor.fetchone()

    # استخراج السنة من تاريخ الانضمام
    if user_data and user_data[0]:
        join_year = user_data[0][:4]  # أخذ أول 4 أرقام (السنة)
    else:
        join_year = "2024"

    # إحصائيات المستخدم
    total_ratings = sum(1 for store in user_stores if store[10] and store[10] > 0) if user_stores else 0
    avg_rating = sum(store[10] for store in user_stores if store[10]) / len([s for s in user_stores if s[10]]) if user_stores and any(s[10] for s in user_stores) else 0
    approved_stores = len([s for s in user_stores if s[8] == 1])

    # الحصول على التصنيفات للنموذج
    cursor.execute('SELECT * FROM categories ORDER BY name')
    categories = cursor.fetchall()

    # الحصول على نقاط المستخدم
    points_summary = get_user_points_summary(session['user_id'])

    conn.close()

    return render_template('dashboard.html', 
                         user_stores=user_stores, 
                         join_year=join_year,
                         total_ratings=total_ratings,
                         avg_rating=avg_rating,
                         approved_stores=approved_stores,
                         categories=categories,
                         user_points=points_summary['available_points'])

# صفحة الخدمات الهامة - مع التسجيل الإجباري
@app.route('/important-services')
def important_services():
    # التحقق من تسجيل الدخول
    if 'user_id' not in session:
        flash('يجب تسجيل الدخول لعرض الخدمات الهامة', 'warning')
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # الحصول على جميع الخدمات مع معلومات التصنيف
    cursor.execute('''
        SELECT s.*, sc.name as category_name, sc.description as category_description, 
               sc.icon as category_icon, sc.color as category_color
        FROM important_services s 
        LEFT JOIN service_categories sc ON s.category = sc.name
        ORDER BY 
            CASE 
                WHEN s.category = 'طوارئ' THEN 1
                WHEN s.category = 'صحة' THEN 2
                WHEN s.category = 'أمن' THEN 3
                ELSE 4
            END, s.name
    ''')
    services = cursor.fetchall()

    # تجميع الخدمات حسب الفئة
    services_by_category = {}
    services_by_category_info = {}
    
    for service in services:
        category = service[4] if service[4] else 'أخرى'
        if category not in services_by_category:
            services_by_category[category] = []
            # حفظ معلومات التصنيف
            services_by_category_info[category] = {
                'icon': service[7] if len(service) > 7 and service[7] else 'bi-gear',
                'color': service[8] if len(service) > 8 and service[8] else '#667eea',
                'description': service[6] if len(service) > 6 and service[6] else ''
            }
        services_by_category[category].append(service)

    conn.close()

    return render_template('important_services.html', 
                         services_by_category=services_by_category,
                         services_by_category_info=services_by_category_info)

# صفحة الصيدليات المناوبة - مع التسجيل الإجباري
@app.route('/duty-pharmacies')
def duty_pharmacies():
    # التحقق من تسجيل الدخول
    if 'user_id' not in session:
        flash('يجب تسجيل الدخول لعرض الصيدليات المناوبة', 'warning')
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # استخدام التوقيت الحالي مع إضافة 3 ساعات لتوقيت دمشق
    from datetime import timezone, timedelta
    damascus_tz = timezone(timedelta(hours=3))  # دمشق UTC+3
    damascus_time = datetime.now(damascus_tz)
    
    # تحديد التاريخ بناءً على الساعة 1:30 صباحاً
    if damascus_time.hour < 1 or (damascus_time.hour == 1 and damascus_time.minute < 30):
        # إذا كان الوقت قبل 1:30 صباحاً، استخدم تاريخ اليوم السابق
        display_date = (damascus_time - timedelta(days=1)).date()
    else:
        # إذا كان الوقت بعد 1:30 صباحاً، استخدم تاريخ اليوم الحالي
        display_date = damascus_time.date()
    
    today = display_date.strftime('%Y-%m-%d')

    print(f"التوقيت الحالي في صفحة الصيدليات: {damascus_time}")
    print(f"تاريخ اليوم في صفحة الصيدليات (مع تطبيق قاعدة 1:30 ص): {today}")

    # الحصول على جميع صيدليات اليوم
    cursor.execute('SELECT * FROM duty_pharmacies WHERE duty_date = ? ORDER BY id', (today,))
    today_pharmacies = cursor.fetchall()
    
    # للتوافق مع الكود القديم
    today_pharmacy = today_pharmacies[0] if today_pharmacies else None

    # الحصول على صيدليات الأسبوع القادم
    cursor.execute('''
        SELECT * FROM duty_pharmacies 
        WHERE duty_date >= ? 
        ORDER BY duty_date ASC 
        LIMIT 7
    ''', (today,))
    upcoming_pharmacies_raw = cursor.fetchall()

    # تحويل التواريخ إلى كائنات datetime
    upcoming_pharmacies = []
    for pharmacy in upcoming_pharmacies_raw:
        pharmacy_list = list(pharmacy)
        try:
            if pharmacy[4]:  # duty_date
                pharmacy_list[4] = datetime.strptime(pharmacy[4], '%Y-%m-%d').date()
        except:
            pharmacy_list[4] = None
        upcoming_pharmacies.append(tuple(pharmacy_list))

    conn.close()

    return render_template('duty_pharmacies.html', 
                         today_pharmacy=today_pharmacy,
                         today_pharmacies=today_pharmacies,
                         upcoming_pharmacies=upcoming_pharmacies,
                         damascus_time=damascus_time)

# لوحة الإدارة الرئيسية
@app.route('/admin')
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('ليس لديك صلاحية للوصول لهذه الصفحة', 'error')
        return redirect(url_for('index'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # إحصائيات سريعة
    cursor.execute('SELECT COUNT(*) FROM stores')
    total_stores = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM stores WHERE is_approved = 0')
    pending_stores = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM categories')
    total_categories = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM important_services')
    total_services = cursor.fetchone()[0]

    conn.close()

    stats = {
        'total_stores': total_stores,
        'total_users': total_users,
        'pending_stores': pending_stores,
        'total_categories': total_categories,
        'total_services': total_services
    }

    return render_template('admin_dashboard.html', stats=stats)

# لوحة الإدارة - الصيدليات المناوبة
@app.route('/admin/duty-pharmacies')
def admin_duty_pharmacies():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('ليس لديك صلاحية للوصول لهذه الصفحة', 'error')
        return redirect(url_for('index'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # جميع الصيدليات المناوبة
    cursor.execute('SELECT * FROM duty_pharmacies ORDER BY duty_date DESC')
    pharmacies = cursor.fetchall()

    conn.close()

    return render_template('admin_duty_pharmacies.html', pharmacies=pharmacies)

# الحصول على الصيدليات من تصنيف محدد (API)
@app.route('/api/get-pharmacies-from-category')
def get_pharmacies_from_category():
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({'error': 'غير مصرح'}), 403

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # البحث عن تصنيف الصيدليات
    cursor.execute('SELECT id FROM categories WHERE name LIKE ?', ('%صيدل%',))
    pharmacy_category = cursor.fetchone()

    if not pharmacy_category:
        conn.close()
        return jsonify({'pharmacies': []})

    # الحصول على الصيدليات من هذا التصنيف
    cursor.execute('''
        SELECT name, address, phone 
        FROM stores 
        WHERE category_id = ? AND is_approved = 1
        ORDER BY name
    ''', (pharmacy_category[0],))

    pharmacies = cursor.fetchall()
    conn.close()

    pharmacies_list = []
    for pharmacy in pharmacies:
        pharmacies_list.append({
            'name': pharmacy[0],
            'address': pharmacy[1],
            'phone': pharmacy[2]
        })

    return jsonify({'pharmacies': pharmacies_list})

# إضافة صيدلية مناوبة جديدة
@app.route('/admin/add-duty-pharmacy', methods=['POST'])
def add_duty_pharmacy():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    name = request.form['name']
    address = request.form['address']
    phone = request.form['phone']
    duty_date = request.form['duty_date']

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO duty_pharmacies (name, address, phone, duty_date) 
        VALUES (?, ?, ?, ?)
    ''', (name, address, phone, duty_date))

    conn.commit()
    conn.close()

    flash('تم إضافة الصيدلية المناوبة بنجاح', 'success')
    return redirect(url_for('admin_duty_pharmacies'))

# تحديث صيدلية مناوبة
@app.route('/admin/update-duty-pharmacy/<int:pharmacy_id>', methods=['POST'])
def update_duty_pharmacy(pharmacy_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    name = request.form['name']
    address = request.form['address']
    phone = request.form['phone']
    duty_date = request.form['duty_date']

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE duty_pharmacies 
        SET name = ?, address = ?, phone = ?, duty_date = ? 
        WHERE id = ?
    ''', (name, address, phone, duty_date, pharmacy_id))

    conn.commit()
    conn.close()

    flash('تم تحديث الصيدلية المناوبة بنجاح', 'success')
    return redirect(url_for('admin_duty_pharmacies'))

# حذف صيدلية مناوبة
@app.route('/admin/delete-duty-pharmacy/<int:pharmacy_id>')
def delete_duty_pharmacy(pharmacy_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    cursor.execute('DELETE FROM duty_pharmacies WHERE id = ?', (pharmacy_id,))

    conn.commit()
    conn.close()

    flash('تم حذف الصيدلية المناوبة بنجاح', 'success')
    return redirect(url_for('admin_duty_pharmacies'))

# API للحصول على صيدليات اليوم - مع التسجيل الإجباري
@app.route('/api/today-pharmacies')
def get_today_pharmacies():
    # التحقق من تسجيل الدخول
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'يجب تسجيل الدخول'}), 401
    
    try:
        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()
        
        # استخدام التوقيت الحالي مع إضافة 3 ساعات لتوقيت دمشق
        from datetime import timezone, timedelta
        damascus_tz = timezone(timedelta(hours=3))  # دمشق UTC+3
        damascus_time = datetime.now(damascus_tz)
        
        # تحديد التاريخ بناءً على الساعة 1:30 صباحاً
        if damascus_time.hour < 1 or (damascus_time.hour == 1 and damascus_time.minute < 30):
            # إذا كان الوقت قبل 1:30 صباحاً، استخدم تاريخ اليوم السابق
            display_date = (damascus_time - timedelta(days=1)).date()
        else:
            # إذا كان الوقت بعد 1:30 صباحاً، استخدم تاريخ اليوم الحالي
            display_date = damascus_time.date()
        
        today = display_date.strftime('%Y-%m-%d')
        
        cursor.execute('SELECT * FROM duty_pharmacies WHERE duty_date = ? ORDER BY id', (today,))
        pharmacies = cursor.fetchall()
        
        pharmacies_list = []
        for pharmacy in pharmacies:
            pharmacies_list.append({
                'id': pharmacy[0],
                'name': pharmacy[1],
                'address': pharmacy[2],
                'phone': pharmacy[3],
                'date': pharmacy[4]
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'pharmacies': pharmacies_list,
            'count': len(pharmacies_list),
            'date': today
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# حذف جميع الصيدليات المناوبة
@app.route('/admin/delete-all-duty-pharmacies')
def delete_all_duty_pharmacies():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    cursor.execute('DELETE FROM duty_pharmacies')

    conn.commit()
    conn.close()

    flash('تم حذف جميع الصيدليات المناوبة بنجاح', 'success')
    return redirect(url_for('admin_duty_pharmacies'))

# إدارة المحلات
@app.route('/admin/stores')
def admin_stores():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('ليس لديك صلاحية للوصول لهذه الصفحة', 'error')
        return redirect(url_for('index'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # جميع المحلات
    cursor.execute('''
        SELECT s.id, s.name, s.category_id, s.address, s.phone, s.description, 
               s.image_url, s.user_id, s.is_approved, s.visits_count, s.rating_avg, 
               s.created_at, c.name as category_name, u.full_name as owner_name 
        FROM stores s 
        LEFT JOIN categories c ON s.category_id = c.id 
        LEFT JOIN users u ON s.user_id = u.id
        ORDER BY s.created_at DESC
    ''')
    stores = cursor.fetchall()

    # التصنيفات للإضافة
    cursor.execute('SELECT * FROM categories ORDER BY name')
    categories = cursor.fetchall()

    # المستخدمين للإضافة
    cursor.execute('SELECT id, full_name FROM users WHERE is_active = 1 ORDER BY full_name')
    users = cursor.fetchall()

    conn.close()
    return render_template('admin_stores.html', stores=stores, categories=categories, users=users)

# إضافة محل جديد
@app.route('/admin/add-store', methods=['POST'])
def add_store():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    name = request.form['name']
    category_id = request.form['category_id']
    address = request.form['address']
    phone = request.form.get('phone', '')
    description = request.form.get('description', '')
    user_id = request.form.get('user_id')
    is_approved = 1 if request.form.get('is_approved') else 0

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO stores (name, category_id, address, phone, description, user_id, is_approved) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (name, category_id, address, phone, description, user_id, is_approved))

    conn.commit()
    conn.close()

    # إنشاء نسخة احتياطية تلقائية
    create_auto_backup('add', 'store', name)

    flash('تم إضافة المحل بنجاح', 'success')
    return redirect(url_for('admin_stores'))

# تعديل محل
@app.route('/admin/edit-store/<int:store_id>', methods=['POST'])
def edit_store(store_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    name = request.form['name']
    category_id = request.form['category_id']
    address = request.form['address']
    phone = request.form.get('phone', '')
    description = request.form.get('description', '')
    user_id = request.form.get('user_id')
    is_approved = 1 if request.form.get('is_approved') else 0

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE stores SET name = ?, category_id = ?, address = ?, phone = ?, 
        description = ?, user_id = ?, is_approved = ? WHERE id = ?
    ''', (name, category_id, address, phone, description, user_id, is_approved, store_id))

    conn.commit()
    conn.close()

    # إنشاء نسخة احتياطية تلقائية
    create_auto_backup('edit', 'store', name)

    flash('تم تحديث المحل بنجاح', 'success')
    return redirect(url_for('admin_stores'))

# حذف محل
@app.route('/admin/delete-store/<int:store_id>')
def delete_store(store_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    cursor.execute('DELETE FROM stores WHERE id = ?', (store_id,))
    conn.commit()
    conn.close()

    flash('تم حذف المحل بنجاح', 'success')
    return redirect(url_for('admin_stores'))

# عرض تفاصيل المحل في صفحة منفصلة
@app.route('/admin/store-details/<int:store_id>')
def admin_store_details(store_id):
    if 'user_id' not in session or not session.get('is_admin'):
        flash('ليس لديك صلاحية للوصول لهذه الصفحة', 'error')
        return redirect(url_for('index'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # جلب تفاصيل المحل
    cursor.execute('''
        SELECT s.id, s.name, s.category_id, s.address, s.phone, s.description, 
               s.image_url, s.user_id, s.is_approved, s.visits_count, s.rating_avg, 
               s.search_count, s.created_at, c.name as category_name, u.full_name as owner_name 
        FROM stores s 
        LEFT JOIN categories c ON s.category_id = c.id 
        LEFT JOIN users u ON s.user_id = u.id
        WHERE s.id = ?
    ''', (store_id,))
    store = cursor.fetchone()

    if not store:
        flash('المحل غير موجود', 'error')
        conn.close()
        return redirect(url_for('admin_stores'))

    # التصنيفات للتعديل
    cursor.execute('SELECT * FROM categories ORDER BY name')
    categories = cursor.fetchall()

    # المستخدمين للتعديل
    cursor.execute('SELECT id, full_name FROM users WHERE is_active = 1 ORDER BY full_name')
    users = cursor.fetchall()

    # التقييمات
    cursor.execute('''
        SELECT r.rating, r.created_at, u.full_name 
        FROM ratings r 
        LEFT JOIN users u ON r.user_id = u.id 
        WHERE r.store_id = ? 
        ORDER BY r.created_at DESC
    ''', (store_id,))
    ratings = cursor.fetchall()

    conn.close()
    return render_template('admin_store_details.html', 
                         store=store, 
                         categories=categories, 
                         users=users,
                         ratings=ratings)

# عرض تفاصيل المستخدم في صفحة منفصلة
@app.route('/admin/user-details/<int:user_id>')
def admin_user_details(user_id):
    if 'user_id' not in session or not session.get('is_admin'):
        flash('ليس لديك صلاحية للوصول لهذه الصفحة', 'error')
        return redirect(url_for('index'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # جلب تفاصيل المستخدم
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()

    if not user:
        flash('المستخدم غير موجود', 'error')
        conn.close()
        return redirect(url_for('admin_users'))

    # جلب محلات المستخدم
    cursor.execute('''
        SELECT s.*, c.name as category_name 
        FROM stores s 
        LEFT JOIN categories c ON s.category_id = c.id 
        WHERE s.user_id = ?
        ORDER BY s.created_at DESC
    ''', (user_id,))
    user_stores = cursor.fetchall()

    # إحصائيات المستخدم
    cursor.execute('SELECT COUNT(*) FROM stores WHERE user_id = ? AND is_approved = 1', (user_id,))
    approved_stores_count = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM stores WHERE user_id = ? AND is_approved = 0', (user_id,))
    pending_stores_count = cursor.fetchone()[0]

    conn.close()
    return render_template('admin_user_details.html', 
                         user=user, 
                         user_stores=user_stores,
                         approved_stores_count=approved_stores_count,
                         pending_stores_count=pending_stores_count)

# عرض تفاصيل التصنيف في صفحة منفصلة
@app.route('/admin/category-details/<int:category_id>')
def admin_category_details(category_id):
    if 'user_id' not in session or not session.get('is_admin'):
        flash('ليس لديك صلاحية للوصول لهذه الصفحة', 'error')
        return redirect(url_for('index'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # جلب تفاصيل التصنيف
    cursor.execute('SELECT * FROM categories WHERE id = ?', (category_id,))
    category = cursor.fetchone()

    if not category:
        flash('التصنيف غير موجود', 'error')
        conn.close()
        return redirect(url_for('admin_categories'))

    # جلب المحلات في هذا التصنيف
    cursor.execute('''
        SELECT s.*, u.full_name as owner_name 
        FROM stores s 
        LEFT JOIN users u ON s.user_id = u.id 
        WHERE s.category_id = ?
        ORDER BY s.created_at DESC
    ''', (category_id,))
    category_stores = cursor.fetchall()

    # إحصائيات التصنيف
    cursor.execute('SELECT COUNT(*) FROM stores WHERE category_id = ? AND is_approved = 1', (category_id,))
    approved_stores_count = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM stores WHERE category_id = ? AND is_approved = 0', (category_id,))
    pending_stores_count = cursor.fetchone()[0]

    conn.close()
    return render_template('admin_category_details.html', 
                         category=category, 
                         category_stores=category_stores,
                         approved_stores_count=approved_stores_count,
                         pending_stores_count=pending_stores_count)

# عرض تفاصيل الخدمة في صفحة منفصلة
@app.route('/admin/service-details/<int:service_id>')
def admin_service_details(service_id):
    if 'user_id' not in session or not session.get('is_admin'):
        flash('ليس لديك صلاحية للوصول لهذه الصفحة', 'error')
        return redirect(url_for('index'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # جلب تفاصيل الخدمة
    cursor.execute('''
        SELECT s.*, sc.name as category_name, sc.color, sc.icon, sc.description as category_description
        FROM important_services s 
        LEFT JOIN service_categories sc ON s.category = sc.name
        WHERE s.id = ?
    ''', (service_id,))
    service = cursor.fetchone()

    if not service:
        flash('الخدمة غير موجودة', 'error')
        conn.close()
        return redirect(url_for('admin_services'))

    # جلب تصنيفات الخدمات للتعديل
    cursor.execute('SELECT * FROM service_categories ORDER BY name')
    service_categories = cursor.fetchall()

    # جلب خدمات أخرى في نفس التصنيف
    cursor.execute('''
        SELECT * FROM important_services 
        WHERE category = ? AND id != ?
        ORDER BY name
    ''', (service[4], service_id))
    related_services = cursor.fetchall()

    conn.close()
    return render_template('admin_service_details.html', 
                         service=service, 
                         service_categories=service_categories,
                         related_services=related_services)

# عرض تفاصيل رسالة الشريط المتحرك في صفحة منفصلة
@app.route('/admin/ticker-details/<int:ticker_id>')
def admin_ticker_details(ticker_id):
    if 'user_id' not in session or not session.get('is_admin'):
        flash('ليس لديك صلاحية للوصول لهذه الصفحة', 'error')
        return redirect(url_for('index'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # التأكد من وجود عمود pages
    try:
        cursor.execute('ALTER TABLE ticker_messages ADD COLUMN pages TEXT DEFAULT "all"')
        conn.commit()
    except:
        pass

    # جلب تفاصيل الرسالة
    cursor.execute('''
        SELECT id, message, type, priority, is_active, direction, speed, 
               background_color, text_color, font_size, created_at, pages 
        FROM ticker_messages WHERE id = ?
    ''', (ticker_id,))
    ticker = cursor.fetchone()

    if not ticker:
        flash('الرسالة غير موجودة', 'error')
        conn.close()
        return redirect(url_for('admin_ticker'))

    conn.close()
    return render_template('admin_ticker_details.html', ticker=ticker)

# عرض تفاصيل الإشعار في صفحة منفصلة
@app.route('/admin/notification-details/<int:notification_id>')
def admin_notification_details(notification_id):
    if 'user_id' not in session or not session.get('is_admin'):
        flash('ليس لديك صلاحية للوصول لهذه الصفحة', 'error')
        return redirect(url_for('index'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # جلب تفاصيل الإشعار
    cursor.execute('SELECT * FROM notifications WHERE id = ?', (notification_id,))
    notification = cursor.fetchone()

    if not notification:
        flash('الإشعار غير موجود', 'error')
        conn.close()
        return redirect(url_for('admin_notifications'))

    conn.close()
    return render_template('admin_notification_details.html', notification=notification)

# عرض تفاصيل تصنيف الخدمة الهامة في صفحة منفصلة
@app.route('/admin/service-category-details/<int:category_id>')
def admin_service_category_details(category_id):
    if 'user_id' not in session or not session.get('is_admin'):
        flash('ليس لديك صلاحية للوصول لهذه الصفحة', 'error')
        return redirect(url_for('index'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # جلب تفاصيل التصنيف
    cursor.execute('SELECT * FROM service_categories WHERE id = ?', (category_id,))
    category = cursor.fetchone()

    if not category:
        flash('التصنيف غير موجود', 'error')
        conn.close()
        return redirect(url_for('admin_services'))

    # جلب الخدمات في هذا التصنيف
    cursor.execute('''
        SELECT * FROM important_services 
        WHERE category = ?
        ORDER BY name
    ''', (category[1],))
    category_services = cursor.fetchall()

    # إحصائيات التصنيف
    cursor.execute('SELECT COUNT(*) FROM important_services WHERE category = ?', (category[1],))
    services_count = cursor.fetchone()[0]

    conn.close()
    return render_template('admin_service_category_details.html', 
                         category=category, 
                         category_services=category_services,
                         services_count=services_count)

# تفعيل/إلغاء تفعيل محل
@app.route('/admin/toggle-store/<int:store_id>')
def toggle_store(store_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    cursor.execute('SELECT is_approved FROM stores WHERE id = ?', (store_id,))
    current_status = cursor.fetchone()[0]
    new_status = 0 if current_status else 1

    cursor.execute('UPDATE stores SET is_approved = ? WHERE id = ?', (new_status, store_id))
    conn.commit()
    conn.close()

    status_text = 'تم تفعيل' if new_status else 'تم إلغاء تفعيل'
    flash(f'{status_text} المحل بنجاح', 'success')
    return redirect(url_for('admin_stores'))

# API للحصول على جميع المستخدمين
@app.route('/api/get-all-users')
def get_all_users():
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({'error': 'غير مصرح'}), 403
    
    try:
        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT u.id, u.full_name, u.phone, COALESCE(up.total_points, 0) as points
            FROM users u 
            LEFT JOIN user_points up ON u.id = up.user_id
            WHERE u.is_active = 1
            ORDER BY u.full_name
        ''')
        
        users_data = cursor.fetchall()
        conn.close()
        
        users = []
        for user in users_data:
            users.append({
                'id': user[0],
                'name': user[1],
                'phone': user[2],
                'points': user[3]
            })
        
        return jsonify(users)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API للحصول على التوقيت الحالي بتوقيت دمشق
@app.route('/api/current-time')
def get_current_time():
    try:
        # استخدام التوقيت الحالي مع إضافة 3 ساعات لتوقيت دمشق
        from datetime import timezone, timedelta
        damascus_tz = timezone(timedelta(hours=3))  # دمشق UTC+3
        damascus_time = datetime.now(damascus_tz)
        
        # تنسيق التاريخ والوقت بالعربية
        arabic_days = ['الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت', 'الأحد']
        arabic_months = ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو', 'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر']
        
        day_name = arabic_days[damascus_time.weekday()]
            
        day = damascus_time.day
        month = arabic_months[damascus_time.month - 1]
        year = damascus_time.year
        hours = damascus_time.hour
        minutes = damascus_time.minute
        ampm = 'مساءً' if hours >= 12 else 'صباحاً'
        display_hours = hours % 12 if hours % 12 != 0 else 12
        
        formatted_time = f"{day_name}, {day} {month} {year} - {display_hours}:{minutes:02d} {ampm}"
        
        return jsonify({
            'datetime': formatted_time,
            'timestamp': damascus_time.isoformat(),
            'timezone': 'Damascus UTC+3'
        })
    except Exception as e:
        print(f"خطأ في الحصول على التوقيت: {e}")
        return jsonify({'error': 'خطأ في الحصول على التوقيت'}), 500


    conn.close()

    status_text = 'تم تفعيل' if new_status else 'تم إلغاء تفعيل'
    flash(f'{status_text} المحل بنجاح', 'success')
    return redirect(url_for('admin_stores'))

# موافقة على محل
@app.route('/admin/approve-store/<int:store_id>')
def approve_store(store_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # الحصول على معلومات المحل والمالك
    cursor.execute('SELECT name, user_id FROM stores WHERE id = ?', (store_id,))
    store = cursor.fetchone()
    
    if not store:
        flash('المحل غير موجود', 'error')
        return redirect(url_for('admin_stores'))
    
    store_name = store[0]
    store_owner_id = store[1]

    cursor.execute('UPDATE stores SET is_approved = 1 WHERE id = ?', (store_id,))
    conn.commit()
    conn.close()

    # منح النقاط لصاحب المحل
    if store_owner_id:
        settings = get_points_settings()
        store_points = settings.get('points_add_store', 10)
        add_points(store_owner_id, store_points, 'store_approved', f'الموافقة على محل: {store_name}', store_id)

    # إنشاء نسخة احتياطية تلقائية
    create_auto_backup('edit', 'store', f'{store_name} (موافقة)')

    settings = get_points_settings()
    points_awarded = settings.get('points_add_store', 10)
    flash(f'تم الموافقة على المحل بنجاح ومنح {points_awarded} نقطة لصاحب المحل', 'success')
    return redirect(url_for('admin_stores'))

# رفض محل
@app.route('/admin/reject-store/<int:store_id>')
def reject_store(store_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    cursor.execute('DELETE FROM stores WHERE id = ?', (store_id,))
    conn.commit()
    conn.close()

    flash('تم رفض المحل وحذفه', 'success')
    return redirect(url_for('admin_stores'))

# إدارة المستخدمين
@app.route('/admin/users')
def admin_users():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('ليس لديك صلاحية للوصول لهذه الصفحة', 'error')
        return redirect(url_for('index'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
    users = cursor.fetchall()

    conn.close()
    return render_template('admin_users.html', users=users)

# تفعيل/إلغاء تفعيل مستخدم
@app.route('/admin/toggle-user/<int:user_id>')
def toggle_user(user_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    cursor.execute('SELECT is_active FROM users WHERE id = ?', (user_id,))
    current_status = cursor.fetchone()[0]
    new_status = 0 if current_status else 1

    cursor.execute('UPDATE users SET is_active = ? WHERE id = ?', (new_status, user_id))
    conn.commit()
    conn.close()

    status_text = 'تم تفعيل' if new_status else 'تم إلغاء تفعيل'
    flash(f'{status_text} المستخدم بنجاح', 'success')
    return redirect(url_for('admin_users'))

# إضافة مستخدم جديد
@app.route('/admin/add-user', methods=['POST'])
def add_user():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    full_name = request.form['full_name']
    phone = request.form['phone']
    password = request.form['password']
    is_admin = 1 if request.form.get('is_admin') else 0
    is_active = 1 if request.form.get('is_active') else 0

    # التحقق من صحة رقم الهاتف
    if not validate_syrian_phone(phone):
        flash('رقم الهاتف يجب أن يكون سوري ويبدأ بـ 09 ويتكون من 10 أرقام', 'error')
        return redirect(url_for('admin_users'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # التحقق من عدم وجود المستخدم
    cursor.execute('SELECT id FROM users WHERE phone = ?', (phone,))
    if cursor.fetchone():
        flash('رقم الهاتف مسجل مسبقاً', 'error')
        conn.close()
        return redirect(url_for('admin_users'))

    password_hash = generate_password_hash(password)
    cursor.execute('''
        INSERT INTO users (full_name, phone, password_hash, is_admin, is_active) 
        VALUES (?, ?, ?, ?, ?)
    ''', (full_name, phone, password_hash, is_admin, is_active))

    conn.commit()
    conn.close()

    # إنشاء نسخة احتياطية تلقائية
    create_auto_backup('add', 'user', full_name)

    flash('تم إضافة المستخدم بنجاح', 'success')
    return redirect(url_for('admin_users'))

# تعديل مستخدم
@app.route('/admin/edit-user/<int:user_id>', methods=['POST'])
def edit_user(user_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    full_name = request.form['full_name']
    phone = request.form['phone']
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    is_admin = 1 if request.form.get('is_admin') else 0
    is_active = 1 if request.form.get('is_active') else 0

    # التحقق من تطابق كلمة المرور
    if new_password and new_password != confirm_password:
        flash('كلمة المرور الجديدة غير متطابقة', 'error')
        return redirect(url_for('admin_user_details', user_id=user_id))

    # التحقق من صحة رقم الهاتف
    if not validate_syrian_phone(phone):
        flash('رقم الهاتف يجب أن يكون سوري ويبدأ بـ 09 ويتكون من 10 أرقام', 'error')
        return redirect(url_for('admin_user_details', user_id=user_id))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # التحقق من عدم وجود رقم الهاتف لمستخدم آخر
    cursor.execute('SELECT id FROM users WHERE phone = ? AND id != ?', (phone, user_id))
    if cursor.fetchone():
        flash('رقم الهاتف مسجل لمستخدم آخر', 'error')
        conn.close()
        return redirect(url_for('admin_user_details', user_id=user_id))

    # تحديث البيانات مع أو بدون كلمة المرور
    if new_password and new_password.strip():
        password_hash = generate_password_hash(new_password)
        cursor.execute('''
            UPDATE users SET full_name = ?, phone = ?, password_hash = ?, is_admin = ?, is_active = ? 
            WHERE id = ?
        ''', (full_name, phone, password_hash, is_admin, is_active, user_id))
        flash('تم تحديث المستخدم وكلمة المرور بنجاح', 'success')
    else:
        cursor.execute('''
            UPDATE users SET full_name = ?, phone = ?, is_admin = ?, is_active = ? 
            WHERE id = ?
        ''', (full_name, phone, is_admin, is_active, user_id))
        flash('تم تحديث المستخدم بنجاح', 'success')

    conn.commit()
    conn.close()

    # إنشاء نسخة احتياطية تلقائية
    create_auto_backup('edit', 'user', full_name)

    return redirect(url_for('admin_user_details', user_id=user_id))

# حذف مستخدم
@app.route('/admin/delete-user/<int:user_id>')
def delete_user(user_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    if user_id == session['user_id']:
        flash('لا يمكنك حذف حسابك الحالي', 'error')
        return redirect(url_for('admin_users'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()

    flash('تم حذف المستخدم بنجاح', 'success')
    return redirect(url_for('admin_users'))

# إدارة التصنيفات
@app.route('/admin/categories')
def admin_categories():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('ليس لديك صلاحية للوصول لهذه الصفحة', 'error')
        return redirect(url_for('index'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM categories ORDER BY id')
    categories = cursor.fetchall()

    conn.close()
    return render_template('admin_categories.html', categories=categories)

# إضافة تصنيف جديد
@app.route('/admin/add-category', methods=['POST'])
def add_category():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    name = request.form['name']
    description = request.form['description']

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    cursor.execute('INSERT INTO categories (name, description) VALUES (?, ?)', (name, description))
    conn.commit()
    conn.close()

    flash('تم إضافة التصنيف بنجاح', 'success')
    return redirect(url_for('admin_categories'))

# تحديث تصنيف
@app.route('/admin/update-category/<int:category_id>', methods=['POST'])
def update_category(category_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    name = request.form['name']
    description = request.form['description']

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    cursor.execute('UPDATE categories SET name = ?, description = ? WHERE id = ?', 
                  (name, description, category_id))
    conn.commit()
    conn.close()

    flash('تم تحديث التصنيف بنجاح', 'success')
    return redirect(url_for('admin_categories'))

# حذف تصنيف
@app.route('/admin/delete-category/<int:category_id>')
def delete_category(category_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    cursor.execute('DELETE FROM categories WHERE id = ?', (category_id,))
    conn.commit()
    conn.close()

    flash('تم حذف التصنيف بنجاح', 'success')
    return redirect(url_for('admin_categories'))

# حذف جميع التصنيفات
@app.route('/admin/delete-all-categories')
def delete_all_categories():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    cursor.execute('DELETE FROM categories')
    conn.commit()
    conn.close()

    flash('تم حذف جميع التصنيفات بنجاح', 'success')
    return redirect(url_for('admin_categories'))

# إدارة الخدمات الهامة
@app.route('/admin/services')
def admin_services():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('ليس لديك صلاحية للوصول لهذه الصفحة', 'error')
        return redirect(url_for('index'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT s.*, sc.name as category_name, sc.color, sc.icon
        FROM important_services s 
        LEFT JOIN service_categories sc ON s.category = sc.name
        ORDER BY s.category, s.name
    ''')
    services = cursor.fetchall()

    cursor.execute('SELECT * FROM service_categories ORDER BY name')
    service_categories = cursor.fetchall()

    conn.close()
    return render_template('admin_services.html', services=services, service_categories=service_categories)

# إضافة تصنيف خدمة جديد
@app.route('/admin/add-service-category', methods=['POST'])
def add_service_category():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    name = request.form['name']
    description = request.form.get('description', '')
    icon = request.form.get('icon', 'bi-gear')
    color = request.form.get('color', '#007bff')

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO service_categories (name, description, icon, color) 
            VALUES (?, ?, ?, ?)
        ''', (name, description, icon, color))
        conn.commit()
        flash('تم إضافة التصنيف بنجاح', 'success')
    except sqlite3.IntegrityError:
        flash('اسم التصنيف موجود مسبقاً', 'error')
    
    conn.close()
    return redirect(url_for('admin_services'))

# تعديل تصنيف خدمة
@app.route('/admin/edit-service-category/<int:category_id>', methods=['POST'])
def edit_service_category(category_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    new_name = request.form['name']
    description = request.form.get('description', '')
    icon = request.form.get('icon', 'bi-gear')
    color = request.form.get('color', '#007bff')

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # الحصول على الاسم القديم للتصنيف
    cursor.execute('SELECT name FROM service_categories WHERE id = ?', (category_id,))
    old_category = cursor.fetchone()
    
    if old_category:
        old_name = old_category[0]
        
        # تحديث التصنيف
        cursor.execute('''
            UPDATE service_categories 
            SET name = ?, description = ?, icon = ?, color = ? 
            WHERE id = ?
        ''', (new_name, description, icon, color, category_id))

        # تحديث جميع الخدمات التي تستخدم هذا التصنيف
        cursor.execute('''
            UPDATE important_services 
            SET category = ? 
            WHERE category = ?
        ''', (new_name, old_name))

        # عدد الخدمات المحدثة
        updated_services_count = cursor.rowcount

        conn.commit()
        
        if updated_services_count > 0:
            flash(f'تم تحديث التصنيف بنجاح وتم تحديث {updated_services_count} خدمة مرتبطة به', 'success')
        else:
            flash('تم تحديث التصنيف بنجاح', 'success')
    else:
        flash('التصنيف غير موجود', 'error')

    conn.close()
    return redirect(url_for('admin_services'))

# حذف تصنيف خدمة
@app.route('/admin/delete-service-category/<int:category_id>')
def delete_service_category(category_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # التحقق من وجود خدمات تستخدم هذا التصنيف
    cursor.execute('SELECT name FROM service_categories WHERE id = ?', (category_id,))
    category = cursor.fetchone()
    
    if category:
        cursor.execute('SELECT COUNT(*) FROM important_services WHERE category = ?', (category[0],))
        services_count = cursor.fetchone()[0]
        
        if services_count > 0:
            flash(f'لا يمكن حذف التصنيف لأنه يحتوي على {services_count} خدمة', 'error')
        else:
            cursor.execute('DELETE FROM service_categories WHERE id = ?', (category_id,))
            conn.commit()
            flash('تم حذف التصنيف بنجاح', 'success')

    conn.close()
    return redirect(url_for('admin_services'))

# إضافة خدمة جديدة
@app.route('/admin/add-service', methods=['POST'])
def add_service():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    name = request.form['name']
    phone = request.form['phone']
    description = request.form['description']
    category = request.form['category']

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO important_services (name, phone, description, category) 
        VALUES (?, ?, ?, ?)
    ''', (name, phone, description, category))
    conn.commit()
    conn.close()

    flash('تم إضافة الخدمة بنجاح', 'success')
    return redirect(url_for('admin_services'))

# تعديل خدمة
@app.route('/admin/edit-service/<int:service_id>', methods=['POST'])
def edit_service(service_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    name = request.form['name']
    phone = request.form['phone']
    description = request.form['description']
    category = request.form['category']

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE important_services SET name = ?, phone = ?, description = ?, category = ? 
        WHERE id = ?
    ''', (name, phone, description, category, service_id))

    conn.commit()
    conn.close()

    flash('تم تحديث الخدمة بنجاح', 'success')
    return redirect(url_for('admin_services'))

# حذف خدمة
@app.route('/admin/delete-service/<int:service_id>')
def delete_service(service_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    cursor.execute('DELETE FROM important_services WHERE id = ?', (service_id,))
    conn.commit()
    conn.close()

    flash('تم حذف الخدمة بنجاح', 'success')
    return redirect(url_for('admin_services'))

# إدارة النقاط والهدايا
@app.route('/admin/points')
def admin_points():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('ليس لديك صلاحية للوصول لهذه الصفحة', 'error')
        return redirect(url_for('index'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # إعدادات النقاط
    cursor.execute('SELECT * FROM points_settings ORDER BY setting_key')
    points_settings = cursor.fetchall()

    # الهدايا
    cursor.execute('SELECT * FROM gifts ORDER BY created_at DESC')
    gifts = cursor.fetchall()

    # طلبات الاستبدال
    cursor.execute('''
        SELECT gr.*, u.full_name as user_name, g.name as gift_name
        FROM gift_redemptions gr
        LEFT JOIN users u ON gr.user_id = u.id
        LEFT JOIN gifts g ON gr.gift_id = g.id
        ORDER BY gr.requested_at DESC
        LIMIT 50
    ''')
    redemptions = cursor.fetchall()

    # إحصائيات النقاط
    cursor.execute('SELECT COUNT(*) FROM user_points WHERE total_points > 0')
    active_users = cursor.fetchone()[0]

    cursor.execute('SELECT SUM(total_points) FROM user_points')
    total_points_issued = cursor.fetchone()[0] or 0

    cursor.execute('SELECT SUM(spent_points) FROM user_points')
    total_points_spent = cursor.fetchone()[0] or 0

    cursor.execute('SELECT COUNT(*) FROM gift_redemptions WHERE status = "pending"')
    pending_redemptions = cursor.fetchone()[0]

    conn.close()

    stats = {
        'active_users': active_users,
        'total_points_issued': total_points_issued,
        'total_points_spent': total_points_spent,
        'pending_redemptions': pending_redemptions
    }

    return render_template('admin_points.html', 
                         points_settings=points_settings,
                         gifts=gifts,
                         redemptions=redemptions,
                         stats=stats)

# صفحة إضافة هدية جديدة
@app.route('/admin/add-gift-page')
def admin_add_gift_page():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('ليس لديك صلاحية للوصول لهذه الصفحة', 'error')
        return redirect(url_for('index'))
    
    # إضافة الإحصائيات المطلوبة للقالب
    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # إحصائيات سريعة
    cursor.execute('SELECT COUNT(*) FROM stores')
    total_stores = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM stores WHERE is_approved = 0')
    pending_stores = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM categories')
    total_categories = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM important_services')
    total_services = cursor.fetchone()[0]

    conn.close()

    stats = {
        'total_stores': total_stores,
        'total_users': total_users,
        'pending_stores': pending_stores,
        'total_categories': total_categories,
        'total_services': total_services
    }
    
    return render_template('admin_add_gift.html', stats=stats)

# تحديث إعدادات النقاط
@app.route('/admin/update-points-settings', methods=['POST'])
def update_points_settings():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))
    
    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()
    
    for key, value in request.form.items():
        cursor.execute('UPDATE points_settings SET setting_value = ? WHERE setting_key = ?', 
                      (int(value), key))
    
    conn.commit()
    conn.close()
    
    flash('تم تحديث إعدادات النقاط بنجاح', 'success')
    return redirect(url_for('admin_points'))

# إضافة هدية جديدة
@app.route('/admin/add-gift', methods=['POST'])
def add_gift():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))
    
    name = request.form['name']
    description = request.form.get('description', '')
    points_cost = int(request.form['points_cost'])
    stock_quantity = int(request.form.get('stock_quantity', -1))
    category = request.form.get('category', 'عام')
    image_url = request.form.get('image_url', '')
    is_active = 1 if request.form.get('is_active') else 0
    
    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO gifts (name, description, points_cost, stock_quantity, category, image_url, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (name, description, points_cost, stock_quantity, category, image_url, is_active))
    
    conn.commit()
    conn.close()
    
    flash('تم إضافة الهدية بنجاح', 'success')
    return redirect(url_for('admin_points'))

# تعديل هدية
@app.route('/admin/edit-gift/<int:gift_id>', methods=['POST'])
def edit_gift(gift_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))
    
    name = request.form['name']
    description = request.form.get('description', '')
    points_cost = int(request.form['points_cost'])
    stock_quantity = int(request.form.get('stock_quantity', -1))
    category = request.form.get('category', 'عام')
    is_active = 1 if request.form.get('is_active') else 0
    
    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE gifts 
        SET name = ?, description = ?, points_cost = ?, stock_quantity = ?, 
            category = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (name, description, points_cost, stock_quantity, category, is_active, gift_id))
    
    conn.commit()
    conn.close()
    
    flash('تم تحديث الهدية بنجاح', 'success')
    return redirect(url_for('admin_points'))

# عرض تفاصيل الهدية في صفحة منفصلة
@app.route('/admin/gift-details/<int:gift_id>')
def admin_gift_details(gift_id):
    if 'user_id' not in session or not session.get('is_admin'):
        flash('ليس لديك صلاحية للوصول لهذه الصفحة', 'error')
        return redirect(url_for('index'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # جلب تفاصيل الهدية
    cursor.execute('SELECT * FROM gifts WHERE id = ?', (gift_id,))
    gift = cursor.fetchone()

    if not gift:
        flash('الهدية غير موجودة', 'error')
        conn.close()
        return redirect(url_for('admin_points'))

    # جلب طلبات الاستبدال للهدية
    cursor.execute('''
        SELECT gr.*, u.full_name as user_name
        FROM gift_redemptions gr
        LEFT JOIN users u ON gr.user_id = u.id
        WHERE gr.gift_id = ?
        ORDER BY gr.requested_at DESC
    ''', (gift_id,))
    redemptions = cursor.fetchall()

    # إحصائيات الهدية
    cursor.execute('SELECT COUNT(*) FROM gift_redemptions WHERE gift_id = ?', (gift_id,))
    total_redemptions = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM gift_redemptions WHERE gift_id = ? AND status = "pending"', (gift_id,))
    pending_redemptions = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM gift_redemptions WHERE gift_id = ? AND status = "approved"', (gift_id,))
    approved_redemptions = cursor.fetchone()[0]

    # إحصائيات سريعة للوحة الإدارة
    cursor.execute('SELECT COUNT(*) FROM stores')
    total_stores = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM stores WHERE is_approved = 0')
    pending_stores = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM categories')
    total_categories = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM important_services')
    total_services = cursor.fetchone()[0]

    stats = {
        'total_stores': total_stores,
        'total_users': total_users,
        'pending_stores': pending_stores,
        'total_categories': total_categories,
        'total_services': total_services
    }

    conn.close()
    return render_template('admin_gift_details.html', 
                         gift=gift, 
                         redemptions=redemptions,
                         total_redemptions=total_redemptions,
                         pending_redemptions=pending_redemptions,
                         approved_redemptions=approved_redemptions,
                         stats=stats)

# حذف هدية
@app.route('/admin/delete-gift/<int:gift_id>')
def delete_gift(gift_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))
    
    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM gifts WHERE id = ?', (gift_id,))
    conn.commit()
    conn.close()
    
    flash('تم حذف الهدية بنجاح', 'success')
    return redirect(url_for('admin_points'))

# الموافقة على طلب استبدال
@app.route('/admin/approve-redemption/<int:redemption_id>')
def approve_redemption(redemption_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))
    
    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()
    
    # تحديث حالة الطلب
    cursor.execute('''
        UPDATE gift_redemptions 
        SET status = 'approved', processed_at = CURRENT_TIMESTAMP, processed_by = ?
        WHERE id = ?
    ''', (session['user_id'], redemption_id))
    
    conn.commit()
    conn.close()
    
    flash('تم الموافقة على طلب الاستبدال', 'success')
    return redirect(url_for('admin_points'))

# رفض طلب استبدال
@app.route('/admin/reject-redemption/<int:redemption_id>')
def reject_redemption(redemption_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))
    
    reason = request.args.get('reason', '')
    
    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()
    
    # الحصول على معلومات الطلب
    cursor.execute('SELECT user_id, gift_id, points_spent FROM gift_redemptions WHERE id = ?', (redemption_id,))
    redemption = cursor.fetchone()
    
    if redemption:
        user_id, gift_id, points_spent = redemption
        
        # إعادة النقاط للمستخدم
        cursor.execute('''
            UPDATE user_points 
            SET available_points = available_points + ?, 
                spent_points = spent_points - ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (points_spent, points_spent, user_id))
        
        # إعادة المخزون
        cursor.execute('SELECT stock_quantity FROM gifts WHERE id = ?', (gift_id,))
        gift = cursor.fetchone()
        if gift and gift[0] > 0:
            cursor.execute('UPDATE gifts SET stock_quantity = stock_quantity + 1 WHERE id = ?', (gift_id,))
        
        # تحديث حالة الطلب
        cursor.execute('''
            UPDATE gift_redemptions 
            SET status = 'rejected', admin_notes = ?, processed_at = CURRENT_TIMESTAMP, processed_by = ?
            WHERE id = ?
        ''', (reason, session['user_id'], redemption_id))
        
        # إضافة سجل إعادة النقاط
        cursor.execute('''
            INSERT INTO points_history 
            (user_id, points, activity_type, activity_description, related_id) 
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, points_spent, 'redemption_refund', f'إعادة نقاط استبدال مرفوض: {reason}', redemption_id))
    
    conn.commit()
    conn.close()
    
    flash('تم رفض طلب الاستبدال وإعادة النقاط', 'success')
    return redirect(url_for('admin_points'))

# إدارة نقاط المستخدمين - صفحة إدارة نقاط مستخدم محدد
@app.route('/admin/manage-user-points/<int:user_id>')
def admin_manage_user_points(user_id):
    if 'user_id' not in session or not session.get('is_admin'):
        flash('ليس لديك صلاحية للوصول لهذه الصفحة', 'error')
        return redirect(url_for('index'))
    
    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()
    
    # الحصول على معلومات المستخدم
    cursor.execute('SELECT id, full_name, phone FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    
    if not user:
        flash('المستخدم غير موجود', 'error')
        return redirect(url_for('admin_users'))
    
    # الحصول على نقاط المستخدم
    points_summary = get_user_points_summary(user_id)
    
    conn.close()
    
    return render_template('admin_manage_user_points.html', 
                         user=user, 
                         points_summary=points_summary)

# إضافة نقاط لمستخدم محدد
@app.route('/admin/add-user-points/<int:user_id>', methods=['POST'])
def admin_add_user_points(user_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))
    
    try:
        points = int(request.form['points'])
        reason = request.form.get('reason', 'إضافة نقاط من قبل الإدارة')
        
        if points <= 0:
            flash('عدد النقاط يجب أن يكون أكبر من صفر', 'error')
            return redirect(url_for('admin_manage_user_points', user_id=user_id))
        
        # إضافة النقاط
        success = add_points(user_id, points, 'admin_add', reason)
        
        if success:
            flash(f'تم إضافة {points} نقطة بنجاح', 'success')
        else:
            flash('خطأ في إضافة النقاط', 'error')
            
    except ValueError:
        flash('عدد النقاط يجب أن يكون رقماً صحيحاً', 'error')
    except Exception as e:
        flash(f'خطأ: {str(e)}', 'error')
    
    return redirect(url_for('admin_manage_user_points', user_id=user_id))

# خصم نقاط من مستخدم محدد
@app.route('/admin/deduct-user-points/<int:user_id>', methods=['POST'])
def admin_deduct_user_points(user_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))
    
    try:
        points = int(request.form['points'])
        reason = request.form.get('reason', 'خصم نقاط من قبل الإدارة')
        
        if points <= 0:
            flash('عدد النقاط يجب أن يكون أكبر من صفر', 'error')
            return redirect(url_for('admin_manage_user_points', user_id=user_id))
        
        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()
        
        # التحقق من وجود نقاط كافية
        cursor.execute('SELECT available_points FROM user_points WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        
        if not result:
            initialize_user_points(user_id)
            available_points = 0
        else:
            available_points = result[0]
        
        if available_points < points:
            flash(f'المستخدم لديه {available_points} نقطة فقط، لا يمكن خصم {points} نقطة', 'error')
            conn.close()
            return redirect(url_for('admin_manage_user_points', user_id=user_id))
        
        # خصم النقاط
        cursor.execute('''
            UPDATE user_points 
            SET available_points = available_points - ?, 
                spent_points = spent_points + ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (points, points, user_id))
        
        # إضافة سجل النقاط
        cursor.execute('''
            INSERT INTO points_history 
            (user_id, points, activity_type, activity_description) 
            VALUES (?, ?, ?, ?)
        ''', (user_id, -points, 'admin_deduct', reason))
        
        # تحديث النقاط في جدول المستخدمين
        cursor.execute('''
            UPDATE users SET total_points = (
                SELECT total_points FROM user_points WHERE user_id = ?
            ) WHERE id = ?
        ''', (user_id, user_id))
        
        conn.commit()
        conn.close()
        
        flash(f'تم خصم {points} نقطة بنجاح', 'success')
        
    except ValueError:
        flash('عدد النقاط يجب أن يكون رقماً صحيحاً', 'error')
    except Exception as e:
        flash(f'خطأ: {str(e)}', 'error')
    
    return redirect(url_for('admin_manage_user_points', user_id=user_id))

# تعديل إجمالي نقاط المستخدم
@app.route('/admin/set-user-points/<int:user_id>', methods=['POST'])
def admin_set_user_points(user_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))
    
    try:
        new_total = int(request.form['total_points'])
        new_available = int(request.form['available_points'])
        reason = request.form.get('reason', 'تعديل النقاط من قبل الإدارة')
        
        if new_total < 0 or new_available < 0:
            flash('النقاط لا يمكن أن تكون أرقاماً سالبة', 'error')
            return redirect(url_for('admin_manage_user_points', user_id=user_id))
        
        if new_available > new_total:
            flash('النقاط المتاحة لا يمكن أن تكون أكثر من إجمالي النقاط', 'error')
            return redirect(url_for('admin_manage_user_points', user_id=user_id))
        
        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()
        
        # تهيئة نقاط المستخدم إذا لم تكن موجودة
        initialize_user_points(user_id)
        
        # الحصول على النقاط الحالية
        cursor.execute('SELECT total_points, available_points FROM user_points WHERE user_id = ?', (user_id,))
        current = cursor.fetchone()
        old_total = current[0] if current else 0
        old_available = current[1] if current else 0
        
        # حساب النقاط المستخدمة
        spent_points = new_total - new_available
        
        # تحديث النقاط
        cursor.execute('''
            UPDATE user_points 
            SET total_points = ?, 
                available_points = ?, 
                spent_points = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (new_total, new_available, spent_points, user_id))
        
        # إضافة سجل التعديل
        points_change = new_total - old_total
        if points_change != 0:
            cursor.execute('''
                INSERT INTO points_history 
                (user_id, points, activity_type, activity_description) 
                VALUES (?, ?, ?, ?)
            ''', (user_id, points_change, 'admin_set', f'{reason} - تعديل من {old_total} إلى {new_total} نقطة'))
        
        # تحديث النقاط في جدول المستخدمين
        cursor.execute('UPDATE users SET total_points = ? WHERE id = ?', (new_total, user_id))
        
        conn.commit()
        conn.close()
        
        flash(f'تم تعديل النقاط بنجاح - الإجمالي: {new_total}، المتاح: {new_available}', 'success')
        
    except ValueError:
        flash('النقاط يجب أن تكون أرقاماً صحيحة', 'error')
    except Exception as e:
        flash(f'خطأ: {str(e)}', 'error')
    
    return redirect(url_for('admin_manage_user_points', user_id=user_id))

# مسح تاريخ نقاط المستخدم
@app.route('/admin/clear-user-points-history/<int:user_id>')
def admin_clear_user_points_history(user_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))
    
    try:
        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()
        
        # حذف تاريخ النقاط
        cursor.execute('DELETE FROM points_history WHERE user_id = ?', (user_id,))
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        flash(f'تم مسح {deleted_count} سجل من تاريخ النقاط', 'success')
        
    except Exception as e:
        flash(f'خطأ: {str(e)}', 'error')
    
    return redirect(url_for('admin_manage_user_points', user_id=user_id))

# إعدادات النظام
@app.route('/admin/settings')
def admin_settings():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('ليس لديك صلاحية للوصول لهذه الصفحة', 'error')
        return redirect(url_for('index'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM site_settings ORDER BY category, setting_key')
    settings = cursor.fetchall()

    # إحصائيات للعرض
    cursor.execute('SELECT COUNT(*) FROM users WHERE is_active = 1')
    total_users = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM stores WHERE is_approved = 1')
    total_stores = cursor.fetchone()[0]

    conn.close()

    stats = {
        'total_users': total_users,
        'total_stores': total_stores
    }

    return render_template('admin_settings.html', settings=settings, stats=stats)

# جدول إعدادات الموقع
def create_settings_table():
    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS site_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            setting_key TEXT UNIQUE NOT NULL,
            setting_value TEXT,
            description TEXT,
            category TEXT DEFAULT 'general'
        )
    ''')

    # إضافة عمود category إذا لم يكن موجوداً
    try:
        cursor.execute('ALTER TABLE site_settings ADD COLUMN category TEXT DEFAULT "general"')
    except:
        pass

    # إضافة الإعدادات الافتراضية إذا لم تكن موجودة
    default_settings = [
        # إعدادات عامة
        ('site_title', 'دليل محلات الحسينية', 'عنوان الموقع', 'general'),
        ('site_description', 'دليل شامل لجميع المحلات والخدمات في منطقة الحسينية', 'وصف الموقع', 'general'),
        ('site_keywords', 'محلات، الحسينية، دليل، خدمات، صيدليات', 'كلمات مفتاحية للموقع', 'general'),
        ('site_logo', '', 'رابط شعار الموقع', 'general'),
        ('maintenance_mode', '0', 'وضع الصيانة', 'general'),
        ('analytics_code', '', 'كود Google Analytics', 'general'),

        # إعدادات الصفحة الرئيسية
        ('show_latest_stores', '1', 'عرض أحدث المحلات', 'homepage'),
        ('show_most_searched_stores', '1', 'عرض الأكثر بحثاً', 'homepage'),
        ('show_top_rated_stores', '1', 'عرض الأعلى تقييماً', 'homepage'),
        ('show_featured_stores', '1', 'عرض المحلات المميزة', 'homepage'),
        ('show_pharmacy_ticker', '1', 'عرض شريط الصيدلية المناوبة', 'homepage'),
        ('show_categories_grid', '1', 'عرض شبكة التصنيفات', 'homepage'),
        ('show_statistics', '1', 'عرض الإحصائيات', 'homepage'),
        ('show_important_services', '1', 'عرض الخدمات الهامة', 'homepage'),

        # أعداد العرض
        ('latest_stores_count', '6', 'عدد أحدث المحلات', 'counts'),
        ('most_searched_stores_count', '6', 'عدد الأكثر بحثاً', 'counts'),
        ('top_rated_stores_count', '6', 'عدد الأعلى تقييماً', 'counts'),
        ('featured_stores_count', '4', 'عدد المحلات المميزة', 'counts'),
        ('categories_grid_count', '8', 'عدد التصنيفات المعروضة', 'counts'),

        # إعدادات التواصل
        ('contact_phone', '0944000000', 'رقم التواصل', 'contact'),
        ('contact_email', 'info@hussainiya.com', 'البريد الإلكتروني', 'contact'),
        ('contact_address', 'منطقة الحسينية، سوريا', 'العنوان', 'contact'),
        ('facebook_link', '', 'رابط فيسبوك', 'contact'),
        ('instagram_link', '', 'رابط انستقرام', 'contact'),
        ('whatsapp_number', '', 'رقم الواتساب', 'contact'),

        # إعدادات متقدمة
        ('auto_approve_stores', '0', 'الموافقة التلقائية على المحلات', 'advanced'),
        ('allow_user_registration', '1', 'السماح بتسجيل المستخدمين', 'advanced'),
        ('require_phone_verification', '0', 'تطلب تأكيد الهاتف', 'advanced'),
        ('max_stores_per_user', '5', 'حد أقصى للمحلات لكل مستخدم', 'advanced'),
        ('enable_reviews', '1', 'تفعيل المراجعات', 'advanced'),
        ('enable_favorites', '1', 'تفعيل المفضلة', 'advanced'),
        ('cache_duration', '3600', 'مدة التخزين المؤقت (ثانية)', 'advanced'),
    ]

    for setting in default_settings:
        cursor.execute('''
            INSERT OR IGNORE INTO site_settings (setting_key, setting_value, description, category) 
            VALUES (?, ?, ?, ?)
        ''', setting)

    conn.commit()
    conn.close()

# حفظ إعدادات الموقع
@app.route('/save-settings', methods=['POST'])
@app.route('/admin/save-settings', methods=['POST'])
def save_settings():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('ليس لديك صلاحية للوصول لهذه الصفحة', 'error')
        return redirect(url_for('index'))

    try:
        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()

        # التأكد من وجود جدول الإعدادات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS site_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key TEXT UNIQUE NOT NULL,
                setting_value TEXT,
                description TEXT,
                category TEXT DEFAULT 'general'
            )
        ''')

        # قائمة إعدادات الخانات المختارة (checkboxes)
        checkbox_settings = [
            'maintenance_mode', 'show_latest_stores', 'show_most_searched_stores', 
            'show_top_rated_stores', 'show_featured_stores', 'show_pharmacy_ticker',
            'show_categories_grid', 'show_statistics', 'auto_approve_stores',
            'allow_user_registration', 'require_phone_verification', 'enable_reviews',
            'enable_favorites'
        ]

        # تحديث إعدادات الخانات المختارة أولاً
        for setting_key in checkbox_settings:
            value = '1' if setting_key in request.form else '0'
            cursor.execute('''
                INSERT OR REPLACE INTO site_settings (setting_key, setting_value) 
                VALUES (?, ?)
            ''', (setting_key, value))
            print(f"تم حفظ {setting_key}: {value}")

        # تحديث باقي الإعدادات النصية والرقمية
        for key, value in request.form.items():
            if key not in checkbox_settings and not key.startswith('csrf_'):
                # تنظيف القيمة
                cleaned_value = value.strip() if value else ''
                cursor.execute('''
                    INSERT OR REPLACE INTO site_settings (setting_key, setting_value) 
                    VALUES (?, ?)
                ''', (key, cleaned_value))
                print(f"تم حفظ {key}: {cleaned_value}")

        conn.commit()

        # التحقق من الحفظ
        cursor.execute('SELECT COUNT(*) FROM site_settings')
        count = cursor.fetchone()[0]
        print(f"عدد الإعدادات المحفوظة: {count}")

        conn.close()

        flash('تم حفظ جميع الإعدادات بنجاح وربطها بقاعدة البيانات', 'success')

    except Exception as e:
        print(f"خطأ في حفظ الإعدادات: {e}")
        flash(f'خطأ في حفظ الإعدادات: {str(e)}', 'error')

    return redirect(url_for('admin_settings'))

# الحصول على إعدادات الموقع
def get_telegram_bot_token():
    """الحصول على توكن بوت التليجرام من قاعدة البيانات أو Secrets"""
    try:
        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()
        
        # البحث في قاعدة البيانات أولاً
        cursor.execute('SELECT setting_value FROM site_settings WHERE setting_key = ?', ('telegram_bot_token',))
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0]:
            return result[0]
        
        # إذا لم يوجد في قاعدة البيانات، البحث في Secrets
        return os.getenv('TELEGRAM_BOT_TOKEN')
    except:
        return os.getenv('TELEGRAM_BOT_TOKEN')

def save_telegram_bot_token(token):
    """حفظ توكن بوت التليجرام في قاعدة البيانات"""
    try:
        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO site_settings (setting_key, setting_value, description, category) 
            VALUES (?, ?, ?, ?)
        ''', ('telegram_bot_token', token, 'توكن بوت التليجرام', 'telegram'))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"خطأ في حفظ توكن التليجرام: {e}")
        return False

def get_site_settings():
    try:
        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()

        # التأكد من وجود جدول الإعدادات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS site_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key TEXT UNIQUE NOT NULL,
                setting_value TEXT,
                description TEXT,
                category TEXT DEFAULT 'general'
            )
        ''')

        cursor.execute('SELECT setting_key, setting_value FROM site_settings')
        settings_data = cursor.fetchall()

        settings = {}
        for setting in settings_data:
            settings[setting[0]] = setting[1] if setting[1] is not None else ''

        # إضافة القيم الافتراضية في حالة عدم وجودها
        default_values = {
            'site_title': 'دليل محلات الحسينية',
            'site_description': 'دليل شامل لجميع المحلات والخدمات في منطقة الحسينية',
            'maintenance_mode': '0',
            'show_latest_stores': '1',
            'show_most_searched_stores': '1',
            'show_top_rated_stores': '1',
            'show_featured_stores': '1',
            'show_categories_grid': '1',
            'show_pharmacy_ticker': '1',
            'show_statistics': '1',
            'latest_stores_count': '6',
            'most_searched_stores_count': '6',
            'top_rated_stores_count': '6',
            'featured_stores_count': '4',
            'categories_grid_count': '8',
            'auto_approve_stores': '0',
            'allow_user_registration': '1',
            'require_phone_verification': '0',
            'enable_reviews': '1',
            'enable_favorites': '1',
            'contact_phone': '0938074766',
            'contact_email': 'info@hussainiya.com',
            'contact_address': 'منطقة الحسينية، سوريا',
            'show_important_services': '1'
        }

        # إضافة الإعدادات المفقودة إلى قاعدة البيانات فقط
        for key, default_value in default_values.items():
            if key not in settings:
                # إدراج الإعداد في قاعدة البيانات إذا لم يكن موجوداً
                cursor.execute('''
                    INSERT OR IGNORE INTO site_settings (setting_key, setting_value, description, category) 
                    VALUES (?, ?, ?, ?)
                ''', (key, default_value, f'إعداد {key}', 'general'))
                settings[key] = default_value

        conn.commit()
        conn.close()

        print(f"تم تحميل {len(settings)} إعداد من قاعدة البيانات")
        return settings

    except Exception as e:
        print(f"خطأ في الحصول على إعدادات الموقع: {e}")
        # إرجاع القيم الافتراضية في حالة الخطأ
        return {
            'site_title': 'دليل محلات الحسينية',
            'site_description': 'دليل شامل لجميع المحلات والخدمات في منطقة الحسينية',
            'maintenance_mode': '0',
            'show_latest_stores': '1',
            'show_most_searched_stores': '1',
            'show_top_rated_stores': '1',
            'show_featured_stores': '1',
            'show_categories_grid': '1',
            'show_pharmacy_ticker': '1',
            'show_statistics': '1',
            'latest_stores_count': '6',
            'most_searched_stores_count': '6',
            'top_rated_stores_count': '6',
            'featured_stores_count': '4',
            'categories_grid_count': '8',
            'auto_approve_stores': '0',
            'allow_user_registration': '1',
            'require_phone_verification': '0',
            'enable_reviews': '1',
            'enable_favorites': '1',
            'contact_phone': '0938074766',
            'contact_email': 'dlelk2023@gmail.com',
            'contact_address': 'ريف دمشق الحسينية',
            'facebook_link': '',
            'whatsapp_number': '0938074766'
        }

# وظيفة النسخ الاحتياطي التلقائي
def create_auto_backup(action_type, item_type, item_name):
    """إنشاء نسخة احتياطية تلقائية وإرسالها لبوت التليجرام"""
    try:
        import zipfile
        from datetime import datetime
        
        # إنشاء مجلد النسخ الاحتياطية المؤقتة
        os.makedirs('temp_backups', exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'auto_backup_{action_type}_{item_type}_{timestamp}.zip'
        backup_path = os.path.join('temp_backups', backup_filename)
        
        # إنشاء ملف ZIP
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # إضافة قاعدة البيانات
            if os.path.exists('hussainiya_stores.db'):
                zipf.write('hussainiya_stores.db')
        
        # إرسال النسخة الاحتياطية لبوت التليجرام
        if telegram_bot:
            asyncio.run(send_backup_to_telegram(backup_path, action_type, item_type, item_name))
        
        # حذف النسخة الاحتياطية المؤقتة
        if os.path.exists(backup_path):
            os.remove(backup_path)
            print(f"✅ تم إنشاء وإرسال النسخة الاحتياطية التلقائية: {backup_filename}")
        
    except Exception as e:
        print(f"❌ خطأ في النسخ الاحتياطي التلقائي: {e}")

async def send_backup_to_telegram(backup_path, action_type, item_type, item_name):
    """إرسال النسخة الاحتياطية لبوت التليجرام"""
    if not telegram_bot:
        return
        
    try:
        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT telegram_id FROM admin_telegram_ids')
        admin_ids = cursor.fetchall()
        conn.close()
        
        if not admin_ids:
            print("⚠️ لا توجد معرفات تليجرام للمديرين")
            return
        
        # معلومات النسخة الاحتياطية
        from datetime import timezone, timedelta
        damascus_tz = timezone(timedelta(hours=3))
        damascus_time = datetime.now(damascus_tz)
        current_time_str = damascus_time.strftime('%Y-%m-%d %H:%M:%S')
        
        action_text = {
            'add': 'إضافة',
            'edit': 'تعديل',
            'delete': 'حذف'
        }.get(action_type, action_type)
        
        item_text = {
            'user': 'مستخدم',
            'store': 'محل',
            'category': 'تصنيف',
            'service': 'خدمة'
        }.get(item_type, item_type)
        
        caption = f"🔄 نسخة احتياطية تلقائية\n\n"
        caption += f"📝 العملية: {action_text} {item_text}\n"
        caption += f"🏷️ العنصر: {item_name}\n"
        caption += f"🕐 التوقيت: {current_time_str}\n"
        caption += f"📁 حجم الملف: {os.path.getsize(backup_path) / 1024:.1f} KB"
        
        # إرسال الملف لجميع المديرين
        for admin_id in admin_ids:
            try:
                with open(backup_path, 'rb') as backup_file:
                    await telegram_bot.send_document(
                        chat_id=admin_id[0],
                        document=backup_file,
                        caption=caption,
                        filename=os.path.basename(backup_path)
                    )
                print(f"✅ تم إرسال النسخة الاحتياطية للمدير {admin_id[0]}")
            except Exception as e:
                print(f"❌ خطأ في إرسال النسخة الاحتياطية للمدير {admin_id[0]}: {e}")
                
    except Exception as e:
        print(f"❌ خطأ في إرسال النسخة الاحتياطية لتليجرام: {e}")

# وظائف إدارة النقاط
def initialize_user_points(user_id):
    """تهيئة نقاط المستخدم الجديد"""
    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT id FROM user_points WHERE user_id = ?', (user_id,))
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO user_points (user_id, total_points, available_points, spent_points) 
            VALUES (?, 0, 0, 0)
        ''', (user_id,))
        conn.commit()
    
    conn.close()

def get_points_settings():
    """الحصول على إعدادات النقاط"""
    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT setting_key, setting_value FROM points_settings')
    settings_data = cursor.fetchall()
    
    settings = {}
    for setting in settings_data:
        settings[setting[0]] = setting[1]
    
    conn.close()
    return settings

def add_points(user_id, points, activity_type, activity_description, related_id=None):
    """إضافة نقاط للمستخدم"""
    try:
        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()
        
        # تهيئة نقاط المستخدم إذا لم تكن موجودة
        initialize_user_points(user_id)
        
        # إضافة النقاط
        cursor.execute('''
            UPDATE user_points 
            SET total_points = total_points + ?, 
                available_points = available_points + ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (points, points, user_id))
        
        # إضافة سجل النقاط
        cursor.execute('''
            INSERT INTO points_history 
            (user_id, points, activity_type, activity_description, related_id) 
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, points, activity_type, activity_description, related_id))
        
        # تحديث النقاط في جدول المستخدمين
        cursor.execute('''
            UPDATE users SET total_points = (
                SELECT total_points FROM user_points WHERE user_id = ?
            ) WHERE id = ?
        ''', (user_id, user_id))
        
        conn.commit()
        conn.close()
        
        print(f"✅ تم إضافة {points} نقطة للمستخدم {user_id} - {activity_description}")
        return True
        
    except Exception as e:
        print(f"خطأ في إضافة النقاط: {e}")
        return False

def can_award_daily_login(user_id):
    """التحقق من إمكانية منح نقاط الدخول اليومي"""
    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()
    
    # الحصول على التوقيت الحالي بتوقيت دمشق
    from datetime import timezone, timedelta
    damascus_tz = timezone(timedelta(hours=3))
    today = datetime.now(damascus_tz).date()
    
    cursor.execute('SELECT last_daily_login FROM user_points WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    if not result:
        initialize_user_points(user_id)
        conn.close()
        return True
    
    last_login = result[0]
    if not last_login:
        conn.close()
        return True
    
    # تحويل النص إلى تاريخ للمقارنة
    try:
        last_login_date = datetime.strptime(last_login, '%Y-%m-%d').date()
        conn.close()
        return today > last_login_date
    except:
        conn.close()
        return True

def award_daily_login_points(user_id):
    """منح نقاط الدخول اليومي"""
    if not can_award_daily_login(user_id):
        return False
    
    settings = get_points_settings()
    daily_points = settings.get('points_daily_login', 2)
    
    # الحصول على التوقيت الحالي بتوقيت دمشق
    from datetime import timezone, timedelta
    damascus_tz = timezone(timedelta(hours=3))
    today = datetime.now(damascus_tz).date().strftime('%Y-%m-%d')
    
    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()
    
    # تحديث تاريخ آخر دخول
    cursor.execute('''
        UPDATE user_points 
        SET last_daily_login = ? 
        WHERE user_id = ?
    ''', (today, user_id))
    
    conn.commit()
    conn.close()
    
    # إضافة النقاط
    return add_points(user_id, daily_points, 'daily_login', 'دخول يومي')

def get_user_points_summary(user_id):
    """الحصول على ملخص نقاط المستخدم"""
    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()
    
    # تهيئة نقاط المستخدم إذا لم تكن موجودة
    initialize_user_points(user_id)
    
    cursor.execute('''
        SELECT total_points, available_points, spent_points, last_daily_login 
        FROM user_points WHERE user_id = ?
    ''', (user_id,))
    
    result = cursor.fetchone()
    if not result:
        result = (0, 0, 0, None)
    
    # تاريخ النقاط
    cursor.execute('''
        SELECT points, activity_type, activity_description, created_at 
        FROM points_history 
        WHERE user_id = ? 
        ORDER BY created_at DESC 
        LIMIT 10
    ''', (user_id,))
    
    history = cursor.fetchall()
    
    conn.close()
    
    return {
        'total_points': result[0],
        'available_points': result[1], 
        'spent_points': result[2],
        'last_daily_login': result[3],
        'history': history
    }

# وظائف بوت التليجرام
async def start_command(update, context):
    """بداية البوت - للمديرين فقط"""
    user_id = update.effective_user.id
    
    # التحقق من أن المستخدم مدير من قاعدة البيانات
    if not is_admin_user(user_id):
        await update.message.reply_text("عذراً، هذا البوت مخصص للمديرين فقط.")
        return
    
    keyboard = [
        [InlineKeyboardButton("عرض المحلات الغير مفعلة", callback_data='pending_stores')],
        [InlineKeyboardButton("إحصائيات سريعة", callback_data='stats')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "مرحباً بك في بوت إدارة دليل محلات الحسينية!\n\n"
        "يمكنك من خلال هذا البوت:\n"
        "• مراجعة المحلات الجديدة\n"
        "• الموافقة على المحلات أو رفضها\n"
        "• مراجعة الإحصائيات",
        reply_markup=reply_markup
    )

async def button_callback(update, context):
    """معالج الأزرار"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not is_admin_user(user_id):
        await query.edit_message_text("عذراً، ليس لديك صلاحية لاستخدام هذا البوت.")
        return
    
    if query.data == 'pending_stores':
        await show_pending_stores(query)
    elif query.data == 'stats':
        await show_stats(query)
    elif query.data.startswith('approve_'):
        store_id = int(query.data.split('_')[1])
        await approve_store_bot(query, store_id)
    elif query.data.startswith('reject_'):
        store_id = int(query.data.split('_')[1])
        await reject_store_bot(query, store_id)
    elif query.data == 'back_to_main':
        keyboard = [
            [InlineKeyboardButton("عرض المحلات الغير مفعلة", callback_data='pending_stores')],
            [InlineKeyboardButton("إحصائيات سريعة", callback_data='stats')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "مرحباً بك في بوت إدارة دليل محلات الحسينية!\n\n"
            "يمكنك من خلال هذا البوت:\n"
            "• مراجعة المحلات الجديدة\n"
            "• الموافقة على المحلات أو رفضها\n"
            "• مراجعة الإحصائيات",
            reply_markup=reply_markup
        )

async def show_pending_stores(query):
    """عرض المحلات في انتظار الموافقة"""
    try:
        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT s.id, s.name, s.address, s.phone, c.name as category_name, u.full_name as owner_name
            FROM stores s 
            LEFT JOIN categories c ON s.category_id = c.id 
            LEFT JOIN users u ON s.user_id = u.id
            WHERE s.is_approved = 0
            ORDER BY s.created_at DESC
            LIMIT 10
        ''')
        
        pending_stores = cursor.fetchall()
        conn.close()
        
        if not pending_stores:
            keyboard = [[InlineKeyboardButton("العودة للقائمة الرئيسية", callback_data='back_to_main')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "✅ لا توجد محلات في انتظار الموافقة",
                reply_markup=reply_markup
            )
            return
        
        message = "📋 المحلات في انتظار الموافقة:\n\n"
        keyboard = []
        
        for store in pending_stores:
            store_id, name, address, phone, category, owner = store
            message += f"🏪 {name}\n"
            message += f"📍 {address}\n"
            message += f"📞 {phone or 'غير محدد'}\n"
            message += f"🏷️ {category or 'غير محدد'}\n"
            message += f"👤 {owner or 'غير محدد'}\n"
            message += "━━━━━━━━━━━━━━━━━\n\n"
            
            keyboard.extend([
                [InlineKeyboardButton(f"✅ الموافقة على {name}", callback_data=f'approve_{store_id}')],
                [InlineKeyboardButton(f"❌ رفض {name}", callback_data=f'reject_{store_id}')]
            ])
        
        keyboard.append([InlineKeyboardButton("العودة للقائمة الرئيسية", callback_data='back_to_main')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # تقسيم الرسالة إذا كانت طويلة
        if len(message) > 4000:
            message = message[:4000] + "...\n\n(عرض أول 10 محلات)"
        
        await query.edit_message_text(message, reply_markup=reply_markup)
        
    except Exception as e:
        await query.edit_message_text(f"خطأ في جلب المحلات: {str(e)}")

async def show_stats(query):
    """عرض الإحصائيات"""
    try:
        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM stores WHERE is_approved = 1')
        approved_stores = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM stores WHERE is_approved = 0')
        pending_stores = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE is_active = 1')
        active_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM categories')
        categories_count = cursor.fetchone()[0]
        
        conn.close()
        
        message = "📊 إحصائيات النظام:\n\n"
        message += f"🏪 المحلات المفعلة: {approved_stores}\n"
        message += f"⏳ المحلات في الانتظار: {pending_stores}\n"
        message += f"👥 المستخدمين النشطين: {active_users}\n"
        message += f"🏷️ التصنيفات: {categories_count}\n"
        
        keyboard = [[InlineKeyboardButton("العودة للقائمة الرئيسية", callback_data='back_to_main')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup)
        
    except Exception as e:
        await query.edit_message_text(f"خطأ في جلب الإحصائيات: {str(e)}")

async def approve_store_bot(query, store_id):
    """الموافقة على محل"""
    try:
        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()
        
        # الحصول على معلومات المحل
        cursor.execute('SELECT name FROM stores WHERE id = ?', (store_id,))
        store = cursor.fetchone()
        
        if not store:
            await query.edit_message_text("المحل غير موجود")
            return
        
        # الموافقة على المحل
        cursor.execute('UPDATE stores SET is_approved = 1 WHERE id = ?', (store_id,))
        conn.commit()
        conn.close()
        
        await query.edit_message_text(f"✅ تم الموافقة على محل: {store[0]}")
        
    except Exception as e:
        await query.edit_message_text(f"خطأ في الموافقة: {str(e)}")

async def reject_store_bot(query, store_id):
    """رفض محل"""
    try:
        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()
        
        # الحصول على معلومات المحل
        cursor.execute('SELECT name FROM stores WHERE id = ?', (store_id,))
        store = cursor.fetchone()
        
        if not store:
            await query.edit_message_text("المحل غير موجود")
            return
        
        # حذف المحل
        cursor.execute('DELETE FROM stores WHERE id = ?', (store_id,))
        conn.commit()
        conn.close()
        
        await query.edit_message_text(f"❌ تم رفض وحذف محل: {store[0]}")
        
    except Exception as e:
        await query.edit_message_text(f"خطأ في الرفض: {str(e)}")

def is_admin_user(telegram_user_id):
    """التحقق من أن المستخدم مدير"""
    try:
        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()
        
        # التحقق من وجود التليجرام ID في جدول المديرين
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_telegram_ids (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                admin_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('SELECT telegram_id FROM admin_telegram_ids WHERE telegram_id = ?', (telegram_user_id,))
        result = cursor.fetchone()
        conn.close()
        
        return result is not None
    except Exception as e:
        print(f"خطأ في التحقق من المدير: {e}")
        return False

def send_redemption_notification_sync(user_id, gift_name, points_spent):
    """إرسال إشعار للمديرين عند طلب استبدال هدية (بدون threading)"""
    if not telegram_bot:
        print("⚠️ بوت التليجرام غير متاح لإرسال إشعار الاستبدال")
        return False
    
    try:
        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()
        
        # الحصول على اسم المستخدم
        cursor.execute('SELECT full_name FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        user_name = user[0] if user else f'مستخدم #{user_id}'
        
        cursor.execute('SELECT telegram_id FROM admin_telegram_ids')
        admin_ids = cursor.fetchall()
        conn.close()
        
        if not admin_ids:
            print("⚠️ لا توجد معرفات تليجرام للمديرين")
            return False
        
        message = f"🎁 طلب استبدال هدية جديد!\n\n"
        message += f"👤 المستخدم: {user_name}\n"
        message += f"🎁 الهدية: {gift_name}\n"
        message += f"⭐ النقاط المستخدمة: {points_spent}\n\n"
        message += "يرجى مراجعة الطلب من لوحة الإدارة"
        
        # استخدام threading.Thread لتشغيل asyncio في خيط منفصل
        import threading
        def send_messages():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def send_to_admins():
                    success_count = 0
                    for admin_id in admin_ids:
                        try:
                            await telegram_bot.send_message(
                                chat_id=admin_id[0],
                                text=message
                            )
                            success_count += 1
                            print(f"✅ تم إرسال إشعار الاستبدال للمدير {admin_id[0]}")
                        except Exception as e:
                            print(f"❌ فشل في إرسال إشعار الاستبدال للمدير {admin_id[0]}: {e}")
                    return success_count > 0
                
                return loop.run_until_complete(send_to_admins())
            except Exception as e:
                print(f"❌ خطأ في thread إرسال الإشعارات: {e}")
                return False
        
        # تشغيل في خيط منفصل لتجنب مشاكل asyncio
        thread = threading.Thread(target=send_messages)
        thread.start()
        return True  # إرجاع True مباشرة
                
    except Exception as e:
        print(f"❌ خطأ عام في إرسال إشعارات استبدال الهدايا: {e}")
        return False

async def send_new_store_notification(store_name, owner_name, category_name):
    """إرسال إشعار للمديرين عند إضافة محل جديد"""
    if not telegram_bot:
        return
        
    try:
        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT telegram_id FROM admin_telegram_ids')
        admin_ids = cursor.fetchall()
        conn.close()
        
        message = f"🆕 محل جديد يحتاج للموافقة!\n\n"
        message += f"🏪 اسم المحل: {store_name}\n"
        message += f"👤 المالك: {owner_name}\n"
        message += f"🏷️ التصنيف: {category_name}\n\n"
        message += "استخدم الأوامر للموافقة أو الرفض"
        
        keyboard = [[InlineKeyboardButton("عرض المحلات المعلقة", callback_data='pending_stores')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        for admin_id in admin_ids:
            try:
                await telegram_bot.send_message(
                    chat_id=admin_id[0],
                    text=message,
                    reply_markup=reply_markup
                )
            except Exception as e:
                print(f"خطأ في إرسال الإشعار للمدير {admin_id[0]}: {e}")
                
    except Exception as e:
        print(f"خطأ في إرسال إشعارات التليجرام: {e}")

def init_telegram_bot():
    """تهيئة بوت التليجرام مع التحقق من صحة التوكن"""
    global telegram_bot, telegram_app
    
    try:
        # الحصول على التوكن من قاعدة البيانات أولاً، ثم من Secrets
        bot_token = get_telegram_bot_token()
        if not bot_token:
            print("⚠️ لم يتم العثور على توكن بوت التليجرام")
            print("💡 لإضافة التوكن: اذهب إلى لوحة الإدارة > إعدادات بوت التليجرام")
            return False
        
        # التحقق من صحة التوكن
        telegram_bot = Bot(token=bot_token)
        
        # اختبار الاتصال
        async def test_connection():
            try:
                me = await telegram_bot.get_me()
                print(f"✅ تم الاتصال بالبوت: @{me.username}")
                return True
            except Exception as e:
                print(f"❌ فشل في الاتصال بالبوت: {e}")
                return False
        
        # تشغيل اختبار الاتصال
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        connection_test = loop.run_until_complete(test_connection())
        
        if not connection_test:
            return False
        
        telegram_app = Application.builder().token(bot_token).build()
        
        # إضافة المعالجات
        telegram_app.add_handler(CommandHandler("start", start_command))
        telegram_app.add_handler(CallbackQueryHandler(button_callback))
        
        print("✅ تم تهيئة بوت التليجرام بنجاح")
        return True
        
    except Exception as e:
        print(f"❌ خطأ في تهيئة بوت التليجرام: {e}")
        telegram_bot = None
        telegram_app = None
        return False

def run_telegram_bot():
    """تشغيل البوت بشكل متزامن في الخيط الرئيسي"""
    if telegram_app:
        try:
            print("🔄 بدء تشغيل بوت التليجرام...")
            # تشغيل البوت بدون خيط منفصل
            telegram_app.run_polling(drop_pending_updates=True)
        except Exception as e:
            print(f"❌ خطأ في تشغيل بوت التليجرام: {e}")

# وظيفة إنشاء جدول صيدليات تلقائي لشهر كامل
@app.route('/admin/generate-monthly-schedule', methods=['POST'])
def generate_monthly_schedule():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    year = int(request.form['year'])
    month = int(request.form['month'])
    pharmacy_names = request.form.getlist('pharmacy_names[]')
    pharmacy_addresses = request.form.getlist('pharmacy_addresses[]')
    pharmacy_phones = request.form.getlist('pharmacy_phones[]')

    if not pharmacy_names:
        flash('يجب إضافة صيدلية واحدة على الأقل', 'error')
        return redirect(url_for('admin_duty_pharmacies'))

    from calendar import monthrange
    days_in_month = monthrange(year, month)[1]

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # حذف الجدول الحالي للشهر المحدد
    cursor.execute('''
        DELETE FROM duty_pharmacies 
        WHERE strftime('%Y-%m', duty_date) = ?
    ''', (f"{year:04d}-{month:02d}",))

    # إنشاء جدول جديد
    pharmacy_count = len(pharmacy_names)
    for day in range(1, days_in_month + 1):
        pharmacy_index = (day - 1) % pharmacy_count
        duty_date = f"{year:04d}-{month:02d}-{day:02d}"

        cursor.execute('''
            INSERT INTO duty_pharmacies (name, address, phone, duty_date) 
            VALUES (?, ?, ?, ?)
        ''', (pharmacy_names[pharmacy_index], 
              pharmacy_addresses[pharmacy_index], 
              pharmacy_phones[pharmacy_index], 
              duty_date))

    conn.commit()
    conn.close()

    flash(f'تم إنشاء جدول المناوبات لشهر {month}/{year} بنجاح', 'success')
    return redirect(url_for('admin_duty_pharmacies'))

# إدارة الإشعارات
@app.route('/admin/notifications')
def admin_notifications():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('ليس لديك صلاحية للوصول لهذه الصفحة', 'error')
        return redirect(url_for('index'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM notifications ORDER BY created_at DESC')
    notifications = cursor.fetchall()

    conn.close()
    return render_template('admin_notifications.html', notifications=notifications)

# إضافة إشعار جديد
@app.route('/admin/add-notification', methods=['POST'])
def add_notification():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    title = request.form['title']
    message = request.form['message']
    notification_type = request.form['type']
    expires_at = request.form.get('expires_at') or None

    # التحقق من تاريخ الانتهاء
    if expires_at:
        from datetime import timezone, timedelta
        damascus_tz = timezone(timedelta(hours=3))  # دمشق UTC+3
        damascus_time = datetime.now(damascus_tz)
        current_time_str = damascus_time.strftime('%Y-%m-%d %H:%M:%S')
        
        # التحقق من أن تاريخ الانتهاء في المستقبل
        if expires_at <= current_time_str:
            flash('تاريخ الانتهاء يجب أن يكون في المستقبل', 'error')
            return redirect(url_for('admin_notifications'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO notifications (title, message, type, expires_at) 
        VALUES (?, ?, ?, ?)
    ''', (title, message, notification_type, expires_at))

    conn.commit()
    conn.close()

    if expires_at:
        flash(f'تم إضافة الإشعار بنجاح وسينتهي تلقائياً في: {expires_at}', 'success')
    else:
        flash('تم إضافة الإشعار بنجاح', 'success')
    
    return redirect(url_for('admin_notifications'))

# تحديث إشعار
@app.route('/admin/update-notification/<int:notification_id>', methods=['POST'])
def update_notification(notification_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    title = request.form['title']
    message = request.form['message']
    notification_type = request.form['type']
    is_active = 1 if request.form.get('is_active') else 0
    expires_at = request.form.get('expires_at') or None

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE notifications 
        SET title = ?, message = ?, type = ?, is_active = ?, expires_at = ? 
        WHERE id = ?
    ''', (title, message, notification_type, is_active, expires_at, notification_id))

    conn.commit()
    conn.close()

    flash('تم تحديث الإشعار بنجاح', 'success')
    return redirect(url_for('admin_notifications'))

# حذف إشعار
@app.route('/admin/delete-notification/<int:notification_id>')
def delete_notification(notification_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    cursor.execute('DELETE FROM notifications WHERE id = ?', (notification_id,))

    conn.commit()
    conn.close()

    flash('تم حذف الإشعار بنجاح', 'success')
    return redirect(url_for('admin_notifications'))

# إضافة محل من قبل المستخدم
@app.route('/add-user-store', methods=['POST'])
def add_user_store():
    if 'user_id' not in session:
        flash('يجب تسجيل الدخول أولاً', 'error')
        return redirect(url_for('login'))

    name = request.form['name']
    category_id = request.form['category_id']
    address = request.form['address']
    phone = request.form.get('phone', '')
    description = request.form.get('description', '')

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO stores (name, category_id, address, phone, description, user_id, is_approved) 
        VALUES (?, ?, ?, ?, ?, ?, 0)
    ''', (name, category_id, address, phone, description, session['user_id']))

    # الحصول على معلومات المستخدم والتصنيف للإشعار
    cursor.execute('SELECT full_name FROM users WHERE id = ?', (session['user_id'],))
    user = cursor.fetchone()
    owner_name = user[0] if user else 'غير محدد'
    
    cursor.execute('SELECT name FROM categories WHERE id = ?', (category_id,))
    category = cursor.fetchone()
    category_name = category[0] if category else 'غير محدد'

    conn.commit()
    conn.close()

    # إنشاء نسخة احتياطية تلقائية
    create_auto_backup('add', 'store', name)

    # إرسال إشعار تليجرام للمديرين (يمكن تحسينه لاحقاً)
    try:
        if telegram_bot:
            print(f"📝 محل جديد: {name} - صاحب المحل: {owner_name}")
    except Exception as e:
        print(f"خطأ في إرسال إشعار التليجرام: {e}")

    flash('تم إضافة المحل بنجاح وهو في انتظار الموافقة', 'success')
    return redirect(url_for('dashboard'))

# تعديل محل من قبل المستخدم
@app.route('/edit-user-store/<int:store_id>', methods=['POST'])
def edit_user_store(store_id):
    if 'user_id' not in session:
        flash('يجب تسجيل الدخول أولاً', 'error')
        return redirect(url_for('login'))

    # التحقق من أن المحل يخص المستخدم الحالي
    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM stores WHERE id = ?', (store_id,))
    store = cursor.fetchone()

    if not store or store[0] != session['user_id']:
        flash('ليس لديك صلاحية لتعديل هذا المحل', 'error')
        conn.close()
        return redirect(url_for('dashboard'))

    name = request.form['name']
    category_id = request.form['category_id']
    address = request.form['address']
    phone = request.form.get('phone', '')
    description = request.form.get('description', '')

    cursor.execute('''
        UPDATE stores SET name = ?, category_id = ?, address = ?, phone = ?, description = ?
        WHERE id = ? AND user_id = ?
    ''', (name, category_id, address, phone, description, store_id, session['user_id']))

    conn.commit()
    conn.close()

    # إنشاء نسخة احتياطية تلقائية
    create_auto_backup('edit', 'store', name)

    flash('تم تحديث المحل بنجاح', 'success')
    return redirect(url_for('dashboard'))

# حذف محل من قبل المستخدم
@app.route('/delete-user-store/<int:store_id>', methods=['DELETE'])
def delete_user_store(store_id):
    if 'user_id' not in session:
        return jsonify({'error': 'يجب تسجيل الدخول أولاً'}), 401

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # التحقق من أن المحل يخص المستخدم الحالي
    cursor.execute('SELECT user_id FROM stores WHERE id = ?', (store_id,))
    store = cursor.fetchone()

    if not store or store[0] != session['user_id']:
        conn.close()
        return jsonify({'error': 'ليس لديك صلاحية لحذف هذا المحل'}), 403

    cursor.execute('DELETE FROM stores WHERE id = ? AND user_id = ?', (store_id, session['user_id']))
    cursor.execute('DELETE FROM ratings WHERE store_id = ?', (store_id,))

    conn.commit()
    conn.close()

    return jsonify({'success': True})

# تحديث الملف الشخصي
@app.route('/update-profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        flash('يجب تسجيل الدخول أولاً', 'error')
        return redirect(url_for('login'))

    full_name = request.form['full_name']
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    if new_password and new_password != confirm_password:
        flash('كلمة المرور غير متطابقة', 'error')
        return redirect(url_for('dashboard'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    if new_password:
        password_hash = generate_password_hash(new_password)
        cursor.execute('UPDATE users SET full_name = ?, password_hash = ? WHERE id = ?', 
                      (full_name, password_hash, session['user_id']))
        flash('تم تحديث الملف الشخصي وكلمة المرور بنجاح', 'success')
    else:
        cursor.execute('UPDATE users SET full_name = ? WHERE id = ?', 
                      (full_name, session['user_id']))
        flash('تم تحديث الملف الشخصي بنجاح', 'success')

    session['user_name'] = full_name
    conn.commit()
    conn.close()

    return redirect(url_for('dashboard'))

# النسخ الاحتياطي والاستعادة
@app.route('/admin/backup')
def admin_backup():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('ليس لديك صلاحية للوصول لهذه الصفحة', 'error')
        return redirect(url_for('index'))

    return render_template('admin_backup.html')

# إنشاء نسخة احتياطية من قاعدة البيانات فقط
@app.route('/admin/create-backup')
def create_backup():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    try:
        # إنشاء مجلد النسخ الاحتياطية
        os.makedirs('backups', exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'hussainiya_backup_{timestamp}.db'
        backup_path = os.path.join('backups', backup_filename)

        # نسخ قاعدة البيانات
        shutil.copy2('hussainiya_stores.db', backup_path)

        flash(f'تم إنشاء النسخة الاحتياطية بنجاح: {backup_filename}', 'success')
    except Exception as e:
        flash(f'خطأ في إنشاء النسخة الاحتياطية: {str(e)}', 'error')

    return redirect(url_for('admin_backup'))

# إنشاء نسخة احتياطية شاملة لجميع الملفات
@app.route('/admin/create-full-backup')
def create_full_backup():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    try:
        import zipfile

        # إنشاء مجلد النسخ الاحتياطية
        os.makedirs('backups', exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'hussainiya_full_backup_{timestamp}.zip'
        backup_path = os.path.join('backups', backup_filename)

        # إنشاء ملف ZIP
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # إضافة قاعدة البيانات
            if os.path.exists('hussainiya_stores.db'):
                zipf.write('hussainiya_stores.db')

            # إضافة ملف التطبيق الرئيسي
            zipf.write('app.py')

            # إضافة جميع القوالب
            for root, dirs, files in os.walk('templates'):
                for file in files:
                    file_path = os.path.join(root, file)
                    zipf.write(file_path)

            # إضافة الملفات الثابتة إذا كانت موجودة
            if os.path.exists('static'):
                for root, dirs, files in os.walk('static'):
                    for file in files:
                        file_path = os.path.join(root, file)
                        zipf.write(file_path)

            # إضافة ملفات التكوين
            config_files = ['pyproject.toml', '.replit', 'style.css', 'script.js']
            for config_file in config_files:
                if os.path.exists(config_file):
                    zipf.write(config_file)

        flash(f'تم إنشاء النسخة الاحتياطية الشاملة بنجاح: {backup_filename}', 'success')
    except Exception as e:
        flash(f'خطأ في إنشاء النسخة الاحتياطية الشاملة: {str(e)}', 'error')

    return redirect(url_for('admin_backup'))

# استعادة النسخة الاحتياطية الشاملة
@app.route('/admin/restore-full-backup', methods=['POST'])
def restore_full_backup():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    if 'backup_file' not in request.files:
        flash('لم يتم اختيار ملف', 'error')
        return redirect(url_for('admin_backup'))

    file = request.files['backup_file']
    if file.filename == '':
        flash('لم يتم اختيار ملف', 'error')
        return redirect(url_for('admin_backup'))

    if file and file.filename.endswith('.zip'):
        try:
            import zipfile

            # إنشاء نسخة احتياطية من الملفات الحالية
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            current_backup = f'hussainiya_full_backup_before_restore_{timestamp}.zip'

            with zipfile.ZipFile(current_backup, 'w', zipfile.ZIP_DEFLATED) as zipf:
                if os.path.exists('hussainiya_stores.db'):
                    zipf.write('hussainiya_stores.db')
                zipf.write('app.py')
                for root, dirs, files in os.walk('templates'):
                    for file_name in files:
                        file_path = os.path.join(root, file_name)
                        zipf.write(file_path)

            # حفظ الملف المرفوع مؤقتاً
            temp_path = f'temp_restore_{timestamp}.zip'
            file.save(temp_path)

            # استخراج الملفات
            with zipfile.ZipFile(temp_path, 'r') as zipf:
                zipf.extractall('.')

            # حذف الملف المؤقت
            os.remove(temp_path)

            flash('تم استعادة النسخة الاحتياطية الشاملة بنجاح', 'success')
        except Exception as e:
            flash(f'خطأ في استعادة النسخة الاحتياطية الشاملة: {str(e)}', 'error')
    else:
        flash('يجب أن يكون الملف من نوع .zip', 'error')

    return redirect(url_for('admin_backup'))

# نظام الإشعارات المتطور
@app.route('/admin/send-notification', methods=['POST'])
def send_notification():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    title = request.form['title']
    message = request.form['message']
    notification_type = request.form['type']
    target_users = request.form.get('target_users', 'all')
    expires_at = request.form.get('expires_at') or None
    priority = int(request.form.get('priority', 1))
    is_popup = 1 if request.form.get('is_popup') else 0

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # إنشاء جدول الإشعارات المتقدم إذا لم يكن موجوداً
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS advanced_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            type TEXT,
            target_users TEXT DEFAULT 'all',
            priority INTEGER DEFAULT 1,
            is_popup BOOLEAN DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            read_by TEXT DEFAULT ''
        )
    ''')

    cursor.execute('''
        INSERT INTO advanced_notifications (title, message, type, target_users, priority, is_popup, expires_at) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (title, message, notification_type, target_users, priority, is_popup, expires_at))

    conn.commit()
    conn.close()

    flash('تم إرسال الإشعار بنجاح', 'success')
    return redirect(url_for('admin_notifications'))

# التحقق اليدوي من الإشعارات المنتهية (للإدارة)
@app.route('/api/check-expired-notifications')
def api_check_expired_notifications():
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({'error': 'غير مصرح'}), 403
    
    try:
        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()
        
        # الحصول على التوقيت الحالي بتوقيت دمشق مع إضافة 3 ساعات
        from datetime import timezone, timedelta
        damascus_tz = timezone(timedelta(hours=3))  # دمشق UTC+3
        damascus_time = datetime.now(damascus_tz)
        current_time_str = damascus_time.strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"🔍 [فحص يدوي] التوقيت الحالي: {current_time_str}")
        
        # البحث عن الإشعارات المنتهية الصلاحية مع تفاصيل أكثر
        cursor.execute('''
            SELECT id, title, expires_at, is_active FROM notifications 
            WHERE expires_at IS NOT NULL AND expires_at <= ?
        ''', (current_time_str,))
        expired_notifications = cursor.fetchall()
        
        expired_details = []
        disabled_count = 0
        
        # تعطيل الإشعارات المنتهية
        for notif in expired_notifications:
            if notif[3] == 1:  # إذا كان نشطاً
                cursor.execute('UPDATE notifications SET is_active = 0 WHERE id = ?', (notif[0],))
                disabled_count += 1
                print(f"✅ [فحص يدوي] تم تعطيل الإشعار: {notif[1]} (ID: {notif[0]})")
            
            expired_details.append({
                'id': notif[0],
                'title': notif[1],
                'expires_at': notif[2],
                'type': 'عادي',
                'was_active': notif[3] == 1
            })
        
        # التحقق من الإشعارات المتقدمة
        expired_advanced_count = 0
        try:
            cursor.execute('''
                SELECT id, title, expires_at, is_active FROM advanced_notifications 
                WHERE expires_at IS NOT NULL AND expires_at <= ?
            ''', (current_time_str,))
            expired_advanced = cursor.fetchall()
            
            for notif in expired_advanced:
                if notif[3] == 1:  # إذا كان نشطاً
                    cursor.execute('UPDATE advanced_notifications SET is_active = 0 WHERE id = ?', (notif[0],))
                    expired_advanced_count += 1
                    disabled_count += 1
                    print(f"✅ [فحص يدوي] تم تعطيل الإشعار المتقدم: {notif[1]} (ID: {notif[0]})")
                
                expired_details.append({
                    'id': notif[0],
                    'title': notif[1],
                    'expires_at': notif[2],
                    'type': 'متقدم',
                    'was_active': notif[3] == 1
                })
        except Exception as e:
            print(f"تحذير في معالجة الإشعارات المتقدمة: {e}")
            expired_advanced = []
        
        conn.commit()
        conn.close()
        
        total_found = len(expired_notifications) + len(expired_advanced)
        
        print(f"📊 [فحص يدوي] النتيجة: تم العثور على {total_found} إشعار منتهي، تم تعطيل {disabled_count} إشعار نشط")
        
        return jsonify({
            'success': True,
            'total_found': total_found,
            'disabled_count': disabled_count,
            'regular_notifications': len(expired_notifications),
            'advanced_notifications': len(expired_advanced),
            'current_time': current_time_str,
            'expired_details': expired_details,
            'message': f'تم العثور على {total_found} إشعار منتهي الصلاحية، تم تعطيل {disabled_count} إشعار نشط'
        })
        
    except Exception as e:
        print(f"❌ خطأ في الفحص اليدوي: {e}")
        return jsonify({'error': f'خطأ في التحقق: {str(e)}'}), 500

# الحصول على الإشعارات للمستخدم
@app.route('/api/get-notifications')
def get_notifications():
    if 'user_id' not in session:
        return jsonify({'notifications': []})

    try:
        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()

        # إنشاء جدول الإشعارات المتقدم إذا لم يكن موجوداً
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS advanced_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                type TEXT,
                target_users TEXT DEFAULT 'all',
                priority INTEGER DEFAULT 1,
                is_popup BOOLEAN DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                read_by TEXT DEFAULT ''
            )
        ''')

        user_id = str(session['user_id'])

        # الحصول على التوقيت الحالي بتوقيت دمشق مع إضافة 3 ساعات
        from datetime import timezone, timedelta
        damascus_tz = timezone(timedelta(hours=3))  # دمشق UTC+3
        damascus_time = datetime.now(damascus_tz)
        current_time_str = damascus_time.strftime('%Y-%m-%d %H:%M:%S')

        # جلب الإشعارات من الجدول المتقدم أو الجدول العادي
        cursor.execute('''
            SELECT * FROM advanced_notifications 
            WHERE is_active = 1 
            AND (expires_at IS NULL OR expires_at > ?)
            AND (target_users = 'all' OR target_users LIKE ?)
            AND (read_by NOT LIKE ? OR read_by IS NULL OR read_by = '')
            ORDER BY priority DESC, created_at DESC
            LIMIT 10
        ''', (current_time_str, f'%{user_id}%', f'%{user_id}%'))

        advanced_notifications = cursor.fetchall()

        # إذا لم توجد إشعارات متقدمة، جلب من الجدول العادي
        if not advanced_notifications:
            cursor.execute('''
                SELECT * FROM notifications 
                WHERE is_active = 1 
                AND (expires_at IS NULL OR expires_at > ?)
                ORDER BY created_at DESC
                LIMIT 5
            ''', (current_time_str,))
            regular_notifications = cursor.fetchall()
            
            notifications_list = []
            for notif in regular_notifications:
                notifications_list.append({
                    'id': notif[0],
                    'title': notif[1],
                    'message': notif[2],
                    'type': notif[3] or 'info',
                    'priority': 1,
                    'is_popup': 0,
                    'created_at': notif[5] if len(notif) > 5 else 'الآن'
                })
        else:
            notifications_list = []
            for notif in advanced_notifications:
                notifications_list.append({
                    'id': notif[0],
                    'title': notif[1],
                    'message': notif[2],
                    'type': notif[3],
                    'priority': notif[5],
                    'is_popup': notif[6],
                    'created_at': notif[8]
                })

        conn.close()
        return jsonify({'notifications': notifications_list})

    except Exception as e:
        print(f"خطأ في API الإشعارات: {e}")
        return jsonify({'notifications': [], 'error': str(e)})

# تعيين الإشعار كمقروء
@app.route('/api/mark-notification-read/<int:notification_id>', methods=['POST'])
def mark_notification_read(notification_id):
    if 'user_id' not in session:
        return jsonify({'error': 'غير مصرح'}), 401

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    user_id = str(session['user_id'])

    cursor.execute('SELECT read_by FROM advanced_notifications WHERE id = ?', (notification_id,))
    result = cursor.fetchone()

    if result:
        read_by = result[0] or ''
        if user_id not in read_by:
            new_read_by = f"{read_by},{user_id}" if read_by else user_id
            cursor.execute('UPDATE advanced_notifications SET read_by = ? WHERE id = ?', 
                          (new_read_by, notification_id))
            conn.commit()

    conn.close()
    return jsonify({'success': True})

# تعطيل الإشعار المنتهي الصلاحية (API للواجهة الأمامية)
@app.route('/api/disable-expired-notification/<int:notification_id>', methods=['POST'])
def disable_expired_notification(notification_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({'error': 'غير مصرح'}), 403
    
    try:
        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()
        
        # الحصول على التوقيت الحالي بتوقيت دمشق مع إضافة 3 ساعات
        from datetime import timezone, timedelta
        damascus_tz = timezone(timedelta(hours=3))  # دمشق UTC+3
        damascus_time = datetime.now(damascus_tz)
        current_time_str = damascus_time.strftime('%Y-%m-%d %H:%M:%S')
        
        # التحقق من انتهاء صلاحية الإشعار قبل التعطيل
        cursor.execute('''
            SELECT title, expires_at FROM notifications 
            WHERE id = ? AND is_active = 1 AND expires_at IS NOT NULL AND expires_at <= ?
        ''', (notification_id, current_time_str))
        
        expired_notification = cursor.fetchone()
        
        if expired_notification:
            # تعطيل الإشعار
            cursor.execute('''
                UPDATE notifications 
                SET is_active = 0 
                WHERE id = ?
            ''', (notification_id,))
            conn.commit()
            
            print(f"✅ تم تعطيل الإشعار من الواجهة: {expired_notification[0]} (ID: {notification_id})")
            
            return jsonify({
                'success': True,
                'message': f'تم تعطيل الإشعار: {expired_notification[0]}',
                'disabled_at': current_time_str
            })
        else:
            # التحقق من الإشعارات المتقدمة
            cursor.execute('''
                SELECT title, expires_at FROM advanced_notifications 
                WHERE id = ? AND is_active = 1 AND expires_at IS NOT NULL AND expires_at <= ?
            ''', (notification_id, current_time_str))
            
            expired_advanced = cursor.fetchone()
            
            if expired_advanced:
                cursor.execute('''
                    UPDATE advanced_notifications 
                    SET is_active = 0 
                    WHERE id = ?
                ''', (notification_id,))
                conn.commit()
                
                print(f"✅ تم تعطيل الإشعار المتقدم من الواجهة: {expired_advanced[0]} (ID: {notification_id})")
                
                return jsonify({
                    'success': True,
                    'message': f'تم تعطيل الإشعار المتقدم: {expired_advanced[0]}',
                    'disabled_at': current_time_str
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'الإشعار غير موجود أو لم تنته صلاحيته بعد'
                })
        
        conn.close()
        
    except Exception as e:
        return jsonify({'error': f'خطأ في تعطيل الإشعار: {str(e)}'}), 500

# تحميل النسخة الاحتياطية
@app.route('/admin/download-backup/<filename>')
def download_backup(filename):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    backup_path = os.path.join('backups', filename)
    if os.path.exists(backup_path):
        return send_file(backup_path, as_attachment=True)
    else:
        flash('الملف غير موجود', 'error')
        return redirect(url_for('admin_backup'))

# رفع واستعادة النسخة الاحتياطية
@app.route('/admin/restore-backup', methods=['POST'])
def restore_backup():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    if 'backup_file' not in request.files:
        flash('لم يتم اختيار ملف', 'error')
        return redirect(url_for('admin_backup'))

    file = request.files['backup_file']
    if file.filename == '':
        flash('لم يتم اختيار ملف', 'error')
        return redirect(url_for('admin_backup'))

    if file and file.filename.endswith('.db'):
        try:
            # إنشاء نسخة احتياطية من قاعدة البيانات الحالية
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            current_backup = f'hussainiya_stores_backup_before_restore_{timestamp}.db'
            shutil.copy2('hussainiya_stores.db', current_backup)

            # استعادة النسخة الاحتياطية المرفوعة
            filename = secure_filename(file.filename)
            file.save('hussainiya_stores.db')

            flash('تم استعادة النسخة الاحتياطية بنجاح', 'success')
        except Exception as e:
            flash(f'خطأ في استعادة النسخة الاحتياطية: {str(e)}', 'error')
    else:
        flash('يجب أن يكون الملف من نوع .db', 'error')

    return redirect(url_for('admin_backup'))

# عرض قائمة النسخ الاحتياطية
@app.route('/admin/list-backups')
def list_backups():
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({'error': 'غير مصرح'}), 403

    backups = []
    if os.path.exists('backups'):
        for filename in os.listdir('backups'):
            if filename.endswith('.db') or filename.endswith('.zip'):
                filepath = os.path.join('backups', filename)
                file_size = os.path.getsize(filepath)
                file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                backups.append({
                    'filename': filename,
                    'size': f"{file_size / 1024:.1f} KB" if file_size < 1024*1024 else f"{file_size / (1024*1024):.1f} MB",
                    'date': file_time.strftime('%Y-%m-%d %H:%M:%S')
                })

    # ترتيب النسخ حسب التاريخ (الأحدث أولاً)
    backups.sort(key=lambda x: x['date'], reverse=True)

    return jsonify({'backups': backups})

# حذف نسخة احتياطية
@app.route('/admin/delete-backup/<filename>')
def delete_backup(filename):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    backup_path = os.path.join('backups', filename)
    if os.path.exists(backup_path):
        os.remove(backup_path)
        flash('تم حذف النسخة الاحتياطية', 'success')
    else:
        flash('الملف غير موجود', 'error')

    return redirect(url_for('admin_backup'))

# الحصول على إشعارات المستخدم
@app.route('/get-notifications')
def get_user_notifications():
    if 'user_id' not in session:
        return jsonify([])

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT 'محل جديد' as type, 'تم إضافة محل جديد' as message, created_at as timestamp
        FROM stores 
        WHERE user_id = ? AND is_approved = 1 
        ORDER BY created_at DESC 
        LIMIT 5
    ''', (session['user_id'],))

    notifications = cursor.fetchall()
    conn.close()

    notifications_list = []
    for notif in notifications:
        notifications_list.append({
            'type': notif[0],
            'message': notif[1],
            'timestamp': notif[2]
        })

    return jsonify(notifications_list)

# تعيين جميع الإشعارات كمقروءة
@app.route('/mark-all-notifications-read', methods=['POST'])
def mark_all_notifications_read():
    if 'user_id' not in session:
        return jsonify({'success': False}), 401

    # يمكن تنفيذ منطق تعيين الإشعارات كمقروءة هنا
    return jsonify({'success': True})

# إضافة التقييمات مع التعليقات
@app.route('/rate-store/<int:store_id>', methods=['POST'])
def rate_store(store_id):
    if 'user_id' not in session:
        return jsonify({'error': 'يجب تسجيل الدخول أولاً'}), 401

    rating = int(request.json.get('rating', 0))
    comment = request.json.get('comment', '').strip()
    
    if rating < 1 or rating > 5:
        return jsonify({'error': 'التقييم يجب أن يكون بين 1 و 5'}), 400
    
    if not comment:
        return jsonify({'error': 'يجب كتابة تعليق مع التقييم'}), 400

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # التحقق من وجود تقييم سابق
    cursor.execute('SELECT id FROM ratings WHERE store_id = ? AND user_id = ?', 
                  (store_id, session['user_id']))
    existing_rating = cursor.fetchone()

    from datetime import timezone, timedelta
    damascus_tz = timezone(timedelta(hours=3))
    damascus_time = datetime.now(damascus_tz)
    current_time_str = damascus_time.strftime('%Y-%m-%d %H:%M:%S')

    is_new_rating = not existing_rating

    if existing_rating:
        # تحديث التقييم الموجود - التحقق من وجود عمود updated_at
        try:
            cursor.execute('UPDATE ratings SET rating = ?, comment = ?, updated_at = ? WHERE store_id = ? AND user_id = ?',
                          (rating, comment, current_time_str, store_id, session['user_id']))
        except sqlite3.OperationalError:
            # إذا لم يكن عمود updated_at موجوداً، تحديث بدونه
            cursor.execute('UPDATE ratings SET rating = ?, comment = ? WHERE store_id = ? AND user_id = ?',
                          (rating, comment, store_id, session['user_id']))
    else:
        # إضافة تقييم جديد - التحقق من وجود عمود updated_at
        try:
            cursor.execute('INSERT INTO ratings (store_id, user_id, rating, comment, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)',
                          (store_id, session['user_id'], rating, comment, current_time_str, current_time_str))
        except sqlite3.OperationalError:
            # إذا لم يكن عمود updated_at موجوداً، إدراج بدونه
            cursor.execute('INSERT INTO ratings (store_id, user_id, rating, comment, created_at) VALUES (?, ?, ?, ?, ?)',
                          (store_id, session['user_id'], rating, comment, current_time_str))

    # حساب متوسط التقييم الجديد
    cursor.execute('SELECT AVG(rating) FROM ratings WHERE store_id = ?', (store_id,))
    avg_rating = cursor.fetchone()[0]

    # تحديث متوسط التقييم في جدول المحلات
    cursor.execute('UPDATE stores SET rating_avg = ? WHERE id = ?', (avg_rating, store_id))

    # الحصول على اسم المحل
    cursor.execute('SELECT name FROM stores WHERE id = ?', (store_id,))
    store_name = cursor.fetchone()
    store_name = store_name[0] if store_name else f'محل #{store_id}'

    conn.commit()
    conn.close()

    # منح النقاط للتقييم الجديد فقط
    if is_new_rating:
        settings = get_points_settings()
        rating_points = settings.get('points_rate_store', 5)
        add_points(session['user_id'], rating_points, 'store_rating', f'تقييم محل: {store_name}', store_id)
        message = 'تم حفظ التقييم والتعليق بنجاح وحصلت على نقاط!'
    else:
        message = 'تم تحديث التقييم والتعليق بنجاح'

    return jsonify({'success': True, 'new_average': avg_rating, 'message': message})

# عرض التقييمات والتعليقات - مع التسجيل الإجباري
@app.route('/store-ratings/<int:store_id>')
def store_ratings(store_id):
    # التحقق من تسجيل الدخول
    if 'user_id' not in session:
        flash('يجب تسجيل الدخول لعرض التقييمات', 'warning')
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # جلب معلومات المحل
    cursor.execute('SELECT name FROM stores WHERE id = ? AND is_approved = 1', (store_id,))
    store = cursor.fetchone()
    
    if not store:
        flash('المحل غير موجود', 'error')
        return redirect(url_for('index'))

    # جلب التقييمات مع أسماء المستخدمين
    # التحقق من وجود عمود updated_at
    try:
        cursor.execute('''
            SELECT r.id, r.rating, r.comment, r.created_at, r.updated_at, u.full_name, r.user_id
            FROM ratings r 
            LEFT JOIN users u ON r.user_id = u.id 
            WHERE r.store_id = ? 
            ORDER BY r.created_at DESC
        ''', (store_id,))
    except sqlite3.OperationalError:
        # إذا لم يكن عمود updated_at موجوداً، استخدم created_at كبديل
        cursor.execute('''
            SELECT r.id, r.rating, r.comment, r.created_at, r.created_at as updated_at, u.full_name, r.user_id
            FROM ratings r 
            LEFT JOIN users u ON r.user_id = u.id 
            WHERE r.store_id = ? 
            ORDER BY r.created_at DESC
        ''', (store_id,))
    ratings = cursor.fetchall()

    # حساب الإحصائيات
    cursor.execute('SELECT AVG(rating), COUNT(*) FROM ratings WHERE store_id = ?', (store_id,))
    stats = cursor.fetchone()
    avg_rating = stats[0] if stats[0] else 0
    total_ratings = stats[1]

    # توزيع النجوم
    star_distribution = {}
    for i in range(1, 6):
        cursor.execute('SELECT COUNT(*) FROM ratings WHERE store_id = ? AND rating = ?', (store_id, i))
        star_distribution[i] = cursor.fetchone()[0]

    conn.close()

    return render_template('store_ratings.html', 
                         store_name=store[0],
                         store_id=store_id,
                         ratings=ratings,
                         avg_rating=avg_rating,
                         total_ratings=total_ratings,
                         star_distribution=star_distribution)

# حذف تقييم (للإدارة)
@app.route('/admin/delete-rating/<int:rating_id>')
def admin_delete_rating(rating_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({'error': 'غير مصرح'}), 403

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # الحصول على معلومات التقييم قبل الحذف
    cursor.execute('SELECT store_id FROM ratings WHERE id = ?', (rating_id,))
    rating = cursor.fetchone()
    
    if not rating:
        conn.close()
        return jsonify({'error': 'التقييم غير موجود'}), 404

    store_id = rating[0]

    # حذف التقييم
    cursor.execute('DELETE FROM ratings WHERE id = ?', (rating_id,))

    # إعادة حساب متوسط التقييم
    cursor.execute('SELECT AVG(rating) FROM ratings WHERE store_id = ?', (store_id,))
    avg_rating = cursor.fetchone()[0] or 0

    # تحديث متوسط التقييم في جدول المحلات
    cursor.execute('UPDATE stores SET rating_avg = ? WHERE id = ?', (avg_rating, store_id))

    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': 'تم حذف التقييم بنجاح'})

# تحديث تعليق المستخدم
@app.route('/update-rating/<int:rating_id>', methods=['POST'])
def update_rating(rating_id):
    if 'user_id' not in session:
        return jsonify({'error': 'يجب تسجيل الدخول أولاً'}), 401

    new_comment = request.json.get('comment', '').strip()
    new_rating = int(request.json.get('rating', 0))
    
    if new_rating < 1 or new_rating > 5:
        return jsonify({'error': 'التقييم يجب أن يكون بين 1 و 5'}), 400
    
    if not new_comment:
        return jsonify({'error': 'يجب كتابة تعليق مع التقييم'}), 400

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # التحقق من أن التقييم يخص المستخدم الحالي
    cursor.execute('SELECT store_id, user_id FROM ratings WHERE id = ?', (rating_id,))
    rating = cursor.fetchone()
    
    if not rating or rating[1] != session['user_id']:
        conn.close()
        return jsonify({'error': 'غير مصرح لك بتعديل هذا التقييم'}), 403

    store_id = rating[0]

    from datetime import timezone, timedelta
    damascus_tz = timezone(timedelta(hours=3))
    damascus_time = datetime.now(damascus_tz)
    current_time_str = damascus_time.strftime('%Y-%m-%d %H:%M:%S')

    # تحديث التقييم والتعليق - التحقق من وجود عمود updated_at
    try:
        cursor.execute('UPDATE ratings SET rating = ?, comment = ?, updated_at = ? WHERE id = ?',
                      (new_rating, new_comment, current_time_str, rating_id))
    except sqlite3.OperationalError:
        # إذا لم يكن عمود updated_at موجوداً، تحديث بدونه
        cursor.execute('UPDATE ratings SET rating = ?, comment = ? WHERE id = ?',
                      (new_rating, new_comment, rating_id))

    # إعادة حساب متوسط التقييم
    cursor.execute('SELECT AVG(rating) FROM ratings WHERE store_id = ?', (store_id,))
    avg_rating = cursor.fetchone()[0]

    # تحديث متوسط التقييم في جدول المحلات
    cursor.execute('UPDATE stores SET rating_avg = ? WHERE id = ?', (avg_rating, store_id))

    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': 'تم تحديث التقييم والتعليق بنجاح'})

# إدارة الشريط المتحرك
@app.route('/admin/ticker')
def admin_ticker():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('ليس لديك صلاحية للوصول لهذه الصفحة', 'error')
        return redirect(url_for('index'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # إضافة عمود الصفحات إذا لم يكن موجوداً
    try:
        cursor.execute('ALTER TABLE ticker_messages ADD COLUMN pages TEXT DEFAULT "all"')
        conn.commit()
    except:
        pass

    cursor.execute('SELECT id, message, type, priority, is_active, direction, speed, background_color, text_color, font_size, created_at, pages FROM ticker_messages ORDER BY priority DESC, created_at DESC')
    ticker_messages = cursor.fetchall()

    conn.close()
    return render_template('admin_ticker.html', ticker_messages=ticker_messages)

# إضافة رسالة للشريط المتحرك
@app.route('/admin/add-ticker', methods=['POST'])
def add_ticker():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    try:
        message = request.form.get('message', '')
        message_type = request.form.get('type', 'custom')
        priority = int(request.form.get('priority', 1))
        direction = request.form.get('direction', 'right')
        speed = int(request.form.get('speed', 50))
        background_color = request.form.get('background_color', '#11998e')
        text_color = request.form.get('text_color', '#ffffff')
        font_size = int(request.form.get('font_size', 16))
        
        # معالجة الصفحات المختارة
        selected_pages = request.form.getlist('pages')
        if 'all' in selected_pages or not selected_pages:
            pages_str = 'all'
        else:
            pages_str = ','.join(selected_pages)

        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()

        # إضافة عمود الصفحات إذا لم يكن موجوداً
        try:
            cursor.execute('ALTER TABLE ticker_messages ADD COLUMN pages TEXT DEFAULT "all"')
        except:
            pass

        # إنشاء رسالة تلقائية حسب النوع
        if message_type == 'latest_stores':
            cursor.execute('''
                SELECT GROUP_CONCAT(name, ' • ') 
                FROM (SELECT name FROM stores WHERE is_approved = 1 ORDER BY created_at DESC LIMIT 5)
            ''')
            result = cursor.fetchone()
            message = f"أحدث المحلات: {result[0] if result and result[0] else 'لا توجد محلات'}"
        elif message_type == 'popular_stores':
            cursor.execute('''
                SELECT GROUP_CONCAT(name, ' • ') 
                FROM (SELECT name FROM stores WHERE is_approved = 1 ORDER BY search_count DESC LIMIT 5)
            ''')
            result = cursor.fetchone()
            message = f"الأكثر بحثاً: {result[0] if result and result[0] else 'لا توجد محلات'}"
        elif message_type == 'top_rated':
            cursor.execute('''
                SELECT GROUP_CONCAT(name, ' • ') 
                FROM (SELECT name FROM stores WHERE is_approved = 1 AND rating_avg > 0 ORDER BY rating_avg DESC LIMIT 5)
            ''')
            result = cursor.fetchone()
            message = f"الأعلى تقييماً: {result[0] if result and result[0] else 'لا توجد محلات'}"
        elif message_type == 'announcement':
            if not message:
                message = "إعلان هام - تابعوا آخر الأخبار والعروض"
        elif message_type == 'emergency':
            if not message:
                message = "⚠️ إشعار طوارئ - للاستفسار اتصل على 110"
        elif message_type == 'welcome':
            if not message:
                message = "مرحباً بكم في دليل محلات الحسينية"

        # التحقق من وجود رسالة
        if not message or message.strip() == '':
            message = "مرحباً بكم في دليل محلات الحسينية"

        cursor.execute('''
            INSERT INTO ticker_messages (message, type, priority, direction, speed, background_color, text_color, font_size, pages) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (message, message_type, priority, direction, speed, background_color, text_color, font_size, pages_str))

        conn.commit()
        conn.close()

        flash('تم إضافة الرسالة للشريط المتحرك بنجاح', 'success')

    except Exception as e:
        flash(f'خطأ في إضافة الرسالة: {str(e)}', 'error')
        print(f"Error in add_ticker: {e}")

    return redirect(url_for('admin_ticker'))

# تحديث رسالة الشريط المتحرك
@app.route('/admin/update-ticker/<int:ticker_id>', methods=['POST'])
def update_ticker(ticker_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    message = request.form['message']
    message_type = request.form['type']
    priority = int(request.form.get('priority', 1))
    is_active = 1 if request.form.get('is_active') else 0
    direction = request.form.get('direction', 'right')
    speed = int(request.form.get('speed', 50))
    background_color = request.form.get('background_color', '#11998e')
    text_color = request.form.get('text_color', '#ffffff')
    font_size = int(request.form.get('font_size', 16))
    
    # معالجة الصفحات المختارة
    selected_pages = request.form.getlist('pages')
    if 'all' in selected_pages or not selected_pages:
        pages_str = 'all'
    else:
        pages_str = ','.join(selected_pages)

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # إضافة عمود الصفحات إذا لم يكن موجوداً
    try:
        cursor.execute('ALTER TABLE ticker_messages ADD COLUMN pages TEXT DEFAULT "all"')
    except:
        pass

    cursor.execute('''
        UPDATE ticker_messages 
        SET message = ?, type = ?, priority = ?, is_active = ?, direction = ?, speed = ?, background_color = ?, text_color = ?, font_size = ?, pages = ?
        WHERE id = ?
    ''', (message, message_type, priority, is_active, direction, speed, background_color, text_color, font_size, pages_str, ticker_id))

    conn.commit()
    conn.close()

    flash('تم تحديث الرسالة بنجاح', 'success')
    return redirect(url_for('admin_ticker'))

# حذف رسالة من الشريط المتحرك
@app.route('/admin/delete-ticker/<int:ticker_id>')
def delete_ticker(ticker_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    cursor.execute('DELETE FROM ticker_messages WHERE id = ?', (ticker_id,))

    conn.commit()
    conn.close()

    flash('تم حذف الرسالة بنجاح', 'success')
    return redirect(url_for('admin_ticker'))

# إنشاء حساب إداري افتراضي
def create_admin_user():
    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # التحقق من وجود حساب إداري بالرقم الجديد
    cursor.execute('SELECT id FROM users WHERE phone = ? AND is_admin = 1', ('0938074766',))
    admin_exists = cursor.fetchone()

    if not admin_exists:
        # تحديث الحساب الإداري القديم إذا وجد
        cursor.execute('UPDATE users SET phone = ?, full_name = ? WHERE is_admin = 1', 
                      ('0938074766', 'مدير النظام'))

        # إذا لم يتم التحديث، إنشاء حساب جديد
        if cursor.rowcount == 0:
            admin_phone = '0938074766'
            admin_password = 'admin123'
            admin_name = 'مدير النظام'

            password_hash = generate_password_hash(admin_password)
            cursor.execute('''
                INSERT INTO users (full_name, phone, password_hash, is_admin, is_active) 
                VALUES (?, ?, ?, 1, 1)
            ''', (admin_name, admin_phone, password_hash))

            print(f"تم إنشاء حساب إداري جديد:")
            print(f"رقم الهاتف: {admin_phone}")
            print(f"كلمة المرور: {admin_password}")
        else:
            print(f"تم تحديث رقم حساب الإدارة إلى: 0938074766")

    conn.commit()
    conn.close()

# إدارة بوت التليجرام
@app.route('/admin/telegram-bot')
def admin_telegram_bot():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('ليس لديك صلاحية للوصول لهذه الصفحة', 'error')
        return redirect(url_for('index'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()
    
    # إنشاء جدول معرفات التليجرام للمديرين إذا لم يكن موجوداً
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_telegram_ids (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            admin_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('SELECT * FROM admin_telegram_ids ORDER BY created_at DESC')
    admin_telegram_ids = cursor.fetchall()
    
    conn.close()
    
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    bot_status = 'متصل' if telegram_bot else 'غير متصل'
    
    return render_template('admin_telegram_bot.html', 
                         admin_telegram_ids=admin_telegram_ids,
                         bot_token_exists=bool(bot_token),
                         bot_status=bot_status)

# إضافة معرف تليجرام مدير
@app.route('/admin/add-telegram-admin', methods=['POST'])
def add_telegram_admin():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    telegram_id = request.form['telegram_id']
    admin_name = request.form.get('admin_name', '')

    try:
        telegram_id = int(telegram_id)
    except ValueError:
        flash('معرف التليجرام يجب أن يكون رقماً', 'error')
        return redirect(url_for('admin_telegram_bot'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO admin_telegram_ids (telegram_id, admin_name) 
            VALUES (?, ?)
        ''', (telegram_id, admin_name))
        conn.commit()
        flash('تم إضافة المدير بنجاح', 'success')
    except sqlite3.IntegrityError:
        flash('هذا المعرف موجود مسبقاً', 'error')
    finally:
        conn.close()

    return redirect(url_for('admin_telegram_bot'))

# حذف معرف تليجرام مدير
@app.route('/admin/delete-telegram-admin/<int:admin_id>')
def delete_telegram_admin(admin_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    cursor.execute('DELETE FROM admin_telegram_ids WHERE id = ?', (admin_id,))
    conn.commit()
    conn.close()

    flash('تم حذف المدير بنجاح', 'success')
    return redirect(url_for('admin_telegram_bot'))

# إعادة الاتصال ببوت التليجرام
@app.route('/admin/reconnect-telegram-bot', methods=['POST'])
def reconnect_telegram_bot():
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({'error': 'غير مصرح'}), 403
    
    global telegram_bot, telegram_app
    
    try:
        # إيقاف البوت الحالي إذا كان يعمل
        if telegram_app:
            try:
                asyncio.run(telegram_app.stop())
            except:
                pass
        
        telegram_bot = None
        telegram_app = None
        
        # محاولة إعادة التهيئة
        if init_telegram_bot():
            return jsonify({
                'success': True,
                'message': 'تم إعادة الاتصال بالبوت بنجاح (سيعمل مع الطلبات)',
                'status': 'متصل'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'فشل في إعادة الاتصال بالبوت. تأكد من صحة التوكن',
                'status': 'غير متصل'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'خطأ في إعادة الاتصال: {str(e)}',
            'status': 'غير متصل'
        })

# API للحصول على حالة البوت
@app.route('/api/telegram-bot-status')
def get_telegram_bot_status():
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({'error': 'غير مصرح'}), 403
    
    bot_token = get_telegram_bot_token()
    bot_status = 'متصل' if telegram_bot else 'غير متصل'
    
    return jsonify({
        'token_exists': bool(bot_token),
        'status': bot_status,
        'connected': telegram_bot is not None
    })

# حفظ توكن بوت التليجرام
@app.route('/admin/save-telegram-token', methods=['POST'])
def save_telegram_token():
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({'error': 'غير مصرح'}), 403
    
    token = request.json.get('token', '').strip()
    
    if not token:
        return jsonify({'success': False, 'message': 'التوكن مطلوب'})
    
    # التحقق من صحة تنسيق التوكن
    import re
    if not re.match(r'^\d+:[A-Za-z0-9_-]+$', token):
        return jsonify({'success': False, 'message': 'تنسيق التوكن غير صحيح'})
    
    if save_telegram_bot_token(token):
        return jsonify({'success': True, 'message': 'تم حفظ التوكن بنجاح'})
    else:
        return jsonify({'success': False, 'message': 'خطأ في حفظ التوكن'})

# حذف توكن بوت التليجرام
@app.route('/admin/delete-telegram-token', methods=['POST'])
def delete_telegram_token():
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({'error': 'غير مصرح'}), 403
    
    try:
        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM site_settings WHERE setting_key = ?', ('telegram_bot_token',))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'تم حذف التوكن بنجاح'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'خطأ في حذف التوكن: {str(e)}'})

# الحصول على التوكن المحفوظ (مخفي جزئياً)
@app.route('/api/get-telegram-token')
def get_saved_telegram_token():
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({'error': 'غير مصرح'}), 403
    
    token = get_telegram_bot_token()
    if token:
        # إخفاء جزء من التوكن للأمان
        if ':' in token:
            parts = token.split(':')
            hidden_token = parts[0] + ':' + parts[1][:8] + '...' + parts[1][-8:]
        else:
            hidden_token = token[:8] + '...' + token[-8:]
        
        return jsonify({'token': hidden_token, 'has_token': True})
    else:
        return jsonify({'token': '', 'has_token': False})

# معالج الأخطاء 404
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# معالج الأخطاء 500
@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    try:
        init_db()
        create_settings_table()
        create_admin_user()
        
        # بدء النظام التلقائي للتحقق من انتهاء صلاحية الإشعارات
        start_notification_checker()
        
        # تهيئة بوت التليجرام فقط (بدون تشغيل في خيط منفصل)
        if init_telegram_bot():
            print("✅ تم تهيئة بوت التليجرام بنجاح (سيعمل عند الحاجة)")
        else:
            print("❌ فشل في تهيئة بوت التليجرام")
        
        print("تم تهيئة قاعدة البيانات بنجاح")
        print("رابط التطبيق: http://0.0.0.0:5000")
        print("لوحة الإدارة: http://0.0.0.0:5000/admin")
        print("إدارة بوت التليجرام: http://0.0.0.0:5000/admin/telegram-bot")
        
        # محاولة استخدام بورت مختلف إذا كان 5000 مشغولاً
        import socket
        def is_port_in_use(port):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(('0.0.0.0', port)) == 0
        
        port = 5000
        while is_port_in_use(port) and port < 5010:
            port += 1
        
        if port != 5000:
            print(f"البورت 5000 مشغول، سيتم استخدام البورت {port}")
        
        app.run(host='0.0.0.0', port=port, debug=True)
    except Exception as e:
        print(f"خطأ في تشغيل التطبيق: {e}")