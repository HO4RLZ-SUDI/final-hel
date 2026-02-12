import cv2
import numpy as np
import os
import sqlite3
import smtplib
import base64
from email.mime.text import MIMEText
from datetime import datetime
from flask import Flask, render_template, request, jsonify
import threading

app = Flask(__name__)

# --- CONFIGURATION (แก้ไขที่นี่) ---
SENDER_EMAIL = "darkton007@gmail.com"
SENDER_PASSWORD = "dejs lrco pcph nyyz" 
TEACHER_EMAIL = "thanaphoom40852@gmail.com"

FACE_DIR = 'faces'
DB_FILE = 'cyber_safety.db'
TRAINER_FILE = 'trainer.yml'

if not os.path.exists(FACE_DIR): os.makedirs(FACE_DIR)

# --- DATABASE INIT ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, date TEXT, status TEXT)')
    conn.close()

# --- FACE RECOGNITION SYSTEM ---
recognizer = cv2.face.LBPHFaceRecognizer_create()

def retrain_lbph():
    if not os.listdir(FACE_DIR): return
    paths = [os.path.join(FACE_DIR, f) for f in os.listdir(FACE_DIR)]
    faces, ids = [], []
    for p in paths:
        uid = int(os.path.split(p)[-1].split(".")[1])
        img = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
        if img is not None:
            faces.append(img)
            ids.append(uid)
    if faces:
        recognizer.train(faces, np.array(ids))
        recognizer.save(TRAINER_FILE)
        print("⚙️  Model Retrained.")

# --- EMAIL SYSTEM (PORT 587) ---
def send_email(subject, body):
    def mail_thread():
        try:
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = SENDER_EMAIL
            msg['To'] = TEACHER_EMAIL

            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
            server.quit()
            print(f"📧 ส่งอีเมลสำเร็จ: {subject}")
        except Exception as e:
            print(f"❌ Email Error: {e}")
    threading.Thread(target=mail_thread).start()

# --- ROUTES ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    name = data['name']
    img_data = base64.b64decode(data['image'].split(',')[1])
    nparr = np.frombuffer(img_data, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute('INSERT INTO users (name) VALUES (?)', (name,))
    uid = cur.lastrowid
    conn.commit()
    conn.close()

    cv2.imwrite(f"{FACE_DIR}/user.{uid}.jpg", frame)
    retrain_lbph()
    
    # ส่งเมลแจ้งลงทะเบียนใหม่
    send_email(f"✅ ลงทะเบียนใหม่: {name}", f"ได้ลงทะเบียนใบหน้าของ {name} เข้าสู่ระบบ CyberGuard เรียบร้อยแล้ว")
    return jsonify({'status': 'registered'})

@app.route('/verify_event', methods=['POST'])
def verify_event():
    data = request.json
    status = data['status'] # Helmet_OK / No_Helmet
    img_data = base64.b64decode(data['image'].split(',')[1])
    nparr = np.frombuffer(img_data, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
    
    name = "Unknown"
    if os.path.exists(TRAINER_FILE):
        recognizer.read(TRAINER_FILE)
        uid, conf = recognizer.predict(frame)
        
        if conf < 75: # มั่นใจเกิน 75%
            conn = sqlite3.connect(DB_FILE)
            res = conn.execute('SELECT name FROM users WHERE id=?', (uid,)).fetchone()
            name = res[0] if res else "Unknown"
            
            # --- DAILY LOG LOGIC ---
            today = datetime.now().strftime('%Y-%m-%d')
            already_logged = conn.execute('SELECT id FROM logs WHERE user_id=? AND date=?', (uid, today)).fetchone()
            
            if not already_logged:
                print(f"🔍 บันทึกประวัติใหม่สำหรับ {name}")
                conn.execute('INSERT INTO logs (user_id, date, status) VALUES (?, ?, ?)', (uid, today, status))
                conn.commit()
                
                # ถ้าไม่ใส่หมวก -> ส่งเมลทันที
                if status == "No_Helmet":
                    send_email(f"❌ พบผู้ไม่สวมหมวก: {name}", f"ตรวจพบ {name} ไม่สวมหมวกนิรภัยเมื่อ {datetime.now().strftime('%H:%M:%S')}")
            else:
                print(f"ℹ️ {name} ถูกบันทึกไปแล้ววันนี้ (ข้ามการส่งเมล)")
            conn.close()
            
    return jsonify({'name': name})

if __name__ == '__main__':
    init_db()
    retrain_lbph()
    app.run(host='0.0.0.0', port=5000)