import os
import smtplib
import mimetypes
import json

from email.message import EmailMessage

BASE_DIR = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(BASE_DIR, 'data/config.json')
MESSAGE_PATH = os.path.join(BASE_DIR, 'data/message.txt')
ATTACHMENTS_DIR = os.path.join(BASE_DIR, 'data/attachments')

with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config = json.load(f)

smtp_server = config['smtp_server']
smtp_port = config['smtp_port']
sender_email = config['sender_email']
sender_password = config['sender_password']
recipients = config['recipients']
subject = config['subject']
attachments = config['attachments']

with open(MESSAGE_PATH, 'r', encoding='utf-8') as f:
    message_body = f.read()

msg = EmailMessage()
msg['From'] = sender_email
msg['To'] = ', '.join(recipients)
msg['Subject'] = subject
msg.set_content(message_body)

for filename in attachments:
    file_path = os.path.join(ATTACHMENTS_DIR, filename)
    if not os.path.exists(file_path):
        print(f'Файл {filename} не найден, пропускаем.')
        continue

    mime_type, _ = mimetypes.guess_type(file_path)
    mime_type = mime_type or 'application/octet-stream'
    main_type, sub_type = mime_type.split('/', 1)

    with open(file_path, 'rb') as f:
        file_data = f.read()

    msg.add_attachment(file_data, maintype=main_type, subtype=sub_type, filename=filename)

try:
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        print("Письмо отправлено.")
except Exception as e:
    print(f"Ошибка {e}")
