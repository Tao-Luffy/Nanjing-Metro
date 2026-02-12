import smtplib
from email.mime.text import MIMEText

# ====== 配置区 ======
smtp_server = "smtp.qq.com"
smtp_port = 465

sender_email = "3852857288@qq.com"
sender_auth_code = "aovpkzqhnsfxccee"

recipient_emails = [
    "1989859094@qq.com",
    "1544825840@qq.com",
]
subject = "更新通知"
body = "Cookie已经失效请尽快更新。\n 网站地址：https://unqualified-developers.github.io/"

def send_email():
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = ", ".join(recipient_emails)

    with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
        server.login(sender_email, sender_auth_code)
        server.sendmail(sender_email, recipient_emails, msg.as_string())