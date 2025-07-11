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
                    <title>المنصة تحت الصيانة</title>
                    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700&display=swap" rel="stylesheet">
                    <style>
                        * { margin: 0; padding: 0; box-sizing: border-box; }
                        
                        body { 
                            font-family: 'Cairo', sans-serif; 
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            min-height: 100vh; 
                            display: flex; 
                            align-items: center; 
                            justify-content: center;
                            overflow: hidden;
                            position: relative;
                        }
                        
                        /* خلفية متحركة */
                        .bg-animation {
                            position: absolute;
                            top: 0;
                            left: 0;
                            width: 100%;
                            height: 100%;
                            overflow: hidden;
                            z-index: 1;
                        }
                        
                        .bg-animation span {
                            position: absolute;
                            display: block;
                            width: 20px;
                            height: 20px;
                            background: rgba(255, 255, 255, 0.1);
                            animation: animate 10s linear infinite;
                            bottom: -150px;
                        }
                        
                        @keyframes animate {
                            0% { transform: translateY(0) rotate(0deg); opacity: 1; border-radius: 0; }
                            100% { transform: translateY(-1000px) rotate(720deg); opacity: 0; border-radius: 50%; }
                        }
                        
                        .container { 
                            background: rgba(255, 255, 255, 0.95); 
                            padding: 60px 40px; 
                            border-radius: 25px; 
                            text-align: center; 
                            box-shadow: 0 25px 50px rgba(0,0,0,0.2);
                            max-width: 600px;
                            backdrop-filter: blur(10px);
                            border: 1px solid rgba(255, 255, 255, 0.3);
                            position: relative;
                            z-index: 2;
                            animation: fadeIn 1s ease-out;
                        }
                        
                        @keyframes fadeIn {
                            from { opacity: 0; transform: translateY(30px); }
                            to { opacity: 1; transform: translateY(0); }
                        }
                        
                        .icon-container {
                            position: relative;
                            display: inline-block;
                            margin-bottom: 30px;
                        }
                        
                        .icon { 
                            font-size: 5em; 
                            background: linear-gradient(135deg, #ffc107, #ff8f00);
                            -webkit-background-clip: text;
                            -webkit-text-fill-color: transparent;
                            background-clip: text;
                            animation: pulse 2s infinite;
                        }
                        
                        @keyframes pulse {
                            0%, 100% { transform: scale(1); }
                            50% { transform: scale(1.1); }
                        }
                        
                        h1 { 
                            color: #2c3e50; 
                            margin-bottom: 25px; 
                            font-size: 2.8em; 
                            font-weight: 700;
                            background: linear-gradient(135deg, #667eea, #764ba2);
                            -webkit-background-clip: text;
                            -webkit-text-fill-color: transparent;
                            background-clip: text;
                        }
                        
                        .subtitle {
                            color: #7f8c8d;
                            font-size: 1.1em;
                            margin-bottom: 15px;
                            font-weight: 600;
                        }
                        
                        .description { 
                            color: #95a5a6; 
                            font-size: 1.1em; 
                            line-height: 1.8;
                            margin-bottom: 35px;
                        }
                        
                        
                        
                        .progress-bar {
                            width: 100%;
                            height: 6px;
                            background: rgba(102, 126, 234, 0.2);
                            border-radius: 3px;
                            overflow: hidden;
                            margin: 30px 0 20px;
                        }
                        
                        .progress {
                            height: 100%;
                            background: linear-gradient(90deg, #667eea, #764ba2);
                            width: 0%;
                            animation: loading 3s ease-in-out infinite;
                            border-radius: 3px;
                        }
                        
                        @keyframes loading {
                            0% { width: 0%; }
                            50% { width: 70%; }
                            100% { width: 100%; }
                        }
                        
                        .status-text {
                            color: #667eea;
                            font-size: 0.95em;
                            font-weight: 600;
                            margin-bottom: 20px;
                        }
                        
                        .footer {
                            margin-top: 40px;
                            padding-top: 25px;
                            border-top: 1px solid rgba(102, 126, 234, 0.2);
                            color: #95a5a6;
                            font-size: 0.9em;
                        }
                        
                        /* عنصر مخفي للوصول لصفحة الإدارة */
                        .hidden-admin {
                            position: absolute;
                            bottom: 10px;
                            right: 10px;
                            width: 10px;
                            height: 10px;
                            background: transparent;
                            cursor: pointer;
                            border: none;
                            opacity: 0;
                        }
                        
                        .hidden-admin:hover {
                            opacity: 0.1;
                            background: rgba(102, 126, 234, 0.1);
                        }
                        
                        @media (max-width: 768px) {
                            .container { 
                                margin: 15px; 
                                padding: 30px 20px; 
                                max-width: 95%;
                            }
                            h1 { 
                                font-size: 2rem; 
                                margin-bottom: 20px;
                            }
                            .icon { 
                                font-size: 3.5em; 
                            }
                            .subtitle {
                                font-size: 1rem;
                                margin-bottom: 12px;
                            }
                            .description {
                                font-size: 1rem;
                                line-height: 1.6;
                                margin-bottom: 25px;
                            }
                            .progress-bar {
                                margin: 25px 0 15px;
                            }
                            .status-text {
                                font-size: 0.9rem;
                                margin-bottom: 15px;
                            }
                            .footer {
                                margin-top: 30px;
                                padding-top: 20px;
                                font-size: 0.85rem;
                            }
                        }
                        
                        @media (max-width: 480px) {
                            .container {
                                margin: 10px;
                                padding: 25px 15px;
                                max-width: 98%;
                            }
                            h1 {
                                font-size: 1.8rem;
                            }
                            .icon {
                                font-size: 3rem;
                            }
                            .subtitle {
                                font-size: 0.95rem;
                            }
                            .description {
                                font-size: 0.95rem;
                            }
                        }
                    </style>
                </head>
                <body>
                    <div class="bg-animation">
                        <span style="left: 10%; animation-delay: 0s;"></span>
                        <span style="left: 20%; animation-delay: 2s;"></span>
                        <span style="left: 30%; animation-delay: 4s;"></span>
                        <span style="left: 40%; animation-delay: 6s;"></span>
                        <span style="left: 50%; animation-delay: 8s;"></span>
                        <span style="left: 60%; animation-delay: 10s;"></span>
                        <span style="left: 70%; animation-delay: 12s;"></span>
                        <span style="left: 80%; animation-delay: 14s;"></span>
                        <span style="left: 90%; animation-delay: 16s;"></span>
                    </div>
                    
                    <div class="container">
                        <div class="icon-container">
                            <div class="icon">⚙️</div>
                        </div>
                        
                        <h1>المنصة تحت الصيانة</h1>
                        <div class="subtitle">جاري العمل على تحسين الخدمات</div>
                        <div class="description">
                            نعتذر عن الإزعاج، نقوم حالياً بأعمال صيانة وتطوير لتحسين تجربتك وإضافة ميزات جديدة.<br>
                            سنعود قريباً بخدمات محسّنة وأداء أفضل!
                        </div>
                        
                        
                        
                        <div class="progress-bar">
                            <div class="progress"></div>
                        </div>
                        <div class="status-text">جاري إتمام أعمال الصيانة...</div>
                        
                        <div class="footer">
                            <strong>شكراً لصبركم</strong><br>
                            فريق دليلك في الحسينية
                        </div>
                        
                        <!-- عنصر مخفي للوصول لصفحة الإدارة -->
                        <button class="hidden-admin" onclick="showAdminLogin()" title=""></button>
                        
                        <!-- نافذة تسجيل دخول المدير المخفية -->
                        <div id="adminLoginModal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 10000; backdrop-filter: blur(5px);">
                            <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); background: white; padding: 30px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); min-width: 300px;">
                                <h4 style="text-align: center; color: #667eea; margin-bottom: 20px; font-family: 'Cairo', sans-serif;">🔐 دخول الإدارة</h4>
                                <form id="adminLoginForm" onsubmit="submitAdminLogin(event)">
                                    <div style="margin-bottom: 15px;">
                                        <label style="display: block; margin-bottom: 5px; color: #555; font-weight: 600;">رقم الهاتف:</label>
                                        <input type="tel" id="adminPhone" placeholder="09xxxxxxxx" style="width: 100%; padding: 10px; border: 2px solid #ddd; border-radius: 8px; font-size: 14px;" required>
                                    </div>
                                    <div style="margin-bottom: 20px;">
                                        <label style="display: block; margin-bottom: 5px; color: #555; font-weight: 600;">كلمة المرور:</label>
                                        <input type="password" id="adminPassword" style="width: 100%; padding: 10px; border: 2px solid #ddd; border-radius: 8px; font-size: 14px;" required>
                                    </div>
                                    <div style="display: flex; gap: 10px;">
                                        <button type="submit" style="flex: 1; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 12px; border-radius: 8px; font-weight: 600; cursor: pointer;">دخول</button>
                                        <button type="button" onclick="hideAdminLogin()" style="flex: 1; background: #dc3545; color: white; border: none; padding: 12px; border-radius: 8px; font-weight: 600; cursor: pointer;">إلغاء</button>
                                    </div>
                                </form>
                                <div id="adminLoginError" style="color: #dc3545; text-align: center; margin-top: 10px; display: none; font-size: 14px;"></div>
                            </div>
                        </div>
                    </div>
                    
                    <script>
                        // تأثير إضافي لجعل الصفحة أكثر تفاعلية
                        document.addEventListener('DOMContentLoaded', function() {
                            // تحديث النص بشكل دوري
                            const statusTexts = [
                                'جاري إتمام أعمال الصيانة...',
                                'تحديث قاعدة البيانات...',
                                'تحسين الأداء...',
                                'اختبار الميزات الجديدة...',
                                'التحقق من الأنظمة...'
                            ];
                            
                            let currentIndex = 0;
                            const statusElement = document.querySelector('.status-text');
                            
                            setInterval(() => {
                                currentIndex = (currentIndex + 1) % statusTexts.length;
                                statusElement.style.opacity = '0';
                                setTimeout(() => {
                                    statusElement.textContent = statusTexts[currentIndex];
                                    statusElement.style.opacity = '1';
                                }, 300);
                            }, 4000);
                        });
                        
                        // وظائف إدارة نافذة تسجيل دخول المدير
                        function showAdminLogin() {
                            document.getElementById('adminLoginModal').style.display = 'block';
                            document.getElementById('adminPhone').focus();
                        }
                        
                        function hideAdminLogin() {
                            document.getElementById('adminLoginModal').style.display = 'none';
                            document.getElementById('adminLoginForm').reset();
                            document.getElementById('adminLoginError').style.display = 'none';
                        }
                        
                        function submitAdminLogin(event) {
                            event.preventDefault();
                            
                            const phone = document.getElementById('adminPhone').value;
                            const password = document.getElementById('adminPassword').value;
                            const errorDiv = document.getElementById('adminLoginError');
                            
                            // إخفاء أي رسائل خطأ سابقة
                            errorDiv.style.display = 'none';
                            
                            // إرسال بيانات تسجيل الدخول
                            fetch('/login', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/x-www-form-urlencoded',
                                },
                                body: `phone=${encodeURIComponent(phone)}&password=${encodeURIComponent(password)}`
                            })
                            .then(response => {
                                // التحقق من نوع الاستجابة
                                const contentType = response.headers.get('content-type');
                                if (contentType && contentType.includes('application/json')) {
                                    return response.json();
                                } else {
                                    return response.text();
                                }
                            })
                            .then(data => {
                                if (typeof data === 'object' && data.success) {
                                    // نجح تسجيل الدخول، توجيه إلى لوحة الإدارة
                                    window.location.href = '/admin';
                                } else if (typeof data === 'object' && !data.success) {
                                    // فشل تسجيل الدخول مع رسالة محددة
                                    errorDiv.textContent = data.message;
                                    errorDiv.style.display = 'block';
                                } else {
                                    // استجابة HTML (ربما صفحة تسجيل الدخول مع خطأ)
                                    errorDiv.textContent = 'رقم الهاتف أو كلمة المرور غير صحيحة أو ليس لديك صلاحيات إدارية';
                                    errorDiv.style.display = 'block';
                                }
                            })
                            .catch(error => {
                                console.error('Error:', error);
                                errorDiv.textContent = 'حدث خطأ أثناء تسجيل الدخول';
                                errorDiv.style.display = 'block';
                            });
                        }
                        
                        // إغلاق النافذة عند الضغط خارجها
                        document.addEventListener('click', function(event) {
                            const modal = document.getElementById('adminLoginModal');
                            if (event.target === modal) {
                                hideAdminLogin();
                            }
                        });
                        
                        // إغلاق النافذة عند الضغط على Escape
                        document.addEventListener('keydown', function(event) {
                            if (event.key === 'Escape') {
                                hideAdminLogin();
                            }
                        });
                    </script>
                </body>
                </html>
            ''', 503
    except Exception as e:
        print(f"خطأ في التحقق من وضع الصيانة: {e}")
        pass

# Context processor لإضافة معلومات المستخدم
@app.context_processor
def inject_user_info():
    user_verification_status = False
    user_can_edit_name = True
    
    if 'user_id' in session:
        try:
            conn = sqlite3.connect('hussainiya_stores.db')
            cursor = conn.cursor()
            cursor.execute('SELECT is_verified, can_edit_name FROM users WHERE id = ?', (session['user_id'],))
            result = cursor.fetchone()
            if result:
                user_verification_status = bool(result[0])
                user_can_edit_name = bool(result[1])
            conn.close()
        except Exception as e:
            print(f"خطأ في الحصول على معلومات التحقق: {e}")
    
    return dict(
        user_verification_status=user_verification_status,
        user_can_edit_name=user_can_edit_name
    )

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
            is_verified BOOLEAN DEFAULT 0,
            can_edit_name BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # إضافة أعمدة التحقق إذا لم تكن موجودة
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT 0')
    except:
        pass
    
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN can_edit_name BOOLEAN DEFAULT 1')
    except:
        pass

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
        conn.commit()
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

    # جدول الإشعارات المتقدمة
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS advanced_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            type TEXT DEFAULT 'info',
            target_users TEXT DEFAULT 'all',
            target_roles TEXT DEFAULT 'all',
            priority INTEGER DEFAULT 1,
            is_popup BOOLEAN DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            action_type TEXT DEFAULT 'none',
            action_url TEXT,
            action_page_content TEXT,
            custom_css TEXT,
            custom_js TEXT,
            show_count INTEGER DEFAULT 0,
            max_shows INTEGER DEFAULT -1,
            auto_dismiss INTEGER DEFAULT 0,
            requires_action BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            read_by TEXT DEFAULT '',
            created_by INTEGER,
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
    ''')

    # إضافة الأعمدة المفقودة للجداول الموجودة
    columns_to_add = [
        ('advanced_notifications', 'created_by', 'INTEGER'),
        ('advanced_notifications', 'read_by', 'TEXT DEFAULT ""'),
        ('advanced_notifications', 'target_roles', 'TEXT DEFAULT "all"'),
        ('advanced_notifications', 'action_type', 'TEXT DEFAULT "none"'),
        ('advanced_notifications', 'action_url', 'TEXT'),
        ('advanced_notifications', 'action_page_content', 'TEXT'),
        ('advanced_notifications', 'custom_css', 'TEXT'),
        ('advanced_notifications', 'custom_js', 'TEXT'),
        ('advanced_notifications', 'show_count', 'INTEGER DEFAULT 0'),
        ('advanced_notifications', 'max_shows', 'INTEGER DEFAULT -1'),
        ('advanced_notifications', 'auto_dismiss', 'INTEGER DEFAULT 0'),
        ('advanced_notifications', 'requires_action', 'BOOLEAN DEFAULT 0')
    ]

    for table_name, column_name, column_def in columns_to_add:
        try:
            cursor.execute(f'ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}')
        except sqlite3.OperationalError:
            pass  # العمود موجود بالفعل

    # جدول قراءة الإشعارات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notification_reads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            notification_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            read_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            action_taken TEXT,
            FOREIGN KEY (notification_id) REFERENCES advanced_notifications (id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            UNIQUE(notification_id, user_id)
        )
    ''')

    # جدول إحصائيات الإشعارات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notification_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            notification_id INTEGER NOT NULL,
            total_sent INTEGER DEFAULT 0,
            total_read INTEGER DEFAULT 0,
            total_clicked INTEGER DEFAULT 0,
            total_dismissed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (notification_id) REFERENCES advanced_notifications (id) ON DELETE CASCADE
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

    # جدول طلبات التحقق
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS verification_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            full_name TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            admin_notes TEXT,
            requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed_at TIMESTAMP,
            processed_by INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
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
        # إنشاء جدول الإشعارات المتقدمة إذا لم يكن موجوداً مع جميع الأعمدة
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS advanced_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                type TEXT DEFAULT 'info',
                target_users TEXT DEFAULT 'all',
                target_roles TEXT DEFAULT 'all',
                priority INTEGER DEFAULT 1,
                is_popup BOOLEAN DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                action_type TEXT DEFAULT 'none',
                action_url TEXT,
                action_page_content TEXT,
                custom_css TEXT,
                custom_js TEXT,
                show_count INTEGER DEFAULT 0,
                max_shows INTEGER DEFAULT -1,
                auto_dismiss INTEGER DEFAULT 0,
                requires_action BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                read_by TEXT DEFAULT '',
                created_by INTEGER,
                FOREIGN KEY (created_by) REFERENCES users (id)
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

    # التأكد من وجود جدول إحصائيات الإشعارات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notification_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            notification_id INTEGER NOT NULL,
            total_sent INTEGER DEFAULT 0,
            total_read INTEGER DEFAULT 0,
            total_clicked INTEGER DEFAULT 0,
            total_dismissed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (notification_id) REFERENCES advanced_notifications (id) ON DELETE CASCADE
        )
    ''')

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
    search_type = request.args.get('type', 'stores')  # stores, all, services

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

    # التحقق من حالة التحقق للمستخدم
    user_verification_status = False
    if 'user_id' in session:
        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()
        cursor.execute('SELECT is_verified FROM users WHERE id = ?', (session['user_id'],))
        result = cursor.fetchone()
        if result:
            user_verification_status = bool(result[0])
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
                         total_results=total_results,
                         user_verification_status=user_verification_status)

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

