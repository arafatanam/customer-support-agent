from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from supabase import create_client
import json
from groq import Groq
from datetime import datetime
import requests
import re
from collections import defaultdict

app = Flask(__name__)
CORS(app)

supabase_url = os.environ.get('SUPABASE_URL')
supabase_key = os.environ.get('SUPABASE_KEY')
groq_api_key = os.environ.get('GROQ_API_KEY')

groq_client = Groq(api_key=groq_api_key)
supabase = create_client(supabase_url, supabase_key)

# In-memory stores
ACTIVE_HANDOFFS = {}
AGENT_MESSAGES = defaultdict(list)


# ─────────────────────────────────────────────
# CONFIG LOADER
# ─────────────────────────────────────────────

def load_store_configs():
    try:
        with open('stores_config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

STORE_CONFIGS = load_store_configs()


def get_store(store_id):
    return STORE_CONFIGS.get(store_id) or STORE_CONFIGS.get('default', {})


# ─────────────────────────────────────────────
# SUPABASE STATE HELPERS
# ─────────────────────────────────────────────

def set_conversation_state(conversation_id, state, value):
    try:
        result = supabase.table('conversations') \
            .select('metadata') \
            .eq('id', conversation_id) \
            .execute()
        existing = result.data[0].get('metadata', {}) if result.data else {}
        existing[state] = value
        supabase.table('conversations') \
            .update({'metadata': existing}) \
            .eq('id', conversation_id) \
            .execute()
    except Exception as e:
        print(f"Error setting state [{state}]: {e}")


def get_conversation_state(conversation_id, state):
    try:
        result = supabase.table('conversations') \
            .select('metadata') \
            .eq('id', conversation_id) \
            .execute()
        if result.data and result.data[0].get('metadata'):
            return result.data[0]['metadata'].get(state)
        return None
    except Exception as e:
        print(f"Error getting state [{state}]: {e}")
        return None


# ─────────────────────────────────────────────
# NOTIFICATION HELPERS
# ─────────────────────────────────────────────

def send_telegram_alert(store_config, customer_info):
    tg = store_config.get('telegram', {})
    bot_token = tg.get('bot_token')
    group_chat_id = tg.get('group_chat_id')
    store_name = store_config.get('name', 'Store')
    conv_id = customer_info['conversation_id']
    store_id = store_config.get('store_id', 'unknown')

    keyboard = {
        "inline_keyboard": [[
            {
                "text": "✅ I'll handle this",
                "callback_data": f"handle__{store_id}__{conv_id}"
            }
        ]]
    }

    message = (
        f"🔴 *URGENT CUSTOMER SUPPORT NEEDED* 🔴\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"*Store:* {store_name}\n"
        f"*Time:* {datetime.now().strftime('%I:%M %p, %b %d')}\n\n"
        f"*Customer contact:*\n"
        f"📧 Email: {customer_info.get('email', 'Not provided')}\n"
        f"📱 Phone: {customer_info.get('phone', 'Not provided')}\n"
        f"💬 Chat ID: `{conv_id}`\n\n"
        f"*Their message:*\n"
        f"\"{customer_info['message'][:200]}\"\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"Press the button below to start chatting with this customer:"
    )

    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={
                "chat_id": group_chat_id,
                "text": message,
                "parse_mode": "Markdown",
                "reply_markup": json.dumps(keyboard)
            },
            timeout=10
        )
        return resp.json()
    except Exception as e:
        print(f"Telegram error: {e}")
        return None


