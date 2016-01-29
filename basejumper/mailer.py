import smtplib
from email.mime.text import MIMEText
import logging


log = logging.getLogger("mailer")


class Mailer(object):
    def __init__(self, server, from_address, user=None, password=None):
        self.smtp = smtplib.SMTP(server)

        if user is None and password is not None:
            log.error("SMTP Password provided but no user provided.")
            user = ""
        elif user is not None and password is None:
            log.error("SMTP User provided but no password provided.")
            password = ""

        if user is not None and password is not None:
            try:
                self.smtp.login(user, password)
            except smtplib.SMTPAuthenticationError:
                log.error("SMTP Credentials Invalid.")
                self.smtp = None
            except smtplib.SMTPException:
                log.error("No suitable authentication method found.")
                self.smtp = None
        self.from_address = from_address

    def send_email(self, subject, message, recipients):
        if self.smtp is None:
            log.error("Unable to send email; see earlier in logs for details.")
            return

        email = MIMEText(message)
        email["Subject"] = subject
        email["From"] = self.from_address
        email["To"] = ",".join(recipients)
        self.smtp.sendmail("fries2@llnl.gov", recipients, email.as_string())