# وظيفة للتحقق من الأسماء العربية
def validate_arabic_name(name):
    """التحقق من أن الاسم باللغة العربية ويحتوي على اسم وكنية على الأقل"""
    import re
    
    # إزالة المسافات الزائدة
    name = name.strip()
    
    # التحقق من أن الاسم يحتوي على أحرف عربية فقط
    arabic_pattern = r'^[\u0600-\u06FF\s]+$'
    if not re.match(arabic_pattern, name):
        return False, 'يجب أن يكون الاسم باللغة العربية فقط'
    
    # تقسيم الاسم إلى أجزاء
    name_parts = [part for part in name.split() if part]
    
    # التحقق من عدد الأجزاء
    if len(name_parts) < 2:
        return False, 'يجب أن يتكون الاسم من اسم وكنية على الأقل'
    
    if len(name_parts) > 4:
        return False, 'الاسم طويل جداً، يجب ألا يزيد عن 4 كلمات'
    
    # التحقق من طول كل جزء
    for part in name_parts:
        if len(part) < 2:
            return False, 'كل جزء من الاسم يجب أن يكون على الأقل حرفين'
        if len(part) > 15:
            return False, 'كل جزء من الاسم يجب ألا يزيد عن 15 حرف'
    
    # التحقق من عدم تكرار نفس الكلمة
    if len(set(name_parts)) != len(name_parts):
        return False, 'لا يجوز تكرار نفس الكلمة في الاسم (مثل محمد محمد)'
    
    return True, 'الاسم صحيح'

def check_name_exists(name):
    """التحقق من وجود اسم مماثل في قاعدة البيانات وإعطاء اقتراحات"""
    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()
    
    # البحث عن الاسم الكامل
    cursor.execute('SELECT full_name FROM users WHERE full_name = ?', (name,))
    exact_match = cursor.fetchone()
    
    if exact_match:
        conn.close()
        name_parts = name.split()
        if len(name_parts) == 2:
            return True, 'هذا الاسم مسجل مسبقاً. يرجى إدخال الاسم الثلاثي (الاسم + اسم الأب + الكنية) للتمييز'
        elif len(name_parts) == 3:
            return True, 'هذا الاسم مسجل مسبقاً. يرجى إدخال الاسم والكنية فقط أو إضافة اسم الجد للتمييز'
        else:
            return True, 'هذا الاسم مسجل مسبقاً. يرجى التأكد من صحة الاسم أو كتابته بصيغة أخرى'
    
    # البحث عن أسماء مشابهة (نفس الاسم الأول والأخير)
    name_parts = name.split()
    if len(name_parts) >= 2:
        first_name = name_parts[0]
        last_name = name_parts[-1]
        
        cursor.execute('''
            SELECT full_name FROM users 
            WHERE full_name LIKE ? AND full_name LIKE ?
        ''', (f'{first_name}%', f'%{last_name}'))
        
        similar_names = cursor.fetchall()
        
        if similar_names:
            conn.close()
            if len(name_parts) == 2:
                return True, f'يوجد اسم مشابه مسجل مسبقاً. يرجى إدخال الاسم الثلاثي (الاسم + اسم الأب + الكنية) للتمييز'
            else:
                return True, f'يوجد اسم مشابه مسجل مسبقاً. يرجى التأكد من صحة الاسم أو إضافة المزيد من التفاصيل للتمييز'
    
    conn.close()
    return False, ''

# تسجيل مستخدم جديد
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name'].strip()
        phone = request.form['phone']
        password = request.form['password']

        # التحقق من صحة الاسم العربي
        name_valid, name_error = validate_arabic_name(full_name)
        if not name_valid:
            flash(name_error, 'error')
            return render_template('register.html')

        # التحقق من عدم وجود الاسم مسبقاً
        name_exists, name_exists_error = check_name_exists(full_name)
        if name_exists:
            flash(name_exists_error, 'error')
            return render_template('register.html')

        # التحقق من صحة رقم الهاتف
        if not validate_syrian_phone(phone):
            flash('رقم الهاتف يجب أن يكون سوري ويبدأ بـ 09 ويتكون من 10 أرقام', 'error')
            return render_template('register.html')

        # التحقق من عدم وجود رقم الهاتف مسبقاً
        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE phone = ?', (phone,))
        if cursor.fetchone():
            flash('رقم الهاتف مسجل مسبقاً', 'error')
            conn.close()
            return render_template('register.html')

        # إنشاء المستخدم الجديد - مع التحقق التلقائي ومنع تعديل الاسم
        password_hash = generate_password_hash(password)
        cursor.execute('INSERT INTO users (full_name, phone, password_hash, is_verified, can_edit_name) VALUES (?, ?, ?, 1, 0)',
                      (full_name, phone, password_hash))
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()

        # تسجيل دخول المستخدم تلقائياً
        session['user_id'] = user_id
        session['user_name'] = full_name
        session['is_admin'] = False
        
        # منح نقاط الدخول اليومي
        award_daily_login_points(user_id)

        flash('مرحباً بك! تم إنشاء حسابك بنجاح مع التحقق التلقائي ودخولك تلقائياً ✅', 'success')
        return redirect(url_for('dashboard'))

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
                
                # التحقق من طلب Ajax للمدير من صفحة الصيانة فقط
                ajax_request = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', '')
                if ajax_request and user[4]:
                    # تسجيل دخول مدير عبر Ajax من صفحة الصيانة
                    return jsonify({'success': True, 'is_admin': True, 'message': 'تم تسجيل الدخول بنجاح'})
                elif ajax_request and not user[4]:
                    # محاولة دخول من غير مدير عبر Ajax
                    return jsonify({'success': False, 'message': 'ليس لديك صلاحيات إدارية'})
                
                # منح نقاط الدخول اليومي
                if award_daily_login_points(user[0]):
                    flash('مرحباً بك! تم منحك نقاط الدخول اليومي', 'success')
                else:
                    flash('مرحباً بك!', 'success')
                
                # التوجيه إلى لوحة الإدارة للمديرين أو لوحة التحكم للمستخدمين العاديين
                if user[4]:  # is_admin
                    return redirect(url_for('admin_dashboard'))
                else:
                    return redirect(url_for('dashboard'))
            else:
                if ajax_request:
                    return jsonify({'success': False, 'message': 'حسابك معطل، تواصل مع الإدارة'})
                flash('حسابك معطل، تواصل مع الإدارة', 'error')
        else:
            ajax_request = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', '')
            if ajax_request:
                return jsonify({'success': False, 'message': 'رقم الهاتف أو كلمة المرور غير صحيحة'})
            flash('رقم الهاتف أو كلمة المرور غير صحيحة', 'error')

    return render_template('login.html')

# تسجيل الخروج
@app.route('/logout')
def logout():
    session.clear()
    flash('تم تسجيل الخروج بنجاح', 'success')
    return redirect(url_for('index'))

# صفحة إشعارات المستخدم
@app.route('/notifications')
def user_notifications():
    if 'user_id' not in session:
        flash('يجب تسجيل الدخول لعرض الإشعارات', 'error')
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()
    
    user_id = session['user_id']
    is_admin = session.get('is_admin', False)
    
    # الحصول على جميع الإشعارات المناسبة للمستخدم
    cursor.execute('''
        SELECT an.id, an.title, an.message, an.type, an.priority, an.is_popup,
               an.action_type, an.action_url, an.created_at, an.expires_at,
               CASE WHEN nr.id IS NOT NULL THEN 1 ELSE 0 END as is_read
        FROM advanced_notifications an
        LEFT JOIN notification_reads nr ON an.id = nr.notification_id AND nr.user_id = ?
        WHERE an.is_active = 1 
            AND (an.target_users = 'all' 
                 OR (an.target_users = 'admins' AND ?)
                 OR (an.target_users = 'users' AND NOT ?)
                 OR an.target_users LIKE '%'||?||'%')
        ORDER BY an.created_at DESC
    ''', (user_id, is_admin, is_admin, str(user_id)))
    
    all_notifications = cursor.fetchall()
    
    # فصل الإشعارات المقروءة وغير المقروءة
    unread_notifications = [notif for notif in all_notifications if notif[10] == 0]
    read_notifications = [notif for notif in all_notifications if notif[10] == 1]
    
    conn.close()
    
    return render_template('user_notifications.html',
                         unread_notifications=unread_notifications,
                         read_notifications=read_notifications,
                         total_unread=len(unread_notifications))

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

# وظيفة للتحقق من التحقق والتوجيه
def check_verification_required():
    """التحقق من أن المستخدم محقق أو توجيهه لصفحة التحقق"""
    if 'user_id' not in session:
        flash('يجب تسجيل الدخول أولاً', 'error')
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()
    cursor.execute('SELECT is_verified FROM users WHERE id = ?', (session['user_id'],))
    user = cursor.fetchone()
    conn.close()
    
    if not user or not user[0]:
        flash('يجب التحقق من حسابك لإجراء هذه العملية. يرجى طلب التحقق من الإدارة.', 'warning')
        return redirect(url_for('verification_page'))
    
    return None

# صفحة طلب التحقق
@app.route('/verification')
def verification_page():
    if 'user_id' not in session:
        flash('يجب تسجيل الدخول أولاً', 'error')
        return redirect(url_for('login'))
    
    # التحقق من حالة المستخدم
    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()
    cursor.execute('SELECT is_verified FROM users WHERE id = ?', (session['user_id'],))
    user = cursor.fetchone()
    
    if user and user[0]:
        flash('حسابك محقق بالفعل', 'success')
        conn.close()
        return redirect(url_for('dashboard'))
    
    # التحقق من طلبات التحقق السابقة
    cursor.execute('''
        SELECT status, admin_notes, requested_at FROM verification_requests 
        WHERE user_id = ? 
        ORDER BY requested_at DESC 
        LIMIT 1
    ''', (session['user_id'],))
    last_request = cursor.fetchone()
    
    conn.close()
    
    return render_template('verification_page.html', last_request=last_request)

