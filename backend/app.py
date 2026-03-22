from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from supabase import create_client
import json
from groq import Groq
from datetime import datetime
import requests
import re

app = Flask(__name__)
CORS(app)

supabase_url = os.environ.get('SUPABASE_URL')
supabase_key = os.environ.get('SUPABASE_KEY')
groq_api_key = os.environ.get('GROQ_API_KEY')

groq_client = Groq(api_key=groq_api_key)
supabase = create_client(supabase_url, supabase_key)

ACTIVE_HANDOFFS = {}

def load_store_configs():
    try:
        with open('stores_config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "default": {
                "name": "Demo Store",
                "brand": {"voice": "luxury"},
                "policies": {},
                "products": {"top_products": []},
                "contact": {"primary_phone": "+8801729103420", "email": "info@prismthestore.com"},
                "faqs": [],
                "escalation": {"escalation_phrase": "I'll connect you with human support."}
            }
        }

STORE_CONFIGS = load_store_configs()

def set_conversation_state(conversation_id, state, value):
    try:
        result = supabase.table('conversations')\
            .select('metadata')\
            .eq('id', conversation_id)\
            .execute()
        existing_metadata = result.data[0].get('metadata', {}) if result.data else {}
        existing_metadata[state] = value
        supabase.table('conversations')\
            .update({'metadata': existing_metadata})\
            .eq('id', conversation_id)\
            .execute()
    except Exception as e:
        print(f"Error setting state: {e}")

def get_conversation_state(conversation_id, state):
    try:
        result = supabase.table('conversations')\
            .select('metadata')\
            .eq('id', conversation_id)\
            .execute()
        if result.data and result.data[0].get('metadata'):
            return result.data[0]['metadata'].get(state)
        return None
    except Exception as e:
        print(f"Error getting state: {e}")
        return None

def send_telegram_alert(bot_token, group_chat_id, customer_info, store_name, store_phone):
    keyboard = {
        "inline_keyboard": [[
            {"text": "✅ I'll handle this", "callback_data": f"handle_{customer_info['conversation_id']}"},
            {"text": "📞 Call customer", "callback_data": f"call_{customer_info['conversation_id']}"}
        ]]
    }
    message = f"""
🔴 *URGENT CUSTOMER SUPPORT NEEDED* 🔴
━━━━━━━━━━━━━━━━━━━━━
*Store:* {store_name}
*Time:* {datetime.now().strftime('%I:%M %p, %b %d')}

*Customer:*
📧 Email: {customer_info.get('email', 'Not provided')}
📱 Phone: {customer_info.get('phone', 'Not provided')}
💬 Chat ID: `{customer_info['conversation_id']}`

*Issue:*
"{customer_info['message'][:200]}"
━━━━━━━━━━━━━━━━━━━━━
Click below to handle this customer:
"""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        "chat_id": group_chat_id,
        "text": message,
        "parse_mode": "Markdown",
        "reply_markup": json.dumps(keyboard)
    }
    try:
        response = requests.post(url, json=data, timeout=10)
        result = response.json()
        print(f"Telegram response: {result}")
        return result
    except Exception as e:
        print(f"Telegram error: {e}")
        return None

@app.route('/')
def home():
    return jsonify({'status': 'online', 'message': 'Customer Support Agent API is running'})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})