def send_email_alert(store_config, customer_info):
    escalation = store_config.get('escalation', {})
    to_email = escalation.get('alert_email')
    store_name = store_config.get('name', 'Store')
    conv_id = customer_info['conversation_id']

    if not to_email:
        print("Email escalation: no alert_email configured")
        return None

    subject = f"[{store_name}] Urgent Support Request"
    body = (
        f"New urgent support request from your AI chat agent.\n\n"
        f"Store: {store_name}\n"
        f"Time: {datetime.now().strftime('%I:%M %p, %b %d %Y')}\n\n"
        f"Customer contact:\n"
        f"  Email: {customer_info.get('email', 'Not provided')}\n"
        f"  Phone: {customer_info.get('phone', 'Not provided')}\n"
        f"  Chat ID: {conv_id}\n\n"
        f"Their message:\n\"{customer_info['message'][:500]}\"\n\n"
        f"---\nSent automatically by Avion AI"
    )

    if sendgrid_api_key:
        try:
            resp = requests.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={
                    "Authorization": f"Bearer {sendgrid_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "personalizations": [{"to": [{"email": to_email}]}],
                    "from": {"email": "noreply@avionai.com", "name": "Avion AI"},
                    "subject": subject,
                    "content": [{"type": "text/plain", "value": body}]
                },
                timeout=10
            )
            return {"ok": resp.status_code in (200, 202)}
        except Exception as e:
            print(f"SendGrid error: {e}")

    print(f"\n{'='*50}")
    print(f"EMAIL ALERT (no SendGrid configured)")
    print(f"To: {to_email}")
    print(f"Subject: {subject}")
    print(body)
    print(f"{'='*50}\n")
    return {"ok": True}


# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────

@app.route('/')
def home():
    return jsonify({
        'status': 'online',
        'message': 'Avion AI — Multi-Store Support API',
        'stores': list(STORE_CONFIGS.keys()),
        'endpoints': ['/chat', '/poll', '/health', '/telegram-webhook', '/test-groq']
    })


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})


