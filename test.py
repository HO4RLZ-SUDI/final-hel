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

# --- CONFIG ---
TEACHER_EMAIL = "ครู@gmail.com"
SENDER_EMAIL = "ระบบ@gmail.com"
SENDER_PASSWORD = "รหัสผ่านแอป16หลัก" # Gmail App Password

FACE_DIR = 'faces'
DB_FILE = 'cyber_safety.db'
TRAINER_FILE = 'trainer.yml'

if not os.path.exists(FACE_DIR): os.makedirs(FACE_DIR)

# Initialize Models
recognizer = cv2.face.LBPHFaceRecognizer_create()
def retrain_lbph():
    if not os.listdir(FACE_DIR): return
    paths = [os.path.join(FACE_DIR, f) for f in os.listdir(FACE_DIR)]
    faces, ids = [], []
    for p in paths:
        ids.append(int(os.path.split(p)[-1].split(".")[1]))
        faces.append(cv2.imread(p, cv2.IMREAD_GRAYSCALE))
    recognizer.train(faces, np.array(ids))
    recognizer.save(TRAINER_FILE)

# --- EMAIL HELPER ---
def send_email(subject, body):
    def mail_thread():
        try:
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = SENDER_EMAIL
            msg['To'] = TEACHER_EMAIL
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(SENDER_EMAIL, SENDER_PASSWORD)
                server.send_message(msg)
        except Exception as e: print(f"Email Error: {e}")
    threading.Thread(target=mail_thread).start()

# --- ROUTES ---
@app.route('/')
def index(): return render_template('index.html')

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
    
    # ส่งเมลแจ้งการลงทะเบียนใหม่
    send_email(f"✅ ลงทะเบียนใหม่: {name}", f"ระบบได้ทำการบันทึกใบหน้าของ {name} เข้าสู่ฐานข้อมูลเรียบร้อยแล้วเมื่อ {datetime.now()}")
    
    return jsonify({'status': 'registered', 'id': uid})

@app.route('/verify_event', methods=['POST'])
def verify_event():
    data = request.json
    status = data['status'] # จาก Teachable Machine
    img_data = base64.b64decode(data['image'].split(',')[1])
    nparr = np.frombuffer(img_data, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
    
    name = "UNKNOWN"
    if os.path.exists(TRAINER_FILE):
        recognizer.read(TRAINER_FILE)
        uid, conf = recognizer.predict(frame)
        if conf < 75:
            conn = sqlite3.connect(DB_FILE)
            res = conn.execute('SELECT name FROM users WHERE id=?', (uid,)).fetchone()
            name = res[0] if res else "UNKNOWN"
            
            # เช็คส่งเมล 1 ครั้งต่อวัน
            today = datetime.now().strftime('%Y-%m-%d')
            logged = conn.execute('SELECT id FROM logs WHERE user_id=? AND date=?', (uid, today)).fetchone()
            if not logged:
                conn.execute('INSERT INTO logs (user_id, date, status) VALUES (?, ?, ?)', (uid, today, status))
                conn.commit()
                if status == "No_Helmet":
                    send_email(f"❌ พบผู้ฝ่าฝืน: {name}", f"นักเรียน {name} ไม่สวมหมวกนิรภัย ตรวจพบเมื่อ {datetime.now()}")
            conn.close()
            
    return jsonify({'name': name})

if __name__ == '__main__':
    conn = sqlite3.connect(DB_FILE)
    conn.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, date TEXT, status TEXT)')
    conn.close()
    retrain_lbph()
    app.run(host='0.0.0.0', port=5000)