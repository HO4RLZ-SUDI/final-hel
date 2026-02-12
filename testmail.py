import smtplib
from email.mime.text import MIMEText

# ใส่ข้อมูลของคุณที่นี่
SENDER_EMAIL = "darkton007@gmail.com"
SENDER_PASSWORD = "dejs lrco pcph nyyz" 
TEACHER_EMAIL = "thanaphoom40852@gmail.com"

msg = MIMEText("ทดสอบการส่งเมลจากระบบ CyberGuard")
msg['Subject'] = "🔔 Test Email"
msg['From'] = SENDER_EMAIL
msg['To'] = TEACHER_EMAIL

try:
    print("กำลังเชื่อมต่อเซิร์ฟเวอร์...")
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(SENDER_EMAIL, SENDER_PASSWORD)
    server.send_message(msg)
    server.quit()
    print("✅ ส่งเมลสำเร็จ! กรุณาเช็คใน Inbox หรือ Junk Mail")
except Exception as e:
    print(f"❌ ส่งไม่สำเร็จเพราะ: {e}")