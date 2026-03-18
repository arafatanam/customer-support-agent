import os
import time
import pickle
import threading
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WhatsAppHandler:
    def __init__(self):
        self.driver = None
        self.is_running = False
        self.session_file = "whatsapp_session.pkl"
        self.group_names = {}  # Store group names by store_id

    def start_driver(self):
        """Start Chrome driver for WhatsApp Web"""
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")  # Run in background
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")

        # Keep session
        options.add_argument("--user-data-dir=./chrome_profile")

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.get("https://web.whatsapp.com")

        # Load saved session if exists
        if os.path.exists(self.session_file):
            with open(self.session_file, "rb") as f:
                cookies = pickle.load(f)
                for cookie in cookies:
                    self.driver.add_cookie(cookie)
            self.driver.refresh()

        self.is_running = True

        # Start monitoring thread for replies
        threading.Thread(target=self.monitor_replies, daemon=True).start()

        return self.driver

    def save_session(self):
        """Save WhatsApp session to avoid QR scan every time"""
        with open(self.session_file, "wb") as f:
            pickle.dump(self.driver.get_cookies(), f)
        logger.info("WhatsApp session saved")

    def wait_for_login(self):
        """Wait for user to scan QR code (first time only)"""
        try:
            WebDriverWait(self.driver, 60).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//div[@contenteditable="true"]'))
            )
            self.save_session()
            logger.info("WhatsApp login successful")
            return True
        except:
            logger.error("Login timeout")
            return False

    def create_or_get_group(self, store_id, group_name, member_phones):
        """Create a WhatsApp group for store team"""
        # Search for first member to start group
        search_box = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, '//div[@contenteditable="true"]'))
        )

        # Click new chat
        new_chat = self.driver.find_element(
            By.XPATH, '//div[@title="New chat"]')
        new_chat.click()
        time.sleep(1)

        # Search for first member
        search = self.driver.find_element(
            By.XPATH, '//div[@contenteditable="true"]')
        search.send_keys(member_phones[0])
        time.sleep(2)

        # Select contact
        contact = self.driver.find_element(By.XPATH, '//div[@class="_ak8q"]')
        contact.click()
        time.sleep(1)

        # Click next
        next_btn = self.driver.find_element(
            By.XPATH, '//span[@data-icon="arrow-forward"]')
        next_btn.click()
        time.sleep(1)

        # Set group name
        group_name_input = self.driver.find_element(
            By.XPATH, '//div[@contenteditable="true"]')
        group_name_input.send_keys(group_name)
        time.sleep(1)

        # Create group
        create_btn = self.driver.find_element(
            By.XPATH, '//span[@data-icon="check"]')
        create_btn.click()
        time.sleep(3)

        # Add other members
        for phone in member_phones[1:]:
            self.add_member_to_group(phone)

        # Store group ID
        self.group_names[store_id] = group_name
        logger.info(f"Group {group_name} created for {store_id}")

        return group_name

    def add_member_to_group(self, phone):
        """Add member to existing group"""
        # Click group info
        group_info = self.driver.find_element(
            By.XPATH, '//div[@title="Group info"]')
        group_info.click()
        time.sleep(1)

        # Click add member
        add_member = self.driver.find_element(
            By.XPATH, '//span[@data-icon="add"]')
        add_member.click()
        time.sleep(1)

        # Search and add
        search = self.driver.find_element(
            By.XPATH, '//div[@contenteditable="true"]')
        search.send_keys(phone)
        time.sleep(2)

        # Select contact
        contact = self.driver.find_element(By.XPATH, '//div[@class="_ak8q"]')
        contact.click()
        time.sleep(1)

        # Confirm add
        confirm = self.driver.find_element(
            By.XPATH, '//span[@data-icon="check"]')
        confirm.click()
        time.sleep(1)

    def send_urgent_alert(self, store_id, group_name, customer_info):
        """Send urgent alert to WhatsApp group"""
        try:
            # Search for group
            search_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//div[@contenteditable="true"]'))
            )
            search_box.clear()
            search_box.send_keys(group_name)
            time.sleep(2)

            # Click on group
            group = self.driver.find_element(
                By.XPATH, f'//span[@title="{group_name}"]')
            group.click()
            time.sleep(2)

            # Format message
            message = f"""
🔴 *URGENT CUSTOMER HELP NEEDED* 🔴
━━━━━━━━━━━━━━━━━━━━━
*Store:* {customer_info['store_name']}
*Customer:* {customer_info['email']}
*Time:* {customer_info['time']}

*Message:* 
"{customer_info['urgent_message']}"

━━━━━━━━━━━━━━━━━━━━━
*To help:*
1. Reply "TAKEN" in group
2. Contact customer via:
   📧 Email: {customer_info['email']}
   📞 Phone: {customer_info.get('phone', 'Not provided')}

*First to reply TAKEN handles this customer*
━━━━━━━━━━━━━━━━━━━━━
"""

            # Find message box and send
            message_box = self.driver.find_element(
                By.XPATH, '//div[@contenteditable="true"][@spellcheck="true"]')
            message_box.send_keys(message)
            message_box.send_keys(Keys.ENTER)

            logger.info(f"Urgent alert sent to {group_name}")

            # Store for reply tracking
            self.track_message(
                store_id, customer_info['conversation_id'], message)

            return True

        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
            return False

    def monitor_replies(self):
        """Monitor group for replies (who took the customer)"""
        while self.is_running:
            try:
                # Check for new messages
                messages = self.driver.find_elements(
                    By.XPATH, '//div[contains(@class, "message-in")]')

                for msg in messages[-5:]:  # Check last 5 messages
                    msg_text = msg.text
                    if "TAKEN" in msg_text.upper():
                        # Find who sent it
                        sender = msg.find_element(
                            By.XPATH, './/span[@dir="auto"]').text

                        # Notify system that someone is handling
                        self.notify_handoff(sender, msg_text)

            except:
                pass
            time.sleep(5)

    def notify_handoff(self, sender, message):
        """Send confirmation back to customer"""
        # This will be called from app.py
        logger.info(f"{sender} is handling customer: {message}")


# Global instance
whatsapp_handler = WhatsAppHandler()