@app.route('/test-groq', methods=['GET'])
def test_groq():
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": "Say 'Groq is working!'"}],
            max_tokens=10
        )
        return jsonify({'status': 'success', 'message': response.choices[0].message.content})
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/contact', methods=['POST'])
def contact_form():
    try:
        data = request.json
        name = data.get('name')
        email = data.get('email')
        company = data.get('company', '')
        message = data.get('message')

        if not name or not email or not message:
            return jsonify({'error': 'Name, email, and message are required.'}), 400

        resend_key = os.environ.get('RESEND_KEY')
        
        if not resend_key:
            print("⚠️ RESEND_KEY not set")
            return jsonify({'error': 'Email service not configured'}), 500

        headers = {
            'Authorization': f'Bearer {resend_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'from': 'onboarding@resend.dev',  # Change to your verified domain later
            'to': ['arafatanam01@gmail.com'],
            'subject': f'New Avion AI Inquiry from {name}',
            'reply_to': email,
            'html': f"""
                <h2>New Inquiry from Avion AI Website</h2>
                <p><strong>Name:</strong> {name}</p>
                <p><strong>Email:</strong> {email}</p>
                <p><strong>Company/Website:</strong> {company or 'Not provided'}</p>
                <p><strong>Message:</strong></p>
                <p>{message.replace(chr(10), '<br>')}</p>
                <hr>
                <p style="color: #666; font-size: 12px;">Sent from avionai.com contact form</p>
            """,
            'text': f"""
New Inquiry from Avion AI Website

Name: {name}
Email: {email}
Company/Website: {company or 'Not provided'}

Message:
{message}

---
Sent from avionai.com contact form
"""
        }
        
        response = requests.post(
            'https://api.resend.com/emails',
            headers=headers,
            json=payload,
            timeout=10
        )
        
        if response.status_code in (200, 201):
            print(f"✅ Contact form email sent from {email}")
            return jsonify({'success': True}), 200
        else:
            print(f"❌ Resend error: {response.status_code} - {response.text}")
            return jsonify({'error': 'Failed to send email'}), 500
            
    except Exception as e:
        print(f"Contact form error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/poll', methods=['GET'])
def poll():
    conversation_id = request.args.get('conversation_id')
    if not conversation_id:
        return jsonify({'messages': []})
    messages = AGENT_MESSAGES.pop(conversation_id, [])
    return jsonify({'messages': messages})


@app.route('/telegram-webhook', methods=['POST'])
def telegram_webhook():
    try:
        data = request.json
        print(f"Webhook received: {json.dumps(data)[:300]}")

        if 'callback_query' in data:
            callback = data['callback_query']
            callback_data = callback['data']
            from_user = callback['from']
            agent_name = from_user.get('first_name', 'Support Agent')

            if callback_data.startswith('handle__'):
                parts = callback_data.split('__', 2)
                if len(parts) != 3:
                    return "OK", 200
                _, store_id, conversation_id = parts

                store_config = get_store(store_id)
                tg = store_config.get('telegram', {})
                bot_token = tg.get('bot_token')
                group_chat_id = tg.get('group_chat_id')

                set_conversation_state(conversation_id, 'handoff_active', True)
                set_conversation_state(conversation_id, 'agent_name', agent_name)
                set_conversation_state(conversation_id, 'agent_telegram_id', from_user.get('id'))
                set_conversation_state(conversation_id, 'store_id', store_id)

                ACTIVE_HANDOFFS[conversation_id] = {
                    'team_member': from_user,
                    'team_member_name': agent_name,
                    'store_id': store_id,
                    'handled_at': datetime.now().isoformat()
                }

                requests.post(
                    f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery",
                    json={
                        "callback_query_id": callback['id'],
                        "text": "You are now chatting with this customer!"
                    }
                )

                requests.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    json={
                        "chat_id": group_chat_id,
                        "text": (
                            f"✅ *{agent_name}* is now handling this customer.\n\n"
                            f"💬 Just type your replies here and they will appear "
                            f"instantly in the customer's chat widget.\n"
                            f"📌 Conversation ID: `{conversation_id}`"
                        ),
                        "parse_mode": "Markdown"
                    }
                )

                AGENT_MESSAGES[conversation_id].append({
                    'text': f"Hi! You're now connected with {agent_name} from our support team. How can I help you?",
                    'agent': agent_name,
                    'timestamp': datetime.now().isoformat()
                })

        elif 'message' in data:
            msg = data['message']
            chat = msg.get('chat', {})
            text = msg.get('text', '')
            from_user = msg.get('from', {})
            is_bot = from_user.get('is_bot', False)

            if not is_bot and text and not text.startswith('/'):
                agent_id = from_user.get('id')
                agent_name = from_user.get('first_name', 'Support Agent')

                matched_conv_id = None
                matched_store = None

                for conv_id, handoff in ACTIVE_HANDOFFS.items():
                    if handoff['team_member'].get('id') == agent_id:
                        matched_conv_id = conv_id
                        matched_store = handoff.get('store_id')
                        break

                if not matched_conv_id:
                    try:
                        result = supabase.table('conversations').select('id, metadata').execute()
                        for row in result.data:
                            meta = row.get('metadata') or {}
                            if (meta.get('handoff_active') and
                                    str(meta.get('agent_telegram_id')) == str(agent_id)):
                                matched_conv_id = row['id']
                                matched_store = meta.get('store_id')
                                ACTIVE_HANDOFFS[matched_conv_id] = {
                                    'team_member': from_user,
                                    'team_member_name': agent_name,
                                    'store_id': matched_store,
                                    'handled_at': datetime.now().isoformat()
                                }
                                break
                    except Exception as e:
                        print(f"Supabase fallback error: {e}")

                if matched_conv_id:
                    store_config = get_store(matched_store) if matched_store else {}
                    tg = store_config.get('telegram', {})
                    bot_token = tg.get('bot_token')
                    group_chat_id = chat.get('id')

                    AGENT_MESSAGES[matched_conv_id].append({
                        'text': text,
                        'agent': agent_name,
                        'timestamp': datetime.now().isoformat()
                    })

                    if bot_token:
                        requests.post(
                            f"https://api.telegram.org/bot{bot_token}/sendMessage",
                            json={
                                "chat_id": group_chat_id,
                                "text": "✓ Delivered to customer",
                                "reply_to_message_id": msg.get('message_id')
                            }
                        )
                else:
                    print(f"No active handoff found for agent {agent_id}")

        return "OK", 200

    except Exception as e:
        print(f"Webhook error: {e}")
        import traceback
        traceback.print_exc()
        return "OK", 200


URGENT_KEYWORDS = [
    'urgent', 'emergency', 'asap', 'immediately', 'quick',
    'speak to human', 'talk to person', 'real person',
    'help me now', 'right now', 'joldi', 'fast', 'quickly',
    'problem', 'issue', 'serious', 'critical', 'important',
    'talk to someone', 'human', 'person', 'agent', 'support team'
]

