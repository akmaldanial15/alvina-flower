from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import sqlite3
import random
import string
import os
import json
from datetime import datetime, timezone, timedelta
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'images')
app.config['RECEIPT_UPLOAD_FOLDER'] = os.path.join('static', 'uploads', 'receipts')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RECEIPT_UPLOAD_FOLDER'], exist_ok=True)
app.secret_key = 'super_secret_alvina_key'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'flower_shop.db')

MYT = timezone(timedelta(hours=8))

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def ensure_tables():
    """Create additional tables if they don't exist."""
    db = get_db()
    db.execute('''CREATE TABLE IF NOT EXISTS admin_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT NOT NULL,
        is_done BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    db.execute('''CREATE TABLE IF NOT EXISTS activity_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT NOT NULL,
        details TEXT,
        icon TEXT DEFAULT 'info',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    db.execute('''CREATE TABLE IF NOT EXISTS homepage_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        label TEXT NOT NULL,
        value TEXT NOT NULL,
        sort_order INTEGER DEFAULT 0
    )''')
    db.execute('''CREATE TABLE IF NOT EXISTS trust_badges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        icon TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        sort_order INTEGER DEFAULT 0
    )''')
    db.execute('''CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_name TEXT NOT NULL,
        order_id TEXT,
        rating INTEGER DEFAULT 5,
        review_text TEXT NOT NULL,
        occasion TEXT DEFAULT '',
        is_featured BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    db.execute('''CREATE TABLE IF NOT EXISTS store_settings (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        is_open BOOLEAN DEFAULT 1,
        whatsapp TEXT DEFAULT '',
        instagram TEXT DEFAULT '',
        facebook TEXT DEFAULT '',
        theme TEXT DEFAULT 'classic'
    )''')
    db.commit()
    
    if not db.execute('SELECT COUNT(*) as c FROM store_settings').fetchone()['c']:
        db.execute("INSERT INTO store_settings (id, is_open, theme) VALUES (1, 1, 'classic')")
        db.commit()

    db.execute('''CREATE TABLE IF NOT EXISTS security_settings (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        honeypot_enabled BOOLEAN DEFAULT 1,
        fast_submit_limit_ms INTEGER DEFAULT 3000,
        spam_order_limit INTEGER DEFAULT 3,
        spam_time_window_mins INTEGER DEFAULT 10
    )''')
    db.commit()

    if not db.execute('SELECT COUNT(*) as c FROM security_settings').fetchone()['c']:
        db.execute("INSERT INTO security_settings (id, honeypot_enabled, fast_submit_limit_ms, spam_order_limit, spam_time_window_mins) VALUES (1, 1, 3000, 3, 10)")
        db.commit()
    
    # ── Migrate store_settings with visitor counter columns ──
    store_cols = {col[1] for col in db.execute('PRAGMA table_info(store_settings)').fetchall()}
    if 'total_visitors' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN total_visitors INTEGER DEFAULT 0")
    if 'show_visitors' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN show_visitors BOOLEAN DEFAULT 1")
    if 'checkout_form_schema' not in store_cols:
        default_schema = json.dumps([
            {"id": "sender_name", "label": "Sender Name", "type": "text", "required": True, "enabled": True},
            {"id": "sender_phone", "label": "Sender Phone", "type": "text", "required": True, "enabled": True},
            {"id": "recipient_name", "label": "Recipient Name", "type": "text", "required": True, "enabled": True},
            {"id": "recipient_phone", "label": "Recipient Phone", "type": "text", "required": True, "enabled": True},
            {"id": "delivery_address", "label": "Delivery Address", "type": "textarea", "required": True, "enabled": True},
            {"id": "delivery_date", "label": "Delivery Date", "type": "date", "required": True, "enabled": True},
            {"id": "card_message", "label": "Card Message", "type": "textarea", "required": False, "enabled": True}
        ])
        db.execute("ALTER TABLE store_settings ADD COLUMN checkout_form_schema TEXT")
        db.execute("UPDATE store_settings SET checkout_form_schema = ?", (default_schema,))
    if 'business_hours' not in store_cols:
        default_hours = json.dumps({
            "0": {"closed": True, "slots": []},                                         # Sunday
            "1": {"closed": False, "slots": [{"start": "15:00", "end": "18:00"}, {"start": "20:00", "end": "22:00"}]}, # Monday
            "2": {"closed": False, "slots": [{"start": "15:00", "end": "18:00"}, {"start": "20:00", "end": "22:00"}]}, # Tuesday
            "3": {"closed": False, "slots": [{"start": "15:00", "end": "18:00"}, {"start": "20:00", "end": "22:00"}]}, # Wednesday
            "4": {"closed": False, "slots": [{"start": "15:00", "end": "18:00"}, {"start": "20:00", "end": "22:00"}]}, # Thursday
            "5": {"closed": False, "slots": [{"start": "15:00", "end": "18:00"}, {"start": "20:00", "end": "22:00"}]}, # Friday
            "6": {"closed": False, "slots": [{"start": "15:00", "end": "18:00"}, {"start": "20:00", "end": "22:00"}]}  # Saturday
        })
        db.execute("ALTER TABLE store_settings ADD COLUMN business_hours TEXT")
        db.execute("UPDATE store_settings SET business_hours = ?", (default_hours,))
    if 'announcement_enabled' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN announcement_enabled BOOLEAN DEFAULT 0")
    if 'announcement_text' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN announcement_text TEXT DEFAULT ''")
    if 'announcement_style' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN announcement_style TEXT DEFAULT 'info'")
    if 'announcement_type' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN announcement_type TEXT DEFAULT 'minimal_bar'")
    if 'announcement_frequency' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN announcement_frequency TEXT DEFAULT 'session'")
    if 'announcement_target_page' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN announcement_target_page TEXT DEFAULT 'all'")
    if 'announcement_start_date' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN announcement_start_date TEXT DEFAULT ''")
    if 'announcement_end_date' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN announcement_end_date TEXT DEFAULT ''")
    if 'announcement_auto_dismiss_sec' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN announcement_auto_dismiss_sec INTEGER DEFAULT 0")
    if 'announcement_delay_sec' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN announcement_delay_sec INTEGER DEFAULT 0")
    if 'announcement_scroll_pct' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN announcement_scroll_pct INTEGER DEFAULT 0")
    if 'announcement_exit_intent' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN announcement_exit_intent BOOLEAN DEFAULT 0")
    if 'announcement_device_target' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN announcement_device_target TEXT DEFAULT 'all'")
    if 'announcement_audience' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN announcement_audience TEXT DEFAULT 'all'")
    if 'announcement_cta_text' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN announcement_cta_text TEXT DEFAULT ''")
    if 'announcement_cta_link' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN announcement_cta_link TEXT DEFAULT ''")
    if 'announcement_color_bg' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN announcement_color_bg TEXT DEFAULT ''")
    if 'announcement_color_text' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN announcement_color_text TEXT DEFAULT ''")
    if 'announcement_geo_target' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN announcement_geo_target TEXT DEFAULT ''")
    if 'announcement_ref_target' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN announcement_ref_target TEXT DEFAULT ''")
    if 'announcement_sound_enabled' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN announcement_sound_enabled BOOLEAN DEFAULT 0")
    if 'announcement_minimize_mode' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN announcement_minimize_mode BOOLEAN DEFAULT 0")
    if 'announcement_ab_test_enabled' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN announcement_ab_test_enabled BOOLEAN DEFAULT 0")
    if 'announcement_variant_b_text' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN announcement_variant_b_text TEXT DEFAULT ''")
    if 'announcement_variant_b_layout' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN announcement_variant_b_layout TEXT DEFAULT 'minimal_bar'")
    # ── Notification Settings Columns ──
    if 'notif_enabled' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN notif_enabled BOOLEAN DEFAULT 0")
    if 'notif_telegram_token' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN notif_telegram_token TEXT DEFAULT ''")
    if 'notif_message_format' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN notif_message_format TEXT DEFAULT 'detailed'")
    if 'notif_quiet_start' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN notif_quiet_start TEXT DEFAULT ''")
    if 'notif_quiet_end' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN notif_quiet_end TEXT DEFAULT ''")
    if 'notif_daily_digest' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN notif_daily_digest BOOLEAN DEFAULT 0")
    if 'notif_digest_time' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN notif_digest_time TEXT DEFAULT '20:00'")
    if 'notif_wa_enabled' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN notif_wa_enabled BOOLEAN DEFAULT 0")
    if 'notif_wa_instance_id' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN notif_wa_instance_id TEXT DEFAULT ''")
    if 'notif_wa_token' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN notif_wa_token TEXT DEFAULT ''")
    if 'notif_wa_phone' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN notif_wa_phone TEXT DEFAULT ''")
    if 'notif_meta_enabled' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN notif_meta_enabled BOOLEAN DEFAULT 0")
    if 'notif_meta_phone_id' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN notif_meta_phone_id TEXT DEFAULT ''")
    if 'notif_meta_token' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN notif_meta_token TEXT DEFAULT ''")
    if 'notif_meta_phone' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN notif_meta_phone TEXT DEFAULT ''")
    if 'notif_meta_template' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN notif_meta_template TEXT DEFAULT ''")
    if 'notif_meta_lang' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN notif_meta_lang TEXT DEFAULT 'en'")
    if 'store_status_mode' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN store_status_mode TEXT DEFAULT 'open'")
    if 'reopen_datetime' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN reopen_datetime TEXT")
    if 'closed_notification_message' not in store_cols:
        db.execute("ALTER TABLE store_settings ADD COLUMN closed_notification_message TEXT DEFAULT 'We are temporarily closed. We will begin accepting orders again shortly.'")
    db.commit()
    
    db.execute('''CREATE TABLE IF NOT EXISTS announcement_analytics (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        views_a INTEGER DEFAULT 0,
        clicks_a INTEGER DEFAULT 0,
        views_b INTEGER DEFAULT 0,
        clicks_b INTEGER DEFAULT 0
    )''')
    db.commit()
    
    if not db.execute('SELECT COUNT(*) as c FROM announcement_analytics').fetchone()['c']:
        db.execute("INSERT INTO announcement_analytics (id) VALUES (1)")
        db.commit()
    
    # ── Notification Recipients Table ──
    db.execute('''CREATE TABLE IF NOT EXISTS notif_recipients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        label TEXT NOT NULL DEFAULT 'Admin',
        chat_id TEXT NOT NULL,
        is_active BOOLEAN DEFAULT 1,
        events TEXT DEFAULT '{"new_order":1,"new_review":1,"bad_review":1,"spam":0,"promo_exhausted":1,"store_toggle":1}',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    db.commit()
    
    # ── Notification Log Table ──
    db.execute('''CREATE TABLE IF NOT EXISTS notif_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT NOT NULL,
        message TEXT NOT NULL,
        recipients_sent TEXT DEFAULT '',
        status TEXT DEFAULT 'sent',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    db.commit()
    
    # ── Migrate promotions table with new columns ──
    promo_columns = {
        'promo_code': "ALTER TABLE promotions ADD COLUMN promo_code TEXT DEFAULT ''",
        'discount_type': "ALTER TABLE promotions ADD COLUMN discount_type TEXT DEFAULT 'percentage'",
        'discount_value': "ALTER TABLE promotions ADD COLUMN discount_value REAL DEFAULT 0",
        'start_date': "ALTER TABLE promotions ADD COLUMN start_date TEXT",
        'end_date': "ALTER TABLE promotions ADD COLUMN end_date TEXT",
        'applies_to': "ALTER TABLE promotions ADD COLUMN applies_to TEXT DEFAULT 'all'",
        'target_categories': "ALTER TABLE promotions ADD COLUMN target_categories TEXT DEFAULT ''",
        'target_product_ids': "ALTER TABLE promotions ADD COLUMN target_product_ids TEXT DEFAULT ''",
        'banner_image': "ALTER TABLE promotions ADD COLUMN banner_image TEXT DEFAULT ''",
        'banner_color': "ALTER TABLE promotions ADD COLUMN banner_color TEXT DEFAULT ''",
        'max_uses': "ALTER TABLE promotions ADD COLUMN max_uses INTEGER",
        'times_used': "ALTER TABLE promotions ADD COLUMN times_used INTEGER DEFAULT 0",
        'min_order_amount': "ALTER TABLE promotions ADD COLUMN min_order_amount REAL DEFAULT 0",
        'max_discount_amount': "ALTER TABLE promotions ADD COLUMN max_discount_amount REAL",
        'sort_order': "ALTER TABLE promotions ADD COLUMN sort_order INTEGER DEFAULT 0",
        'is_public': "ALTER TABLE promotions ADD COLUMN is_public BOOLEAN DEFAULT 0",
    }
    existing = [row[1] for row in db.execute("PRAGMA table_info(promotions)").fetchall()]
    for col, sql in promo_columns.items():
        if col not in existing:
            try:
                db.execute(sql)
            except Exception:
                pass
    
    # ── Migrate orders table with promo tracking and payment columns ──
    order_columns = {
        'promo_code_used': "ALTER TABLE orders ADD COLUMN promo_code_used TEXT DEFAULT ''",
        'discount_amount': "ALTER TABLE orders ADD COLUMN discount_amount REAL DEFAULT 0",
        'original_amount': "ALTER TABLE orders ADD COLUMN original_amount REAL DEFAULT 0",
        'checkout_data': "ALTER TABLE orders ADD COLUMN checkout_data TEXT DEFAULT '{}'",
        'payment_status': "ALTER TABLE orders ADD COLUMN payment_status TEXT DEFAULT 'unpaid'",
        'payment_method': "ALTER TABLE orders ADD COLUMN payment_method TEXT DEFAULT ''",
        'payment_proof_img': "ALTER TABLE orders ADD COLUMN payment_proof_img TEXT DEFAULT ''",
        'payment_ref_no': "ALTER TABLE orders ADD COLUMN payment_ref_no TEXT DEFAULT ''",
        'payment_verified_at': "ALTER TABLE orders ADD COLUMN payment_verified_at TEXT DEFAULT ''",
        'receipt_number': "ALTER TABLE orders ADD COLUMN receipt_number TEXT DEFAULT ''"
    }
    existing_order = [row[1] for row in db.execute("PRAGMA table_info(orders)").fetchall()]
    for col, sql in order_columns.items():
        if col not in existing_order:
            try:
                db.execute(sql)
            except Exception:
                pass
    
    db.commit()
    
    # Seed defaults if tables are empty
    if not db.execute('SELECT COUNT(*) as c FROM homepage_stats').fetchone()['c']:
        for sort_order, (label, value) in enumerate([
            ('Arrangements', '24+'),
            ('Rating', '4.9★'),
            ('Happy Clients', '500+')
        ]):
            db.execute('INSERT INTO homepage_stats (label, value, sort_order) VALUES (?, ?, ?)',
                       (label, value, sort_order))
        db.commit()
    
    if not db.execute('SELECT COUNT(*) as c FROM trust_badges').fetchone()['c']:
        badges = [
            ('🌹', 'Always Fresh', 'Hand-selected daily from trusted farms for guaranteed freshness', 0),
            ('🎀', 'Premium Wrapping', 'Korean-style luxury wrapping with silk ribbons and tissue', 1),
            ('✨', 'Crafted with Care', 'Every arrangement is uniquely designed with attention to detail', 2),
            ('💬', 'WhatsApp Support', 'Chat with us anytime for custom orders and personalisation', 3),
        ]
        for icon, title, desc, sort in badges:
            db.execute('INSERT INTO trust_badges (icon, title, description, sort_order) VALUES (?, ?, ?, ?)',
                       (icon, title, desc, sort))
        db.commit()

ensure_tables()

@app.context_processor
def inject_global_settings():
    db = get_db()
    store_row = db.execute('SELECT * FROM store_settings WHERE id = 1').fetchone()
    store_settings = dict(store_row) if store_row else {
        'is_open': 1, 'whatsapp': '', 'instagram': '', 'facebook': '', 'theme': 'classic',
        'total_visitors': 0, 'show_visitors': 1, 'checkout_form_schema': '[]',
        'notif_wa_enabled': 0, 'notif_wa_instance_id': '', 'notif_wa_token': '', 'notif_wa_phone': '',
        'notif_meta_enabled': 0, 'notif_meta_phone_id': '', 'notif_meta_token': '', 'notif_meta_phone': '',
        'notif_meta_template': '', 'notif_meta_lang': 'en',
        'store_status_mode': 'open', 'reopen_datetime': None,
        'closed_notification_message': 'We are temporarily closed. We will begin accepting orders again shortly.'
    }
    
    # Auto-reopen check if store is closed and reopen time has passed
    if store_settings.get('store_status_mode') == 'closed' and store_settings.get('reopen_datetime'):
        try:
            reopen_str = store_settings['reopen_datetime'].replace('T', ' ')
            if len(reopen_str) > 16:
                reopen_dt = datetime.strptime(reopen_str[:19], '%Y-%m-%d %H:%M:%S')
            else:
                reopen_dt = datetime.strptime(reopen_str[:16], '%Y-%m-%d %H:%M')
            reopen_dt = reopen_dt.replace(tzinfo=MYT)
            
            if datetime.now(MYT) >= reopen_dt:
                db.execute("UPDATE store_settings SET store_status_mode = 'open', is_open = 1, reopen_datetime = NULL WHERE id = 1")
                db.commit()
                # Reload settings
                store_row = db.execute('SELECT * FROM store_settings WHERE id = 1').fetchone()
                if store_row:
                    store_settings = dict(store_row)
        except Exception:
            pass

    try:
        store_settings['checkout_form_schema_parsed'] = json.loads(store_settings.get('checkout_form_schema', '[]'))
    except:
        store_settings['checkout_form_schema_parsed'] = []
    
    try:
        store_settings['business_hours_parsed'] = json.loads(store_settings.get('business_hours', '{}'))
    except:
        store_settings['business_hours_parsed'] = {}
    
    
    sec_row = db.execute('SELECT * FROM security_settings WHERE id = 1').fetchone()
    security_settings = dict(sec_row) if sec_row else {
        'honeypot_enabled': 1, 'fast_submit_limit_ms': 3000, 
        'spam_order_limit': 3, 'spam_time_window_mins': 10
    }
    return dict(store_settings=store_settings, security_settings=security_settings)

def log_activity(action, details='', icon='info'):
    try:
        db = get_db()
        now = datetime.now(MYT).strftime('%Y-%m-%d %H:%M:%S')
        db.execute('INSERT INTO activity_log (action, details, icon, created_at) VALUES (?, ?, ?, ?)',
                   (action, details, icon, now))
        db.commit()
    except Exception:
        pass

def generate_order_id():
    prefix = '00001' if random.random() > 0.5 else '00002'
    chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"{prefix}-{chars}"

import requests as http_requests

def send_notification(event_type, message_detailed, message_compact='', priority='normal'):
    """Send Telegram and WhatsApp push notifications to all subscribed recipients.
    - Reads config from DB (changes take effect instantly)
    - Respects quiet hours (critical priority bypasses)
    - Supports daily digest mode (logs instead of sending)
    - Sends to all active recipients
    - Logs every notification attempt
    """
    try:
        db = get_db()
        store = db.execute('SELECT * FROM store_settings WHERE id = 1').fetchone()
        if not store or (not store['notif_enabled'] and not store['notif_wa_enabled'] and not store['notif_meta_enabled']):
            return
        
        msg_format = store['notif_message_format'] or 'detailed'
        message = message_detailed if msg_format == 'detailed' else (message_compact or message_detailed)
        
        # Quiet hours check (critical bypasses)
        quiet_start = (store['notif_quiet_start'] or '').strip()
        quiet_end = (store['notif_quiet_end'] or '').strip()
        if quiet_start and quiet_end and priority != 'critical':
            now_time = datetime.now(MYT).strftime('%H:%M')
            if quiet_start <= quiet_end:
                if quiet_start <= now_time <= quiet_end:
                    _log_notification(db, event_type, message, '', 'silenced_quiet')
                    return
            else:
                if now_time >= quiet_start or now_time <= quiet_end:
                    _log_notification(db, event_type, message, '', 'silenced_quiet')
                    return
        
        # Daily digest mode (non-critical only)
        if store['notif_daily_digest'] and priority != 'critical':
            _log_notification(db, event_type, message, '', 'queued_digest')
            return
        
        sent_to = []

        # ── Send Telegram Notifications ──
        if store['notif_enabled']:
            token = (store['notif_telegram_token'] or '').strip()
            if token:
                # Get active recipients subscribed to this event
                recipients = db.execute('SELECT * FROM notif_recipients WHERE is_active = 1').fetchall()
                for r in recipients:
                    try:
                        events = json.loads(r['events'] or '{}')
                    except:
                        events = {}
                    
                    if not events.get(event_type, 0):
                        continue
                    
                    chat_id = (r['chat_id'] or '').strip()
                    if not chat_id:
                        continue
                    
                    try:
                        url = f'https://api.telegram.org/bot{token}/sendMessage'
                        http_requests.post(url, json={
                            'chat_id': chat_id,
                            'text': message,
                            'parse_mode': 'HTML'
                        }, timeout=5)
                        sent_to.append(r['label'])
                    except Exception:
                        pass

        # ── Send WhatsApp Notifications (Green API) ──
        if store['notif_wa_enabled']:
            wa_instance = (store['notif_wa_instance_id'] or '').strip()
            wa_token = (store['notif_wa_token'] or '').strip()
            wa_phone = (store['notif_wa_phone'] or '').strip()
            
            if wa_instance and wa_token and wa_phone:
                clean_phone = ''.join(c for c in wa_phone if c.isdigit())
                if clean_phone:
                    wa_chat_id = f"{clean_phone}@c.us"
                    try:
                        # Convert basic HTML formatting to WhatsApp markdown
                        wa_message = message.replace('<b>', '*').replace('</b>', '*').replace('<i>', '_').replace('</i>', '_').replace('<br>', '\n').replace('<br/>', '\n')
                        # Remove other HTML tags
                        import re
                        wa_message = re.sub(r'<[^>]+>', '', wa_message)
                        
                        wa_url = f"https://api.green-api.com/waInstance{wa_instance}/sendMessage/{wa_token}"
                        http_requests.post(wa_url, json={
                            'chatId': wa_chat_id,
                            'message': wa_message
                        }, timeout=5)
                        sent_to.append(f"WhatsApp ({wa_phone})")
                    except Exception:
                        pass

        # ── Send Meta WhatsApp Notifications (Official API) ──
        meta_failed = False
        meta_err = ""
        if store['notif_meta_enabled']:
            phone_id = (store['notif_meta_phone_id'] or '').strip()
            meta_token = (store['notif_meta_token'] or '').strip()
            recipient_phone = (store['notif_meta_phone'] or '').strip()
            template_name = (store['notif_meta_template'] or '').strip()
            template_lang = (store['notif_meta_lang'] or 'en').strip()
            
            if phone_id and meta_token and recipient_phone and template_name:
                clean_phone = ''.join(c for c in recipient_phone if c.isdigit())
                if clean_phone:
                    try:
                        import re
                        clean_msg = re.sub(r'<[^>]+>', '', message)
                        
                        parameters = []
                        if template_name.lower() == 'hello_world':
                            # hello_world template does not accept any parameters
                            parameters = []
                        elif event_type == 'new_order':
                            order_id_match = re.search(r'(?:ID|Order ID|Order):\s*(\S+)', clean_msg)
                            name_match = re.search(r'(?:Name|Sender|Customer|Recipient):\s*([^\n]+)', clean_msg)
                            price_match = re.search(r'(?:Price|Total|Amount):\s*(RM\s*\d+(?:\.\d+)?|\d+(?:\.\d+)?)', clean_msg)
                            date_match = re.search(r'(?:Date|Delivery Date):\s*([^\n]+)', clean_msg)
                            
                            order_id = order_id_match.group(1) if order_id_match else "Unknown ID"
                            customer_name = name_match.group(1).strip() if name_match else "Customer"
                            total = price_match.group(1) if price_match else "N/A"
                            date = date_match.group(1).strip() if date_match else "N/A"
                            
                            parameters = [
                                {"type": "text", "text": customer_name},
                                {"type": "text", "text": order_id},
                                {"type": "text", "text": total},
                                {"type": "text", "text": date}
                            ]
                        elif event_type in ['new_review', 'bad_review']:
                            name_match = re.search(r'([^\n]+)\s+gave\s+(\d+)', clean_msg)
                            if not name_match:
                                name_match = re.search(r'(?:Name|Customer):\s*([^\n]+)', clean_msg)
                            
                            rating_match = re.search(r'(\d+)\s*★', clean_msg)
                            if not rating_match:
                                rating_match = re.search(r'(?:Rating):\s*(\d+)', clean_msg)
                                
                            customer_name = name_match.group(1).strip() if name_match else "Customer"
                            rating = f"{rating_match.group(1)}/5" if rating_match else "5/5"
                            
                            text_lines = [line.strip() for line in clean_msg.split('\n') if line.strip()]
                            review_text = text_lines[-1] if text_lines else "No comment"
                            
                            parameters = [
                                {"type": "text", "text": customer_name},
                                {"type": "text", "text": rating},
                                {"type": "text", "text": review_text}
                            ]
                        else:
                            parameters = [
                                {"type": "text", "text": event_type.replace('_', ' ').title()},
                                {"type": "text", "text": clean_msg[:100]}
                            ]
                        
                        meta_url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
                        meta_payload = {
                            "messaging_product": "whatsapp",
                            "to": clean_phone,
                            "type": "template",
                            "template": {
                                "name": template_name,
                                "language": {
                                    "code": template_lang
                                }
                            }
                        }
                        if parameters:
                            meta_payload["template"]["components"] = [
                                {
                                    "type": "body",
                                    "parameters": parameters
                                }
                            ]
                        
                        meta_headers = {
                            "Authorization": f"Bearer {meta_token}",
                            "Content-Type": "application/json"
                        }
                        resp = http_requests.post(meta_url, json=meta_payload, headers=meta_headers, timeout=5)
                        if resp.status_code >= 200 and resp.status_code < 300:
                            sent_to.append(f"Meta WA ({recipient_phone})")
                        else:
                            meta_failed = True
                            try:
                                err_data = resp.json().get('error', {})
                                meta_err = err_data.get('message', resp.text)
                            except:
                                meta_err = resp.text
                    except Exception as e:
                        meta_failed = True
                        meta_err = str(e)
        
        if sent_to:
            status = 'sent'
            if meta_failed:
                status = 'failed'
                message += f"\n\n[Meta WA Error: {meta_err}]"
        elif meta_failed:
            status = 'failed'
            message += f"\n\n[Meta WA Error: {meta_err}]"
        else:
            status = 'no_recipients'
            
        _log_notification(db, event_type, message, ', '.join(sent_to), status)
        
    except Exception:
        pass

def _log_notification(db, event_type, message, recipients_sent, status):
    """Log a notification attempt and auto-cleanup old entries."""
    try:
        now = datetime.now(MYT).strftime('%Y-%m-%d %H:%M:%S')
        db.execute('INSERT INTO notif_log (event_type, message, recipients_sent, status, created_at) VALUES (?, ?, ?, ?, ?)',
                   (event_type, message[:500], recipients_sent, status, now))
        db.execute('DELETE FROM notif_log WHERE id NOT IN (SELECT id FROM notif_log ORDER BY id DESC LIMIT 200)')
        db.commit()
    except Exception:
        pass

# ══════════════════════════════════════════
# PROMOTION HELPERS
# ══════════════════════════════════════════

def auto_expire_promotions():
    """Deactivate promotions past their end_date."""
    try:
        db = get_db()
        now = datetime.now(MYT).strftime('%Y-%m-%d')
        db.execute('''
            UPDATE promotions SET is_active = 0 
            WHERE end_date IS NOT NULL AND end_date != '' AND end_date < ? AND is_active = 1
        ''', (now,))
        # Activate scheduled promos whose start_date has arrived
        db.execute('''
            UPDATE promotions SET is_active = 1
            WHERE start_date IS NOT NULL AND start_date != '' AND start_date <= ?
            AND (end_date IS NULL OR end_date = '' OR end_date >= ?)
            AND is_active = 0
        ''', (now, now))
        db.commit()
    except Exception:
        pass

def get_active_promotions(db=None):
    """Get all currently active and valid promotions."""
    if db is None:
        db = get_db()
    auto_expire_promotions()
    now = datetime.now(MYT).strftime('%Y-%m-%d')
    promos = db.execute('''
        SELECT * FROM promotions WHERE is_active = 1
        AND (start_date IS NULL OR start_date = '' OR start_date <= ?)
        AND (end_date IS NULL OR end_date = '' OR end_date >= ?)
        AND (max_uses IS NULL OR times_used < max_uses)
        ORDER BY sort_order ASC, id DESC
    ''', (now, now)).fetchall()
    return promos

def promo_applies_to_product(promo, product):
    """Check if a promotion applies to a specific product."""
    applies_to = promo['applies_to'] or 'all'
    if applies_to == 'all':
        return True
    if applies_to == 'category':
        target_cats = [c.strip() for c in (promo['target_categories'] or '').split(',') if c.strip()]
        return product['category'] in target_cats
    if applies_to == 'products':
        target_ids = [int(x.strip()) for x in (promo['target_product_ids'] or '').split(',') if x.strip().isdigit()]
        return product['id'] in target_ids
    return True

def calculate_discount(promo, price):
    """Calculate the discount amount for a given price and promotion."""
    discount_type = promo['discount_type'] or 'percentage'
    discount_value = float(promo['discount_value'] or 0)
    min_amount = float(promo['min_order_amount'] or 0)
    
    if price < min_amount:
        return 0
    
    if discount_type == 'percentage':
        discount = price * (discount_value / 100)
    else:
        discount = discount_value
    
    # Cap at max_discount_amount if set
    max_disc = promo['max_discount_amount']
    if max_disc and discount > float(max_disc):
        discount = float(max_disc)
    
    # Never discount more than the price
    return min(discount, price)

def get_product_promos(product, active_promos=None):
    """Get the best applicable auto-apply promotion for a product."""
    if active_promos is None:
        active_promos = get_active_promotions()
    
    best_promo = None
    best_discount = 0
    for promo in active_promos:
        # Ignore promotions with a specific promo code (they must be manually applied)
        if promo['promo_code'] and promo['promo_code'].strip() != '':
            continue
            
        if promo_applies_to_product(promo, product):
            disc = calculate_discount(promo, product['price'])
            if disc > best_discount:
                best_discount = disc
                best_promo = promo
    return best_promo, best_discount

def get_promo_status(promo):
    """Return status string: active, scheduled, expired, inactive."""
    now = datetime.now(MYT).strftime('%Y-%m-%d')
    start = promo['start_date'] or ''
    end = promo['end_date'] or ''
    
    if end and end < now:
        return 'expired'
    if start and start > now:
        return 'scheduled'
    if promo['is_active']:
        max_uses = promo['max_uses']
        if max_uses and promo['times_used'] >= max_uses:
            return 'exhausted'
        return 'active'
    return 'inactive'

@app.route('/deploy-webhook', methods=['POST'])
def deploy_webhook():
    token = request.args.get('token')
    if token != 'alvina_deploy_secret_2026':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        import subprocess
        result = subprocess.run(['git', 'pull', 'origin', 'main'], cwd=BASE_DIR, capture_output=True, text=True, check=True)
        
        # Touch passenger_wsgi.py to reload Phusion Passenger
        wsgi_path = os.path.join(BASE_DIR, 'passenger_wsgi.py')
        if os.path.exists(wsgi_path):
            os.utime(wsgi_path, None)
            
        return jsonify({
            'success': True,
            'message': 'Deployment successful! Code pulled and server restarted.',
            'git_output': result.stdout
        }), 200
    except subprocess.CalledProcessError as e:
        return jsonify({
            'success': False,
            'error': f'Git pull failed: {e.stderr}'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ══════════════════════════════════════════
# CUSTOMER ROUTES
# ══════════════════════════════════════════


@app.route('/')
def home():
    db = get_db()
    promotions = get_active_promotions(db)
    products = db.execute('SELECT * FROM products LIMIT 6').fetchall()
    
    categories = db.execute('''
        SELECT category, COUNT(*) as count, MIN(price) as min_price 
        FROM products GROUP BY category ORDER BY count DESC
    ''').fetchall()
    
    occasions = db.execute('''
        SELECT use, COUNT(*) as count 
        FROM products GROUP BY use ORDER BY count DESC
    ''').fetchall()
    
    bestsellers = db.execute('SELECT * FROM products ORDER BY price DESC LIMIT 4').fetchall()
    # dynamically calculate hero stats
    total_products = db.execute('SELECT COUNT(*) as c FROM products').fetchone()['c']
    avg_rating_res = db.execute('SELECT AVG(rating) as a FROM reviews').fetchone()
    avg_rating = round(avg_rating_res['a'], 1) if avg_rating_res['a'] else 5.0
    total_orders = db.execute('SELECT COUNT(*) as c FROM orders WHERE status != "cancelled"').fetchone()['c']
    # start them a bit higher for impressive looks if there are no orders
    display_orders = total_orders if total_orders > 10 else (total_orders + 500) 
    
    # ── Visitor Counter (session-based) ──
    store_row = db.execute('SELECT total_visitors, show_visitors FROM store_settings WHERE id = 1').fetchone()
    total_visitors = store_row['total_visitors'] if store_row else 0
    show_visitors = store_row['show_visitors'] if store_row else 1
    
    if not session.get('has_visited'):
        session['has_visited'] = True
        db.execute('UPDATE store_settings SET total_visitors = total_visitors + 1 WHERE id = 1')
        db.commit()
        total_visitors += 1
    
    hero_stats = [
        {'label': 'Arrangements', 'value': f'{total_products}+'},
        {'label': 'Rating', 'value': f'{avg_rating}★'},
        {'label': 'Happy Clients', 'value': f'{display_orders}+'}
    ]
    
    if show_visitors:
        hero_stats.append({'label': 'Visitors', 'value': f'{total_visitors:,}'})
    
    trust_badges = db.execute('SELECT * FROM trust_badges ORDER BY sort_order').fetchall()
    featured_reviews = db.execute('SELECT * FROM reviews WHERE is_featured = 1 ORDER BY created_at DESC LIMIT 6').fetchall()
    
    # Build product discount info for featured products
    product_promos = {}
    for p in products:
        best_promo, best_disc = get_product_promos(p, promotions)
        if best_promo and best_disc > 0:
            product_promos[p['id']] = {
                'discount': best_disc,
                'final_price': p['price'] - best_disc,
                'promo_title': best_promo['title'],
                'discount_display': best_promo['discount']
            }
    
    return render_template('index.html', 
        promotions=promotions, products=products,
        categories=categories, occasions=occasions,
        bestsellers=bestsellers, total_products=total_products,
        hero_stats=hero_stats, trust_badges=trust_badges,
        featured_reviews=featured_reviews,
        product_promos=product_promos)

@app.route('/search')
def search_products():
    query = request.args.get('q', '').strip()
    db = get_db()
    if query:
        search_term = f'%{query}%'
        products = db.execute('''
            SELECT * FROM products 
            WHERE name LIKE ? OR description LIKE ? OR category LIKE ? OR budget LIKE ? OR use LIKE ?
        ''', (search_term, search_term, search_term, search_term, search_term)).fetchall()
    else:
        products = []
    all_products_list = db.execute('SELECT * FROM products').fetchall()
    active_promos = get_active_promotions(db)
    product_promos = {}
    for p in (products if products else []):
        best_promo, best_disc = get_product_promos(p, active_promos)
        if best_promo and best_disc > 0:
            product_promos[p['id']] = {
                'discount': best_disc,
                'final_price': p['price'] - best_disc,
                'promo_title': best_promo['title'],
                'discount_display': best_promo['discount']
            }
    return render_template('search_results.html', products=products, query=query, all_products=all_products_list, product_promos=product_promos)

@app.route('/products')
def all_products():
    db = get_db()
    products = db.execute('SELECT * FROM products').fetchall()
    active_promos = get_active_promotions(db)
    product_promos = {}
    for p in products:
        best_promo, best_disc = get_product_promos(p, active_promos)
        if best_promo and best_disc > 0:
            product_promos[p['id']] = {
                'discount': best_disc,
                'final_price': p['price'] - best_disc,
                'promo_title': best_promo['title'],
                'discount_display': best_promo['discount']
            }
    
    # Gather filter data
    categories = db.execute('SELECT DISTINCT category FROM products ORDER BY category').fetchall()
    occasions = db.execute('SELECT DISTINCT use FROM products ORDER BY use').fetchall()
    budgets = db.execute('SELECT DISTINCT budget FROM products ORDER BY budget').fetchall()
    
    # Price range
    price_data = db.execute('SELECT MIN(price) as min_price, MAX(price) as max_price FROM products').fetchone()
    min_price = price_data['min_price'] if price_data['min_price'] else 0
    max_price = price_data['max_price'] if price_data['max_price'] else 500
    
    # Pre-selected filter from query params
    selected_category = request.args.get('category', '')
    selected_occasion = request.args.get('occasion', '')
    search_query = request.args.get('q', '')
    
    # Calculate global dynamic stats
    avg_rating_res = db.execute('SELECT AVG(rating) as a FROM reviews').fetchone()
    avg_rating = round(avg_rating_res['a'], 1) if avg_rating_res['a'] else 5.0
    total_products = db.execute('SELECT COUNT(*) as c FROM products').fetchone()['c']
    
    return render_template('products.html', 
        products=products, product_promos=product_promos,
        categories=categories, occasions=occasions, budgets=budgets,
        min_price=min_price, max_price=max_price,
        selected_category=selected_category,
        selected_occasion=selected_occasion,
        search_query=search_query,
        avg_rating=avg_rating,
        total_products=total_products)

@app.route('/products/<int:id>')
def product_detail(id):
    db = get_db()
    product = db.execute('SELECT * FROM products WHERE id = ?', (id,)).fetchone()
    if not product:
        return "Product not found", 404
    
    active_promos = get_active_promotions(db)
    best_promo, best_disc = get_product_promos(product, active_promos)
    
    # Get all applicable promos for this product (not just the best one)
    applicable_promos = []
    for p in active_promos:
        if promo_applies_to_product(p, product):
            applicable_promos.append(p)
            
    sec = db.execute('SELECT * FROM security_settings WHERE id = 1').fetchone()
    if not sec:
        sec = {'honeypot_enabled': 1, 'fast_submit_limit_ms': 3000, 'spam_order_limit': 3, 'spam_time_window_mins': 10}
    
    return render_template('product_detail.html', 
        product=product, 
        best_promo=best_promo, 
        best_discount=best_disc,
        applicable_promos=applicable_promos,
        security_settings=sec)

@app.route('/api/validate-promo', methods=['POST'])
def validate_promo():
    """Validate a promo code for a specific product."""
    data = request.json
    code = (data.get('promo_code') or '').strip().upper()
    product_id = data.get('product_id')
    
    if not code:
        return jsonify({'valid': False, 'error': 'Please enter a promo code'})
    
    db = get_db()
    promo = db.execute('SELECT * FROM promotions WHERE UPPER(promo_code) = ?', (code,)).fetchone()
    
    if not promo:
        return jsonify({'valid': False, 'error': 'Invalid promo code'})
    
    status = get_promo_status(promo)
    if status == 'expired':
        return jsonify({'valid': False, 'error': 'This promo code has expired'})
    if status == 'scheduled':
        return jsonify({'valid': False, 'error': 'This promo code is not yet active'})
    if status == 'exhausted':
        send_notification('promo_exhausted',
            f'🎫 <b>Promo Exhausted</b>\nCode: {code}\nUsed: {promo["times_used"]}/{promo["max_uses"]}\nTitle: {promo["title"]}',
            f'🎫 Promo {code} exhausted ({promo["times_used"]}/{promo["max_uses"]})')
        return jsonify({'valid': False, 'error': 'This promo code has reached its usage limit'})
    if status != 'active':
        return jsonify({'valid': False, 'error': 'This promo code is not active'})
    
    product = db.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    if not product:
        return jsonify({'valid': False, 'error': 'Product not found'})
    
    if not promo_applies_to_product(promo, product):
        return jsonify({'valid': False, 'error': 'This code does not apply to this product'})
    
    discount = calculate_discount(promo, product['price'])
    if discount <= 0:
        min_amt = promo['min_order_amount'] or 0
        return jsonify({'valid': False, 'error': f'Minimum order RM {min_amt:.0f} required'})
    
    final_price = product['price'] - discount
    return jsonify({
        'valid': True,
        'discount': round(discount, 2),
        'final_price': round(final_price, 2),
        'original_price': product['price'],
        'promo_title': promo['title'],
        'discount_display': promo['discount'],
        'promo_id': promo['id']
    })

@app.route('/api/order', methods=['POST'])
def place_order():
    data = request.json
    product_id = data.get('product_id')
    price = data.get('price')
    promo_code = (data.get('promo_code') or '').strip().upper()
    honeypot = data.get('alt_shipping_zipcode', '').strip()
    checkout_data = data.get('checkout_data', {})
    checkout_data_str = json.dumps(checkout_data)

    if not product_id or price is None:
        return jsonify({'success': False, 'error': 'Missing price or product_id'}), 400

    db = get_db()
    
    # Store Status Validation
    store_row = db.execute('SELECT store_status_mode, closed_notification_message FROM store_settings WHERE id = 1').fetchone()
    store_status = store_row['store_status_mode'] if store_row else 'open'
    closed_msg = store_row['closed_notification_message'] if store_row else 'We are temporarily closed. We will begin accepting orders again shortly.'
    
    if store_status == 'closed':
        return jsonify({'success': False, 'error': closed_msg}), 403
        
    if store_status == 'fully_booked':
        delivery_date_str = checkout_data.get('delivery_date', '').strip()
        if not delivery_date_str:
            return jsonify({'success': False, 'error': 'Delivery date is required'}), 400
        try:
            delivery_date = datetime.strptime(delivery_date_str, '%Y-%m-%d').date()
            today = datetime.now(MYT).date()
            if (delivery_date - today).days < 3:
                return jsonify({'success': False, 'error': 'Delivery date must be at least 3 days in the future when the store is fully booked today.'}), 400
        except Exception:
            return jsonify({'success': False, 'error': 'Invalid delivery date format'}), 400

    db = get_db()
    sec = db.execute('SELECT * FROM security_settings WHERE id = 1').fetchone()
    
    # Defaults in case DB missing
    honeypot_enabled = sec['honeypot_enabled'] if sec else 1
    spam_order_limit = sec['spam_order_limit'] if sec else 3
    spam_time_window_mins = sec['spam_time_window_mins'] if sec else 10

    # Anti-Spam Pillar 1: Honeypot Trap
    if honeypot_enabled and honeypot:
        # Silently pretend success to trick the bot without modifying the DB
        return jsonify({'success': True, 'order_id': generate_order_id()})

    # Anti-Spam Pillar 3: Session Rate Limiting
    now_dt = datetime.now()
    if 'recent_orders' not in session:
        session['recent_orders'] = []
    
    # Filter array to purely items within the dynamic time window
    time_window_seconds = spam_time_window_mins * 60
    window_ago = now_dt.timestamp() - time_window_seconds
    recent = [ts for ts in session['recent_orders'] if ts > window_ago]
    
    if len(recent) >= spam_order_limit:
        session['recent_orders'] = recent
        send_notification('spam',
            f'🛡️ <b>Spam Blocked</b>\nRate limit triggered\nSession hit {spam_order_limit} orders in {spam_time_window_mins}min',
            f'🛡️ Spam blocked — {spam_order_limit} orders in {spam_time_window_mins}min')
        return jsonify({'success': False, 'error': 'spam_limit_reached'}), 429
        
    order_id = generate_order_id()
    db = get_db()
    # Log valid attempt
    recent.append(now_dt.timestamp())
    session['recent_orders'] = recent
    
    now = now_dt.strftime('%Y-%m-%d %H:%M:%S')
    
    original_price = float(price)
    discount_amount = 0.0
    promo_used = ''
    
    # Apply promo code if provided
    if promo_code:
        promo = db.execute('SELECT * FROM promotions WHERE UPPER(promo_code) = ?', (promo_code,)).fetchone()
        if promo and get_promo_status(promo) == 'active':
            product = db.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
            if product and promo_applies_to_product(promo, product):
                discount_amount = calculate_discount(promo, original_price)
                promo_used = promo_code
                # Increment usage count
                db.execute('UPDATE promotions SET times_used = times_used + 1 WHERE id = ?', (promo['id'],))
    
    final_price = original_price - discount_amount
    
    db.execute('''
        INSERT INTO orders (id, total_amount, status, products, created_at, promo_code_used, discount_amount, original_amount, checkout_data)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (order_id, final_price, 'Processing', f'[{{"product_id": {product_id}, "quantity": 1}}]', now, promo_used, discount_amount, original_price, checkout_data_str))
    db.commit()
    
    product = db.execute('SELECT name FROM products WHERE id = ?', (product_id,)).fetchone()
    pname = product['name'] if product else f'Product #{product_id}'
    
    if discount_amount > 0:
        log_activity('New Order Placed', f'Order {order_id} — RM {final_price:.2f} for {pname} (saved RM {discount_amount:.2f} with {promo_used})', 'order')
    else:
        log_activity('New Order Placed', f'Order {order_id} — RM {final_price:.2f} for {pname}', 'order')
    
    promo_line = f'\n🎫 Promo: {promo_used} (saved RM {discount_amount:.2f})' if promo_used else ''
    send_notification('new_order',
        f'🛒 <b>New Order!</b>\nOrder: {order_id}\nProduct: {pname}\nAmount: RM {final_price:.2f}{promo_line}',
        f'🛒 New order {order_id} — RM {final_price:.2f}')
    
    return jsonify({'success': True, 'order_id': order_id, 'final_price': round(final_price, 2), 'discount': round(discount_amount, 2)})

@app.route('/promotions')
def customer_promotions():
    """Customer-facing promotions / deals page."""
    db = get_db()
    active_promos = get_active_promotions(db)
    all_products_list = db.execute('SELECT * FROM products').fetchall()
    
    # Build promo data with applicable product counts
    promo_data = []
    for promo in active_promos:
        applicable_products = [p for p in all_products_list if promo_applies_to_product(promo, p)]
        promo_data.append({
            'promo': promo,
            'product_count': len(applicable_products),
            'sample_products': applicable_products[:4],
            'status': get_promo_status(promo)
        })
    
    return render_template('promotions.html', promo_data=promo_data)

@app.route('/track')
def track_order():
    order_id = request.args.get('id', '').strip()
    db = get_db()
    
    if not order_id:
        return render_template('track.html')
        
    order_row = db.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    
    if order_row:
        import json
        order = dict(order_row)
        items = json.loads(order['products'])
        main_product = None
        if items:
            p_id = items[0].get('product_id')
            if p_id:
                p_row = db.execute('SELECT * FROM products WHERE id = ?', (p_id,)).fetchone()
                if p_row:
                    main_product = dict(p_row)
                else:
                    main_product = {'id': p_id, 'name': 'Unknown Product', 'image': '', 'category': '', 'price': order.get('total_amount', 0)}
        try:
            order['checkout_data'] = json.loads(order.get('checkout_data') or '{}')
        except:
            order['checkout_data'] = {}
        
        # Check if review exists
        has_review = False
        rev = db.execute('SELECT id FROM reviews WHERE order_id = ?', (order_id,)).fetchone()
        if rev:
            has_review = True
            
        return render_template('track.html', order_id=order_id, order=order, order_product=main_product, has_review=has_review)
    else:
        return render_template('track.html', order_id=order_id, order=None)

@app.route('/invoice/<order_id>')
def view_invoice(order_id):
    db = get_db()
    order_row = db.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    if not order_row:
        return "Order not found", 404
        
    import json
    order = dict(order_row)
    
    order['payment_status'] = order.get('payment_status', 'unpaid')
    order['payment_method'] = order.get('payment_method', '')
    
    # Generate unique transaction reference if not present
    ref_no = order.get('payment_ref_no', '')
    if not ref_no:
        import random
        import string
        rand_letters = ''.join(random.choices(string.ascii_uppercase, k=4))
        rand_digits = ''.join(random.choices(string.digits, k=4))
        ref_no = f"ALV-{rand_letters}-{rand_digits}"
        db.execute('UPDATE orders SET payment_ref_no = ? WHERE id = ?', (ref_no, order_id))
        db.commit()
    order['payment_ref_no'] = ref_no
    
    raw_items = json.loads(order['products'])
    items = []
    for it in raw_items:
        p_id = it.get('product_id')
        p = db.execute('SELECT name, image, price FROM products WHERE id=?', (p_id,)).fetchone()
        if p:
            it['name'] = p['name']
            it['image'] = p['image']
            it['price'] = p['price']
        else:
            it['name'] = f"Product #{p_id}"
            it['image'] = ''
            it['price'] = order.get('total_amount', 0)
        items.append(it)
    order['items'] = items
    try:
        order['checkout_data'] = json.loads(order.get('checkout_data') or '{}')
    except:
        order['checkout_data'] = {}
    
    from datetime import datetime
    now_str = datetime.now().strftime("%B %d, %Y - %I:%M %p")
    
    return render_template('invoice.html', order=order, items=items, now=now_str)

@app.route('/api/upload-payment-proof/<order_id>', methods=['POST'])
def upload_payment_proof(order_id):
    db = get_db()
    order_row = db.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    if not order_row:
        return jsonify({'success': False, 'error': 'Order not found'}), 404
        
    payment_method = request.form.get('payment_method', '').strip()
    payment_ref_no = request.form.get('payment_ref_no', '').strip()
    
    if not payment_method:
        return jsonify({'success': False, 'error': 'Please select a payment method'}), 400
        
    file = request.files.get('payment_proof')
    file_path = ''
    if file and file.filename:
        filename = secure_filename(file.filename)
        saved_filename = f"{order_id}_{filename}"
        filepath = os.path.join(app.config['RECEIPT_UPLOAD_FOLDER'], saved_filename)
        file.save(filepath)
        file_path = f"/static/uploads/receipts/{saved_filename}"
        
    db.execute('''
        UPDATE orders 
        SET payment_status = 'pending_verification',
            payment_method = ?,
            payment_ref_no = ?,
            payment_proof_img = ?
        WHERE id = ?
    ''', (payment_method, payment_ref_no, file_path, order_id))
    db.commit()
    
    log_activity('Payment Proof Uploaded', f'Proof uploaded for Order {order_id} via {payment_method}', 'payment')
    
    send_notification('payment_proof_uploaded',
        f'💳 <b>Payment Proof Uploaded</b>\nOrder: {order_id}\nMethod: {payment_method}\nRef No: {payment_ref_no or "None"}',
        f'💳 Payment proof uploaded for order {order_id}')
        
    return jsonify({'success': True})

@app.route('/receipt/<order_id>')
def view_receipt(order_id):
    # Publicly accessible via the secure order ID, just like tracking.
    db = get_db()
    order_row = db.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    if not order_row:
        return "Order not found", 404
        
    import json
    order = dict(order_row)
    
    # If the order is not paid, redirect to the invoice payment/upload screen
    if order.get('payment_status', 'unpaid') != 'paid':
        return redirect(url_for('view_invoice', order_id=order_id))
    raw_items = json.loads(order['products'])
    items = []
    for it in raw_items:
        p_id = it.get('product_id')
        qty = it.get('quantity', 1)
        p = db.execute('SELECT name, image, price FROM products WHERE id=?', (p_id,)).fetchone()
        if p:
            it['name'] = p['name']
            it['image'] = p['image']
            it['price'] = p['price']
        else:
            it['name'] = f"Product #{p_id}"
            it['image'] = ''
            it['price'] = order.get('total_amount', 0)
        items.append(it)
    order['items'] = items
    try:
        order['checkout_data'] = json.loads(order.get('checkout_data') or '{}')
    except:
        order['checkout_data'] = {}
    
    # Import datetime locally to format the generation time
    from datetime import datetime
    now_str = datetime.now().strftime("%B %d, %Y - %I:%M %p")
    
    return render_template('receipt.html', order=order, items=items, now=now_str)

# ══════════════════════════════════════════
# CUSTOMER REVIEWS
# ══════════════════════════════════════════

@app.route('/api/review', methods=['POST'])
def submit_review():
    data = request.json
    name = data.get('customer_name', '').strip()
    order_id = data.get('order_id', '').strip()
    rating = int(data.get('rating', 5))
    text = data.get('review_text', '').strip()
    occasion = data.get('occasion', '').strip()
    
    if not name or not text:
        return jsonify({'success': False, 'error': 'Name and review text required'}), 400
    if rating < 1 or rating > 5:
        return jsonify({'success': False, 'error': 'Rating must be 1-5'}), 400
        
    db = get_db()
    
    if order_id:
        existing = db.execute('SELECT id FROM reviews WHERE order_id = ?', (order_id,)).fetchone()
        if existing:
            return jsonify({'success': False, 'error': 'A review for this order has already been submitted.'}), 400
    now = datetime.now(MYT).strftime('%Y-%m-%d %H:%M:%S')
    db.execute('''
        INSERT INTO reviews (customer_name, order_id, rating, review_text, occasion, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (name, order_id, rating, text, occasion, now))
    db.commit()
    log_activity('New Review', f'{name} left a {rating}★ review', 'review')
    
    # Telegram notifications for reviews
    review_preview = text[:100] + ('...' if len(text) > 100 else '')
    send_notification('new_review',
        f'⭐ <b>New {rating}★ Review</b>\nBy: {name}\n"{review_preview}"',
        f'⭐ {name}: {rating}★ review')
    
    if rating <= 2:
        send_notification('bad_review',
            f'⚠️ <b>BAD REVIEW ALERT</b>\n{name} gave {rating}★\n"{review_preview}"\n\n⚡ Respond quickly!',
            f'⚠️ Bad review! {name}: {rating}★',
            priority='critical')
    
    return jsonify({'success': True})

# ══════════════════════════════════════════
# ADMIN AUTH
# ══════════════════════════════════════════

@app.route('/secret-alvina-admin', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'alvina' and password == 'alvina123':
            session['admin_logged_in'] = True
            log_activity('Admin Login', 'Alvina logged into the admin panel', 'login')
            return redirect(url_for('admin_dashboard'))
        else:
            error = 'Invalid username or password'
    return render_template('admin_login.html', error=error)

# ══════════════════════════════════════════
# ADMIN DASHBOARD (ENHANCED)
# ══════════════════════════════════════════

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    db = get_db()
    orders = db.execute('SELECT * FROM orders ORDER BY created_at DESC').fetchall()
    products = db.execute('SELECT * FROM products').fetchall()
    promotions = db.execute('SELECT * FROM promotions').fetchall()
    notes = db.execute('SELECT * FROM admin_notes ORDER BY is_done ASC, created_at DESC').fetchall()
    # Auto cleanup old activities: keep at least 40, delete older than 1 month
    db.execute('''
        DELETE FROM activity_log 
        WHERE created_at < datetime('now', '-1 month') 
        AND id NOT IN (SELECT id FROM activity_log ORDER BY id DESC LIMIT 40)
    ''')
    db.commit()
    
    activity = db.execute('SELECT * FROM activity_log ORDER BY created_at DESC LIMIT 20').fetchall()    
    # ── Core Stats ──
    total_rm = sum(float(o['total_amount']) for o in orders)
    avg_order = total_rm / len(orders) if orders else 0
    active_promos = sum(1 for p in promotions if p['is_active'])
    
    # ── Category & Budget Summaries ──
    category_summary = {}
    budget_summary = {}
    use_summary = {}
    for p in products:
        cat = p['category']
        category_summary[cat] = category_summary.get(cat, 0) + 1
        bud = p['budget']
        budget_summary[bud] = budget_summary.get(bud, 0) + 1
        use = p['use']
        use_summary[use] = use_summary.get(use, 0) + 1
    
    # ── Price Range ──
    price_range = {'min': 0, 'max': 0, 'avg': 0}
    if products:
        prices = [p['price'] for p in products]
        price_range = {
            'min': min(prices),
            'max': max(prices),
            'avg': sum(prices) / len(prices)
        }
    
    # ── Revenue by Month (last 12 months) ──
    revenue_data = db.execute('''
        SELECT strftime('%Y-%m', created_at) as month, SUM(total_amount) as monthly_total, COUNT(*) as order_count
        FROM orders
        GROUP BY month
        ORDER BY month DESC
        LIMIT 12
    ''').fetchall()
    revenue_chart = {
        'labels': [r['month'] for r in reversed(revenue_data)] if revenue_data else [],
        'values': [float(r['monthly_total']) for r in reversed(revenue_data)] if revenue_data else [],
        'counts': [r['order_count'] for r in reversed(revenue_data)] if revenue_data else []
    }
    
    # ── Order Status Breakdown ──
    status_counts = {'Processing': 0, 'Shipped': 0, 'Delivered': 0, 'Cancelled': 0}
    for o in orders:
        status = o['status']
        status_counts[status] = status_counts.get(status, 0) + 1
    
    # ── Top Products (most featured / highest priced) ──
    top_products = db.execute('SELECT * FROM products ORDER BY price DESC LIMIT 5').fetchall()
    
    # ══ NEW: Delivery Tracking — Deliveries Today & Tomorrow ══
    now = datetime.now(MYT)
    today_str = now.strftime('%Y-%m-%d')
    tomorrow_str = (now + timedelta(days=1)).strftime('%Y-%m-%d')
    
    deliveries_today = 0
    deliveries_tomorrow = 0
    pending_fulfillments = []  # Orders not yet delivered/cancelled
    
    for o in orders:
        # Parse delivery_date from checkout_data JSON
        try:
            cdata = json.loads(o['checkout_data']) if o['checkout_data'] else {}
        except (json.JSONDecodeError, TypeError):
            cdata = {}
        
        delivery_date = cdata.get('delivery_date', '')
        
        if delivery_date == today_str:
            deliveries_today += 1
        elif delivery_date == tomorrow_str:
            deliveries_tomorrow += 1
        
        # Collect unfulfilled orders (Processing or Shipped, not yet Delivered/Cancelled)
        if o['status'] in ('Processing', 'Shipped'):
            pending_fulfillments.append({
                'id': o['id'],
                'status': o['status'],
                'total_amount': float(o['total_amount']),
                'created_at': o['created_at'],
                'delivery_date': delivery_date,
                'customer_name': cdata.get('sender_name', cdata.get('recipient_name', '—')),
                'recipient': cdata.get('recipient_name', '—'),
            })
    
    # Only show top 8 pending fulfillments, most urgent first (by delivery_date, then created_at)
    pending_fulfillments.sort(key=lambda x: (x['delivery_date'] or '9999-99-99', x['created_at'] or ''))
    pending_fulfillments = pending_fulfillments[:8]
    
    # ══ NEW: Low Stock Alerts ══
    low_stock_threshold = 5
    low_stock_products = []
    for p in products:
        # Products may have a 'stock' field; handle gracefully if missing
        stock = None
        try:
            stock = p['stock']
        except (IndexError, KeyError):
            pass
        if stock is not None and int(stock) <= low_stock_threshold:
            low_stock_products.append({
                'id': p['id'],
                'name': p['name'],
                'category': p['category'],
                'stock': int(stock),
                'image': p['image'],
            })
    low_stock_products.sort(key=lambda x: x['stock'])
    
    # ══ NEW: Pending Reviews Count ══
    all_reviews = db.execute('SELECT * FROM reviews').fetchall()
    total_reviews = len(all_reviews)
    featured_reviews = sum(1 for r in all_reviews if r['is_featured'])
    unfeatured_reviews = total_reviews - featured_reviews
    avg_rating = sum(r['rating'] for r in all_reviews) / total_reviews if total_reviews else 0
    
    # ══ NEW: Revenue by Category ══
    category_revenue = {}
    for o in orders:
        if o['status'] == 'Cancelled':
            continue
        try:
            items = json.loads(o['products']) if o['products'] else []
        except (json.JSONDecodeError, TypeError):
            items = []
        for item in items:
            pid = item.get('product_id')
            if pid:
                prod = db.execute('SELECT category FROM products WHERE id = ?', (pid,)).fetchone()
                if prod:
                    cat = prod['category']
                    category_revenue[cat] = category_revenue.get(cat, 0) + float(o['total_amount'])
    
    # ══ NEW: Unfulfilled Revenue ══
    unfulfilled_revenue = sum(float(o['total_amount']) for o in orders if o['status'] in ('Processing', 'Shipped'))
    
    # ── Dynamic Greeting ──
    hour = now.hour
    if hour < 12:
        greeting = "Good Morning"
        greeting_emoji = "☀️"
        greeting_msg = "Start your day blooming!"
    elif hour < 17:
        greeting = "Good Afternoon"
        greeting_emoji = "🌤️"
        greeting_msg = "Hope your flowers are selling well!"
    else:
        greeting = "Good Evening"
        greeting_emoji = "🌙"
        greeting_msg = "Time to review today's performance."
    
    return render_template('admin_dashboard.html', 
        orders=orders, 
        products=products, 
        total_rm=total_rm,
        avg_order=avg_order,
        active_promos=active_promos,
        category_summary=category_summary,
        budget_summary=budget_summary,
        use_summary=use_summary,
        price_range=price_range,
        revenue_chart=json.dumps(revenue_chart),
        status_counts=status_counts,
        top_products=top_products,
        notes=notes,
        activity=activity,
        promotions=promotions,
        greeting=greeting,
        greeting_emoji=greeting_emoji,
        greeting_msg=greeting_msg,
        current_date=now.strftime('%A, %d %B %Y'),
        # ── New operational data ──
        deliveries_today=deliveries_today,
        deliveries_tomorrow=deliveries_tomorrow,
        pending_fulfillments=pending_fulfillments,
        low_stock_products=low_stock_products,
        total_reviews=total_reviews,
        featured_reviews=featured_reviews,
        unfeatured_reviews=unfeatured_reviews,
        avg_review_rating=round(avg_rating, 1),
        category_revenue=json.dumps(category_revenue),
        unfulfilled_revenue=unfulfilled_revenue,
    )

# ══════════════════════════════════════════
# ADMIN PRODUCTS
# ══════════════════════════════════════════

@app.route('/admin/products')
def admin_products():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    db = get_db()
    products = db.execute('SELECT * FROM products').fetchall()
    return render_template('admin_products.html', products=products)

@app.route('/admin/products/add', methods=['GET', 'POST'])
def admin_add_product():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        db = get_db()
        name = request.form.get('name')
        description = request.form.get('description')
        price = request.form.get('price')
        category = request.form.get('category')
        budget = request.form.get('budget')
        use = request.form.get('use')
        
        image_file = request.files.get('image')
        image_path = '/static/images/default.png'
        if image_file and image_file.filename:
            filename = secure_filename(image_file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(filepath)
            image_path = f'/static/images/{filename}'

        db.execute('''
            INSERT INTO products (name, description, price, image, category, budget, use)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (name, description, price, image_path, category, budget, use))
        db.commit()
        log_activity('Product Added', f'"{name}" added to catalogue — RM {price}', 'product')
        return redirect(url_for('admin_products'))

    return render_template('admin_product_add.html')

@app.route('/admin/products/delete/<int:id>', methods=['POST'])
def delete_product(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    db = get_db()
    product = db.execute('SELECT name FROM products WHERE id = ?', (id,)).fetchone()
    pname = product['name'] if product else f'Product #{id}'
    db.execute('DELETE FROM products WHERE id = ?', (id,))
    db.commit()
    log_activity('Product Deleted', f'"{pname}" removed from catalogue', 'delete')
    return redirect(url_for('admin_products'))

@app.route('/admin/products/bulk', methods=['POST'])
def bulk_admin_products():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    data = request.json
    action = data.get('action')
    product_ids = data.get('product_ids', [])
    
    if not product_ids:
        return jsonify({'success': False, 'error': 'No products selected'}), 400
        
    db = get_db()
    
    if action == 'delete':
        for pid in product_ids:
            product = db.execute('SELECT name FROM products WHERE id = ?', (pid,)).fetchone()
            pname = product['name'] if product else f'Product #{pid}'
            db.execute('DELETE FROM products WHERE id = ?', (pid,))
        db.commit()
        log_activity('Bulk Deleted', f'{len(product_ids)} products removed from catalogue', 'delete')
        return jsonify({'success': True, 'message': f'{len(product_ids)} products deleted.'})
        
    elif action == 'edit_category':
        new_category = data.get('category')
        if not new_category:
            return jsonify({'success': False, 'error': 'No category specified'}), 400
            
        placeholders = ','.join(['?'] * len(product_ids))
        query = f'UPDATE products SET category = ? WHERE id IN ({placeholders})'
        params = [new_category] + product_ids
        
        db.execute(query, params)
        db.commit()
        log_activity('Bulk Category Edit', f'{len(product_ids)} products moved to {new_category}', 'edit')
        return jsonify({'success': True, 'message': f'{len(product_ids)} products successfully moved to {new_category}.'})
        
    return jsonify({'success': False, 'error': 'Invalid action'}), 400

@app.route('/admin/products/edit/<int:id>', methods=['GET', 'POST'])
def edit_product(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    db = get_db()
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = request.form.get('price')
        category = request.form.get('category')
        budget = request.form.get('budget')
        use = request.form.get('use')
        
        image_file = request.files.get('image')
        if image_file and image_file.filename:
            filename = secure_filename(image_file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(filepath)
            image_path = f'/static/images/{filename}'
            db.execute('''
                UPDATE products 
                SET name=?, description=?, price=?, image=?, category=?, budget=?, use=? 
                WHERE id=?
            ''', (name, description, price, image_path, category, budget, use, id))
        else:
            db.execute('''
                UPDATE products 
                SET name=?, description=?, price=?, category=?, budget=?, use=? 
                WHERE id=?
            ''', (name, description, price, category, budget, use, id))
            
        db.commit()
        log_activity('Product Updated', f'"{name}" details updated', 'edit')
        return redirect(url_for('admin_products'))

    product = db.execute('SELECT * FROM products WHERE id = ?', (id,)).fetchone()
    if not product:
        return "Product not found", 404
        
    return render_template('admin_product_edit.html', product=product)

# ══════════════════════════════════════════
# ADMIN ORDERS (NEW)
# ══════════════════════════════════════════

@app.route('/admin/orders')
def admin_orders():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    db = get_db()
    orders = db.execute('SELECT * FROM orders ORDER BY created_at DESC').fetchall()
    
    import json
    from datetime import datetime, timedelta
    
    # Time boundaries for revenue calculations
    now = datetime.now()
    week_str = (now - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
    month_str = (now - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
    year_str = (now - timedelta(days=365)).strftime('%Y-%m-%d %H:%M:%S')
    
    rev_week = 0.0
    rev_month = 0.0
    rev_year = 0.0
    
    product_sales = {}
    parsed_orders = []
    
    for row in orders:
        try: # Convert sqlite3.Row to dict safely if needed, or row is dict-like
            o = dict(row)
        except:
            o = {k: row[k] for k in row.keys()}
            
        # Ensure fallback for new columns
        o['original_amount'] = o.get('original_amount', o['total_amount'])
        o['discount_amount'] = o.get('discount_amount', 0.0)
        o['promo_code_used'] = o.get('promo_code_used', '')
        
        if o['status'] != 'Cancelled' and o.get('created_at'):
            amt = float(o['total_amount'])
            if o['created_at'] >= week_str: rev_week += amt
            if o['created_at'] >= month_str: rev_month += amt
            if o['created_at'] >= year_str: rev_year += amt
            
        items = []
        try:
            raw_items = json.loads(o['products'])
            for it in raw_items:
                pid = it.get('product_id')
                qty = it.get('quantity', 1)
                p = db.execute('SELECT name, image FROM products WHERE id=?', (pid,)).fetchone()
                if p:
                    it['name'] = p['name']
                    it['image'] = p['image']
                else:
                    it['name'] = f"Product #{pid}"
                    it['image'] = ''
                items.append(it)
                
                # Track top selling products
                if o['status'] != 'Cancelled':
                    if pid not in product_sales:
                        product_sales[pid] = {'name': it['name'], 'image': it['image'], 'units': 0}
                    product_sales[pid]['units'] += qty
        except Exception as e:
            pass
            
        o['parsed_items'] = items
        o['items_json'] = json.dumps(items).replace("'", "\\'") # for JS injection
        
        # Parse checkout data safely
        try:
            c_data = json.loads(o.get('checkout_data') or '{}')
        except:
            c_data = {}
        o['checkout_data_parsed'] = c_data
        o['checkout_data_json'] = json.dumps(c_data).replace("'", "\\'")
        
        parsed_orders.append(o)
        
    top_products = sorted(product_sales.values(), key=lambda x: x['units'], reverse=True)[:3]
    
    # Gather stats
    total = len(parsed_orders)
    processing = sum(1 for o in parsed_orders if o['status'] == 'Processing')
    shipped = sum(1 for o in parsed_orders if o['status'] == 'Shipped')
    delivered = sum(1 for o in parsed_orders if o['status'] == 'Delivered')
    cancelled = sum(1 for o in parsed_orders if o['status'] == 'Cancelled')
    total_revenue = sum(float(o['total_amount']) for o in parsed_orders if o['status'] != 'Cancelled')
    
    return render_template('admin_orders.html', 
        orders=parsed_orders,
        total=total,
        processing=processing,
        shipped=shipped,
        delivered=delivered,
        cancelled=cancelled,
        total_revenue=total_revenue,
        rev_week=rev_week,
        rev_month=rev_month,
        rev_year=rev_year,
        top_products=top_products
    )

@app.route('/admin/orders/update/<order_id>', methods=['POST'])
def update_order_status(order_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    db = get_db()
    new_status = request.form.get('status')
    if new_status in ['Processing', 'Shipped', 'Delivered', 'Cancelled']:
        db.execute('UPDATE orders SET status = ? WHERE id = ?', (new_status, order_id))
        db.commit()
        log_activity('Order Updated', f'Order {order_id} status → {new_status}', 'order')
    return redirect(url_for('admin_orders'))

@app.route('/admin/orders/delete/<order_id>', methods=['POST'])
def delete_order(order_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    db = get_db()
    db.execute('DELETE FROM orders WHERE id = ?', (order_id,))
    db.commit()
    log_activity('Order Deleted', f'Order {order_id} was deleted from the system', 'delete')
    return redirect(url_for('admin_orders'))

@app.route('/api/admin/verify_payment/<order_id>', methods=['POST'])
def admin_verify_payment(order_id):
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    db = get_db()
    order_row = db.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    if not order_row:
        return jsonify({'success': False, 'error': 'Order not found'}), 404
        
    order = dict(order_row)
        
    # Generate receipt number: e.g. REC-2026-0001
    year = datetime.now(MYT).year
    # Count orders that already have a receipt number to determine the next serial
    last_no_row = db.execute("SELECT COUNT(*) as c FROM orders WHERE receipt_number IS NOT NULL AND receipt_number LIKE ?", (f"REC-{year}-%",)).fetchone()
    last_no = last_no_row['c'] if last_no_row else 0
    receipt_no = f"REC-{year}-{last_no + 1:04d}"
    
    now_str = datetime.now(MYT).strftime('%Y-%m-%d %H:%M:%S')
    
    payment_method = order.get('payment_method') or 'Manual Verification'
    payment_ref_no = order.get('payment_ref_no')
    if not payment_ref_no:
        import random
        import string
        rand_letters = ''.join(random.choices(string.ascii_uppercase, k=4))
        rand_digits = ''.join(random.choices(string.digits, k=4))
        payment_ref_no = f"ALV-{rand_letters}-{rand_digits}"
        
    db.execute('''
        UPDATE orders 
        SET payment_status = 'paid',
            receipt_number = ?,
            payment_verified_at = ?,
            payment_method = ?,
            payment_ref_no = ?
        WHERE id = ?
    ''', (receipt_no, now_str, payment_method, payment_ref_no, order_id))
    db.commit()
    
    log_activity('Payment Verified', f'Verified payment for Order {order_id} (Receipt: {receipt_no})', 'payment')
    
    # Notify Customer/Admin
    send_notification('payment_verified',
        f'🟢 <b>Payment Approved!</b>\nOrder: {order_id}\nReceipt: {receipt_no}\nVerified on: {now_str}',
        f'🟢 Payment approved for {order_id} (Receipt: {receipt_no})')
        
    return jsonify({'success': True, 'receipt_number': receipt_no})

@app.route('/api/admin/reject_payment/<order_id>', methods=['POST'])
def admin_reject_payment(order_id):
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
    data = request.json or {}
    reason = data.get('reason', 'Incorrect payment receipt/details.').strip()
    
    db = get_db()
    order = db.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    if not order:
        return jsonify({'success': False, 'error': 'Order not found'}), 404
        
    # Reset status back to unpaid
    db.execute('''
        UPDATE orders 
        SET payment_status = 'unpaid',
            payment_ref_no = '',
            payment_proof_img = ''
        WHERE id = ?
    ''', (order_id,))
    db.commit()
    
    log_activity('Payment Rejected', f'Rejected proof for Order {order_id}. Reason: {reason}', 'payment')
    
    send_notification('payment_rejected',
        f'❌ <b>Payment Proof Rejected</b>\nOrder: {order_id}\nReason: {reason}\nStatus: Reset to Unpaid',
        f'❌ Payment proof rejected for {order_id}')
        
    return jsonify({'success': True})

# ══════════════════════════════════════════
# ADMIN NOTES (NEW)
# ══════════════════════════════════════════

@app.route('/admin/notes/add', methods=['POST'])
def admin_add_note():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    content = request.form.get('content', '').strip()
    if content:
        db = get_db()
        now = datetime.now(MYT).strftime('%Y-%m-%d %H:%M:%S')
        db.execute('INSERT INTO admin_notes (content, created_at) VALUES (?, ?)', (content, now))
        db.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/notes/toggle/<int:id>', methods=['POST'])
def admin_toggle_note(id):
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    db = get_db()
    note = db.execute('SELECT is_done FROM admin_notes WHERE id = ?', (id,)).fetchone()
    if note:
        new_val = 0 if note['is_done'] else 1
        db.execute('UPDATE admin_notes SET is_done = ? WHERE id = ?', (new_val, id))
        db.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/notes/delete/<int:id>', methods=['POST'])
def admin_delete_note(id):
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    db = get_db()
    db.execute('DELETE FROM admin_notes WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('admin_dashboard'))

# ══════════════════════════════════════════
# ADMIN PROMOTIONS (ENHANCED)
# ══════════════════════════════════════════

@app.route('/admin/promotions', methods=['GET', 'POST'])
def admin_promotions():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    db = get_db()
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        discount = request.form.get('discount')
        promo_code = (request.form.get('promo_code') or '').strip().upper()
        discount_type = request.form.get('discount_type', 'percentage')
        discount_value = float(request.form.get('discount_value') or 0)
        start_date = request.form.get('start_date') or ''
        end_date = request.form.get('end_date') or ''
        applies_to = request.form.get('applies_to', 'all')
        target_categories = request.form.get('target_categories', '')
        target_product_ids = request.form.get('target_product_ids', '')
        banner_color = request.form.get('banner_color', '')
        max_uses = request.form.get('max_uses')
        max_uses = int(max_uses) if max_uses else None
        min_order_amount = float(request.form.get('min_order_amount') or 0)
        max_discount_amount = request.form.get('max_discount_amount')
        max_discount_amount = float(max_discount_amount) if max_discount_amount else None
        sort_order = int(request.form.get('sort_order') or 0)
        is_active = 1 if request.form.get('is_active') == 'on' else 0
        is_public = 1 if request.form.get('is_public') == 'on' else 0
        
        # Handle banner image upload
        banner_image = ''
        image_file = request.files.get('banner_image')
        if image_file and image_file.filename:
            filename = secure_filename(image_file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(filepath)
            banner_image = f'/static/images/{filename}'
        
        db.execute('''
            INSERT INTO promotions (title, description, discount, promo_code, discount_type, discount_value,
                start_date, end_date, applies_to, target_categories, target_product_ids,
                banner_image, banner_color, max_uses, min_order_amount, max_discount_amount,
                sort_order, is_active, is_public)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (title, description, discount, promo_code, discount_type, discount_value,
              start_date, end_date, applies_to, target_categories, target_product_ids,
              banner_image, banner_color, max_uses, min_order_amount, max_discount_amount,
              sort_order, is_active, is_public))
        db.commit()
        log_activity('Promotion Created', f'"{title}" — {discount} discount (code: {promo_code or "none"})', 'promo')
        return redirect(url_for('admin_promotions'))

    auto_expire_promotions()
    promotions = db.execute('SELECT * FROM promotions ORDER BY sort_order ASC, id DESC').fetchall()
    
    # Compute stats
    total_promos = len(promotions)
    active_count = sum(1 for p in promotions if get_promo_status(p) == 'active')
    scheduled_count = sum(1 for p in promotions if get_promo_status(p) == 'scheduled')
    expired_count = sum(1 for p in promotions if get_promo_status(p) == 'expired')
    total_uses = sum(p['times_used'] or 0 for p in promotions)
    
    # Total discount given via orders
    total_discount_given = db.execute('SELECT COALESCE(SUM(discount_amount), 0) as total FROM orders WHERE discount_amount > 0').fetchone()['total']
    
    # Enrich promotions with status
    promo_list = []
    for p in promotions:
        promo_list.append({
            'promo': p,
            'status': get_promo_status(p)
        })
    
    # Get categories for targeting dropdown
    categories = db.execute('SELECT DISTINCT category FROM products ORDER BY category').fetchall()
    products_list = db.execute('SELECT id, name FROM products ORDER BY name').fetchall()
    
    return render_template('admin_promotions.html', 
        promo_list=promo_list,
        total_promos=total_promos,
        active_count=active_count,
        scheduled_count=scheduled_count,
        expired_count=expired_count,
        total_uses=total_uses,
        total_discount_given=total_discount_given,
        categories=categories,
        products_list=products_list)

@app.route('/admin/promotions/delete/<int:id>', methods=['POST'])
def delete_promotion(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    db = get_db()
    promo = db.execute('SELECT title FROM promotions WHERE id = ?', (id,)).fetchone()
    pname = promo['title'] if promo else f'Promotion #{id}'
    db.execute('DELETE FROM promotions WHERE id = ?', (id,))
    db.commit()
    log_activity('Promotion Deleted', f'"{pname}" removed', 'delete')
    return redirect(url_for('admin_promotions'))

@app.route('/admin/promotions/toggle/<int:id>', methods=['POST'])
def toggle_promotion(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    db = get_db()
    promo = db.execute('SELECT is_active, title FROM promotions WHERE id = ?', (id,)).fetchone()
    if promo:
        new_val = 0 if promo['is_active'] else 1
        db.execute('UPDATE promotions SET is_active = ? WHERE id = ?', (new_val, id))
        db.commit()
        status = 'activated' if new_val else 'deactivated'
        log_activity('Promotion Toggled', f'"{promo["title"]}" {status}', 'promo')
    return redirect(url_for('admin_promotions'))

@app.route('/admin/promotions/generate-code')
def generate_promo_code():
    """API: Generate a random voucher code."""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    prefix = request.args.get('prefix', 'ALV').strip().upper()[:5]
    length = min(int(request.args.get('length', 6)), 10)
    db = get_db()
    # Generate unique code (try up to 10 times)
    for _ in range(10):
        chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
        code = f'{prefix}-{chars}'
        existing = db.execute('SELECT id FROM promotions WHERE UPPER(promo_code) = ?', (code,)).fetchone()
        if not existing:
            return jsonify({'code': code})
    return jsonify({'code': f'{prefix}-{chars}'})

@app.route('/admin/promotions/duplicate/<int:id>', methods=['POST'])
def duplicate_promotion(id):
    """Clone an existing promotion with a new code."""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    db = get_db()
    promo = db.execute('SELECT * FROM promotions WHERE id = ?', (id,)).fetchone()
    if not promo:
        return redirect(url_for('admin_promotions'))
    
    # Generate a new unique code
    base_code = promo['promo_code'] or 'ALV'
    prefix = base_code.split('-')[0] if '-' in base_code else 'ALV'
    new_code = ''
    for _ in range(10):
        chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        new_code = f'{prefix}-{chars}'
        existing = db.execute('SELECT id FROM promotions WHERE UPPER(promo_code) = ?', (new_code,)).fetchone()
        if not existing:
            break
    
    db.execute('''
        INSERT INTO promotions (title, description, discount, promo_code, discount_type, discount_value,
            start_date, end_date, applies_to, target_categories, target_product_ids,
            banner_image, banner_color, max_uses, min_order_amount, max_discount_amount,
            sort_order, is_active, times_used)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
    ''', (f"{promo['title']} (Copy)", promo['description'], promo['discount'], new_code,
          promo['discount_type'], promo['discount_value'],
          promo['start_date'], promo['end_date'], promo['applies_to'],
          promo['target_categories'], promo['target_product_ids'],
          promo['banner_image'], promo['banner_color'], promo['max_uses'],
          promo['min_order_amount'], promo['max_discount_amount'], promo['sort_order']))
    db.commit()
    log_activity('Promotion Duplicated', f'Cloned "{promo["title"]}" → new code {new_code}', 'promo')
    return redirect(url_for('admin_promotions'))

@app.route('/admin/promotions/usage/<int:id>')
def promo_usage(id):
    """Show usage history for a specific promotion."""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    db = get_db()
    promo = db.execute('SELECT * FROM promotions WHERE id = ?', (id,)).fetchone()
    if not promo:
        return redirect(url_for('admin_promotions'))
    
    # Get orders that used this promo code
    code = promo['promo_code'] or ''
    orders = []
    if code:
        orders = db.execute('''
            SELECT * FROM orders WHERE UPPER(promo_code_used) = ? ORDER BY created_at DESC
        ''', (code.upper(),)).fetchall()
    
    total_discount = sum(float(o['discount_amount'] or 0) for o in orders)
    total_revenue = sum(float(o['total_amount'] or 0) for o in orders)
    
    return render_template('admin_promo_usage.html',
        promo=promo,
        orders=orders,
        total_discount=total_discount,
        total_revenue=total_revenue,
        status=get_promo_status(promo))

@app.route('/admin/promotions/edit/<int:id>', methods=['GET', 'POST'])
def edit_promotion(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    db = get_db()
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        discount = request.form.get('discount')
        promo_code = (request.form.get('promo_code') or '').strip().upper()
        discount_type = request.form.get('discount_type', 'percentage')
        discount_value = float(request.form.get('discount_value') or 0)
        start_date = request.form.get('start_date') or ''
        end_date = request.form.get('end_date') or ''
        applies_to = request.form.get('applies_to', 'all')
        target_categories = request.form.get('target_categories', '')
        target_product_ids = request.form.get('target_product_ids', '')
        banner_color = request.form.get('banner_color', '')
        max_uses = request.form.get('max_uses')
        max_uses = int(max_uses) if max_uses else None
        min_order_amount = float(request.form.get('min_order_amount') or 0)
        max_discount_amount = request.form.get('max_discount_amount')
        max_discount_amount = float(max_discount_amount) if max_discount_amount else None
        sort_order = int(request.form.get('sort_order') or 0)
        is_active = 1 if request.form.get('is_active') == 'on' else 0
        is_public = 1 if request.form.get('is_public') == 'on' else 0
        
        # Handle banner image upload
        banner_image_sql = ''
        image_file = request.files.get('banner_image')
        if image_file and image_file.filename:
            filename = secure_filename(image_file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(filepath)
            banner_image_sql = f'/static/images/{filename}'
            db.execute('''
                UPDATE promotions 
                SET title=?, description=?, discount=?, promo_code=?, discount_type=?, discount_value=?,
                    start_date=?, end_date=?, applies_to=?, target_categories=?, target_product_ids=?,
                    banner_image=?, banner_color=?, max_uses=?, min_order_amount=?, max_discount_amount=?,
                    sort_order=?, is_active=?, is_public=?
                WHERE id=?
            ''', (title, description, discount, promo_code, discount_type, discount_value,
                  start_date, end_date, applies_to, target_categories, target_product_ids,
                  banner_image_sql, banner_color, max_uses, min_order_amount, max_discount_amount,
                  sort_order, is_active, is_public, id))
        else:
            db.execute('''
                UPDATE promotions 
                SET title=?, description=?, discount=?, promo_code=?, discount_type=?, discount_value=?,
                    start_date=?, end_date=?, applies_to=?, target_categories=?, target_product_ids=?,
                    banner_color=?, max_uses=?, min_order_amount=?, max_discount_amount=?,
                    sort_order=?, is_active=?, is_public=?
                WHERE id=?
            ''', (title, description, discount, promo_code, discount_type, discount_value,
                  start_date, end_date, applies_to, target_categories, target_product_ids,
                  banner_color, max_uses, min_order_amount, max_discount_amount,
                  sort_order, is_active, is_public, id))
        
        db.commit()
        log_activity('Promotion Updated', f'"{title}" details changed', 'edit')
        return redirect(url_for('admin_promotions'))

    promotion = db.execute('SELECT * FROM promotions WHERE id = ?', (id,)).fetchone()
    if not promotion:
        return "Promotion not found", 404
    
    categories = db.execute('SELECT DISTINCT category FROM products ORDER BY category').fetchall()
    products_list = db.execute('SELECT id, name FROM products ORDER BY name').fetchall()
    
    return render_template('admin_promotion_edit.html', promotion=promotion, categories=categories, products_list=products_list)

# ══════════════════════════════════════════
# ADMIN SEARCH API (NEW)
# ══════════════════════════════════════════

@app.route('/admin/search')
def admin_search():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({'products': [], 'orders': []})
    db = get_db()
    term = f'%{q}%'
    products = db.execute('SELECT id, name, price, category FROM products WHERE name LIKE ? OR category LIKE ? LIMIT 5', 
                          (term, term)).fetchall()
    orders = db.execute('SELECT id, total_amount, status FROM orders WHERE id LIKE ? LIMIT 5', 
                        (term,)).fetchall()
    return jsonify({
        'products': [dict(p) for p in products],
        'orders': [dict(o) for o in orders]
    })

# ══════════════════════════════════════════
# ADMIN — HOMEPAGE STATS
# ══════════════════════════════════════════

@app.route('/admin/homepage-stats', methods=['GET', 'POST'])
def admin_homepage_stats():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    db = get_db()
    if request.method == 'POST':
        # Update all stats
        stat_ids = request.form.getlist('stat_id')
        for sid in stat_ids:
            label = request.form.get(f'label_{sid}', '')
            value = request.form.get(f'value_{sid}', '')
            sort_order = request.form.get(f'sort_{sid}', 0)
            db.execute('UPDATE homepage_stats SET label=?, value=?, sort_order=? WHERE id=?',
                       (label, value, sort_order, sid))
        db.commit()
        log_activity('Stats Updated', 'Homepage hero stats updated', 'edit')
        return redirect(url_for('admin_homepage_stats'))
    stats = db.execute('SELECT * FROM homepage_stats ORDER BY sort_order').fetchall()
    return render_template('admin_homepage_settings.html', stats=stats, section='stats')

@app.route('/admin/homepage-stats/add', methods=['POST'])
def admin_add_stat():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    db = get_db()
    label = request.form.get('label', '')
    value = request.form.get('value', '')
    max_sort = db.execute('SELECT MAX(sort_order) as m FROM homepage_stats').fetchone()['m'] or 0
    db.execute('INSERT INTO homepage_stats (label, value, sort_order) VALUES (?, ?, ?)',
               (label, value, max_sort + 1))
    db.commit()
    return redirect(url_for('admin_homepage_stats'))

@app.route('/admin/homepage-stats/delete/<int:id>', methods=['POST'])
def admin_delete_stat(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    db = get_db()
    db.execute('DELETE FROM homepage_stats WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('admin_homepage_stats'))

# ══════════════════════════════════════════
# ADMIN — TRUST BADGES
# ══════════════════════════════════════════

@app.route('/admin/trust-badges', methods=['GET', 'POST'])
def admin_trust_badges():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    db = get_db()
    if request.method == 'POST':
        badge_ids = request.form.getlist('badge_id')
        for bid in badge_ids:
            icon = request.form.get(f'icon_{bid}', '')
            title = request.form.get(f'title_{bid}', '')
            desc = request.form.get(f'desc_{bid}', '')
            sort_order = request.form.get(f'sort_{bid}', 0)
            db.execute('UPDATE trust_badges SET icon=?, title=?, description=?, sort_order=? WHERE id=?',
                       (icon, title, desc, sort_order, bid))
        db.commit()
        log_activity('Trust Badges Updated', 'Why Choose section updated', 'edit')
        return redirect(url_for('admin_trust_badges'))
    badges = db.execute('SELECT * FROM trust_badges ORDER BY sort_order').fetchall()
    return render_template('admin_homepage_settings.html', badges=badges, section='badges')

@app.route('/admin/trust-badges/add', methods=['POST'])
def admin_add_badge():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    db = get_db()
    icon = request.form.get('icon', '🌸')
    title = request.form.get('title', '')
    desc = request.form.get('description', '')
    max_sort = db.execute('SELECT MAX(sort_order) as m FROM trust_badges').fetchone()['m'] or 0
    db.execute('INSERT INTO trust_badges (icon, title, description, sort_order) VALUES (?, ?, ?, ?)',
               (icon, title, desc, max_sort + 1))
    db.commit()
    return redirect(url_for('admin_trust_badges'))

@app.route('/admin/trust-badges/delete/<int:id>', methods=['POST'])
def admin_delete_badge(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    db = get_db()
    db.execute('DELETE FROM trust_badges WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('admin_trust_badges'))

# ══════════════════════════════════════════
# ADMIN — REVIEWS MANAGEMENT
# ══════════════════════════════════════════

@app.route('/admin/reviews')
def admin_reviews():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    analysis_type = request.args.get('sentiment', 'simple')
    
    db = get_db()
    reviews = db.execute('SELECT * FROM reviews ORDER BY created_at DESC').fetchall()
    featured_count = sum(1 for r in reviews if r['is_featured'])
    
    # Calculate general stats
    total = len(reviews)
    avg_rating = sum(r['rating'] for r in reviews) / total if total > 0 else 0
    star_distribution = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    for r in reviews:
        star_distribution[r['rating']] += 1
        
    # Algorithmic Sentiment Analysis
    positive_words = ['love', 'beautiful', 'excellent', 'great', 'fresh', 'perfect', 'amazing', 'happy', 'stunning', 'recommend', 'gorgeous']
    negative_words = ['bad', 'late', 'withered', 'dead', 'terrible', 'disappointed', 'ugly', 'broken', 'poor', 'ruined']
    
    # Pre-process reviews with sentiment flags
    processed_reviews = []
    for row in reviews:
        r = dict(row)
        text_lower = r['review_text'].lower()
        
        if analysis_type == 'detailed':
            # Detailed mode: weight words and calculate a polarity score
            score = 0
            found_pos = []
            found_neg = []
            words = text_lower.split()
            for i, w in enumerate(words):
                w = w.strip('.,!?()"\'')
                multiplier = 1
                if i > 0 and words[i-1] in ['not', 'never', "don't", 'no']:
                    multiplier = -1
                if i > 0 and words[i-1] in ['very', 'extremely', 'really']:
                    multiplier *= 1.5
                    
                if w in positive_words:
                    score += (1 * multiplier)
                    found_pos.append(w)
                elif w in negative_words:
                    score -= (1 * multiplier)
                    found_neg.append(w)
                    
            # Combine rating into overall score
            rating_diff = r['rating'] - 3
            final_sentiment_score = score + (rating_diff * 0.5)
            
            if final_sentiment_score > 1.5: sentiment = "Very Positive"
            elif final_sentiment_score > 0: sentiment = "Positive"
            elif final_sentiment_score < -1.5: sentiment = "Very Negative"
            elif final_sentiment_score < 0: sentiment = "Negative"
            else: sentiment = "Neutral"
            
            r['sentiment_label'] = sentiment
            r['pos_words'] = list(set(found_pos))
            r['neg_words'] = list(set(found_neg))
            
        else:
            # Simple mode: just base it strictly on rating
            if r['rating'] >= 4: sentiment = "Positive"
            elif r['rating'] == 3: sentiment = "Neutral"
            else: sentiment = "Negative"
            
            r['sentiment_label'] = sentiment
            r['pos_words'] = []
            r['neg_words'] = []

        processed_reviews.append(r)
        
    analysis_stats = {
        'type': analysis_type,
        'avg_rating': round(avg_rating, 1),
        'stars': star_distribution,
        'total': total
    }
        
    return render_template('admin_reviews.html', 
        reviews=processed_reviews, 
        featured_count=featured_count, 
        stats=analysis_stats)

@app.route('/admin/reviews/add', methods=['POST'])
def admin_add_review():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
        
    name = request.form.get('customer_name', '').strip()
    rating = int(request.form.get('rating', 5))
    text = request.form.get('review_text', '').strip()
    occasion = request.form.get('occasion', '').strip()
    is_featured = 1 if request.form.get('is_featured') == 'on' else 0
    now = datetime.now(MYT).strftime('%Y-%m-%d %H:%M:%S')
    
    db = get_db()
    db.execute('''
        INSERT INTO reviews (customer_name, rating, review_text, occasion, created_at, is_featured)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (name, rating, text, occasion, now, is_featured))
    db.commit()
    
    log_activity('Added Review', f'Manually added a {rating}★ review by {name}', 'review')
    return redirect(url_for('admin_reviews'))

@app.route('/admin/reviews/edit/<int:id>', methods=['POST'])
def admin_edit_review(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
        
    name = request.form.get('customer_name', '').strip()
    rating = int(request.form.get('rating', 5))
    text = request.form.get('review_text', '').strip()
    occasion = request.form.get('occasion', '').strip()
    
    db = get_db()
    db.execute('''
        UPDATE reviews 
        SET customer_name = ?, rating = ?, review_text = ?, occasion = ?
        WHERE id = ?
    ''', (name, rating, text, occasion, id))
    db.commit()
    
    log_activity('Edited Review', f'Updated review #{id} by {name}', 'review')
    return redirect(url_for('admin_reviews'))

@app.route('/admin/reviews/toggle/<int:id>', methods=['POST'])
def admin_toggle_review(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    db = get_db()
    review = db.execute('SELECT is_featured FROM reviews WHERE id = ?', (id,)).fetchone()
    if review:
        new_val = 0 if review['is_featured'] else 1
        db.execute('UPDATE reviews SET is_featured = ? WHERE id = ?', (new_val, id))
        db.commit()
        action = 'Featured' if new_val else 'Unfeatured'
        log_activity(f'Review {action}', f'Review #{id} {action.lower()} on homepage', 'review')
    return redirect(url_for('admin_reviews'))

@app.route('/admin/reviews/delete/<int:id>', methods=['POST'])
def admin_delete_review(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    db = get_db()
    db.execute('DELETE FROM reviews WHERE id = ?', (id,))
    db.commit()
    log_activity('Review Deleted', f'Review #{id} deleted', 'delete')
    return redirect(url_for('admin_reviews'))

@app.route('/admin/settings', methods=['GET', 'POST'])
def admin_settings():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
        
    db = get_db()
    
    if request.method == 'POST':
        # Security Settings
        honeypot = 1 if request.form.get('honeypot_enabled') else 0
        fast_limit_sec = float(request.form.get('fast_submit_limit_sec', 3))
        fast_limit_ms = int(fast_limit_sec * 1000)
        spam_order = int(request.form.get('spam_order_limit', 3))
        spam_time = int(request.form.get('spam_time_window_mins', 10))
        
        # Store Settings
        store_status_mode = request.form.get('store_status_mode', 'open').strip()
        is_open = 1 if store_status_mode == 'open' else 0
        reopen_datetime = request.form.get('reopen_datetime', '').strip() or None
        closed_notification_message = request.form.get('closed_notification_message', '').strip() or 'We are temporarily closed. We will begin accepting orders again shortly.'
        whatsapp = request.form.get('whatsapp', '').strip()
        instagram = request.form.get('instagram', '').strip()
        facebook = request.form.get('facebook', '').strip()
        theme = request.form.get('theme', 'classic')
        
        # Visitor Counter Settings
        show_visitors = 1 if request.form.get('show_visitors') else 0
        total_visitors_val = request.form.get('total_visitors')
        
        # Checkout Form Schema & Business Hours
        checkout_form_schema = request.form.get('checkout_form_schema')
        business_hours = request.form.get('business_hours')
        
        # Announcement Settings (God-Tier)
        ann_fields = {
            'announcement_enabled': 1 if request.form.get('announcement_enabled') else 0,
            'announcement_text': request.form.get('announcement_text', '').strip(),
            'announcement_style': request.form.get('announcement_style', 'info'),
            'announcement_type': request.form.get('announcement_type', 'minimal_bar'),
            'announcement_frequency': request.form.get('announcement_frequency', 'session'),
            'announcement_target_page': request.form.get('announcement_target_page', 'all'),
            'announcement_start_date': request.form.get('announcement_start_date', ''),
            'announcement_end_date': request.form.get('announcement_end_date', ''),
            'announcement_auto_dismiss_sec': int(float(request.form.get('announcement_auto_dismiss_sec') or 0)),
            'announcement_delay_sec': int(float(request.form.get('announcement_delay_sec') or 0)),
            'announcement_scroll_pct': int(float(request.form.get('announcement_scroll_pct') or 0)),
            'announcement_exit_intent': 1 if request.form.get('announcement_exit_intent') else 0,
            'announcement_device_target': request.form.get('announcement_device_target', 'all'),
            'announcement_audience': request.form.get('announcement_audience', 'all'),
            'announcement_cta_text': request.form.get('announcement_cta_text', '').strip(),
            'announcement_cta_link': request.form.get('announcement_cta_link', '').strip(),
            'announcement_color_bg': request.form.get('announcement_color_bg', '').strip(),
            'announcement_color_text': request.form.get('announcement_color_text', '').strip(),
            'announcement_geo_target': request.form.get('announcement_geo_target', '').strip(),
            'announcement_ref_target': request.form.get('announcement_ref_target', '').strip(),
            'announcement_sound_enabled': 1 if request.form.get('announcement_sound_enabled') else 0,
            'announcement_minimize_mode': 1 if request.form.get('announcement_minimize_mode') else 0,
            'announcement_ab_test_enabled': 1 if request.form.get('announcement_ab_test_enabled') else 0,
            'announcement_variant_b_text': request.form.get('announcement_variant_b_text', '').strip(),
            'announcement_variant_b_layout': request.form.get('announcement_variant_b_layout', 'minimal_bar')
        }
        
        # Notification Settings
        notif_fields = {
            'notif_enabled': 1 if request.form.get('notif_enabled') else 0,
            'notif_telegram_token': request.form.get('notif_telegram_token', '').strip(),
            'notif_message_format': request.form.get('notif_message_format', 'detailed'),
            'notif_quiet_start': request.form.get('notif_quiet_start', '').strip(),
            'notif_quiet_end': request.form.get('notif_quiet_end', '').strip(),
            'notif_daily_digest': 1 if request.form.get('notif_daily_digest') else 0,
            'notif_digest_time': request.form.get('notif_digest_time', '20:00').strip(),
            'notif_wa_enabled': 1 if request.form.get('notif_wa_enabled') else 0,
            'notif_wa_instance_id': request.form.get('notif_wa_instance_id', '').strip(),
            'notif_wa_token': request.form.get('notif_wa_token', '').strip(),
            'notif_wa_phone': request.form.get('notif_wa_phone', '').strip(),
            'notif_meta_enabled': 1 if request.form.get('notif_meta_enabled') else 0,
            'notif_meta_phone_id': request.form.get('notif_meta_phone_id', '').strip(),
            'notif_meta_token': request.form.get('notif_meta_token', '').strip(),
            'notif_meta_phone': request.form.get('notif_meta_phone', '').strip(),
            'notif_meta_template': request.form.get('notif_meta_template', '').strip(),
            'notif_meta_lang': request.form.get('notif_meta_lang', 'en').strip(),
        }
        db.execute('''
            UPDATE security_settings 
            SET honeypot_enabled = ?, fast_submit_limit_ms = ?, spam_order_limit = ?, spam_time_window_mins = ?
            WHERE id = 1
        ''', (honeypot, fast_limit_ms, spam_order, spam_time))
        
        # Build the store update dynamically
        update_cols = [
            "is_open = ?", "whatsapp = ?", "instagram = ?", "facebook = ?", "theme = ?", 
            "show_visitors = ?", "checkout_form_schema = COALESCE(?, checkout_form_schema)", 
            "business_hours = COALESCE(?, business_hours)",
            "store_status_mode = ?", "reopen_datetime = ?", "closed_notification_message = ?"
        ]
        update_vals = [is_open, whatsapp, instagram, facebook, theme, show_visitors, checkout_form_schema, business_hours, store_status_mode, reopen_datetime, closed_notification_message]
        
        if total_visitors_val is not None and total_visitors_val != '':
            update_cols.append("total_visitors = ?")
            update_vals.append(max(0, int(total_visitors_val)))
            
        for k, v in ann_fields.items():
            update_cols.append(f"{k} = ?")
            update_vals.append(v)
        
        for k, v in notif_fields.items():
            update_cols.append(f"{k} = ?")
            update_vals.append(v)
            
        sql = f"UPDATE store_settings SET {', '.join(update_cols)} WHERE id = 1"
        db.execute(sql, tuple(update_vals))
        
        db.commit()
        log_activity('Settings Updated', 'Alvina updated the master storefront settings & security rules', 'shield')
        return redirect(url_for('admin_settings', success='true'))
        
    settings = db.execute('SELECT * FROM security_settings WHERE id = 1').fetchone()
    if not settings:
        settings = {'honeypot_enabled': 1, 'fast_submit_limit_ms': 3000, 'spam_order_limit': 3, 'spam_time_window_mins': 10}
        
    store_row = db.execute('SELECT * FROM store_settings WHERE id = 1').fetchone()
    store = dict(store_row) if store_row else {
        'is_open': 1, 'whatsapp': '', 'instagram': '', 'facebook': '', 'theme': 'classic',
        'total_visitors': 0, 'show_visitors': 1,
        'store_status_mode': 'open', 'reopen_datetime': None,
        'closed_notification_message': 'We are temporarily closed. We will begin accepting orders again shortly.'
    }
                 
    analytics = db.execute('SELECT * FROM announcement_analytics WHERE id = 1').fetchone()
    analytics_dict = dict(analytics) if analytics else {}
    for key in ['views_a', 'clicks_a', 'views_b', 'clicks_b']:
        if key not in analytics_dict:
            analytics_dict[key] = 0
        
    settings_dict = dict(settings)
    settings_dict['fast_submit_limit_sec'] = int(settings_dict['fast_submit_limit_ms'] / 1000)
        
    return render_template('admin_settings.html', settings=settings_dict, store=store, analytics=analytics_dict)

@app.route('/admin/logout')
def admin_logout():
    log_activity('Admin Logout', 'Alvina logged out', 'logout')
    session.pop('admin_logged_in', None)
    return redirect(url_for('home'))

@app.route('/api/track_announcement', methods=['POST'])
def track_announcement():
    data = request.get_json()
    if not data: return jsonify({'status': 'error'})
    action = data.get('action') # 'view' or 'click'
    variant = data.get('variant') # 'A' or 'B'
    if action not in ('view', 'click') or variant not in ('A', 'B'):
        return jsonify({'status': 'error'})
    
    col = f"{action}s_{variant.lower()}"
    db = get_db()
    db.execute(f"UPDATE announcement_analytics SET {col} = {col} + 1 WHERE id = 1")
    db.commit()
    return jsonify({'status': 'ok'})

# ══════════════════════════════════════════
# DASHBOARD QUICK-ACTION API ENDPOINTS
# ══════════════════════════════════════════

@app.route('/api/admin/toggle_store', methods=['POST'])
def api_toggle_store():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False}), 403
    db = get_db()
    current = db.execute('SELECT store_status_mode FROM store_settings WHERE id = 1').fetchone()
    current_mode = current['store_status_mode'] if current else 'open'
    
    if current_mode == 'open':
        new_mode = 'fully_booked'
        new_is_open = 0
    else:
        new_mode = 'open'
        new_is_open = 1
        
    db.execute('UPDATE store_settings SET store_status_mode = ?, is_open = ?, reopen_datetime = NULL WHERE id = 1', (new_mode, new_is_open))
    db.commit()
    
    status_text = 'Open' if new_is_open else 'Fully Booked Today'
    log_activity('Store Status Changed', f'Store set to: {status_text}', 'info')
    emoji = '🟢' if new_is_open else '🟡'
    send_notification('store_toggle',
        f'{emoji} <b>Store Status Changed</b>\nNow: {status_text}',
        f'{emoji} Store → {status_text}')
    return jsonify({'success': True, 'is_open': bool(new_is_open), 'store_status_mode': new_mode})

@app.route('/api/admin/toggle_announcement', methods=['POST'])
def api_toggle_announcement():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False}), 403
    db = get_db()
    current = db.execute('SELECT announcement_enabled FROM store_settings WHERE id = 1').fetchone()
    new_val = 0 if current['announcement_enabled'] else 1
    db.execute('UPDATE store_settings SET announcement_enabled = ? WHERE id = 1', (new_val,))
    db.commit()
    status_text = 'Enabled' if new_val else 'Disabled'
    log_activity('Announcement Toggled', f'Announcement banner: {status_text}', 'info')
    send_notification('store_toggle',
        f'📢 <b>Announcement {status_text}</b>\nBanner has been {status_text.lower()}',
        f'📢 Announcement → {status_text}')
    return jsonify({'success': True, 'enabled': bool(new_val)})

@app.route('/api/admin/quick_fulfill/<order_id>', methods=['POST'])
def api_quick_fulfill(order_id):
    if not session.get('admin_logged_in'):
        return jsonify({'success': False}), 403
    db = get_db()
    db.execute('UPDATE orders SET status = ? WHERE id = ?', ('Delivered', order_id))
    db.commit()
    log_activity('Order Fulfilled', f'Order {order_id} marked as Delivered from dashboard', 'order')
    return jsonify({'success': True})

# ══════════════════════════════════════════
# NOTIFICATION API ENDPOINTS
# ══════════════════════════════════════════

@app.route('/api/admin/test_notification', methods=['POST'])
def api_test_notification():
    """Send a test notification to verify Telegram setup."""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False}), 403
    data = request.json
    token = (data.get('token') or '').strip()
    chat_id = (data.get('chat_id') or '').strip()
    if not token or not chat_id:
        return jsonify({'success': False, 'error': 'Bot Token and Chat ID are required'})
    try:
        url = f'https://api.telegram.org/bot{token}/sendMessage'
        resp = http_requests.post(url, json={
            'chat_id': chat_id,
            'text': '🌸 <b>Lvina\'s Florist</b>\n\n✅ Test notification successful!\nYou will receive order alerts here.',
            'parse_mode': 'HTML'
        }, timeout=10)
        result = resp.json()
        if result.get('ok'):
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': result.get('description', 'Unknown error')})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/notif_recipients', methods=['GET'])
def api_get_recipients():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False}), 403
    db = get_db()
    rows = db.execute('SELECT * FROM notif_recipients ORDER BY created_at DESC').fetchall()
    return jsonify({'success': True, 'recipients': [dict(r) for r in rows]})

@app.route('/api/admin/notif_recipients/add', methods=['POST'])
def api_add_recipient():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False}), 403
    data = request.json
    label = (data.get('label') or 'Admin').strip()
    chat_id = (data.get('chat_id') or '').strip()
    if not chat_id:
        return jsonify({'success': False, 'error': 'Chat ID is required'})
    
    # Check max 5 recipients
    db = get_db()
    count = db.execute('SELECT COUNT(*) as c FROM notif_recipients').fetchone()['c']
    if count >= 5:
        return jsonify({'success': False, 'error': 'Maximum 5 recipients allowed'})
    
    # Check duplicate
    existing = db.execute('SELECT id FROM notif_recipients WHERE chat_id = ?', (chat_id,)).fetchone()
    if existing:
        return jsonify({'success': False, 'error': 'This Chat ID is already added'})
    
    default_events = json.dumps({"new_order":1,"new_review":1,"bad_review":1,"spam":0,"promo_exhausted":1,"store_toggle":1})
    now = datetime.now(MYT).strftime('%Y-%m-%d %H:%M:%S')
    db.execute('INSERT INTO notif_recipients (label, chat_id, is_active, events, created_at) VALUES (?, ?, 1, ?, ?)',
               (label, chat_id, default_events, now))
    db.commit()
    
    # Send welcome message
    store = db.execute('SELECT notif_telegram_token FROM store_settings WHERE id = 1').fetchone()
    token = (store['notif_telegram_token'] or '').strip() if store else ''
    if token:
        try:
            http_requests.post(f'https://api.telegram.org/bot{token}/sendMessage', json={
                'chat_id': chat_id,
                'text': f'🌸 <b>Welcome, {label}!</b>\n\nYou have been added as a notification recipient for Lvina\'s Florist.\nYou will receive order & review alerts here.',
                'parse_mode': 'HTML'
            }, timeout=5)
        except Exception:
            pass
    
    log_activity('Recipient Added', f'Notification recipient "{label}" added', 'info')
    return jsonify({'success': True})

@app.route('/api/admin/notif_recipients/delete/<int:id>', methods=['POST'])
def api_delete_recipient(id):
    if not session.get('admin_logged_in'):
        return jsonify({'success': False}), 403
    db = get_db()
    r = db.execute('SELECT label FROM notif_recipients WHERE id = ?', (id,)).fetchone()
    db.execute('DELETE FROM notif_recipients WHERE id = ?', (id,))
    db.commit()
    if r:
        log_activity('Recipient Removed', f'Notification recipient "{r["label"]}" removed', 'info')
    return jsonify({'success': True})

@app.route('/api/admin/notif_recipients/toggle/<int:id>', methods=['POST'])
def api_toggle_recipient(id):
    if not session.get('admin_logged_in'):
        return jsonify({'success': False}), 403
    db = get_db()
    r = db.execute('SELECT is_active FROM notif_recipients WHERE id = ?', (id,)).fetchone()
    if r:
        new_val = 0 if r['is_active'] else 1
        db.execute('UPDATE notif_recipients SET is_active = ? WHERE id = ?', (new_val, id))
        db.commit()
    return jsonify({'success': True, 'is_active': bool(new_val) if r else False})

@app.route('/api/admin/notif_recipients/update/<int:id>', methods=['POST'])
def api_update_recipient(id):
    if not session.get('admin_logged_in'):
        return jsonify({'success': False}), 403
    data = request.json
    db = get_db()
    label = (data.get('label') or '').strip()
    events = data.get('events')
    updates = []
    vals = []
    if label:
        updates.append('label = ?')
        vals.append(label)
    if events is not None:
        updates.append('events = ?')
        vals.append(json.dumps(events))
    if updates:
        vals.append(id)
        db.execute(f'UPDATE notif_recipients SET {", ".join(updates)} WHERE id = ?', tuple(vals))
        db.commit()
    return jsonify({'success': True})

@app.route('/api/admin/notif_log', methods=['GET'])
def api_notif_log():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False}), 403
    db = get_db()
    rows = db.execute('SELECT * FROM notif_log ORDER BY id DESC LIMIT 50').fetchall()
    return jsonify({'success': True, 'logs': [dict(r) for r in rows]})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 6006))
    app.run(debug=True, host='0.0.0.0', port=port)
