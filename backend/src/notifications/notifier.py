"""
Notification service for sending email notifications.
"""
import os
import logging
from typing import Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending email notifications."""

    def __init__(self):
        # Email configuration
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USER')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.from_email = os.getenv('FROM_EMAIL', self.smtp_user)

        logger.info(f"Email notification service initialized (SMTP: {self.smtp_host}:{self.smtp_port})")

    def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None
    ) -> bool:
        """
        Send an email notification.

        Args:
            to_email: Recipient email address
            subject: Email subject line
            body_text: Plain text email body
            body_html: Optional HTML email body

        Returns:
            True if email was sent successfully, False otherwise
        """
        if not self.smtp_user or not self.smtp_password:
            logger.warning("SMTP credentials not configured, skipping email")
            return False

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = to_email

            # Attach plain text and HTML versions
            part1 = MIMEText(body_text, 'plain')
            msg.attach(part1)

            if body_html:
                part2 = MIMEText(body_html, 'html')
                msg.attach(part2)

            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    def send_tee_time_notification(
        self,
        user_email: str,
        user_name: Optional[str],
        course_name: str,
        tee_off_date: str,
        tee_off_time: str,
        available_spots: int,
        group_size: int
    ) -> dict:
        """
        Send email notification about an available tee time.

        Args:
            user_email: User's email address
            user_name: User's first name (optional)
            course_name: Name of the golf course
            tee_off_date: Date of the tee time
            tee_off_time: Time of the tee time (Eastern Time)
            available_spots: Number of available spots
            group_size: Requested group size

        Returns:
            Dict with success status for email
        """
        greeting = f"Hi {user_name}!" if user_name else "Hi!"

        # Create email content
        email_subject = f"Tee Time Available: {course_name} on {tee_off_date}"

        email_body_text = f"""{greeting}

Great news! A tee time matching your search is now available:

Course: {course_name}
Date: {tee_off_date}
Time: {tee_off_time} ET
Available Spots: {available_spots}
Your Group Size: {group_size}

Book now before it's gone!

Log in to your account to view details and book:
https://your-tee-time-app.com/dashboard

Happy golfing!
Bergen County Golf Tee Time Finder
"""

        email_body_html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .tee-time-card {{ background: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .detail-row {{ display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #eee; }}
        .detail-label {{ font-weight: bold; color: #667eea; }}
        .cta-button {{ display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
        .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏌️ Tee Time Available!</h1>
        </div>
        <div class="content">
            <p>{greeting}</p>
            <p>Great news! A tee time matching your search is now available:</p>

            <div class="tee-time-card">
                <div class="detail-row">
                    <span class="detail-label">Course:</span>
                    <span>{course_name}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Date:</span>
                    <span>{tee_off_date}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Time:</span>
                    <span>{tee_off_time} ET</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Available Spots:</span>
                    <span>{available_spots}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Your Group Size:</span>
                    <span>{group_size}</span>
                </div>
            </div>

            <p style="text-align: center;">
                <a href="https://your-tee-time-app.com/dashboard" class="cta-button">View & Book Now</a>
            </p>

            <p style="color: #999; font-size: 14px;">Book quickly - tee times go fast!</p>
        </div>
        <div class="footer">
            <p>Happy golfing!<br>Bergen County Golf Tee Time Finder</p>
        </div>
    </div>
</body>
</html>
"""

        # Send email notification
        email_sent = self.send_email(user_email, email_subject, email_body_text, email_body_html)

        return {
            'email_sent': email_sent
        }

    def send_batched_tee_time_notification(
        self,
        user_email: str,
        user_name: Optional[str],
        search_id: int,
        tee_times: list,
        group_size: int
    ) -> dict:
        """
        Send email notification about multiple available tee times in one email.

        Args:
            user_email: User's email address
            user_name: User's first name (optional)
            search_id: ID of the search request
            tee_times: List of dicts with tee time details (course_name, tee_off_date, tee_off_time, available_spots)
            group_size: Requested group size

        Returns:
            Dict with success status for email
        """
        greeting = f"Hi {user_name}!" if user_name else "Hi!"

        count = len(tee_times)
        plural = "s" if count > 1 else ""

        # Create email content
        email_subject = f"{count} Tee Time{plural} Available - Search #{search_id}"

        # Build plain text list
        tee_times_text = ""
        for i, tt in enumerate(tee_times, 1):
            tee_times_text += f"""
{i}. {tt['course_name']}
   Date: {tt['tee_off_date']}
   Time: {tt['tee_off_time']} ET
   Available Spots: {tt['available_spots']}
"""

        email_body_text = f"""{greeting}

Great news! We found {count} tee time{plural} matching your search:
{tee_times_text}
Your Group Size: {group_size}

Book now before they're gone!

Would you like to:
- Keep this search active to find more tee times?
- Cancel this search if you found what you need?

Log in to your account to manage your searches:
https://your-tee-time-app.com/dashboard

Happy golfing!
Bergen County Golf Tee Time Finder
"""

        # Build HTML list
        tee_times_html = ""
        for tt in tee_times:
            tee_times_html += f"""
            <div class="tee-time-card">
                <div class="detail-row">
                    <span class="detail-label">Course:</span>
                    <span>{tt['course_name']}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Date:</span>
                    <span>{tt['tee_off_date']}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Time:</span>
                    <span>{tt['tee_off_time']} ET</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Available Spots:</span>
                    <span>{tt['available_spots']}</span>
                </div>
            </div>
"""

        email_body_html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .tee-time-card {{ background: white; padding: 20px; margin: 15px 0; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .detail-row {{ display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #eee; }}
        .detail-row:last-child {{ border-bottom: none; }}
        .detail-label {{ font-weight: bold; color: #667eea; }}
        .cta-button {{ display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
        .info-box {{ background: #e8f4fd; border-left: 4px solid #667eea; padding: 15px; margin: 20px 0; border-radius: 5px; }}
        .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏌️ {count} Tee Time{plural} Available!</h1>
        </div>
        <div class="content">
            <p>{greeting}</p>
            <p>Great news! We found <strong>{count} tee time{plural}</strong> matching your search:</p>

            {tee_times_html}

            <div class="info-box">
                <strong>Your Group Size:</strong> {group_size} player{plural if group_size > 1 else ""}
            </div>

            <p style="text-align: center;">
                <a href="https://your-tee-time-app.com/dashboard" class="cta-button">View & Manage Searches</a>
            </p>

            <p style="color: #999; font-size: 14px;">
                <strong>Next Steps:</strong><br>
                • Book quickly - tee times go fast!<br>
                • Keep your search active to find more options<br>
                • Cancel your search if you found what you need
            </p>
        </div>
        <div class="footer">
            <p>Happy golfing!<br>Bergen County Golf Tee Time Finder</p>
        </div>
    </div>
</body>
</html>
"""

        # Send email notification
        email_sent = self.send_email(user_email, email_subject, email_body_text, email_body_html)

        return {
            'email_sent': email_sent
        }


# Create singleton instance
notification_service = NotificationService()
