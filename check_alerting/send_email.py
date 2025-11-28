# based on https://stackoverflow.com/a/6270987 and https://stackoverflow.com/a/32873143

import os
import smtplib
import ssl
from email.mime.text import MIMEText

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
FROM = os.environ["FROM_EMAIL"]
PASSWORD = os.environ["FROM_EMAIL_PASSWORD"]
TO = os.environ["TO_EMAIL"]

msg = MIMEText("Email text")

msg["Subject"] = "Subject"
msg["From"] = FROM
msg["To"] = TO

with smtplib.SMTP_SSL(
    "smtp.gmail.com", port=465, context=ssl.create_default_context()
) as s:
    s.login(user=FROM, password=PASSWORD)
    s.sendmail(FROM, [TO], msg.as_string())