# طلب التحقق
@app.route('/request-verification', methods=['POST'])
def request_verification():
    if 'user_id' not in session:
        return jsonify({'error': 'يجب تسجيل الدخول أولاً'}), 401
    
    user_id = session['user_id']
    
    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()
    
    # التحقق من وجود طلب معلق
    cursor.execute('SELECT id FROM verification_requests WHERE user_id = ? AND status = "pending"', (user_id,))
    if cursor.fetchone():
        conn.close()
        return jsonify({'error': 'لديك طلب تحقق معلق بالفعل'}), 400
    
    # التحقق من أن المستخدم غير محقق
    cursor.execute('SELECT is_verified FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    if user and user[0]:
        conn.close()
        return jsonify({'error': 'حسابك محقق بالفعل'}), 400
    
    # الحصول على اسم المستخدم الحالي
    cursor.execute('SELECT full_name FROM users WHERE id = ?', (user_id,))
    user_data = cursor.fetchone()
    if not user_data:
        conn.close()
        return jsonify({'error': 'خطأ في بيانات المستخدم'}), 400
    
    full_name = user_data[0]
    
    # التحقق من صحة الاسم العربي
    name_valid, name_error = validate_arabic_name(full_name)
    if not name_valid:
        conn.close()
        return jsonify({'error': name_error}), 400
    
    # إنشاء طلب التحقق
    cursor.execute('''
        INSERT INTO verification_requests (user_id, full_name) 
        VALUES (?, ?)
    ''', (user_id, full_name))
    
    conn.commit()
    
    # الحصول على معلومات المستخدم للإشعار
    cursor.execute('SELECT full_name, phone FROM users WHERE id = ?', (user_id,))
    user_info = cursor.fetchone()
    
    conn.close()
    
    # إرسال إشعار للإدارة عبر التليجرام
    try:
        if telegram_bot:
            asyncio.run(send_verification_request_notification(user_id, user_info[0], user_info[1]))
    except Exception as e:
        print(f"خطأ في إرسال إشعار التحقق: {e}")
    
    return jsonify({'success': True, 'message': 'تم إرسال طلب التحقق بنجاح'})

# استبدال هدية
@app.route('/redeem-gift/<int:gift_id>', methods=['POST'])
def redeem_gift(gift_id):
    if 'user_id' not in session:
        return jsonify({'error': 'يجب تسجيل الدخول أولاً', 'redirect': '/login'}), 401
    
    user_id = session['user_id']
    
    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()
    
    # التحقق من أن المستخدم محقق
    cursor.execute('SELECT is_verified FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    
    if not user or not user[0]:
        conn.close()
        return jsonify({'error': 'يجب أن يكون حسابك محققاً لاستبدال النقاط', 'redirect': '/verification'}), 403
    
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
                asyncio.run(send_redemption_notification(user_id, gift[1], gift_points_cost))
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

# صفحة إضافة محل جديد للمديرين
@app.route('/admin/add-store', methods=['GET'])
def admin_add_store_page():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('ليس لديك صلاحية للوصول لهذه الصفحة', 'error')
        return redirect(url_for('index'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # التصنيفات للإضافة
    cursor.execute('SELECT * FROM categories ORDER BY name')
    categories = cursor.fetchall()

    # المستخدمين للإضافة
    cursor.execute('SELECT id, full_name FROM users WHERE is_active = 1 ORDER BY full_name')
    users = cursor.fetchall()

    conn.close()
    return render_template('admin_add_store.html', categories=categories, users=users)

# صفحة إضافة محل جديد للمستخدمين العاديين
@app.route('/add-store', methods=['GET'])
def add_store_page():
    if 'user_id' not in session:
        flash('يجب تسجيل الدخول لإضافة محل', 'warning')
        return redirect(url_for('login'))
    
    # التحقق من التحقق
    redirect_response = check_verification_required()
    if redirect_response:
        return redirect_response
    
    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM categories ORDER BY name')
    categories = cursor.fetchall()
    conn.close()
    
    return render_template('add_store.html', categories=categories)

# إضافة محل جديد للمستخدمين العاديين
@app.route('/add-store', methods=['POST'])
def add_store_user():
    if 'user_id' not in session:
        flash('يجب تسجيل الدخول لإضافة محل', 'warning')
        return redirect(url_for('login'))
    
    # التحقق من التحقق
    redirect_response = check_verification_required()
    if redirect_response:
        return redirect_response
    
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
    
    conn.commit()
    conn.close()
    
    flash('تم إضافة المحل بنجاح وسيتم مراجعته من قبل الإدارة', 'success')
    return redirect(url_for('dashboard'))

# إضافة محل جديد للإدارة
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

    def add_store_operation():
        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO stores (name, category_id, address, phone, description, user_id, is_approved) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (name, category_id, address, phone, description, user_id, is_approved))
        conn.commit()
        conn.close()

    # تنفيذ العملية مع النسخ الاحتياطي التلقائي
    execute_db_operation_with_backup(
        add_store_operation, 
        'add', 
        'store', 
        name, 
        session.get('user_name', 'مدير')
    )

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

    def edit_store_operation():
        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE stores SET name = ?, category_id = ?, address = ?, phone = ?, 
            description = ?, user_id = ?, is_approved = ? WHERE id = ?
        ''', (name, category_id, address, phone, description, user_id, is_approved, store_id))
        conn.commit()
        conn.close()

    # تنفيذ العملية مع النسخ الاحتياطي التلقائي
    execute_db_operation_with_backup(
        edit_store_operation, 
        'edit', 
        'store', 
        name, 
        session.get('user_name', 'مدير')
    )

    flash('تم تحديث المحل بنجاح', 'success')
    return redirect(url_for('admin_stores'))

# حذف محل
@app.route('/admin/delete-store/<int:store_id>')
def delete_store(store_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    # الحصول على اسم المحل قبل الحذف
    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name FROM stores WHERE id = ?', (store_id,))
    store = cursor.fetchone()
    store_name = store[0] if store else f'محل #{store_id}'
    conn.close()

    def delete_store_operation():
        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM stores WHERE id = ?', (store_id,))
        conn.commit()
        conn.close()

    # تنفيذ العملية مع النسخ الاحتياطي التلقائي
    execute_db_operation_with_backup(
        delete_store_operation, 
        'delete', 
        'store', 
        store_name, 
        session.get('user_name', 'مدير')
    )

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

# عرض تفاصيل المحل في صفحة مستقلة
@app.route('/store/<int:store_id>')
def store_details(store_id):
    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # جلب تفاصيل المحل
    cursor.execute('''
        SELECT s.id, s.name, s.category_id, s.address, s.phone, s.description, 
               s.image_url, s.user_id, s.is_approved, s.visits_count, s.rating_avg, 
               s.search_count, COALESCE(s.created_at, '') as created_at, 
               c.name as category_name, u.full_name as owner_name
        FROM stores s 
        LEFT JOIN categories c ON s.category_id = c.id
        LEFT JOIN users u ON s.user_id = u.id
        WHERE s.id = ? AND s.is_approved = 1
    ''', (store_id,))
    store = cursor.fetchone()

    if not store:
        flash('المحل غير موجود أو غير معتمد', 'error')
        conn.close()
        return redirect(url_for('index'))

    # تحديث عداد الزيارات
    cursor.execute('''
        UPDATE stores 
        SET visits_count = COALESCE(visits_count, 0) + 1 
        WHERE id = ?
    ''', (store_id,))
    conn.commit()

    # جلب التقييمات
    cursor.execute('''
        SELECT r.id, r.rating, r.comment, r.created_at, r.created_at, u.full_name, u.is_verified
        FROM ratings r
        LEFT JOIN users u ON r.user_id = u.id
        WHERE r.store_id = ?
        ORDER BY r.created_at DESC
        LIMIT 10
    ''', (store_id,))
    ratings = cursor.fetchall()

    # حساب متوسط التقييم
    cursor.execute('''
        SELECT AVG(CAST(rating AS REAL)), COUNT(*) 
        FROM ratings 
        WHERE store_id = ?
    ''', (store_id,))
    rating_stats = cursor.fetchone()
    avg_rating = rating_stats[0] if rating_stats[0] else 0
    total_ratings = rating_stats[1] if rating_stats[1] else 0

    # توزيع النجوم
    star_distribution = {}
    for i in range(1, 6):
        cursor.execute('SELECT COUNT(*) FROM ratings WHERE store_id = ? AND rating = ?', (store_id, i))
        star_distribution[i] = cursor.fetchone()[0]

    # المحلات المشابهة من نفس التصنيف
    similar_stores = []
    if store[2]:  # category_id
        cursor.execute('''
            SELECT s.*, c.name as category_name
            FROM stores s
            LEFT JOIN categories c ON s.category_id = c.id
            WHERE s.category_id = ? AND s.id != ? AND s.is_approved = 1
            ORDER BY s.rating_avg DESC, s.visits_count DESC
            LIMIT 5
        ''', (store[2], store_id))
        similar_stores = cursor.fetchall()

    conn.close()

    # التحقق من حالة التحقق للمستخدم
    user_verification_status = False
    if 'user_id' in session:
        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()
        cursor.execute('SELECT is_verified FROM users WHERE id = ?', (session['user_id'],))
        user_result = cursor.fetchone()
        user_verification_status = user_result[0] if user_result else False
        conn.close()

    return render_template('store_details.html', 
                         store=store, 
                         ratings=ratings,
                         avg_rating=avg_rating,
                         total_ratings=total_ratings,
                         star_distribution=star_distribution,
                         similar_stores=similar_stores,
                         user_verification_status=user_verification_status)

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

# عرض قراء الإشعار المتقدم
@app.route('/admin/notification-readers/<int:notification_id>')
def admin_notification_readers(notification_id):
    if 'user_id' not in session or not session.get('is_admin'):
        flash('ليس لديك صلاحية للوصول لهذه الصفحة', 'error')
        return redirect(url_for('index'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # جلب تفاصيل الإشعار المتقدم
    cursor.execute('SELECT * FROM advanced_notifications WHERE id = ?', (notification_id,))
    notification = cursor.fetchone()

    if not notification:
        flash('الإشعار غير موجود', 'error')
        conn.close()
        return redirect(url_for('admin_advanced_notifications'))

    # جلب قائمة المستخدمين الذين قرأوا الإشعار
    read_by_data = notification[20] if len(notification) > 20 and notification[20] else ''  # read_by column
    readers = []
    clickers = []
    dismissers = []
    
    if read_by_data:
        import json
        try:
            read_data = json.loads(read_by_data)
            
            # جلب معلومات المستخدمين
            for user_action in read_data:
                if isinstance(user_action, dict):
                    user_id = user_action.get('user_id')
                    action = user_action.get('action', 'read')
                    timestamp = user_action.get('timestamp', '')
                    
                    cursor.execute('SELECT id, full_name, phone FROM users WHERE id = ?', (user_id,))
                    user = cursor.fetchone()
                    
                    if user:
                        user_info = {
                            'id': user[0],
                            'name': user[1],
                            'phone': user[2],
                            'timestamp': timestamp,
                            'action': action
                        }
                        
                        if action == 'read':
                            readers.append(user_info)
                        elif action == 'clicked':
                            clickers.append(user_info)
                        elif action == 'dismissed':
                            dismissers.append(user_info)
        except json.JSONDecodeError:
            pass

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
    
    return render_template('admin_notification_readers.html', 
                         notification=notification,
                         readers=readers,
                         clickers=clickers,
                         dismissers=dismissers,
                         stats=stats)

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

# API للحصول على حالة طلب التحقق
@app.route('/api/verification-status')
def get_verification_status():
    if 'user_id' not in session:
        return jsonify({'error': 'يجب تسجيل الدخول'}), 401
    
    try:
        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()
        
        # التحقق من حالة المستخدم
        cursor.execute('SELECT is_verified FROM users WHERE id = ?', (session['user_id'],))
        user = cursor.fetchone()
        
        if user and user[0]:
            conn.close()
            return jsonify({'status': 'verified', 'message': 'حسابك محقق'})
        
        # البحث عن طلب تحقق معلق
        cursor.execute('''
            SELECT status, requested_at, admin_notes FROM verification_requests 
            WHERE user_id = ? 
            ORDER BY requested_at DESC 
            LIMIT 1
        ''', (session['user_id'],))
        
        request_data = cursor.fetchone()
        conn.close()
        
        if request_data:
            status, requested_at, admin_notes = request_data
            if status == 'pending':
                return jsonify({'status': 'pending', 'message': 'طلبك قيد المراجعة', 'requested_at': requested_at})
            elif status == 'rejected':
                return jsonify({'status': 'rejected', 'message': 'تم رفض طلبك', 'reason': admin_notes})
            elif status == 'approved':
                return jsonify({'status': 'approved', 'message': 'تم قبول طلبك'})
        
        return jsonify({'status': 'none', 'message': 'لم تطلب التحقق بعد'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API للحصول على الإشعارات غير المقروءة للمستخدم
@app.route('/api/unread-notifications')
def get_unread_notifications():
    if 'user_id' not in session:
        return jsonify({'error': 'يجب تسجيل الدخول'}), 401
    
    try:
        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()
        
        user_id = session['user_id']
        is_admin = session.get('is_admin', False)
        
        # الحصول على الإشعارات غير المقروءة
        cursor.execute('''
            SELECT an.id, an.title, an.message, an.type, an.priority, an.is_popup,
                   an.action_type, an.action_url, an.action_page_content,
                   an.custom_css, an.custom_js, an.auto_dismiss, an.requires_action,
                   an.created_at, an.show_count, an.max_shows
            FROM advanced_notifications an
            LEFT JOIN notification_reads nr ON an.id = nr.notification_id AND nr.user_id = ?
            WHERE an.is_active = 1 
                AND (an.expires_at IS NULL OR an.expires_at > datetime('now', '+3 hours'))
                AND nr.id IS NULL
                AND (an.target_users = 'all' 
                     OR (an.target_users = 'admins' AND ?)
                     OR (an.target_users = 'users' AND NOT ?)
                     OR an.target_users LIKE '%'||?||'%')
                AND (an.max_shows = -1 OR an.show_count < an.max_shows)
            ORDER BY an.priority DESC, an.created_at DESC
        ''', (user_id, is_admin, is_admin, str(user_id)))
        
        notifications_data = cursor.fetchall()
        
        notifications = []
        for notif in notifications_data:
            notifications.append({
                'id': notif[0],
                'title': notif[1],
                'message': notif[2],
                'type': notif[3],
                'priority': notif[4],
                'is_popup': bool(notif[5]),
                'action_type': notif[6],
                'action_url': notif[7],
                'action_page_content': notif[8],
                'custom_css': notif[9],
                'custom_js': notif[10],
                'auto_dismiss': notif[11],
                'requires_action': bool(notif[12]),
                'created_at': notif[13],
                'show_count': notif[14],
                'max_shows': notif[15]
            })
        
        # تحديث عداد العرض
        if notifications:
            notification_ids = [str(n['id']) for n in notifications]
            cursor.execute(f'''
                UPDATE advanced_notifications 
                SET show_count = show_count + 1 
                WHERE id IN ({','.join(['?' for _ in notification_ids])})
            ''', notification_ids)
            conn.commit()
        
        conn.close()
        
        return jsonify({
            'success': True,
            'notifications': notifications,
            'count': len(notifications)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500



# API للحصول على عدد الإشعارات غير المقروءة
@app.route('/api/unread-count')
def get_unread_count():
    if 'user_id' not in session:
        return jsonify({'count': 0})
    
    try:
        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()
        
        user_id = session['user_id']
        is_admin = session.get('is_admin', False)
        
        cursor.execute('''
            SELECT COUNT(*)
            FROM advanced_notifications an
            LEFT JOIN notification_reads nr ON an.id = nr.notification_id AND nr.user_id = ?
            WHERE an.is_active = 1 
                AND (an.expires_at IS NULL OR an.expires_at > datetime('now', '+3 hours'))
                AND nr.id IS NULL
                AND (an.target_users = 'all' 
                     OR (an.target_users = 'admins' AND ?)
                     OR (an.target_users = 'users' AND NOT ?)
                     OR an.target_users LIKE '%'||?||'%')
        ''', (user_id, is_admin, is_admin, str(user_id)))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return jsonify({'count': count})
        
    except Exception as e:
        return jsonify({'count': 0})

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

# API للتحقق من انتهاء صلاحية الإشعارات المتقدمة
@app.route('/api/check-expired-advanced-notifications')
def check_expired_advanced_notifications():
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({'error': 'غير مصرح'}), 403
    
    try:
        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()
        
        # التوقيت الحالي بدمشق
        from datetime import timezone, timedelta
        damascus_tz = timezone(timedelta(hours=3))
        damascus_time = datetime.now(damascus_tz)
        current_time_str = damascus_time.strftime('%Y-%m-%d %H:%M:%S')
        
        # البحث عن الإشعارات المنتهية الصلاحية والنشطة
        cursor.execute('''
            SELECT id, title, type, expires_at, is_active 
            FROM advanced_notifications 
            WHERE is_active = 1 AND expires_at IS NOT NULL AND expires_at <= ?
        ''', (current_time_str,))
        expired_notifications = cursor.fetchall()
        
        disabled_count = 0
        expired_details = []
        
        if expired_notifications:
            # تعطيل الإشعارات المنتهية الصلاحية
            cursor.execute('''
                UPDATE advanced_notifications 
                SET is_active = 0 
                WHERE is_active = 1 AND expires_at IS NOT NULL AND expires_at <= ?
            ''', (current_time_str,))
            disabled_count = cursor.rowcount
            conn.commit()
            
            # تجميع التفاصيل
            for notification in expired_notifications:
                expired_details.append({
                    'id': notification[0],
                    'title': notification[1],
                    'type': notification[2],
                    'expires_at': notification[3],
                    'was_active': bool(notification[4])
                })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'total_found': len(expired_notifications),
            'disabled_count': disabled_count,
            'expired_details': expired_details,
            'current_time': current_time_str
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# API لتعطيل إشعار متقدم منتهي الصلاحية
@app.route('/api/disable-expired-advanced-notification/<int:notification_id>', methods=['POST'])
def disable_expired_advanced_notification(notification_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({'error': 'غير مصرح'}), 403
    
    try:
        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()
        
        cursor.execute('UPDATE advanced_notifications SET is_active = 0 WHERE id = ?', (notification_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

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

    cursor.execute('SELECT id, full_name, phone, password_hash, is_active, is_admin, is_verified, can_edit_name, created_at FROM users ORDER BY created_at DESC')
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

    def add_user_operation():
        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()

        # التحقق من عدم وجود المستخدم
        cursor.execute('SELECT id FROM users WHERE phone = ?', (phone,))
        if cursor.fetchone():
            conn.close()
            raise Exception('رقم الهاتف مسجل مسبقاً')

        password_hash = generate_password_hash(password)
        cursor.execute('''
            INSERT INTO users (full_name, phone, password_hash, is_admin, is_active) 
            VALUES (?, ?, ?, ?, ?)
        ''', (full_name, phone, password_hash, is_admin, is_active))
        conn.commit()
        conn.close()

    try:
        # تنفيذ العملية مع النسخ الاحتياطي التلقائي
        execute_db_operation_with_backup(
            add_user_operation, 
            'add', 
            'user', 
            full_name, 
            session.get('user_name', 'مدير')
        )
        flash('تم إضافة المستخدم بنجاح', 'success')
    except Exception as e:
        flash(str(e), 'error')

    return redirect(url_for('admin_users'))

# تفعيل/إلغاء تفعيل التحقق للمستخدم
@app.route('/admin/toggle-user-verification/<int:user_id>')
def toggle_user_verification(user_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # الحصول على الحالة الحالية
    cursor.execute('SELECT is_verified, can_edit_name FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    
    if user:
        current_verified = user[0] if user[0] is not None else 0
        new_verified = 0 if current_verified else 1
        new_can_edit = 0 if new_verified else 1  # إذا تم التحقق، منع التعديل
        
        cursor.execute('UPDATE users SET is_verified = ?, can_edit_name = ? WHERE id = ?', 
                      (new_verified, new_can_edit, user_id))
        conn.commit()
        
        status_text = 'تم تفعيل التحقق' if new_verified else 'تم إلغاء التحقق'
        flash(f'{status_text} للمستخدم بنجاح', 'success')
    else:
        flash('المستخدم غير موجود', 'error')

    conn.close()
    return redirect(url_for('admin_user_details', user_id=user_id))

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
    is_verified = 1 if request.form.get('is_verified') else 0
    can_edit_name = 1 if request.form.get('can_edit_name') else 0

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
            UPDATE users SET full_name = ?, phone = ?, password_hash = ?, is_admin = ?, is_active = ?, is_verified = ?, can_edit_name = ? 
            WHERE id = ?
        ''', (full_name, phone, password_hash, is_admin, is_active, is_verified, can_edit_name, user_id))
        flash('تم تحديث المستخدم وكلمة المرور بنجاح', 'success')
    else:
        cursor.execute('''
            UPDATE users SET full_name = ?, phone = ?, is_admin = ?, is_active = ?, is_verified = ?, can_edit_name = ? 
            WHERE id = ?
        ''', (full_name, phone, is_admin, is_active, is_verified, can_edit_name, user_id))
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

    # الحصول على اسم المستخدم قبل الحذف
    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()
    cursor.execute('SELECT full_name FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    user_name = user[0] if user else f'مستخدم #{user_id}'
    conn.close()

    def delete_user_operation():
        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
        conn.close()

    # تنفيذ العملية مع النسخ الاحتياطي التلقائي
    execute_db_operation_with_backup(
        delete_user_operation, 
        'delete', 
        'user', 
        user_name, 
        session.get('user_name', 'مدير')
    )

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

# إدارة طلبات التحقق
@app.route('/admin/verification-requests')
def admin_verification_requests():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('ليس لديك صلاحية للوصول لهذه الصفحة', 'error')
        return redirect(url_for('index'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # جلب جميع طلبات التحقق مع تحويل التوقيت
    cursor.execute('''
        SELECT vr.id, vr.user_id, vr.full_name, vr.status, vr.admin_notes, 
               datetime(vr.requested_at, '+3 hours') as requested_at_damascus,
               u.full_name as user_name, u.phone, u.is_verified, 
               admin_user.full_name as processed_by_name,
               datetime(vr.processed_at, '+3 hours') as processed_at_damascus
        FROM verification_requests vr
        LEFT JOIN users u ON vr.user_id = u.id
        LEFT JOIN users admin_user ON vr.processed_by = admin_user.id
        ORDER BY vr.requested_at DESC
    ''')
    verification_requests_raw = cursor.fetchall()

    # تحويل النتائج لتكون متوافقة مع القالب مع إضافة التوقيت المحدث
    verification_requests = []
    for row in verification_requests_raw:
        # إعادة ترتيب البيانات لتتطابق مع القالب
        verification_requests.append((
            row[0],  # id
            row[1],  # user_id
            row[2],  # full_name (الاسم المطلوب)
            row[3],  # status
            row[4],  # admin_notes
            row[5],  # requested_at_damascus
            row[6],  # user_name
            row[7],  # phone
            row[8],  # is_verified
            row[9],  # processed_by_name
            row[10] # processed_at_damascus
        ))

    # إحصائيات
    cursor.execute('SELECT COUNT(*) FROM verification_requests WHERE status = "pending"')
    pending_requests = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM verification_requests WHERE status = "approved"')
    approved_requests = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM verification_requests WHERE status = "rejected"')
    rejected_requests = cursor.fetchone()[0]

    conn.close()

    stats = {
        'pending_requests': pending_requests,
        'approved_requests': approved_requests,
        'rejected_requests': rejected_requests
    }

    return render_template('admin_verification_requests.html', 
                         verification_requests=verification_requests,
                         stats=stats)

# الموافقة على طلب التحقق
@app.route('/admin/approve-verification/<int:request_id>')
def approve_verification_request(request_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # الحصول على معلومات الطلب
    cursor.execute('SELECT user_id, full_name FROM verification_requests WHERE id = ? AND status = "pending"', (request_id,))
    request_data = cursor.fetchone()
    
    if not request_data:
        flash('الطلب غير موجود أو تم معالجته مسبقاً', 'error')
        conn.close()
        return redirect(url_for('admin_verification_requests'))

    user_id, full_name = request_data

    # تحديث حالة الطلب
    cursor.execute('''
        UPDATE verification_requests 
        SET status = 'approved', processed_at = CURRENT_TIMESTAMP, processed_by = ?
        WHERE id = ?
    ''', (session['user_id'], request_id))

    # تحديث حالة المستخدم
    cursor.execute('''
        UPDATE users 
        SET is_verified = 1, can_edit_name = 0
        WHERE id = ?
    ''', (user_id,))

    conn.commit()

    # الحصول على معلومات المستخدم للإشعار
    cursor.execute('SELECT full_name, phone FROM users WHERE id = ?', (user_id,))
    user_info = cursor.fetchone()

    conn.close()

    # إرسال إشعار للمستخدم
    try:
        if telegram_bot:
            asyncio.run(send_verification_status_notification(user_id, user_info[0], 'approved'))
    except Exception as e:
        print(f"خطأ في إرسال إشعار الموافقة: {e}")

    flash('تم الموافقة على طلب التحقق بنجاح', 'success')
    return redirect(url_for('admin_verification_requests'))

# صفحة رفض طلب التحقق
@app.route('/admin/reject-verification-page/<int:request_id>')
def reject_verification_page(request_id):
    if 'user_id' not in session or not session.get('is_admin'):
        flash('ليس لديك صلاحية للوصول لهذه الصفحة', 'error')
        return redirect(url_for('index'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # الحصول على معلومات الطلب مع تحويل التوقيت
    cursor.execute('''
        SELECT vr.id, vr.user_id, vr.full_name, vr.status, vr.admin_notes, 
               datetime(vr.requested_at, '+3 hours') as requested_at_damascus,
               datetime(vr.processed_at, '+3 hours') as processed_at_damascus,
               vr.processed_by,
               u.full_name as user_name, u.phone, u.is_verified
        FROM verification_requests vr
        LEFT JOIN users u ON vr.user_id = u.id
        WHERE vr.id = ? AND vr.status = "pending"
    ''', (request_id,))
    request_data_raw = cursor.fetchone()
    
    if not request_data_raw:
        flash('الطلب غير موجود أو تم معالجته مسبقاً', 'error')
        conn.close()
        return redirect(url_for('admin_verification_requests'))

    # تحويل البيانات لتكون متوافقة مع القالب
    request_data = (
        request_data_raw[0],  # id
        request_data_raw[1],  # user_id
        request_data_raw[2],  # full_name
        request_data_raw[3],  # status
        request_data_raw[4],  # admin_notes
        request_data_raw[5],  # requested_at_damascus
        request_data_raw[6],  # processed_at_damascus
        request_data_raw[7],  # processed_by
        request_data_raw[8],  # user_name
        request_data_raw[9],  # phone
        request_data_raw[10]  # is_verified
    )

    conn.close()
    return render_template('admin_reject_verification.html', request_data=request_data)

# رفض طلب التحقق
@app.route('/admin/reject-verification/<int:request_id>', methods=['POST'])
def reject_verification_request(request_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    # الحصول على السبب
    reason = request.form.get('reason', '')
    custom_reason = request.form.get('custom_reason', '')
    
    # إذا كان السبب مخصص، استخدم النص المخصص
    if reason == 'custom' and custom_reason:
        final_reason = custom_reason
    elif reason and reason != 'custom':
        final_reason = reason
    else:
        final_reason = 'لم يتم توضيح السبب'

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # الحصول على معلومات الطلب
    cursor.execute('SELECT user_id, full_name FROM verification_requests WHERE id = ? AND status = "pending"', (request_id,))
    request_data = cursor.fetchone()
    
    if not request_data:
        flash('الطلب غير موجود أو تم معالجته مسبقاً', 'error')
        conn.close()
        return redirect(url_for('admin_verification_requests'))

    user_id, full_name = request_data

    # تحديث حالة الطلب
    cursor.execute('''
        UPDATE verification_requests 
        SET status = 'rejected', admin_notes = ?, processed_at = CURRENT_TIMESTAMP, processed_by = ?
        WHERE id = ?
    ''', (final_reason, session['user_id'], request_id))

    conn.commit()

    # الحصول على معلومات المستخدم للإشعار
    cursor.execute('SELECT full_name, phone FROM users WHERE id = ?', (user_id,))
    user_info = cursor.fetchone()

    conn.close()

    # إرسال إشعار للمستخدم
    try:
        if telegram_bot:
            asyncio.run(send_verification_status_notification(user_id, user_info[0], 'rejected', final_reason))
    except Exception as e:
        print(f"خطأ في إرسال إشعار الرفض: {e}")

    flash(f'تم رفض طلب التحقق بسبب: {final_reason}', 'success')
    return redirect(url_for('admin_verification_requests'))

# تمكين/تعطيل النسخ الاحتياطية التلقائية
@app.route('/admin/toggle-auto-backup')
def toggle_auto_backup():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))
    
    global AUTO_BACKUP_ENABLED
    AUTO_BACKUP_ENABLED = not AUTO_BACKUP_ENABLED
    
    status = "مفعل" if AUTO_BACKUP_ENABLED else "معطل"
    flash(f'النسخ الاحتياطي التلقائي الآن {status}', 'success')
    
    return redirect(url_for('admin_backup'))

# API للحصول على حالة النسخ التلقائي
@app.route('/api/auto-backup-status')
def get_auto_backup_status():
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({'error': 'غير مصرح'}), 403
    
    return jsonify({
        'enabled': AUTO_BACKUP_ENABLED,
        'bot_available': telegram_bot is not None
    })

# إدارة الكوبونات
@app.route('/admin/coupons')
def admin_coupons():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('ليس لديك صلاحية للوصول لهذه الصفحة', 'error')
        return redirect(url_for('index'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # إنشاء جدول الكوبونات إذا لم يكن موجوداً
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS coupons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT UNIQUE NOT NULL,
            points INTEGER NOT NULL,
            max_uses INTEGER NOT NULL,
            current_uses INTEGER DEFAULT 0,
            expires_at DATETIME NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER,
            description TEXT,
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
    ''')

    # إنشاء جدول استخدام الكوبونات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS coupon_uses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            coupon_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            points_awarded INTEGER NOT NULL,
            used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (coupon_id) REFERENCES coupons (id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            UNIQUE(coupon_id, user_id)
        )
    ''')

    # جلب جميع الكوبونات مع معلومات المنشئ
    cursor.execute('''
        SELECT c.*, u.full_name as creator_name
        FROM coupons c 
        LEFT JOIN users u ON c.created_by = u.id
        ORDER BY c.created_at DESC
    ''')
    coupons = cursor.fetchall()

    # إحصائيات الكوبونات
    cursor.execute('SELECT COUNT(*) FROM coupons WHERE is_active = 1')
    active_coupons = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM coupons WHERE expires_at < datetime("now", "+3 hours")')
    expired_coupons = cursor.fetchone()[0]

    cursor.execute('SELECT SUM(current_uses) FROM coupons')
    total_uses = cursor.fetchone()[0] or 0

    cursor.execute('SELECT SUM(points * current_uses) FROM coupons')
    total_points_awarded = cursor.fetchone()[0] or 0

    conn.close()

    stats = {
        'active_coupons': active_coupons,
        'expired_coupons': expired_coupons,
        'total_uses': total_uses,
        'total_points_awarded': total_points_awarded
    }

    return render_template('admin_coupons.html', coupons=coupons, stats=stats)

# إضافة كوبون جديد
@app.route('/admin/add-coupon', methods=['POST'])
def add_coupon():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    name = request.form['name']
    code = request.form['code'].upper()
    points = int(request.form['points'])
    max_uses = int(request.form['max_uses'])
    expires_at = request.form['expires_at']
    description = request.form.get('description', '')

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO coupons (name, code, points, max_uses, expires_at, created_by, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (name, code, points, max_uses, expires_at, session['user_id'], description))
        
        conn.commit()
        flash('تم إضافة الكوبون بنجاح', 'success')
    except sqlite3.IntegrityError:
        flash('كود الكوبون موجود مسبقاً', 'error')
    
    conn.close()
    return redirect(url_for('admin_coupons'))

# تفاصيل الكوبون
@app.route('/admin/coupon-details/<int:coupon_id>')
def admin_coupon_details(coupon_id):
    if 'user_id' not in session or not session.get('is_admin'):
        flash('ليس لديك صلاحية للوصول لهذه الصفحة', 'error')
        return redirect(url_for('index'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # جلب تفاصيل الكوبون
    cursor.execute('''
        SELECT c.*, u.full_name as creator_name
        FROM coupons c 
        LEFT JOIN users u ON c.created_by = u.id
        WHERE c.id = ?
    ''', (coupon_id,))
    coupon = cursor.fetchone()

    if not coupon:
        flash('الكوبون غير موجود', 'error')
        conn.close()
        return redirect(url_for('admin_coupons'))

    # جلب سجل الاستخدامات مع معلومات المستخدمين
    cursor.execute('''
        SELECT cu.*, u.full_name as user_name, u.phone
        FROM coupon_uses cu
        LEFT JOIN users u ON cu.user_id = u.id
        WHERE cu.coupon_id = ?
        ORDER BY cu.used_at DESC
    ''', (coupon_id,))
    usage_history = cursor.fetchall()

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

    # إحصائيات الكوبون المحدد
    usage_count = len(usage_history)
    total_points = sum(usage[3] for usage in usage_history) if usage_history else 0

    conn.close()

    stats = {
        'total_stores': total_stores,
        'total_users': total_users,
        'pending_stores': pending_stores,
        'total_categories': total_categories,
        'total_services': total_services
    }

    return render_template('admin_coupon_details.html', 
                         coupon=coupon, 
                         usage_history=usage_history,
                         stats=stats,
                         usage_count=usage_count,
                         total_points=total_points)

# تعديل كوبون
@app.route('/admin/edit-coupon/<int:coupon_id>', methods=['POST'])
def edit_coupon(coupon_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    name = request.form['name']
    code = request.form['code'].upper()
    points = int(request.form['points'])
    max_uses = int(request.form['max_uses'])
    expires_at = request.form['expires_at']
    description = request.form.get('description', '')
    is_active = 1 if request.form.get('is_active') else 0

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    try:
        cursor.execute('''
            UPDATE coupons 
            SET name = ?, code = ?, points = ?, max_uses = ?, expires_at = ?, description = ?, is_active = ?
            WHERE id = ?
        ''', (name, code, points, max_uses, expires_at, description, is_active, coupon_id))
        
        conn.commit()
        flash('تم تحديث الكوبون بنجاح', 'success')
    except sqlite3.IntegrityError:
        flash('كود الكوبون موجود مسبقاً', 'error')
    
    conn.close()
    return redirect(url_for('admin_coupon_details', coupon_id=coupon_id))

# تفعيل/إلغاء تفعيل كوبون
@app.route('/admin/toggle-coupon/<int:coupon_id>')
def toggle_coupon(coupon_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    cursor.execute('SELECT is_active FROM coupons WHERE id = ?', (coupon_id,))
    current_status = cursor.fetchone()
    
    if current_status:
        new_status = 0 if current_status[0] else 1
        cursor.execute('UPDATE coupons SET is_active = ? WHERE id = ?', (new_status, coupon_id))
        conn.commit()
        
        status_text = 'تم تفعيل' if new_status else 'تم إلغاء تفعيل'
        flash(f'{status_text} الكوبون بنجاح', 'success')
    
    conn.close()
    return redirect(url_for('admin_coupons'))

# حذف كوبون
@app.route('/admin/delete-coupon/<int:coupon_id>')
def delete_coupon(coupon_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    cursor.execute('DELETE FROM coupons WHERE id = ?', (coupon_id,))
    conn.commit()
    conn.close()

    flash('تم حذف الكوبون بنجاح', 'success')
    return redirect(url_for('admin_coupons'))

# استخدام كوبون من قبل المستخدم
@app.route('/use-coupon', methods=['POST'])
def use_coupon():
    if 'user_id' not in session:
        return jsonify({'error': 'يجب تسجيل الدخول أولاً'}), 401

    coupon_code = request.json.get('code', '').upper().strip()
    
    if not coupon_code:
        return jsonify({'error': 'يجب إدخال كود الكوبون'}), 400

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # التحقق من الكوبون
    cursor.execute('''
        SELECT id, name, points, max_uses, current_uses, expires_at, is_active
        FROM coupons 
        WHERE code = ?
    ''', (coupon_code,))
    
    coupon = cursor.fetchone()
    
    if not coupon:
        conn.close()
        return jsonify({'error': 'كود الكوبون غير صحيح'}), 400
    
    coupon_id, name, points, max_uses, current_uses, expires_at, is_active = coupon
    
    # التحقق من تفعيل الكوبون
    if not is_active:
        conn.close()
        return jsonify({'error': 'هذا الكوبون غير مفعل'}), 400
    
    # التحقق من انتهاء الصلاحية
    from datetime import timezone, timedelta
    damascus_tz = timezone(timedelta(hours=3))
    current_time = datetime.now(damascus_tz).strftime('%Y-%m-%d %H:%M:%S')
    
    if expires_at < current_time:
        conn.close()
        return jsonify({'error': 'انتهت صلاحية هذا الكوبون'}), 400
    
    # التحقق من عدد الاستخدامات
    if current_uses >= max_uses:
        conn.close()
        return jsonify({'error': 'تم استنفاد جميع استخدامات هذا الكوبون'}), 400
    
    # التحقق من عدم استخدام المستخدم للكوبون مسبقاً
    cursor.execute('SELECT id FROM coupon_uses WHERE coupon_id = ? AND user_id = ?', 
                  (coupon_id, session['user_id']))
    
    if cursor.fetchone():
        conn.close()
        return jsonify({'error': 'لقد استخدمت هذا الكوبون من قبل'}), 400
    
    try:
        # إضافة النقاط للمستخدم
        add_points(session['user_id'], points, 'coupon_use', f'استخدام كوبون: {name}', coupon_id)
        
        # تسجيل استخدام الكوبون
        cursor.execute('''
            INSERT INTO coupon_uses (coupon_id, user_id, points_awarded)
            VALUES (?, ?, ?)
        ''', (coupon_id, session['user_id'], points))
        
        # تحديث عداد الاستخدامات
        cursor.execute('UPDATE coupons SET current_uses = current_uses + 1 WHERE id = ?', (coupon_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': f'تم استخدام الكوبون بنجاح! حصلت على {points} نقطة',
            'points_awarded': points
        })
        
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': f'خطأ في استخدام الكوبون: {str(e)}'}), 500

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
        SELECT gr.id, gr.user_id, gr.gift_id, gr.points_spent, gr.status, 
               gr.admin_notes, gr.requested_at, gr.processed_at, gr.processed_by,
               u.full_name as user_name, u.phone as user_phone,
               g.name as gift_name, g.description as gift_description
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

# متغير للتحكم في النسخ الاحتياطية التلقائية
AUTO_BACKUP_ENABLED = True

# وظيفة النسخ الاحتياطي التلقائي المحسنة
def create_auto_backup(action_type, item_type, item_name, user_name=None):
    """إنشاء نسخة احتياطية تلقائية وإرسالها لبوت التليجرام عند أي تغيير في قاعدة البيانات"""
    if not AUTO_BACKUP_ENABLED:
        return
        
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
            asyncio.run(send_backup_to_telegram(backup_path, action_type, item_type, item_name, user_name))
        
        # حذف النسخة الاحتياطية المؤقتة
        if os.path.exists(backup_path):
            os.remove(backup_path)
            print(f"✅ تم إنشاء وإرسال النسخة الاحتياطية التلقائية: {backup_filename}")
        
    except Exception as e:
        print(f"❌ خطأ في النسخ الاحتياطي التلقائي: {e}")

# وظيفة معالجة العمليات على قاعدة البيانات مع النسخ التلقائي
def execute_db_operation_with_backup(operation_func, action_type, item_type, item_name, user_name=None, *args, **kwargs):
    """تنفيذ عملية على قاعدة البيانات مع إنشاء نسخة احتياطية تلقائية"""
    try:
        # تنفيذ العملية
        result = operation_func(*args, **kwargs)
        
        # إنشاء نسخة احتياطية تلقائية بعد نجاح العملية
        create_auto_backup(action_type, item_type, item_name, user_name)
        
        return result
    except Exception as e:
        print(f"❌ خطأ في تنفيذ العملية: {e}")
        raise e

async def send_backup_to_telegram(backup_path, action_type, item_type, item_name, user_name=None):
    """إرسال النسخة الاحتياطية لبوت التليجرام مع معلومات مفصلة"""
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
            'add': '➕ إضافة',
            'edit': '✏️ تعديل', 
            'delete': '🗑️ حذف',
            'approve': '✅ موافقة',
            'reject': '❌ رفض',
            'restore': '🔄 استعادة'
        }.get(action_type, action_type)
        
        item_text = {
            'user': '👤 مستخدم',
            'store': '🏪 محل',
            'category': '🏷️ تصنيف',
            'service': '🔧 خدمة',
            'pharmacy': '💊 صيدلية',
            'notification': '📢 إشعار',
            'gift': '🎁 هدية',
            'coupon': '🎟️ كوبون',
            'backup': '💾 نسخة احتياطية',
            'settings': '⚙️ إعدادات'
        }.get(item_type, item_type)
        
        file_size = os.path.getsize(backup_path) / 1024
        size_text = f"{file_size:.1f} KB" if file_size < 1024 else f"{file_size/1024:.1f} MB"
        
        caption = f"🔄 **نسخة احتياطية تلقائية**\n\n"
        caption += f"📝 **العملية:** {action_text}\n"
        caption += f"🏷️ **النوع:** {item_text}\n"
        caption += f"📄 **العنصر:** `{item_name}`\n"
        
        if user_name:
            caption += f"👤 **المستخدم:** {user_name}\n"
            
        caption += f"🕐 **التوقيت:** {current_time_str}\n"
        caption += f"📁 **الحجم:** {size_text}\n\n"
        caption += f"💡 **ملاحظة:** تم إنشاء هذه النسخة تلقائياً عند حدوث تغيير في قاعدة البيانات"
        
        # إرسال الملف لجميع المديرين
        success_count = 0
        for admin_id in admin_ids:
            try:
                with open(backup_path, 'rb') as backup_file:
                    await telegram_bot.send_document(
                        chat_id=admin_id[0],
                        document=backup_file,
                        caption=caption,
                        filename=os.path.basename(backup_path),
                        parse_mode='Markdown'
                    )
                success_count += 1
                print(f"✅ تم إرسال النسخة الاحتياطية للمدير {admin_id[0]}")
            except Exception as e:
                print(f"❌ خطأ في إرسال النسخة الاحتياطية للمدير {admin_id[0]}: {e}")
        
        print(f"📊 تم إرسال النسخة الاحتياطية لـ {success_count} من أصل {len(admin_ids)} مدير")
                
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

async def send_redemption_notification(user_id, gift_name, points_spent):
    """إرسال إشعار للمديرين عند طلب استبدال هدية"""
    if not telegram_bot:
        return
        
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
        
        message = f"🎁 طلب استبدال هدية جديد!\n\n"
        message += f"👤 المستخدم: {user_name}\n"
        message += f"🎁 الهدية: {gift_name}\n"
        message += f"⭐ النقاط المستخدمة: {points_spent}\n\n"
        message += "يرجى مراجعة الطلب من لوحة الإدارة"
        
        for admin_id in admin_ids:
            try:
                await telegram_bot.send_message(
                    chat_id=admin_id[0],
                    text=message
                )
            except Exception as e:
                print(f"خطأ في إرسال إشعار الاستبدال للمدير {admin_id[0]}: {e}")
                
    except Exception as e:
        print(f"خطأ في إرسال إشعارات استبدال الهدايا: {e}")

async def send_verification_request_notification(user_id, user_name, user_phone):
    """إرسال إشعار للمديرين عند طلب التحقق"""
    if not telegram_bot:
        return
        
    try:
        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT telegram_id FROM admin_telegram_ids')
        admin_ids = cursor.fetchall()
        conn.close()
        
        message = f"✅ طلب تحقق جديد!\n\n"
        message += f"👤 المستخدم: {user_name}\n"
        message += f"📞 الهاتف: {user_phone}\n"
        message += f"🆔 معرف المستخدم: {user_id}\n\n"
        message += "يرجى مراجعة الطلب من لوحة الإدارة"
        
        keyboard = [[InlineKeyboardButton("مراجعة طلبات التحقق", url=f"https://{os.getenv('REPL_SLUG', 'localhost')}-{os.getenv('REPL_OWNER', 'user')}.replit.dev/admin/verification-requests")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        for admin_id in admin_ids:
            try:
                await telegram_bot.send_message(
                    chat_id=admin_id[0],
                    text=message,
                    reply_markup=reply_markup
                )
            except Exception as e:
                print(f"خطأ في إرسال إشعار التحقق للمدير {admin_id[0]}: {e}")
                
    except Exception as e:
        print(f"خطأ في إرسال إشعارات طلبات التحقق: {e}")

async def send_verification_status_notification(user_id, user_name, status, reason=None):
    """إرسال إشعار للمستخدم بحالة طلب التحقق"""
    if not telegram_bot:
        return
        
    try:
        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()
        
        # البحث عن معرف التليجرام للمستخدم (إذا كان متوفراً)
        # يمكن إضافة جدول لربط المستخدمين بمعرفات التليجرام الخاصة بهم
        # حالياً سنرسل الإشعار للمديرين فقط ليقوموا بإبلاغ المستخدم
        
        cursor.execute('SELECT telegram_id FROM admin_telegram_ids')
        admin_ids = cursor.fetchall()
        conn.close()
        
        if status == 'approved':
            message = f"✅ تم الموافقة على طلب التحقق\n\n"
            message += f"👤 المستخدم: {user_name}\n"
            message += f"🆔 معرف المستخدم: {user_id}\n\n"
            message += "تم منح شارة التحقق للمستخدم"
        else:
            message = f"❌ تم رفض طلب التحقق\n\n"
            message += f"👤 المستخدم: {user_name}\n"
            message += f"🆔 معرف المستخدم: {user_id}\n"
            if reason:
                message += f"📝 السبب: {reason}\n\n"
            message += "يرجى إبلاغ المستخدم بالقرار"
        
        for admin_id in admin_ids:
            try:
                await telegram_bot.send_message(
                    chat_id=admin_id[0],
                    text=message
                )
            except Exception as e:
                print(f"خطأ في إرسال إشعار حالة التحقق للمدير {admin_id[0]}: {e}")
                
    except Exception as e:
        print(f"خطأ في إرسال إشعارات حالة التحقق: {e}")

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
    """تهيئة بوت التليجرام"""
    global telegram_bot, telegram_app
    
    try:
        # الحصول على التوكن من Secrets
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            print("⚠️ لم يتم العثور على TELEGRAM_BOT_TOKEN في Secrets")
            return
        
        telegram_bot = Bot(token=bot_token)
        telegram_app = Application.builder().token(bot_token).build()
        
        # إضافة المعالجات
        telegram_app.add_handler(CommandHandler("start", start_command))
        telegram_app.add_handler(CallbackQueryHandler(button_callback))
        
        print("✅ تم تهيئة بوت التليجرام بنجاح")
        
    except Exception as e:
        print(f"❌ خطأ في تهيئة بوت التليجرام: {e}")

def run_telegram_bot():
    """تشغيل البوت في خيط منفصل"""
    try:
        if telegram_app:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            telegram_app.run_polling()
    except Exception as e:
        print(f"خطأ في تشغيل بوت التليجرام: {e}")

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

# إدارة الإشعارات المتقدمة
@app.route('/admin/advanced-notifications')
def admin_advanced_notifications():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('ليس لديك صلاحية للوصول لهذه الصفحة', 'error')
        return redirect(url_for('index'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # التأكد من وجود جدول الإشعارات المتقدمة مع جميع الأعمدة
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS advanced_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            type TEXT DEFAULT 'info',
            target_users TEXT DEFAULT 'all',
            target_roles TEXT DEFAULT 'all',
            priority INTEGER DEFAULT 1,
            is_popup BOOLEAN DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            action_type TEXT DEFAULT 'none',
            action_url TEXT,
            action_page_content TEXT,
            custom_css TEXT,
            custom_js TEXT,
            show_count INTEGER DEFAULT 0,
            max_shows INTEGER DEFAULT -1,
            auto_dismiss INTEGER DEFAULT 0,
            requires_action BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            created_by INTEGER,
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
    ''')

    # إضافة الأعمدة المفقودة إذا لم تكن موجودة
    columns_to_add = [
        ('created_by', 'INTEGER'),
        ('target_roles', 'TEXT DEFAULT "all"'),
        ('action_type', 'TEXT DEFAULT "none"'),
        ('action_url', 'TEXT'),
        ('action_page_content', 'TEXT'),
        ('custom_css', 'TEXT'),
        ('custom_js', 'TEXT'),
        ('show_count', 'INTEGER DEFAULT 0'),
        ('max_shows', 'INTEGER DEFAULT -1'),
        ('auto_dismiss', 'INTEGER DEFAULT 0'),
        ('requires_action', 'BOOLEAN DEFAULT 0')
    ]

    for column_name, column_def in columns_to_add:
        try:
            cursor.execute(f'ALTER TABLE advanced_notifications ADD COLUMN {column_name} {column_def}')
        except sqlite3.OperationalError:
            pass  # العمود موجود بالفعل

    # الحصول على جميع الإشعارات المتقدمة مع الإحصائيات
    cursor.execute('''
        SELECT an.*, u.full_name as creator_name,
               COALESCE(ns.total_sent, 0) as total_sent,
               COALESCE(ns.total_read, 0) as total_read,
               COALESCE(ns.total_clicked, 0) as total_clicked,
               COALESCE(ns.total_dismissed, 0) as total_dismissed
        FROM advanced_notifications an
        LEFT JOIN users u ON an.created_by = u.id
        LEFT JOIN notification_stats ns ON an.id = ns.notification_id
        ORDER BY an.created_at DESC
    ''')
    notifications_raw = cursor.fetchall()
    
    # معالجة التواريخ للتأكد من أنها نصوص
    notifications = []
    for notif in notifications_raw:
        notif_list = list(notif)
        # التأكد من أن created_at (index 18) و expires_at (index 19) هما نصوص
        if notif_list[18] and not isinstance(notif_list[18], str):
            notif_list[18] = str(notif_list[18])
        if notif_list[19] and not isinstance(notif_list[19], str):
            notif_list[19] = str(notif_list[19])
        notifications.append(tuple(notif_list))

    # الحصول على المستخدمين للإرسال المخصص
    cursor.execute('SELECT id, full_name, phone FROM users WHERE is_active = 1 ORDER BY full_name')
    users = cursor.fetchall()

    # إحصائيات عامة
    cursor.execute('SELECT COUNT(*) FROM advanced_notifications WHERE is_active = 1')
    active_count = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM advanced_notifications WHERE expires_at < datetime("now", "+3 hours")')
    expired_count = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM advanced_notifications WHERE is_popup = 1')
    popup_count = cursor.fetchone()[0]

    stats = {
        'active_count': active_count,
        'expired_count': expired_count,
        'popup_count': popup_count,
        'total_count': len(notifications)
    }

    conn.close()
    return render_template('admin_advanced_notifications.html', 
                         notifications=notifications, 
                         users=users,
                         stats=stats)

# إضافة إشعار متقدم جديد
@app.route('/admin/add-advanced-notification', methods=['POST'])
def add_advanced_notification():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    try:
        title = request.form['title']
        message = request.form['message']
        notification_type = request.form['type']
        target_users = request.form['target_users']
        priority = int(request.form.get('priority', 1))
        is_popup = 1 if request.form.get('is_popup') else 0
        action_type = request.form.get('action_type', 'none')
        action_url = request.form.get('action_url', '')
        action_page_content = request.form.get('action_page_content', '')
        custom_css = request.form.get('custom_css', '')
        custom_js = request.form.get('custom_js', '')
        auto_dismiss = int(request.form.get('auto_dismiss', 0))
        requires_action = 1 if request.form.get('requires_action') else 0
        max_shows = int(request.form.get('max_shows', -1))
        expires_at = request.form.get('expires_at') or None

        # معالجة المستخدمين المحددين
        if target_users == 'specific':
            selected_users = request.form.getlist('selected_users')
            target_users = ','.join(selected_users)

        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO advanced_notifications 
            (title, message, type, target_users, priority, is_popup, action_type, 
             action_url, action_page_content, custom_css, custom_js, auto_dismiss,
             requires_action, max_shows, expires_at, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (title, message, notification_type, target_users, priority, is_popup,
              action_type, action_url, action_page_content, custom_css, custom_js,
              auto_dismiss, requires_action, max_shows, expires_at, session['user_id']))

        notification_id = cursor.lastrowid

        # إنشاء سجل إحصائيات
        cursor.execute('''
            INSERT INTO notification_stats (notification_id, total_sent)
            VALUES (?, 0)
        ''', (notification_id,))

        conn.commit()
        conn.close()

        flash('تم إضافة الإشعار المتقدم بنجاح', 'success')
    except Exception as e:
        flash(f'خطأ في إضافة الإشعار: {str(e)}', 'error')

    return redirect(url_for('admin_advanced_notifications'))

# تعديل إشعار متقدم
@app.route('/admin/edit-advanced-notification/<int:notification_id>', methods=['POST'])
def edit_advanced_notification(notification_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    try:
        title = request.form['title']
        message = request.form['message']
        notification_type = request.form['type']
        target_users = request.form['target_users']
        priority = int(request.form.get('priority', 1))
        is_popup = 1 if request.form.get('is_popup') else 0
        is_active = 1 if request.form.get('is_active') else 0
        action_type = request.form.get('action_type', 'none')
        action_url = request.form.get('action_url', '')
        action_page_content = request.form.get('action_page_content', '')
        custom_css = request.form.get('custom_css', '')
        custom_js = request.form.get('custom_js', '')
        auto_dismiss = int(request.form.get('auto_dismiss', 0))
        requires_action = 1 if request.form.get('requires_action') else 0
        max_shows = int(request.form.get('max_shows', -1))
        expires_at = request.form.get('expires_at') or None

        # معالجة المستخدمين المحددين
        if target_users == 'specific':
            selected_users = request.form.getlist('selected_users')
            target_users = ','.join(selected_users)

        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE advanced_notifications 
            SET title = ?, message = ?, type = ?, target_users = ?, priority = ?,
                is_popup = ?, is_active = ?, action_type = ?, action_url = ?,
                action_page_content = ?, custom_css = ?, custom_js = ?,
                auto_dismiss = ?, requires_action = ?, max_shows = ?, expires_at = ?
            WHERE id = ?
        ''', (title, message, notification_type, target_users, priority, is_popup,
              is_active, action_type, action_url, action_page_content, custom_css,
              custom_js, auto_dismiss, requires_action, max_shows, expires_at, notification_id))

        conn.commit()
        conn.close()

        flash('تم تحديث الإشعار بنجاح', 'success')
    except Exception as e:
        flash(f'خطأ في تحديث الإشعار: {str(e)}', 'error')

    return redirect(url_for('admin_advanced_notifications'))

# صفحة تعديل إشعار متقدم
@app.route('/admin/edit-advanced-notification-page/<int:notification_id>')
def edit_advanced_notification_page(notification_id):
    if 'user_id' not in session or not session.get('is_admin'):
        flash('ليس لديك صلاحية للوصول لهذه الصفحة', 'error')
        return redirect(url_for('index'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # جلب تفاصيل الإشعار
    cursor.execute('SELECT * FROM advanced_notifications WHERE id = ?', (notification_id,))
    notification_raw = cursor.fetchone()

    if not notification_raw:
        flash('الإشعار غير موجود', 'error')
        conn.close()
        return redirect(url_for('admin_advanced_notifications'))

    # تحويل البيانات لقائمة وإصلاح التواريخ
    notification = list(notification_raw)
    
    # التأكد من أن التواريخ في فهارس 18 و 19 هي نصوص
    if notification[18] and not isinstance(notification[18], str):
        notification[18] = str(notification[18])
    if notification[19] and not isinstance(notification[19], str):
        notification[19] = str(notification[19])
    
    # تحويل القائمة إلى tuple مرة أخرى
    notification = tuple(notification)

    # الحصول على المستخدمين للإرسال المخصص
    cursor.execute('SELECT id, full_name, phone FROM users WHERE is_active = 1 ORDER BY full_name')
    users = cursor.fetchall()

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
    return render_template('admin_edit_advanced_notification.html', 
                         notification=notification, 
                         users=users,
                         stats=stats)

# حذف إشعار متقدم
@app.route('/admin/delete-advanced-notification/<int:notification_id>')
def delete_advanced_notification(notification_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    try:
        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()

        cursor.execute('DELETE FROM advanced_notifications WHERE id = ?', (notification_id,))
        conn.commit()
        conn.close()

        flash('تم حذف الإشعار بنجاح', 'success')
    except Exception as e:
        flash(f'خطأ في حذف الإشعار: {str(e)}', 'error')

    return redirect(url_for('admin_advanced_notifications'))

# عرض صفحة مخصصة للإشعار
@app.route('/notification-page/<int:notification_id>')
def notification_page(notification_id):
    if 'user_id' not in session:
        flash('يجب تسجيل الدخول لعرض هذا المحتوى', 'error')
        return redirect(url_for('login'))

    try:
        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()

        cursor.execute('''
            SELECT title, message, action_page_content, custom_css, custom_js
            FROM advanced_notifications
            WHERE id = ? AND is_active = 1
        ''', (notification_id,))
        
        notification = cursor.fetchone()
        conn.close()

        if not notification:
            flash('الإشعار غير موجود أو غير متاح', 'error')
            return redirect(url_for('index'))

        # تسجيل النقر
        mark_notification_read_data = {
            'notification_id': notification_id,
            'action_taken': 'clicked'
        }
        
        return render_template('notification_page.html',
                             title=notification[0],
                             message=notification[1],
                             content=notification[2],
                             custom_css=notification[3],
                             custom_js=notification[4],
                             notification_id=notification_id)

    except Exception as e:
        flash('خطأ في عرض الإشعار', 'error')
        return redirect(url_for('index'))

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
    # التحقق من التحقق المطلوب
    verification_check = check_verification_required()
    if verification_check:
        return verification_check

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

    # إرسال إشعار تليجرام للمديرين
    try:
        if telegram_bot:
            asyncio.run(send_new_store_notification(name, owner_name, category_name))
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

    full_name = request.form['full_name'].strip()
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    if new_password and new_password != confirm_password:
        flash('كلمة المرور غير متطابقة', 'error')
        return redirect(url_for('dashboard'))

    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()

    # التحقق من إمكانية تعديل الاسم
    cursor.execute('SELECT can_edit_name, is_verified FROM users WHERE id = ?', (session['user_id'],))
    user_perms = cursor.fetchone()
    
    if not user_perms:
        flash('خطأ في بيانات المستخدم', 'error')
        conn.close()
        return redirect(url_for('dashboard'))
    
    can_edit_name = user_perms[0] if user_perms[0] is not None else 1
    is_verified = user_perms[1] if user_perms[1] is not None else 0

    if new_password:
        password_hash = generate_password_hash(new_password)
        if can_edit_name:
            # التحقق من صحة الاسم العربي إذا تم تعديله
            name_valid, name_error = validate_arabic_name(full_name)
            if not name_valid:
                flash(name_error, 'error')
                conn.close()
                return redirect(url_for('dashboard'))
            
            # التحقق من عدم وجود الاسم مسبقاً
            name_exists, name_exists_error = check_name_exists(full_name)
            if name_exists:
                # التحقق من أن الاسم ليس نفس اسم المستخدم الحالي
                cursor.execute('SELECT full_name FROM users WHERE id = ?', (session['user_id'],))
                current_name_result = cursor.fetchone()
                if current_name_result:
                    current_name = current_name_result[0]
                    if full_name != current_name:
                        flash(name_exists_error, 'error')
                        conn.close()
                        return redirect(url_for('dashboard'))
                else:
                    flash('خطأ في الحصول على الاسم الحالي', 'error')
                    conn.close()
                    return redirect(url_for('dashboard'))
            
            cursor.execute('UPDATE users SET full_name = ?, password_hash = ? WHERE id = ?', 
                          (full_name, password_hash, session['user_id']))
            session['user_name'] = full_name
            flash('تم تحديث الملف الشخصي وكلمة المرور بنجاح', 'success')
        else:
            cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', 
                          (password_hash, session['user_id']))
            flash('تم تحديث كلمة المرور بنجاح. لا يمكن تعديل الاسم للمستخدمين المحققين', 'success')
    else:
        if can_edit_name:
            # التحقق من صحة الاسم العربي
            name_valid, name_error = validate_arabic_name(full_name)
            if not name_valid:
                flash(name_error, 'error')
                conn.close()
                return redirect(url_for('dashboard'))
            
            # التحقق من عدم وجود الاسم مسبقاً
            name_exists, name_exists_error = check_name_exists(full_name)
            if name_exists:
                # التحقق من أن الاسم ليس نفس اسم المستخدم الحالي
                cursor.execute('SELECT full_name FROM users WHERE id = ?', (session['user_id'],))
                current_name_result = cursor.fetchone()
                if current_name_result:
                    current_name = current_name_result[0]
                    if full_name != current_name:
                        flash(name_exists_error, 'error')
                        conn.close()
                        return redirect(url_for('dashboard'))
                else:
                    flash('خطأ في الحصول على الاسم الحالي', 'error')
                    conn.close()
                    return redirect(url_for('dashboard'))
            
            cursor.execute('UPDATE users SET full_name = ? WHERE id = ?', 
                          (full_name, session['user_id']))
            session['user_name'] = full_name
            flash('تم تحديث الملف الشخصي بنجاح', 'success')
        else:
            flash('لا يمكن تعديل الاسم للمستخدمين المحققين', 'warning')

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

# حفظ النسخة الشاملة المرفوعة
@app.route('/admin/save-uploaded-full-backup', methods=['POST'])
def save_uploaded_full_backup():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    try:
        if 'backup_file' not in request.files:
            flash('لم يتم اختيار ملف', 'error')
            return redirect(url_for('admin_backup'))

        file = request.files['backup_file']
        if file.filename == '':
            flash('لم يتم اختيار ملف', 'error')
            return redirect(url_for('admin_backup'))

        if not file.filename.endswith('.zip'):
            flash('يجب أن يكون الملف من نوع .zip للنسخة الشاملة', 'error')
            return redirect(url_for('admin_backup'))

        # إنشاء مجلد النسخ الاحتياطية
        os.makedirs('backups', exist_ok=True)

        # إنشاء اسم ملف مميز للنسخة الشاملة المرفوعة
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        original_name = secure_filename(file.filename)
        name_without_ext = os.path.splitext(original_name)[0]
        
        # تمييز النسخة الشاملة المرفوعة في الاسم
        new_filename = f"uploaded_full_{name_without_ext}_{timestamp}.zip"
        backup_path = os.path.join('backups', new_filename)

        # حفظ الملف
        file.save(backup_path)

        file_size = os.path.getsize(backup_path)
        size_text = f"{file_size / 1024:.1f} KB" if file_size < 1024*1024 else f"{file_size / (1024*1024):.1f} MB"
        
        flash(f'تم حفظ النسخة الشاملة المرفوعة بنجاح: {new_filename} ({size_text})', 'success')

    except Exception as e:
        flash(f'خطأ في حفظ النسخة الشاملة المرفوعة: {str(e)}', 'error')

    return redirect(url_for('admin_backup'))

# استعادة النسخة الاحتياطية الشاملة
@app.route('/admin/restore-full-backup', methods=['POST'])
def restore_full_backup():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    # التحقق من وجود اسم ملف من القائمة
    backup_filename = request.form.get('backup_filename')
    merge_data = request.form.get('merge_data') == 'on'
    structure_only = request.form.get('structure_only') == 'on'
    
    try:
        import zipfile
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if backup_filename:
            # استعادة من النسخ الموجودة في القائمة
            backup_path = os.path.join('backups', backup_filename)
            
            if not os.path.exists(backup_path):
                flash('الملف غير موجود', 'error')
                return redirect(url_for('admin_backup'))
            
            if not backup_filename.endswith('.zip'):
                flash('يجب أن يكون الملف من نوع .zip للنسخة الشاملة', 'error')
                return redirect(url_for('admin_backup'))
            
            # إنشاء نسخة احتياطية من الملفات الحالية
            current_backup = f'hussainiya_full_backup_before_restore_{timestamp}.zip'
            
            with zipfile.ZipFile(current_backup, 'w', zipfile.ZIP_DEFLATED) as zipf:
                if os.path.exists('hussainiya_stores.db'):
                    zipf.write('hussainiya_stores.db')
                zipf.write('app.py')
                for root, dirs, files in os.walk('templates'):
                    for file_name in files:
                        file_path = os.path.join(root, file_name)
                        zipf.write(file_path)
            
            temp_backup_path = f'temp_restore_{timestamp}.zip'
            shutil.copy2(backup_path, temp_backup_path)
            
        else:
            # استعادة من ملف مرفوع
            if 'backup_file' not in request.files:
                flash('لم يتم اختيار ملف', 'error')
                return redirect(url_for('admin_backup'))

            file = request.files['backup_file']
            if file.filename == '':
                flash('لم يتم اختيار ملف', 'error')
                return redirect(url_for('admin_backup'))

            if not file.filename.endswith('.zip'):
                flash('يجب أن يكون الملف من نوع .zip', 'error')
                return redirect(url_for('admin_backup'))

            # إنشاء نسخة احتياطية من الملفات الحالية
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
            temp_backup_path = f'temp_restore_{timestamp}.zip'
            file.save(temp_backup_path)

        # استخراج إلى مجلد مؤقت
        temp_extract_dir = f'temp_extract_{timestamp}'
        os.makedirs(temp_extract_dir, exist_ok=True)
        
        with zipfile.ZipFile(temp_backup_path, 'r') as zipf:
            zipf.extractall(temp_extract_dir)

        # معالجة قاعدة البيانات
        extracted_db_path = os.path.join(temp_extract_dir, 'hussainiya_stores.db')
        
        if structure_only:
            # استعادة البنية فقط بدون البيانات
            if os.path.exists(extracted_db_path):
                success, structure_log = restore_structure_only(extracted_db_path, 'hussainiya_stores.db')
                
                if success:
                    flash('تم استعادة بنية قاعدة البيانات بنجاح مع الحفاظ على البيانات!', 'success')
                    for log_entry in structure_log[:10]:
                        flash(log_entry, 'info')
                    if len(structure_log) > 10:
                        flash(f'... و {len(structure_log) - 10} تحديث آخر', 'info')
                else:
                    flash('فشل في استعادة بنية قاعدة البيانات', 'error')
                    for log_entry in structure_log:
                        flash(log_entry, 'error')
            
            # استعادة الملفات والقوالب والكود
            restore_code_and_templates(temp_extract_dir)
            flash('تم استعادة البنية والتصميم والكود بنجاح مع الحفاظ على البيانات!', 'success')
            
        elif os.path.exists(extracted_db_path):
            if merge_data:
                # دمج البيانات
                success, merge_log = merge_databases(extracted_db_path, 'hussainiya_stores.db')
                
                if success:
                    flash(f'تم دمج البيانات بنجاح من النسخة الشاملة!', 'success')
                    for log_entry in merge_log[:10]:
                        flash(log_entry, 'info')
                    if len(merge_log) > 10:
                        flash(f'... و {len(merge_log) - 10} عملية أخرى', 'info')
                else:
                    flash('فشل في دمج البيانات من النسخة الشاملة', 'error')
                    for log_entry in merge_log:
                        flash(log_entry, 'error')
            else:
                # استعادة كاملة
                shutil.copy2(extracted_db_path, 'hussainiya_stores.db')
                flash('تم استعادة قاعدة البيانات من النسخة الشاملة بنجاح', 'success')

        # نسخ الملفات الأخرى إذا لم يكن الدمج مفعلاً ولم يكن استعادة البنية فقط
        if not merge_data and not structure_only:
            # نسخ app.py
            extracted_app_path = os.path.join(temp_extract_dir, 'app.py')
            if os.path.exists(extracted_app_path):
                shutil.copy2(extracted_app_path, 'app.py')
            
            # نسخ مجلد templates
            extracted_templates_path = os.path.join(temp_extract_dir, 'templates')
            if os.path.exists(extracted_templates_path):
                if os.path.exists('templates'):
                    shutil.rmtree('templates')
                shutil.copytree(extracted_templates_path, 'templates')
            
            flash('تم استعادة النسخة الاحتياطية الشاملة بنجاح (استعادة كاملة)', 'success')

        # تنظيف الملفات المؤقتة
        if os.path.exists(temp_backup_path):
            os.remove(temp_backup_path)
        if os.path.exists(temp_extract_dir):
            shutil.rmtree(temp_extract_dir)

    except Exception as e:
        flash(f'خطأ في استعادة النسخة الاحتياطية الشاملة: {str(e)}', 'error')

    return redirect(url_for('admin_backup'))

def restore_structure_only(source_db_path, target_db_path):
    """استعادة بنية قاعدة البيانات فقط مع الحفاظ على البيانات"""
    try:
        import sqlite3
        import tempfile
        
        # إنشاء ملف مؤقت لنسخ البيانات الحالية
        temp_data_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        temp_data_file.close()
        
        log = []
        
        # نسخ البيانات الحالية إلى ملف مؤقت
        shutil.copy2(target_db_path, temp_data_file.name)
        log.append("✅ تم نسخ البيانات الحالية للحفظ المؤقت")
        
        # الاتصال بقاعدة البيانات المصدر والهدف
        source_conn = sqlite3.connect(source_db_path)
        target_conn = sqlite3.connect(target_db_path)
        temp_conn = sqlite3.connect(temp_data_file.name)
        
        source_cursor = source_conn.cursor()
        target_cursor = target_conn.cursor()
        temp_cursor = temp_conn.cursor()
        
        # الحصول على قائمة الجداول من المصدر
        source_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        source_tables = [row[0] for row in source_cursor.fetchall()]
        
        # الحصول على قائمة الجداول الحالية
        temp_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        current_tables = [row[0] for row in temp_cursor.fetchall()]
        
        # إنشاء الجداول الجديدة أو تحديث البنية
        for table in source_tables:
            # الحصول على بنية الجدول من المصدر
            source_cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}'")
            table_schema = source_cursor.fetchone()
            
            if table_schema:
                # حذف الجدول الحالي إذا كان موجوداً
                target_cursor.execute(f"DROP TABLE IF EXISTS {table}")
                
                # إنشاء الجدول الجديد بالبنية المحدثة
                target_cursor.execute(table_schema[0])
                log.append(f"✅ تم تحديث بنية جدول {table}")
                
                # استعادة البيانات إذا كان الجدول موجوداً في النسخة السابقة
                if table in current_tables:
                    try:
                        # الحصول على أعمدة الجدول الجديد
                        target_cursor.execute(f"PRAGMA table_info({table})")
                        new_columns = [col[1] for col in target_cursor.fetchall()]
                        
                        # الحصول على أعمدة الجدول القديم
                        temp_cursor.execute(f"PRAGMA table_info({table})")
                        old_columns = [col[1] for col in temp_cursor.fetchall()]
                        
                        # العثور على الأعمدة المشتركة
                        common_columns = [col for col in new_columns if col in old_columns]
                        
                        if common_columns:
                            columns_str = ', '.join(common_columns)
                            
                            # نسخ البيانات للأعمدة المشتركة
                            temp_cursor.execute(f"SELECT {columns_str} FROM {table}")
                            data = temp_cursor.fetchall()
                            
                            if data:
                                placeholders = ', '.join(['?' for _ in common_columns])
                                target_cursor.executemany(f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})", data)
                                log.append(f"✅ تم استعادة {len(data)} سجل من جدول {table}")
                            else:
                                log.append(f"ℹ️ جدول {table} فارغ")
                        else:
                            log.append(f"⚠️ لا توجد أعمدة مشتركة في جدول {table}")
                            
                    except Exception as e:
                        log.append(f"⚠️ تعذر استعادة بيانات جدول {table}: {str(e)}")
                else:
                    log.append(f"ℹ️ جدول {table} جديد - لا توجد بيانات للاستعادة")
        
        # إنشاء الفهارس والمفاتيح الخارجية
        source_cursor.execute("SELECT sql FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'")
        indexes = source_cursor.fetchall()
        
        for index in indexes:
            if index[0]:
                try:
                    target_cursor.execute(index[0])
                    log.append(f"✅ تم إنشاء فهرس")
                except Exception as e:
                    log.append(f"⚠️ فشل في إنشاء فهرس: {str(e)}")
        
        # حفظ التغييرات
        target_conn.commit()
        
        # إغلاق الاتصالات
        source_conn.close()
        target_conn.close()
        temp_conn.close()
        
        # حذف الملف المؤقت
        os.unlink(temp_data_file.name)
        
        log.append("🎉 تم استعادة البنية بنجاح مع الحفاظ على جميع البيانات")
        return True, log
        
    except Exception as e:
        return False, [f"❌ خطأ في استعادة البنية: {str(e)}"]

def restore_code_and_templates(extract_dir):
    """استعادة ملفات الكود والقوالب"""
    try:
        # نسخ app.py
        extracted_app_path = os.path.join(extract_dir, 'app.py')
        if os.path.exists(extracted_app_path):
            shutil.copy2(extracted_app_path, 'app.py')
        
        # نسخ مجلد templates
        extracted_templates_path = os.path.join(extract_dir, 'templates')
        if os.path.exists(extracted_templates_path):
            if os.path.exists('templates'):
                shutil.rmtree('templates')
            shutil.copytree(extracted_templates_path, 'templates')
        
        # نسخ الملفات الثابتة إذا كانت موجودة
        extracted_static_path = os.path.join(extract_dir, 'static')
        if os.path.exists(extracted_static_path):
            if os.path.exists('static'):
                shutil.rmtree('static')
            shutil.copytree(extracted_static_path, 'static')
        
        # نسخ ملفات CSS و JS
        for file_name in ['style.css', 'script.js']:
            extracted_file_path = os.path.join(extract_dir, file_name)
            if os.path.exists(extracted_file_path):
                shutil.copy2(extracted_file_path, file_name)
        
        return True
        
    except Exception as e:
        print(f"خطأ في استعادة الملفات: {e}")
        return False

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
@app.route('/api/mark-notification-read', methods=['POST'])
@app.route('/api/mark-notification-read/<int:notification_id>', methods=['POST'])
def mark_notification_read(notification_id=None):
    if 'user_id' not in session:
        return jsonify({'error': 'يجب تسجيل الدخول'}), 401
    
    try:
        if notification_id is None:
            # استخدام البيانات من الـ JSON
            data = request.get_json()
            notification_id = data.get('notification_id')
            action_taken = data.get('action_taken', 'read')
        else:
            # استخدام notification_id من URL
            action_taken = 'read'
        
        conn = sqlite3.connect('hussainiya_stores.db')
        cursor = conn.cursor()
        
        user_id = str(session['user_id'])

        # للإشعارات المتقدمة
        cursor.execute('SELECT read_by FROM advanced_notifications WHERE id = ?', (notification_id,))
        result = cursor.fetchone()

        if result:
            read_by = result[0] or ''
            if user_id not in read_by:
                new_read_by = f"{read_by},{user_id}" if read_by else user_id
                cursor.execute('UPDATE advanced_notifications SET read_by = ? WHERE id = ?', 
                              (new_read_by, notification_id))
        
        # تسجيل القراءة في جدول notification_reads
        cursor.execute('''
            INSERT OR REPLACE INTO notification_reads 
            (notification_id, user_id, action_taken)
            VALUES (?, ?, ?)
        ''', (notification_id, session['user_id'], action_taken))
        
        # تحديث الإحصائيات
        cursor.execute('''
            INSERT OR IGNORE INTO notification_stats (notification_id, total_sent)
            VALUES (?, 1)
        ''', (notification_id,))
        
        if action_taken == 'read':
            cursor.execute('''
                UPDATE notification_stats 
                SET total_read = total_read + 1
                WHERE notification_id = ?
            ''', (notification_id,))
        elif action_taken == 'clicked':
            cursor.execute('''
                UPDATE notification_stats 
                SET total_clicked = total_clicked + 1
                WHERE notification_id = ?
            ''', (notification_id,))
        elif action_taken == 'dismissed':
            cursor.execute('''
                UPDATE notification_stats 
                SET total_dismissed = total_dismissed + 1
                WHERE notification_id = ?
            ''', (notification_id,))

        conn.commit()
        conn.close()
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

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

# دمج البيانات من قاعدة بيانات احتياطية
def merge_databases(backup_db_path, current_db_path):
    """دمج البيانات من قاعدة البيانات الاحتياطية مع الحالية مع الحفاظ على جميع البيانات الحالية"""
    current_conn = None
    temp_backup_conn = None
    
    try:
        # التأكد من إغلاق جميع الاتصالات السابقة
        import gc
        gc.collect()
        
        # نسخ قاعدة البيانات الاحتياطية إلى ملف مؤقت لتجنب القفل
        temp_backup_path = f"temp_merge_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy2(backup_db_path, temp_backup_path)
        
        # الاتصال بقاعدة البيانات الحالية
        current_conn = sqlite3.connect(current_db_path, timeout=30.0)
        current_conn.execute('PRAGMA journal_mode=WAL')
        current_cursor = current_conn.cursor()
        
        # الاتصال بقاعدة البيانات الاحتياطية المؤقتة
        temp_backup_conn = sqlite3.connect(temp_backup_path, timeout=30.0)
        temp_backup_cursor = temp_backup_conn.cursor()
        
        merge_log = []
        merge_log.append("بدء عملية دمج البيانات مع الحفاظ على جميع البيانات الحالية...")
        
        # دمج جدول المستخدمين
        merge_log.extend(merge_users_table_safe(current_cursor, temp_backup_cursor))
        
        # دمج جدول التصنيفات
        merge_log.extend(merge_categories_table_safe(current_cursor, temp_backup_cursor))
        
        # دمج جدول المحلات
        merge_log.extend(merge_stores_table_safe(current_cursor, temp_backup_cursor))
        
        # دمج جدول الخدمات الهامة
        merge_log.extend(merge_services_table_safe(current_cursor, temp_backup_cursor))
        
        # دمج جدول تصنيفات الخدمات
        merge_log.extend(merge_service_categories_table_safe(current_cursor, temp_backup_cursor))
        
        # دمج جدول الصيدليات المناوبة
        merge_log.extend(merge_duty_pharmacies_table_safe(current_cursor, temp_backup_cursor))
        
        # دمج جدول الإشعارات
        merge_log.extend(merge_notifications_table_safe(current_cursor, temp_backup_cursor))
        
        # دمج جدول الشريط المتحرك
        merge_log.extend(merge_ticker_messages_table_safe(current_cursor, temp_backup_cursor))
        
        # دمج جدول التقييمات
        merge_log.extend(merge_ratings_table_safe(current_cursor, temp_backup_cursor))
        
        # دمج جدول إعدادات الموقع
        merge_log.extend(merge_site_settings_table_safe(current_cursor, temp_backup_cursor))
        
        # دمج جدول النقاط والهدايا
        merge_log.extend(merge_points_tables_safe(current_cursor, temp_backup_cursor))
        
        # حفظ التغييرات
        current_conn.commit()
        
        # إغلاق الاتصالات
        temp_backup_conn.close()
        current_conn.close()
        
        # حذف الملف المؤقت
        if os.path.exists(temp_backup_path):
            os.remove(temp_backup_path)
        
        merge_log.append("تم إنهاء عملية الدمج بنجاح مع الحفاظ على جميع البيانات الحالية")
        return True, merge_log
        
    except Exception as e:
        # التأكد من إغلاق الاتصالات في حالة الخطأ
        if temp_backup_conn:
            try:
                temp_backup_conn.close()
            except:
                pass
        if current_conn:
            try:
                current_conn.rollback()
                current_conn.close()
            except:
                pass
        
        # حذف الملف المؤقت
        if 'temp_backup_path' in locals() and os.path.exists(temp_backup_path):
            try:
                os.remove(temp_backup_path)
            except:
                pass
        
        return False, [f"خطأ في دمج البيانات: {str(e)}"]

def merge_users_table_safe(current_cursor, backup_cursor):
    """دمج جدول المستخدمين بطريقة آمنة - الحفاظ على جميع البيانات الموجودة وإضافة الجديدة فقط"""
    log = []
    try:
        # جلب المستخدمين من النسخة الاحتياطية
        backup_cursor.execute('''
            SELECT id, full_name, phone, password_hash, is_active, is_admin, is_verified, can_edit_name, created_at
            FROM users
        ''')
        backup_users = backup_cursor.fetchall()
        
        # جلب جميع المستخدمين الحاليين
        current_cursor.execute('SELECT phone FROM users')
        existing_phones = set(row[0] for row in current_cursor.fetchall())
        
        updated_count = 0
        added_count = 0
        preserved_count = 0
        
        for user in backup_users:
            phone = user[2]
            
            if phone in existing_phones:
                # المستخدم موجود - الاحتفاظ بالبيانات الحالية تماماً
                preserved_count += 1
                log.append(f"تم الاحتفاظ بالمستخدم الموجود: {user[1]} ({phone})")
            else:
                # مستخدم جديد - إضافته
                try:
                    current_cursor.execute('''
                        INSERT INTO users (full_name, phone, password_hash, is_active, is_admin, is_verified, can_edit_name, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', user[1:])
                    added_count += 1
                    log.append(f"تم إضافة المستخدم الجديد: {user[1]} ({phone})")
                except Exception as e:
                    log.append(f"خطأ في إضافة المستخدم {user[1]}: {str(e)}")
        
        log.insert(0, f"المستخدمين: تم إضافة {added_count} جديد، المحافظة على {preserved_count} موجود")
        
    except Exception as e:
        log.append(f"خطأ في دمج المستخدمين: {str(e)}")
    
    return log

def merge_categories_table_safe(current_cursor, backup_cursor):
    """دمج جدول التصنيفات بطريقة آمنة"""
    log = []
    try:
        backup_cursor.execute('SELECT id, name, description FROM categories')
        backup_categories = backup_cursor.fetchall()
        
        # جلب التصنيفات الحالية
        current_cursor.execute('SELECT name FROM categories')
        existing_names = set(row[0] for row in current_cursor.fetchall())
        
        added_count = 0
        preserved_count = 0
        
        for category in backup_categories:
            if category[1] in existing_names:
                preserved_count += 1
            else:
                current_cursor.execute('INSERT INTO categories (name, description) VALUES (?, ?)', 
                                     (category[1], category[2]))
                added_count += 1
        
        log.append(f"التصنيفات: تم إضافة {added_count} جديد، المحافظة على {preserved_count} موجود")
        
    except Exception as e:
        log.append(f"خطأ في دمج التصنيفات: {str(e)}")
    
    return log

def merge_stores_table_safe(current_cursor, backup_cursor):
    """دمج جدول المحلات بطريقة آمنة"""
    log = []
    try:
        backup_cursor.execute('''
            SELECT id, name, category_id, address, phone, description, image_url, 
                   user_id, is_approved, visits_count, search_count, rating_avg, created_at
            FROM stores
        ''')
        backup_stores = backup_cursor.fetchall()
        
        # جلب المحلات الحالية (بناءً على الاسم والعنوان)
        current_cursor.execute('SELECT name, address FROM stores')
        existing_stores = set((row[0], row[1]) for row in current_cursor.fetchall())
        
        added_count = 0
        preserved_count = 0
        
        for store in backup_stores:
            store_key = (store[1], store[3])  # (name, address)
            
            if store_key in existing_stores:
                preserved_count += 1
            else:
                current_cursor.execute('''
                    INSERT INTO stores (name, category_id, address, phone, description, image_url, 
                                      user_id, is_approved, visits_count, search_count, rating_avg, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', store[1:])
                added_count += 1
        
        log.append(f"المحلات: تم إضافة {added_count} جديد، المحافظة على {preserved_count} موجود")
        
    except Exception as e:
        log.append(f"خطأ في دمج المحلات: {str(e)}")
    
    return log

def merge_services_table_safe(current_cursor, backup_cursor):
    """دمج جدول الخدمات الهامة بطريقة آمنة"""
    log = []
    try:
        backup_cursor.execute('SELECT id, name, phone, description, category FROM important_services')
        backup_services = backup_cursor.fetchall()
        
        # جلب الخدمات الحالية
        current_cursor.execute('SELECT name, phone FROM important_services')
        existing_services = set((row[0], row[1]) for row in current_cursor.fetchall())
        
        added_count = 0
        preserved_count = 0
        
        for service in backup_services:
            service_key = (service[1], service[2])  # (name, phone)
            
            if service_key in existing_services:
                preserved_count += 1
            else:
                current_cursor.execute('''
                    INSERT INTO important_services (name, phone, description, category) 
                    VALUES (?, ?, ?, ?)
                ''', (service[1], service[2], service[3], service[4]))
                added_count += 1
        
        log.append(f"الخدمات الهامة: تم إضافة {added_count} جديد، المحافظة على {preserved_count} موجود")
        
    except Exception as e:
        log.append(f"خطأ في دمج الخدمات الهامة: {str(e)}")
    
    return log

def merge_service_categories_table_safe(current_cursor, backup_cursor):
    """دمج جدول تصنيفات الخدمات بطريقة آمنة"""
    log = []
    try:
        backup_cursor.execute('SELECT id, name, description, icon, color FROM service_categories')
        backup_categories = backup_cursor.fetchall()
        
        # جلب تصنيفات الخدمات الحالية
        current_cursor.execute('SELECT name FROM service_categories')
        existing_names = set(row[0] for row in current_cursor.fetchall())
        
        added_count = 0
        preserved_count = 0
        
        for category in backup_categories:
            if category[1] in existing_names:
                preserved_count += 1
            else:
                current_cursor.execute('''
                    INSERT INTO service_categories (name, description, icon, color) 
                    VALUES (?, ?, ?, ?)
                ''', (category[1], category[2], category[3], category[4]))
                added_count += 1
        
        log.append(f"تصنيفات الخدمات: تم إضافة {added_count} جديد، المحافظة على {preserved_count} موجود")
        
    except Exception as e:
        log.append(f"خطأ في دمج تصنيفات الخدمات: {str(e)}")
    
    return log

def merge_duty_pharmacies_table_safe(current_cursor, backup_cursor):
    """دمج جدول الصيدليات المناوبة بطريقة آمنة"""
    log = []
    try:
        backup_cursor.execute('SELECT id, name, address, phone, duty_date FROM duty_pharmacies')
        backup_pharmacies = backup_cursor.fetchall()
        
        # جلب الصيدليات المناوبة الحالية
        current_cursor.execute('SELECT duty_date FROM duty_pharmacies')
        existing_dates = set(row[0] for row in current_cursor.fetchall())
        
        added_count = 0
        preserved_count = 0
        
        for pharmacy in backup_pharmacies:
            if pharmacy[4] in existing_dates:
                preserved_count += 1
            else:
                current_cursor.execute('''
                    INSERT INTO duty_pharmacies (name, address, phone, duty_date) 
                    VALUES (?, ?, ?, ?)
                ''', (pharmacy[1], pharmacy[2], pharmacy[3], pharmacy[4]))
                added_count += 1
        
        log.append(f"الصيدليات المناوبة: تم إضافة {added_count} جديد، المحافظة على {preserved_count} موجود")
        
    except Exception as e:
        log.append(f"خطأ في دمج الصيدليات المناوبة: {str(e)}")
    
    return log

def merge_notifications_table_safe(current_cursor, backup_cursor):
    """دمج جدول الإشعارات بطريقة آمنة"""
    log = []
    try:
        backup_cursor.execute('''
            SELECT id, title, message, type, is_active, created_at, expires_at 
            FROM notifications
        ''')
        backup_notifications = backup_cursor.fetchall()
        
        # جلب الإشعارات الحالية
        current_cursor.execute('SELECT title, message FROM notifications')
        existing_notifications = set((row[0], row[1]) for row in current_cursor.fetchall())
        
        added_count = 0
        preserved_count = 0
        
        for notification in backup_notifications:
            notification_key = (notification[1], notification[2])  # (title, message)
            
            if notification_key in existing_notifications:
                preserved_count += 1
            else:
                current_cursor.execute('''
                    INSERT INTO notifications (title, message, type, is_active, created_at, expires_at) 
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (notification[1], notification[2], notification[3], notification[4], notification[5], notification[6]))
                added_count += 1
        
        log.append(f"الإشعارات: تم إضافة {added_count} جديد، المحافظة على {preserved_count} موجود")
        
    except Exception as e:
        log.append(f"خطأ في دمج الإشعارات: {str(e)}")
    
    return log

def merge_ticker_messages_table_safe(current_cursor, backup_cursor):
    """دمج جدول الشريط المتحرك بطريقة آمنة"""
    log = []
    try:
        backup_cursor.execute('''
            SELECT id, message, type, priority, is_active, direction, speed, 
                   background_color, text_color, font_size, created_at
            FROM ticker_messages
        ''')
        backup_messages = backup_cursor.fetchall()
        
        # جلب رسائل الشريط المتحرك الحالية
        current_cursor.execute('SELECT message FROM ticker_messages')
        existing_messages = set(row[0] for row in current_cursor.fetchall())
        
        added_count = 0
        preserved_count = 0
        
        for message in backup_messages:
            if message[1] in existing_messages:
                preserved_count += 1
            else:
                try:
                    current_cursor.execute('''
                        INSERT INTO ticker_messages (message, type, priority, is_active, direction, 
                                                   speed, background_color, text_color, font_size, created_at) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', message[1:])
                    added_count += 1
                except:
                    # إذا فشل، جرب بدون الأعمدة الجديدة
                    current_cursor.execute('''
                        INSERT INTO ticker_messages (message, type, priority, is_active, created_at) 
                        VALUES (?, ?, ?, ?, ?)
                    ''', (message[1], message[2], message[3], message[4], message[10]))
                    added_count += 1
        
        log.append(f"رسائل الشريط المتحرك: تم إضافة {added_count} جديد، المحافظة على {preserved_count} موجود")
        
    except Exception as e:
        log.append(f"خطأ في دمج رسائل الشريط المتحرك: {str(e)}")
    
    return log

def merge_ratings_table_safe(current_cursor, backup_cursor):
    """دمج جدول التقييمات بطريقة آمنة"""
    log = []
    try:
        backup_cursor.execute('''
            SELECT id, store_id, user_id, rating, comment, created_at
            FROM ratings
        ''')
        backup_ratings = backup_cursor.fetchall()
        
        # جلب التقييمات الحالية
        current_cursor.execute('SELECT store_id, user_id FROM ratings')
        existing_ratings = set((row[0], row[1]) for row in current_cursor.fetchall())
        
        added_count = 0
        preserved_count = 0
        
        for rating in backup_ratings:
            rating_key = (rating[1], rating[2])  # (store_id, user_id)
            
            if rating_key in existing_ratings:
                preserved_count += 1
            else:
                try:
                    current_cursor.execute('''
                        INSERT INTO ratings (store_id, user_id, rating, comment, created_at, updated_at) 
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (rating[1], rating[2], rating[3], rating[4], rating[5], rating[5]))
                    added_count += 1
                except:
                    current_cursor.execute('''
                        INSERT INTO ratings (store_id, user_id, rating, comment, created_at) 
                        VALUES (?, ?, ?, ?, ?)
                    ''', (rating[1], rating[2], rating[3], rating[4], rating[5]))
                    added_count += 1
        
        log.append(f"التقييمات: تم إضافة {added_count} جديد، المحافظة على {preserved_count} موجود")
        
    except Exception as e:
        log.append(f"خطأ في دمج التقييمات: {str(e)}")
    
    return log

def merge_site_settings_table_safe(current_cursor, backup_cursor):
    """دمج جدول إعدادات الموقع بطريقة آمنة"""
    log = []
    try:
        backup_cursor.execute('''
            SELECT id, setting_key, setting_value, description, category 
            FROM site_settings
        ''')
        backup_settings = backup_cursor.fetchall()
        
        # جلب الإعدادات الحالية
        current_cursor.execute('SELECT setting_key FROM site_settings')
        existing_keys = set(row[0] for row in current_cursor.fetchall())
        
        added_count = 0
        preserved_count = 0
        
        for setting in backup_settings:
            if setting[1] in existing_keys:
                preserved_count += 1
            else:
                current_cursor.execute('''
                    INSERT INTO site_settings (setting_key, setting_value, description, category) 
                    VALUES (?, ?, ?, ?)
                ''', (setting[1], setting[2], setting[3], setting[4]))
                added_count += 1
        
        log.append(f"إعدادات الموقع: تم إضافة {added_count} جديد، المحافظة على {preserved_count} موجود")
        
    except Exception as e:
        log.append(f"خطأ في دمج إعدادات الموقع: {str(e)}")
    
    return log

def merge_points_tables_safe(current_cursor, backup_cursor):
    """دمج جداول النقاط والهدايا بطريقة آمنة"""
    log = []
    try:
        # دمج إعدادات النقاط
        try:
            backup_cursor.execute('''
                SELECT id, setting_key, setting_value, description, updated_at 
                FROM points_settings
            ''')
            backup_points_settings = backup_cursor.fetchall()
            
            # جلب إعدادات النقاط الحالية
            current_cursor.execute('SELECT setting_key FROM points_settings')
            existing_keys = set(row[0] for row in current_cursor.fetchall())
            
            for setting in backup_points_settings:
                if setting[1] not in existing_keys:
                    current_cursor.execute('''
                        INSERT INTO points_settings (setting_key, setting_value, description, updated_at) 
                        VALUES (?, ?, ?, ?)
                    ''', (setting[1], setting[2], setting[3], setting[4]))
        except:
            pass
        
        # دمج الهدايا
        try:
            backup_cursor.execute('''
                SELECT id, name, description, points_cost, is_active, stock_quantity, 
                       image_url, category, created_at, updated_at 
                FROM gifts
            ''')
            backup_gifts = backup_cursor.fetchall()
            
            # جلب الهدايا الحالية
            current_cursor.execute('SELECT name FROM gifts')
            existing_names = set(row[0] for row in current_cursor.fetchall())
            
            gifts_added = 0
            for gift in backup_gifts:
                if gift[1] not in existing_names:
                    current_cursor.execute('''
                        INSERT INTO gifts (name, description, points_cost, is_active, stock_quantity, 
                                         image_url, category, created_at, updated_at) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', gift[1:])
                    gifts_added += 1
            
            log.append(f"الهدايا: تم إضافة {gifts_added} هدية جديدة، المحافظة على الهدايا الموجودة")
        except:
            pass
        
        log.append("تم دمج جداول النقاط والهدايا بنجاح مع الحفاظ على البيانات الحالية")
        
    except Exception as e:
        log.append(f"خطأ في دمج جداول النقاط: {str(e)}")
    
    return log

def merge_categories_table(cursor):
    """دمج جدول التصنيفات"""
    log = []
    try:
        cursor.execute('SELECT id, name, description FROM backup_db.categories')
        backup_categories = cursor.fetchall()
        
        updated_count = 0
        added_count = 0
        
        for category in backup_categories:
            cursor.execute('SELECT id FROM categories WHERE name = ?', (category[1],))
            existing = cursor.fetchone()
            
            if existing:
                cursor.execute('UPDATE categories SET description = ? WHERE name = ?', 
                             (category[2], category[1]))
                if cursor.rowcount > 0:
                    updated_count += 1
            else:
                cursor.execute('INSERT INTO categories (name, description) VALUES (?, ?)', 
                             (category[1], category[2]))
                added_count += 1
        
        log.append(f"التصنيفات: تم إضافة {added_count} وتحديث {updated_count}")
        
    except Exception as e:
        log.append(f"خطأ في دمج التصنيفات: {str(e)}")
    
    return log

def merge_stores_table(cursor):
    """دمج جدول المحلات"""
    log = []
    try:
        cursor.execute('''
            SELECT id, name, category_id, address, phone, description, image_url, 
                   user_id, is_approved, visits_count, search_count, rating_avg, created_at
            FROM backup_db.stores
        ''')
        backup_stores = cursor.fetchall()
        
        updated_count = 0
        added_count = 0
        
        for store in backup_stores:
            # البحث عن محل بنفس الاسم والعنوان
            cursor.execute('SELECT id FROM stores WHERE name = ? AND address = ?', 
                         (store[1], store[3]))
            existing = cursor.fetchone()
            
            if existing:
                # تحديث المحل الموجود (الحفاظ على الإحصائيات الأعلى)
                cursor.execute('''
                    SELECT visits_count, search_count, rating_avg, is_approved 
                    FROM stores WHERE id = ?
                ''', (existing[0],))
                current_stats = cursor.fetchone()
                
                new_visits = max(current_stats[0] or 0, store[9] or 0)
                new_search = max(current_stats[1] or 0, store[10] or 0)
                new_rating = max(current_stats[2] or 0, store[11] or 0)
                new_approved = max(current_stats[3] or 0, store[8] or 0)
                
                cursor.execute('''
                    UPDATE stores SET 
                        description = ?, phone = ?, image_url = ?, 
                        visits_count = ?, search_count = ?, rating_avg = ?, is_approved = ?
                    WHERE id = ?
                ''', (store[5], store[4], store[6], new_visits, new_search, new_rating, new_approved, existing[0]))
                
                if cursor.rowcount > 0:
                    updated_count += 1
            else:
                # إضافة محل جديد
                cursor.execute('''
                    INSERT INTO stores (name, category_id, address, phone, description, image_url, 
                                      user_id, is_approved, visits_count, search_count, rating_avg, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', store[1:])
                added_count += 1
        
        log.append(f"المحلات: تم إضافة {added_count} وتحديث {updated_count}")
        
    except Exception as e:
        log.append(f"خطأ في دمج المحلات: {str(e)}")
    
    return log

def merge_services_table(cursor):
    """دمج جدول الخدمات الهامة"""
    log = []
    try:
        cursor.execute('SELECT id, name, phone, description, category FROM backup_db.important_services')
        backup_services = cursor.fetchall()
        
        updated_count = 0
        added_count = 0
        
        for service in backup_services:
            cursor.execute('SELECT id FROM important_services WHERE name = ? AND phone = ?', 
                         (service[1], service[2]))
            existing = cursor.fetchone()
            
            if existing:
                cursor.execute('''
                    UPDATE important_services SET description = ?, category = ? 
                    WHERE id = ?
                ''', (service[3], service[4], existing[0]))
                if cursor.rowcount > 0:
                    updated_count += 1
            else:
                cursor.execute('''
                    INSERT INTO important_services (name, phone, description, category) 
                    VALUES (?, ?, ?, ?)
                ''', (service[1], service[2], service[3], service[4]))
                added_count += 1
        
        log.append(f"الخدمات الهامة: تم إضافة {added_count} وتحديث {updated_count}")
        
    except Exception as e:
        log.append(f"خطأ في دمج الخدمات الهامة: {str(e)}")
    
    return log

def merge_service_categories_table(cursor):
    """دمج جدول تصنيفات الخدمات"""
    log = []
    try:
        cursor.execute('SELECT id, name, description, icon, color FROM backup_db.service_categories')
        backup_categories = cursor.fetchall()
        
        updated_count = 0
        added_count = 0
        
        for category in backup_categories:
            cursor.execute('SELECT id FROM service_categories WHERE name = ?', (category[1],))
            existing = cursor.fetchone()
            
            if existing:
                cursor.execute('''
                    UPDATE service_categories SET description = ?, icon = ?, color = ? 
                    WHERE name = ?
                ''', (category[2], category[3], category[4], category[1]))
                if cursor.rowcount > 0:
                    updated_count += 1
            else:
                cursor.execute('''
                    INSERT INTO service_categories (name, description, icon, color) 
                    VALUES (?, ?, ?, ?)
                ''', (category[1], category[2], category[3], category[4]))
                added_count += 1
        
        log.append(f"تصنيفات الخدمات: تم إضافة {added_count} وتحديث {updated_count}")
        
    except Exception as e:
        log.append(f"خطأ في دمج تصنيفات الخدمات: {str(e)}")
    
    return log

def merge_duty_pharmacies_table(cursor):
    """دمج جدول الصيدليات المناوبة"""
    log = []
    try:
        cursor.execute('SELECT id, name, address, phone, duty_date FROM backup_db.duty_pharmacies')
        backup_pharmacies = cursor.fetchall()
        
        updated_count = 0
        added_count = 0
        
        for pharmacy in backup_pharmacies:
            cursor.execute('SELECT id FROM duty_pharmacies WHERE duty_date = ?', (pharmacy[4],))
            existing = cursor.fetchone()
            
            if existing:
                cursor.execute('''
                    UPDATE duty_pharmacies SET name = ?, address = ?, phone = ? 
                    WHERE duty_date = ?
                ''', (pharmacy[1], pharmacy[2], pharmacy[3], pharmacy[4]))
                if cursor.rowcount > 0:
                    updated_count += 1
            else:
                cursor.execute('''
                    INSERT INTO duty_pharmacies (name, address, phone, duty_date) 
                    VALUES (?, ?, ?, ?)
                ''', (pharmacy[1], pharmacy[2], pharmacy[3], pharmacy[4]))
                added_count += 1
        
        log.append(f"الصيدليات المناوبة: تم إضافة {added_count} وتحديث {updated_count}")
        
    except Exception as e:
        log.append(f"خطأ في دمج الصيدليات المناوبة: {str(e)}")
    
    return log

def merge_notifications_table(cursor):
    """دمج جدول الإشعارات"""
    log = []
    try:
        cursor.execute('''
            SELECT id, title, message, type, is_active, created_at, expires_at 
            FROM backup_db.notifications
        ''')
        backup_notifications = cursor.fetchall()
        
        added_count = 0
        
        for notification in backup_notifications:
            # إضافة الإشعارات الجديدة فقط (تجنب التكرار بناءً على العنوان والرسالة)
            cursor.execute('SELECT id FROM notifications WHERE title = ? AND message = ?', 
                         (notification[1], notification[2]))
            existing = cursor.fetchone()
            
            if not existing:
                cursor.execute('''
                    INSERT INTO notifications (title, message, type, is_active, created_at, expires_at) 
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (notification[1], notification[2], notification[3], notification[4], notification[5], notification[6]))
                added_count += 1
        
        log.append(f"الإشعارات: تم إضافة {added_count} إشعار جديد")
        
    except Exception as e:
        log.append(f"خطأ في دمج الإشعارات: {str(e)}")
    
    return log

def merge_ticker_messages_table(cursor):
    """دمج جدول الشريط المتحرك"""
    log = []
    try:
        cursor.execute('''
            SELECT id, message, type, priority, is_active, direction, speed, 
                   background_color, text_color, font_size, created_at
            FROM backup_db.ticker_messages
        ''')
        backup_messages = cursor.fetchall()
        
        added_count = 0
        
        for message in backup_messages:
            # إضافة الرسائل الجديدة فقط
            cursor.execute('SELECT id FROM ticker_messages WHERE message = ?', (message[1],))
            existing = cursor.fetchone()
            
            if not existing:
                try:
                    cursor.execute('''
                        INSERT INTO ticker_messages (message, type, priority, is_active, direction, 
                                                   speed, background_color, text_color, font_size, created_at) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', message[1:])
                    added_count += 1
                except:
                    # إذا فشل، جرب بدون الأعمدة الجديدة
                    cursor.execute('''
                        INSERT INTO ticker_messages (message, type, priority, is_active, created_at) 
                        VALUES (?, ?, ?, ?, ?)
                    ''', (message[1], message[2], message[3], message[4], message[10]))
                    added_count += 1
        
        log.append(f"رسائل الشريط المتحرك: تم إضافة {added_count} رسالة جديدة")
        
    except Exception as e:
        log.append(f"خطأ في دمج رسائل الشريط المتحرك: {str(e)}")
    
    return log

def merge_ratings_table(cursor):
    """دمج جدول التقييمات"""
    log = []
    try:
        cursor.execute('''
            SELECT id, store_id, user_id, rating, comment, created_at
            FROM backup_db.ratings
        ''')
        backup_ratings = cursor.fetchall()
        
        updated_count = 0
        added_count = 0
        
        for rating in backup_ratings:
            cursor.execute('SELECT id, rating, comment FROM ratings WHERE store_id = ? AND user_id = ?', 
                         (rating[1], rating[2]))
            existing = cursor.fetchone()
            
            if existing:
                # تحديث التقييم إذا كان مختلفاً
                if existing[1] != rating[3] or existing[2] != rating[4]:
                    try:
                        cursor.execute('''
                            UPDATE ratings SET rating = ?, comment = ?, updated_at = ? 
                            WHERE store_id = ? AND user_id = ?
                        ''', (rating[3], rating[4], rating[5], rating[1], rating[2]))
                    except:
                        cursor.execute('''
                            UPDATE ratings SET rating = ?, comment = ? 
                            WHERE store_id = ? AND user_id = ?
                        ''', (rating[3], rating[4], rating[1], rating[2]))
                    updated_count += 1
            else:
                # إضافة تقييم جديد
                try:
                    cursor.execute('''
                        INSERT INTO ratings (store_id, user_id, rating, comment, created_at, updated_at) 
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (rating[1], rating[2], rating[3], rating[4], rating[5], rating[5]))
                except:
                    cursor.execute('''
                        INSERT INTO ratings (store_id, user_id, rating, comment, created_at) 
                        VALUES (?, ?, ?, ?, ?)
                    ''', (rating[1], rating[2], rating[3], rating[4], rating[5]))
                added_count += 1
        
        log.append(f"التقييمات: تم إضافة {added_count} وتحديث {updated_count}")
        
    except Exception as e:
        log.append(f"خطأ في دمج التقييمات: {str(e)}")
    
    return log

def merge_site_settings_table(cursor):
    """دمج جدول إعدادات الموقع"""
    log = []
    try:
        cursor.execute('''
            SELECT id, setting_key, setting_value, description, category 
            FROM backup_db.site_settings
        ''')
        backup_settings = cursor.fetchall()
        
        updated_count = 0
        added_count = 0
        
        for setting in backup_settings:
            cursor.execute('SELECT id FROM site_settings WHERE setting_key = ?', (setting[1],))
            existing = cursor.fetchone()
            
            if existing:
                cursor.execute('''
                    UPDATE site_settings SET setting_value = ?, description = ?, category = ? 
                    WHERE setting_key = ?
                ''', (setting[2], setting[3], setting[4], setting[1]))
                if cursor.rowcount > 0:
                    updated_count += 1
            else:
                cursor.execute('''
                    INSERT INTO site_settings (setting_key, setting_value, description, category) 
                    VALUES (?, ?, ?, ?)
                ''', (setting[1], setting[2], setting[3], setting[4]))
                added_count += 1
        
        log.append(f"إعدادات الموقع: تم إضافة {added_count} وتحديث {updated_count}")
        
    except Exception as e:
        log.append(f"خطأ في دمج إعدادات الموقع: {str(e)}")
    
    return log

def merge_points_tables(cursor):
    """دمج جداول النقاط والهدايا"""
    log = []
    try:
        # دمج إعدادات النقاط
        try:
            cursor.execute('''
                SELECT id, setting_key, setting_value, description, updated_at 
                FROM backup_db.points_settings
            ''')
            backup_points_settings = cursor.fetchall()
            
            for setting in backup_points_settings:
                cursor.execute('SELECT id FROM points_settings WHERE setting_key = ?', (setting[1],))
                if cursor.fetchone():
                    cursor.execute('''
                        UPDATE points_settings SET setting_value = ?, description = ?, updated_at = ? 
                        WHERE setting_key = ?
                    ''', (setting[2], setting[3], setting[4], setting[1]))
                else:
                    cursor.execute('''
                        INSERT INTO points_settings (setting_key, setting_value, description, updated_at) 
                        VALUES (?, ?, ?, ?)
                    ''', (setting[1], setting[2], setting[3], setting[4]))
        except:
            pass
        
        # دمج الهدايا
        try:
            cursor.execute('''
                SELECT id, name, description, points_cost, is_active, stock_quantity, 
                       image_url, category, created_at, updated_at 
                FROM backup_db.gifts
            ''')
            backup_gifts = cursor.fetchall()
            
            gifts_added = 0
            for gift in backup_gifts:
                cursor.execute('SELECT id FROM gifts WHERE name = ?', (gift[1],))
                if not cursor.fetchone():
                    cursor.execute('''
                        INSERT INTO gifts (name, description, points_cost, is_active, stock_quantity, 
                                         image_url, category, created_at, updated_at) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', gift[1:])
                    gifts_added += 1
            
            log.append(f"الهدايا: تم إضافة {gifts_added} هدية جديدة")
        except:
            pass
        
        log.append("تم دمج جداول النقاط والهدايا بنجاح")
        
    except Exception as e:
        log.append(f"خطأ في دمج جداول النقاط: {str(e)}")
    
    return log

# حفظ النسخة المرفوعة في جدول النسخ الاحتياطية
@app.route('/admin/save-uploaded-backup', methods=['POST'])
def save_uploaded_backup():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    try:
        if 'backup_file' not in request.files:
            flash('لم يتم اختيار ملف', 'error')
            return redirect(url_for('admin_backup'))

        file = request.files['backup_file']
        if file.filename == '':
            flash('لم يتم اختيار ملف', 'error')
            return redirect(url_for('admin_backup'))

        # التحقق من نوع الملف
        allowed_extensions = ['.db', '.zip']
        if not any(file.filename.endswith(ext) for ext in allowed_extensions):
            flash('يجب أن يكون الملف من نوع .db أو .zip', 'error')
            return redirect(url_for('admin_backup'))

        # إنشاء مجلد النسخ الاحتياطية
        os.makedirs('backups', exist_ok=True)

        # إنشاء اسم ملف مميز للنسخة المرفوعة
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        original_name = secure_filename(file.filename)
        name_without_ext = os.path.splitext(original_name)[0]
        file_ext = os.path.splitext(original_name)[1]
        
        # تمييز النسخة المرفوعة في الاسم
        new_filename = f"uploaded_{name_without_ext}_{timestamp}{file_ext}"
        backup_path = os.path.join('backups', new_filename)

        # حفظ الملف
        file.save(backup_path)

        file_size = os.path.getsize(backup_path)
        size_text = f"{file_size / 1024:.1f} KB" if file_size < 1024*1024 else f"{file_size / (1024*1024):.1f} MB"
        
        flash(f'تم حفظ النسخة المرفوعة بنجاح: {new_filename} ({size_text})', 'success')

    except Exception as e:
        flash(f'خطأ في حفظ النسخة المرفوعة: {str(e)}', 'error')

    return redirect(url_for('admin_backup'))

# رفع واستعادة النسخة الاحتياطية
@app.route('/admin/restore-backup', methods=['POST'])
def restore_backup():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))

    # التحقق من وجود اسم ملف من القائمة
    backup_filename = request.form.get('backup_filename')
    merge_data = request.form.get('merge_data') == 'on'
    
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if backup_filename:
            # استعادة من النسخ الموجودة في القائمة
            backup_path = os.path.join('backups', backup_filename)
            
            if not os.path.exists(backup_path):
                flash('الملف غير موجود', 'error')
                return redirect(url_for('admin_backup'))
            
            # إنشاء نسخة احتياطية من قاعدة البيانات الحالية
            current_backup = f'hussainiya_stores_backup_before_restore_{timestamp}.db'
            shutil.copy2('hussainiya_stores.db', current_backup)
            
            temp_backup_path = f'temp_restore_{timestamp}.db'
            shutil.copy2(backup_path, temp_backup_path)
            
        else:
            # استعادة من ملف مرفوع
            if 'backup_file' not in request.files:
                flash('لم يتم اختيار ملف', 'error')
                return redirect(url_for('admin_backup'))

            file = request.files['backup_file']
            if file.filename == '':
                flash('لم يتم اختيار ملف', 'error')
                return redirect(url_for('admin_backup'))

            if not file.filename.endswith('.db'):
                flash('يجب أن يكون الملف من نوع .db', 'error')
                return redirect(url_for('admin_backup'))

            # إنشاء نسخة احتياطية من قاعدة البيانات الحالية
            current_backup = f'hussainiya_stores_backup_before_restore_{timestamp}.db'
            shutil.copy2('hussainiya_stores.db', current_backup)

            # حفظ الملف المرفوع مؤقتاً
            filename = secure_filename(file.filename)
            temp_backup_path = f'temp_backup_{timestamp}.db'
            file.save(temp_backup_path)

        # تطبيق الاستعادة حسب النوع المختار
        if merge_data:
            # دمج البيانات
            success, merge_log = merge_databases(temp_backup_path, 'hussainiya_stores.db')
            
            if success:
                flash(f'تم دمج البيانات بنجاح! تفاصيل العملية:', 'success')
                for log_entry in merge_log[:10]:  # عرض أول 10 سطور
                    flash(log_entry, 'info')
                if len(merge_log) > 10:
                    flash(f'... و {len(merge_log) - 10} عملية أخرى', 'info')
            else:
                flash('فشل في دمج البيانات', 'error')
                for log_entry in merge_log:
                    flash(log_entry, 'error')
        else:
            # استعادة كاملة (الطريقة القديمة)
            shutil.copy2(temp_backup_path, 'hussainiya_stores.db')
            flash('تم استعادة النسخة الاحتياطية بنجاح (استعادة كاملة)', 'success')

        # حذف الملف المؤقت
        if os.path.exists(temp_backup_path):
            os.remove(temp_backup_path)

    except Exception as e:
        flash(f'خطأ في استعادة النسخة الاحتياطية: {str(e)}', 'error')

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
        return jsonify({'error': 'يجب تسجيل الدخول أولاً', 'redirect': '/login'}), 401

    # التحقق من أن المستخدم محقق
    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()
    cursor.execute('SELECT is_verified FROM users WHERE id = ?', (session['user_id'],))
    user = cursor.fetchone()
    
    if not user or not user[0]:
        conn.close()
        return jsonify({'error': 'يجب التحقق من حسابك لإجراء التقييمات. سيتم توجيهك إلى صفحة التحقق.', 'redirect': '/verification'}), 403

    rating = int(request.json.get('rating', 0))
    comment = request.json.get('comment', '').strip()
    
    if rating < 1 or rating > 5:
        conn.close()
        return jsonify({'error': 'التقييم يجب أن يكون بين 1 و 5'}), 400
    
    if not comment:
        conn.close()
        return jsonify({'error': 'يجب كتابة تعليق مع التقييم'}), 400

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
            SELECT r.id, r.rating, r.comment, r.created_at, r.updated_at, u.full_name, r.user_id, u.is_verified
            FROM ratings r 
            LEFT JOIN users u ON r.user_id = u.id 
            WHERE r.store_id = ? 
            ORDER BY r.created_at DESC
        ''', (store_id,))
    except sqlite3.OperationalError:
        # إذا لم يكن عمود updated_at موجوداً، استخدم created_at كبديل
        cursor.execute('''
            SELECT r.id, r.rating, r.comment, r.created_at, r.created_at as updated_at, u.full_name, r.user_id, u.is_verified
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
        return jsonify({'error': 'يجب تسجيل الدخول أولاً', 'redirect': '/login'}), 401

    # التحقق من أن المستخدم محقق
    conn = sqlite3.connect('hussainiya_stores.db')
    cursor = conn.cursor()
    cursor.execute('SELECT is_verified FROM users WHERE id = ?', (session['user_id'],))
    user = cursor.fetchone()
    
    if not user or not user[0]:
        conn.close()
        return jsonify({'error': 'يجب أن يكون حسابك محققاً لتعديل التقييمات', 'redirect': '/verification'}), 403

    new_comment = request.json.get('comment', '').strip()
    new_rating = int(request.json.get('rating', 0))
    
    if new_rating < 1 or new_rating > 5:
        conn.close()
        return jsonify({'error': 'التقييم يجب أن يكون بين 1 و 5'}), 400
    
    if not new_comment:
        conn.close()
        return jsonify({'error': 'يجب كتابة تعليق مع التقييم'}), 400

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
        
        # تهيئة وتشغيل بوت التليجرام
        init_telegram_bot()
        if telegram_app:
            bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
            bot_thread.start()
            print("✅ تم تشغيل بوت التليجرام في الخلفية")
        
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