@app.route('/telegram-webhook', methods=['POST'])
def telegram_webhook():
    try:
        data = request.json
        if 'callback_query' in data:
            callback = data['callback_query']
            callback_data = callback['data']
            from_user = callback['from']
            if callback_data.startswith('handle_'):
                conversation_id = callback_data.replace('handle_', '')
                ACTIVE_HANDOFFS[conversation_id] = {
                    'team_member': from_user,
                    'team_member_name': from_user.get('first_name', 'Team Member'),
                    'handled_at': datetime.now().isoformat()
                }
                answer_url = f"https://api.telegram.org/bot8651304807:AAHfdlnbPZr0sOKHc6RuA0MHVOGoDC-hWM4/answerCallbackQuery"
                requests.post(answer_url, json={
                    "callback_query_id": callback['id'],
                    "text": "You are now handling this customer!"
                })
        return "OK", 200
    except Exception as e:
        print(f"Webhook error: {e}")
        return "OK", 200

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        message = data.get('message', '')
        conversation_id = data.get('conversation_id', 'new')
        store_id = data.get('store_id', 'default')
        customer_email = data.get('email', '')
        customer_phone = data.get('phone', '')

        store_config = STORE_CONFIGS.get(store_id, STORE_CONFIGS.get('default', {}))
        telegram_config = store_config.get('telegram', {})

        print(f"\n=== CHAT REQUEST ===")
        print(f"Message: {message}")
        print(f"Email: {customer_email} | Phone: {customer_phone}")
        print(f"Conversation ID: {conversation_id}")

        # ── STEP 1: If waiting for contact info ──────────────────────────────
        # This fires when the customer's message IS the phone/email they typed
        if conversation_id != 'new':
            waiting_for_contact = get_conversation_state(conversation_id, 'waiting_for_contact')
            print(f"Waiting for contact: {waiting_for_contact}")

            if waiting_for_contact:
                is_phone = bool(re.match(
                    r'^(?:\+8801|01)[3-9]\d{8}$|^\d{11}$|^\+?[0-9\s\-\(\)]{10,15}$',
                    message.strip()
                ))
                is_email_msg = bool(re.match(
                    r'^[^\s@]+@[^\s@]+\.[^\s@]+$',
                    message.strip()
                ))

                # Also accept contact info passed in the email/phone fields
                # (frontend may send it either way)
                resolved_phone = message.strip() if is_phone else customer_phone
                resolved_email = message.strip() if is_email_msg else customer_email

                if is_phone or is_email_msg or customer_phone or customer_email:
                    # Clear waiting state
                    set_conversation_state(conversation_id, 'waiting_for_contact', False)

                    urgent_message = get_conversation_state(
                        conversation_id, 'urgent_message'
                    ) or "URGENT: Please contact me"

                    if telegram_config.get('enabled'):
                        customer_info = {
                            'email': resolved_email or 'Not provided',
                            'phone': resolved_phone or 'Not provided',
                            'message': urgent_message,
                            'conversation_id': conversation_id
                        }
                        result = send_telegram_alert(
                            telegram_config['bot_token'],
                            telegram_config['group_chat_id'],
                            customer_info,
                            store_config.get('name', 'Prism The Store'),
                            store_config.get('contact', {}).get('primary_phone', '+8801729103420')
                        )

                        contact_shown = resolved_phone or resolved_email
                        store_phone = store_config.get('contact', {}).get('primary_phone', '+8801729103420')

                        if result and result.get('ok'):
                            return jsonify({
                                'response': (
                                    f"✅ Thank you! Our team has been notified and will contact you "
                                    f"at {contact_shown} within 15 minutes. "
                                    f"For immediate help, call us at {store_phone}."
                                ),
                                'conversation_id': conversation_id,
                                'handoff_initiated': True
                            })
                        else:
                            # Telegram call failed — still tell them to call
                            return jsonify({
                                'response': (
                                    f"Thank you! Please call us directly at {store_phone} "
                                    f"for the fastest assistance."
                                ),
                                'conversation_id': conversation_id,
                                'handoff_initiated': True
                            })
                    else:
                        store_phone = store_config.get('contact', {}).get('primary_phone', '+8801729103420')
                        return jsonify({
                            'response': f"Thank you! Please call us at {store_phone} for immediate help.",
                            'conversation_id': conversation_id,
                            'handoff_initiated': True
                        })
                else:
                    # Still invalid — ask again
                    return jsonify({
                        'response': (
                            "Please provide a valid phone number (e.g. 01713162795) "
                            "or email address so our team can reach you."
                        ),
                        'conversation_id': conversation_id,
                        'ask_contact': True
                    })

        # ── STEP 2: Urgency detection ────────────────────────────────────────
        urgent_keywords = [
            'urgent', 'emergency', 'asap', 'immediately', 'quick',
            'speak to human', 'talk to person', 'real person',
            'help me now', 'right now', 'joldi', 'fast', 'quickly',
            'problem', 'issue', 'serious', 'critical', 'important',
            'talk to someone', 'human', 'person', 'agent', 'support team'
        ]
        is_urgent = any(kw in message.lower() for kw in urgent_keywords)

        if is_urgent and telegram_config.get('enabled'):
            # Create conversation if new
            if conversation_id == 'new':
                result = supabase.table('conversations')\
                    .insert({'messages': [{"role": "system", "content": "Support session."}]})\
                    .execute()
                conversation_id = result.data[0]['id']

            set_conversation_state(conversation_id, 'waiting_for_contact', True)
            set_conversation_state(conversation_id, 'urgent_message', message)

            return jsonify({
                'response': (
                    "I understand this is urgent. Please share your phone number or email "
                    "and our team will contact you right away:"
                ),
                'conversation_id': conversation_id,
                'ask_contact': True
            })

        # ── STEP 3: Order tracking shortcut ─────────────────────────────────
        order_keywords = ['order', 'track', 'where', 'parcel', 'delivery', 'shipping', 'received']
        if any(w in message.lower() for w in order_keywords) and not is_urgent:
            phone = store_config.get('contact', {}).get('primary_phone', '+8801729103420')
            return jsonify({
                'response': (
                    f"For order tracking, please contact our Dhaka store at {phone}. "
                    "They'll have the most up-to-date information on your order."
                ),
                'conversation_id': conversation_id
            })

        # ── STEP 4: Normal AI conversation ───────────────────────────────────
        system_prompt = f"""You are a friendly customer support agent for {store_config.get('name', 'Prism The Store')}.
Brand Voice: {store_config.get('brand', {}).get('voice', 'Warm, professional, helpful')}
Phone: {store_config.get('contact', {}).get('primary_phone', '+8801729103420')}
Email: {store_config.get('contact', {}).get('email', 'info@prismthestore.com')}
Hours: {store_config.get('contact', {}).get('support_hours', '10 AM to 10 PM')}
Rules:
1. For order tracking always refer to the store phone number.
2. Keep responses concise and warm.
3. If someone wants a human, say you'll connect them and ask for their contact info."""

        if conversation_id != 'new':
            history = supabase.table('conversations')\
                .select('messages')\
                .eq('id', conversation_id)\
                .execute()
            messages = history.data[0]['messages'] if history.data else []
        else:
            messages = [{"role": "system", "content": system_prompt}]
            result = supabase.table('conversations')\
                .insert({'messages': messages})\
                .execute()
            conversation_id = result.data[0]['id']

        messages.append({"role": "user", "content": message})

        ai_response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.7,
            max_tokens=200
        )
        ai_message = ai_response.choices[0].message.content
        messages.append({"role": "assistant", "content": ai_message})

        supabase.table('conversations')\
            .update({'messages': messages})\
            .eq('id', conversation_id)\
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
            'note': 'For detailed tracking, please call +8801729103420'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