ORDER_KEYWORDS = ['order', 'track', 'where', 'parcel', 'delivery', 'shipping', 'received']


def is_valid_phone(text):
    return bool(re.match(
        r'^(?:\+8801|01)[3-9]\d{8}$|^\d{11}$|^\+?[0-9\s\-\(\)]{10,15}$',
        text.strip()
    ))


def is_valid_email(text):
    return bool(re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', text.strip()))


@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        message = data.get('message', '').strip()
        conversation_id = data.get('conversation_id', 'new')
        store_id = data.get('store_id', 'default')
        customer_email = data.get('email', '').strip()
        customer_phone = data.get('phone', '').strip()

        store_config = get_store(store_id)
        tg_config = store_config.get('telegram', {})
        escalation = store_config.get('escalation', {})
        contact = store_config.get('contact', {})
        store_name = store_config.get('name', 'Our Store')
        store_phone = contact.get('primary_phone', '')

        uses_telegram = tg_config.get('enabled', False)
        uses_email = escalation.get('mode') == 'email'

        print(f"\n=== CHAT [{store_id}] ===")
        print(f"Message: {message} | conv: {conversation_id}")
        print(f"Escalation: {'telegram' if uses_telegram else 'email' if uses_email else 'none'}")

        # STEP 1: Waiting for contact info
        if conversation_id != 'new':
            waiting = get_conversation_state(conversation_id, 'waiting_for_contact')
            if waiting:
                phone_in_msg = is_valid_phone(message)
                email_in_msg = is_valid_email(message)
                resolved_phone = message if phone_in_msg else customer_phone
                resolved_email = message if email_in_msg else customer_email

                if phone_in_msg or email_in_msg or customer_phone or customer_email:
                    set_conversation_state(conversation_id, 'waiting_for_contact', False)
                    urgent_msg = get_conversation_state(
                        conversation_id, 'urgent_message'
                    ) or "URGENT: Please contact me"

                    customer_info = {
                        'email': resolved_email or 'Not provided',
                        'phone': resolved_phone or 'Not provided',
                        'message': urgent_msg,
                        'conversation_id': conversation_id
                    }
                    contact_shown = resolved_phone or resolved_email

                    alert_ok = False

                    if uses_telegram:
                        result = send_telegram_alert(store_config, customer_info)
                        alert_ok = bool(result and result.get('ok'))

                    elif uses_email:
                        result = send_email_alert(store_config, customer_info)
                        alert_ok = bool(result and result.get('ok'))

                    if alert_ok or uses_email:
                        if uses_email:
                            return jsonify({
                                'response': (
                                    f"✅ Thank you! Our team has received your request and will "
                                    f"reach out to you at {contact_shown} within 24 hours. "
                                    f"You can also email us directly at "
                                    f"{contact.get('email', '')}."
                                ),
                                'conversation_id': conversation_id,
                                'handoff_initiated': True
                            })
                        return jsonify({
                            'response': (
                                f"✅ Thank you! Our team has been notified and will be "
                                f"with you shortly. You can keep chatting here — a team "
                                f"member will join this conversation."
                            ),
                            'conversation_id': conversation_id,
                            'handoff_initiated': True
                        })
                    else:
                        return jsonify({
                            'response': (
                                f"Thank you! Please call us directly at {store_phone} "
                                f"for the fastest assistance."
                            ),
                            'conversation_id': conversation_id,
                            'handoff_initiated': True
                        })
                else:
                    return jsonify({
                        'response': (
                            "Please provide a valid phone number (e.g. 01713162795) "
                            "or email address so our team can reach you."
                        ),
                        'conversation_id': conversation_id,
                        'ask_contact': True
                    })

        # STEP 2: Handoff already active
        if conversation_id != 'new':
            handoff_active = get_conversation_state(conversation_id, 'handoff_active')
            if handoff_active and uses_telegram:
                bot_token = tg_config.get('bot_token')
                group_chat_id = tg_config.get('group_chat_id')
                requests.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    json={
                        "chat_id": group_chat_id,
                        "text": f"💬 *Customer says:*\n{message}",
                        "parse_mode": "Markdown"
                    }
                )
                return jsonify({
                    'response': '',
                    'conversation_id': conversation_id,
                    'handoff_active': True
                })

        # STEP 3: Urgency detection
        is_urgent = any(kw in message.lower() for kw in URGENT_KEYWORDS)

        if is_urgent and (uses_telegram or uses_email):
            if conversation_id == 'new':
                result = supabase.table('conversations') \
                    .insert({'messages': [{"role": "system", "content": "Support session."}], 'metadata': {}}) \
                    .execute()
                conversation_id = result.data[0]['id']

            set_conversation_state(conversation_id, 'waiting_for_contact', True)
            set_conversation_state(conversation_id, 'urgent_message', message)

            prompt_suffix = (
                "and our team will contact you shortly."
                if uses_email
                else "and a team member will join this chat right away."
            )
            return jsonify({
                'response': (
                    f"I understand this is urgent. Please share your phone number "
                    f"or email {prompt_suffix}"
                ),
                'conversation_id': conversation_id,
                'ask_contact': True
            })

        # STEP 4: Order tracking shortcut
        is_order = any(w in message.lower() for w in ORDER_KEYWORDS)
        if is_order and not is_urgent and store_phone:
            return jsonify({
                'response': (
                    f"For order tracking, please contact our store at {store_phone}. "
                    f"They'll have the most up-to-date information on your order."
                ),
                'conversation_id': conversation_id
            })

        # STEP 5: Normal AI conversation
        faqs_text = "\n".join(
            f"Q: {f['question']}\nA: {f['answer']}"
            for f in store_config.get('faqs', [])
        )
        products_text = ", ".join(store_config.get('products', {}).get('top_products', []))

        # Build system prompt using list join (avoids f-string backslash issues)
        system_prompt_parts = [
            f"You are a friendly, helpful customer support agent for {store_name}.",
            "",
            f"Brand Voice: {store_config.get('brand', {}).get('voice', 'Warm, professional, helpful')}",
            f"Store Website: {store_config.get('website', '')}",
            f"Phone: {store_phone}",
            f"Email: {contact.get('email', '')}",
            f"Support Hours: {contact.get('support_hours', '9 AM to 6 PM')}",
            "",
        ]

        if products_text:
            system_prompt_parts.append(f"Top Products: {products_text}")
            system_prompt_parts.append("")

        if faqs_text:
            system_prompt_parts.append("Frequently Asked Questions:")
            system_prompt_parts.append(faqs_text)
            system_prompt_parts.append("")

        system_prompt_parts.extend([
            "Rules:",
            "1. Keep responses concise, warm, and on-brand.",
            "2. For order tracking, always refer customers to the store phone number.",
            "3. If someone wants to speak to a human, ask for their contact details so the team can reach them.",
            "4. Never make up information not provided above.",
            f"5. Always stay in character as a support agent for {store_name}."
        ])

        system_prompt = "\n".join(system_prompt_parts)

        # Get conversation history
        if conversation_id != 'new':
            history = supabase.table('conversations') \
                .select('messages') \
                .eq('id', conversation_id) \
                .execute()
            messages = history.data[0]['messages'] if history.data else []
            if not messages:
                messages = [{"role": "system", "content": system_prompt}]
        else:
            messages = [{"role": "system", "content": system_prompt}]
            result = supabase.table('conversations') \
                .insert({'messages': messages, 'metadata': {}}) \
                .execute()
            conversation_id = result.data[0]['id']

        messages.append({"role": "user", "content": message})

        ai_resp = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.7,
            max_tokens=200
        )
        ai_message = ai_resp.choices[0].message.content
        messages.append({"role": "assistant", "content": ai_message})

        supabase.table('conversations') \
            .update({'messages': messages}) \
            .eq('id', conversation_id) \
            .execute()

        return jsonify({'response': ai_message, 'conversation_id': conversation_id})

    except Exception as e:
        print(f"Chat error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/order-status', methods=['POST'])
def order_status():
    try:
        order_number = request.json.get('order_number')
        return jsonify({
            'status': 'shipped',
            'estimated_delivery': '3-5 business days',
            'order_number': order_number,
            'note': 'For detailed tracking please contact the store directly.'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
