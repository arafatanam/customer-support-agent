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

ACTIVE_HANDOFFS = {}
AGENT_MESSAGES = defaultdict(list)

BOT_TOKEN = "8651304807:AAHfdlnbPZr0sOKHc6RuA0MHVOGoDC-hWM4"
GROUP_CHAT_ID = -1003552610562

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
            {"text": "✅ I'll handle this", "callback_data": f"handle_{customer_info['conversation_id']}"}
        ]]
    }
    message = f"""
🔴 *URGENT CUSTOMER SUPPORT NEEDED* 🔴
━━━━━━━━━━━━━━━━━━━━━
*Store:* {store_name}
*Time:* {datetime.now().strftime('%I:%M %p, %b %d')}

*Customer contact:*
📧 Email: {customer_info.get('email', 'Not provided')}
📱 Phone: {customer_info.get('phone', 'Not provided')}
💬 Chat ID: `{customer_info['conversation_id']}`

*Their message:*
"{customer_info['message'][:200]}"
━━━━━━━━━━━━━━━━━━━━━
Press the button below to start chatting with this customer:
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
        print(f"Telegram alert response: {result}")
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

@app.route('/poll', methods=['GET'])
def poll():
    """Widget polls this endpoint every 2.5s to receive agent messages"""
    conversation_id = request.args.get('conversation_id')
    if not conversation_id:
        return jsonify({'messages': []})
    messages = AGENT_MESSAGES.pop(conversation_id, [])
    return jsonify({'messages': messages})

@app.route('/telegram-webhook', methods=['POST'])
def telegram_webhook():
    try:
        data = request.json
        print(f"Webhook received: {json.dumps(data, indent=2)}")

        # ── Button click: agent claims a customer ──
        if 'callback_query' in data:
            callback = data['callback_query']
            callback_data = callback['data']
            from_user = callback['from']
            agent_name = from_user.get('first_name', 'Support Agent')

            if callback_data.startswith('handle_'):
                conversation_id = callback_data.replace('handle_', '')

                # Save handoff state to Supabase (persists across restarts)
                set_conversation_state(conversation_id, 'handoff_active', True)
                set_conversation_state(conversation_id, 'agent_name', agent_name)
                set_conversation_state(conversation_id, 'agent_telegram_id', from_user.get('id'))

                # Save to memory for fast lookup
                ACTIVE_HANDOFFS[conversation_id] = {
                    'team_member': from_user,
                    'team_member_name': agent_name,
                    'handled_at': datetime.now().isoformat()
                }

                # Acknowledge the button tap
                requests.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery",
                    json={
                        "callback_query_id": callback['id'],
                        "text": "You are now chatting with this customer!"
                    }
                )

                # Post confirmation in the Telegram group
                requests.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                    json={
                        "chat_id": GROUP_CHAT_ID,
                        "text": (
                            f"✅ *{agent_name}* is now handling this customer.\n\n"
                            f"💬 Just type your replies here and they will appear instantly in the customer's chat widget.\n"
                            f"📌 Conversation ID: `{conversation_id}`"
                        ),
                        "parse_mode": "Markdown"
                    }
                )

                # Send first message to customer widget via polling queue
                AGENT_MESSAGES[conversation_id].append({
                    'text': f"Hi! You're now connected with {agent_name} from our support team. How can I help you?",
                    'agent': agent_name,
                    'timestamp': datetime.now().isoformat()
                })

        # ── Agent types a reply in the Telegram group ──
        elif 'message' in data:
            msg = data['message']
            chat = msg.get('chat', {})
            text = msg.get('text', '')
            from_user = msg.get('from', {})
            is_bot = from_user.get('is_bot', False)

            # Only forward real human messages from the support group
            if (
                chat.get('id') == GROUP_CHAT_ID and
                not is_bot and
                text and
                not text.startswith('/')
            ):
                agent_id = from_user.get('id')
                agent_name = from_user.get('first_name', 'Support Agent')

                # Find which conversation this agent is handling
                matched_conv_id = None

                # Check in-memory first (fast)
                for conv_id, handoff in ACTIVE_HANDOFFS.items():
                    if handoff['team_member'].get('id') == agent_id:
                        matched_conv_id = conv_id
                        break

                # Fall back to Supabase if server was restarted
                if not matched_conv_id:
                    try:
                        result = supabase.table('conversations')\
                            .select('id, metadata')\
                            .execute()
                        for row in result.data:
                            meta = row.get('metadata') or {}
                            if (meta.get('handoff_active') and
                                str(meta.get('agent_telegram_id')) == str(agent_id)):
                                matched_conv_id = row['id']
                                # Restore to memory
                                ACTIVE_HANDOFFS[matched_conv_id] = {
                                    'team_member': from_user,
                                    'team_member_name': agent_name,
                                    'handled_at': datetime.now().isoformat()
                                }
                                break
                    except Exception as e:
                        print(f"Supabase fallback error: {e}")

                if matched_conv_id:
                    # Queue message for widget to pick up via polling
                    AGENT_MESSAGES[matched_conv_id].append({
                        'text': text,
                        'agent': agent_name,
                        'timestamp': datetime.now().isoformat()
                    })
                    # Confirm delivery in Telegram
                    requests.post(
                        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                        json={
                            "chat_id": GROUP_CHAT_ID,
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

                resolved_phone = message.strip() if is_phone else customer_phone
                resolved_email = message.strip() if is_email_msg else customer_email

                if is_phone or is_email_msg or customer_phone or customer_email:
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
                                    f"✅ Thank you! Our team has been notified and will be with you shortly. "
                                    f"You can keep chatting here — a team member will join this conversation."
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
                        store_phone = store_config.get('contact', {}).get('primary_phone', '+8801729103420')
                        return jsonify({
                            'response': f"Thank you! Please call us at {store_phone} for immediate help.",
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

        # ── STEP 2: If handoff is already active, forward to Telegram ────────
        if conversation_id != 'new':
            handoff_active = get_conversation_state(conversation_id, 'handoff_active')
            if handoff_active:
                agent_name = get_conversation_state(conversation_id, 'agent_name') or 'our team'
                requests.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                    json={
                        "chat_id": GROUP_CHAT_ID,
                        "text": f"💬 *Customer says:*\n{message}",
                        "parse_mode": "Markdown"
                    }
                )
                return jsonify({
                    'response': '',
                    'conversation_id': conversation_id,
                    'handoff_active': True
                })

        # ── STEP 3: Urgency detection ─────────────────────────────────────────
        urgent_keywords = [
            'urgent', 'emergency', 'asap', 'immediately', 'quick',
            'speak to human', 'talk to person', 'real person',
            'help me now', 'right now', 'joldi', 'fast', 'quickly',
            'problem', 'issue', 'serious', 'critical', 'important',
            'talk to someone', 'human', 'person', 'agent', 'support team'
        ]
        is_urgent = any(kw in message.lower() for kw in urgent_keywords)

        if is_urgent and telegram_config.get('enabled'):
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
                    "and our team will join this chat right away:"
                ),
                'conversation_id': conversation_id,
                'ask_contact': True
            })

        # ── STEP 4: Order tracking shortcut ──────────────────────────────────
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

        # ── STEP 5: Normal AI conversation ───────────────────────────────────
        system_prompt = f"""You are a friendly customer support agent for {store_config.get('name', 'Prism The Store')}.
Brand Voice: {store_config.get('brand', {}).get('voice', 'Warm, professional, helpful')}
Phone: {store_config.get('contact', {}).get('primary_phone', '+8801729103420')}
Email: {store_config.get('contact', {}).get('email', 'info@prismthestore.com')}
Hours: {store_config.get('contact', {}).get('support_hours', '10 AM to 10 PM')}
Rules:
1. For order tracking always refer to the store phone number.
2. Keep responses concise and warm.
3. If someone wants a human, say you will connect them and ask for their contact info."""

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
