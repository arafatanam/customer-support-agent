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

# Environment variables
supabase_url = os.environ.get('SUPABASE_URL')
supabase_key = os.environ.get('SUPABASE_KEY')
groq_api_key = os.environ.get('GROQ_API_KEY')

# Initialize clients
groq_client = Groq(api_key=groq_api_key)
supabase = create_client(supabase_url, supabase_key)

# In-memory stores for active handoffs and agent messages
ACTIVE_HANDOFFS = {}
AGENT_MESSAGES = defaultdict(list)

# CONFIGURATION


def load_store_configs():
    try:
        with open('stores_config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


STORE_CONFIGS = load_store_configs()


def get_store(store_id):
    return STORE_CONFIGS.get(store_id) or STORE_CONFIGS.get('default', {})

# SUPABASE HELPERS (Conversation State)


def set_conversation_state(conversation_id, state, value):
    """Store metadata like waiting_for_contact, handoff_active, etc."""
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
    """Retrieve metadata for a conversation"""
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


def get_conversation_history(conversation_id):
    """Get full conversation history for Telegram alert"""
    try:
        result = supabase.table('conversations') \
            .select('messages') \
            .eq('id', conversation_id) \
            .execute()
        if result.data and result.data[0].get('messages'):
            messages = result.data[0]['messages']
            history = ""
            for msg in messages[1:]:  # Skip system prompt
                role = msg.get('role')
                content = msg.get('content', '')[:300]
                if role == 'user':
                    history += f"\n👤 Customer: {content}"
                elif role == 'assistant':
                    history += f"\n🤖 AI: {content}"
            return history
        return "\n(No conversation history)"
    except Exception as e:
        print(f"Error fetching history: {e}")
        return "\n(Unable to fetch history)"

# TELEGRAM ALERT (with full conversation history)


def send_telegram_alert(store_config, customer_info, conversation_history):
    """Send urgent alert to Telegram group with full chat history"""
    tg = store_config.get('telegram', {})
    bot_token = tg.get('bot_token')
    group_chat_id = tg.get('group_chat_id')
    store_name = store_config.get('name', 'Store')
    conv_id = customer_info['conversation_id']
    store_id = store_config.get('store_id', 'unknown')

    keyboard = {
        "inline_keyboard": [[
            {"text": "✅ I'll handle this",
                "callback_data": f"handle__{store_id}__{conv_id}"}
        ]]
    }

    message = (
        f"*URGENT CUSTOMER SUPPORT NEEDED*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"*Store:* {store_name}\n"
        f"*Time:* {datetime.now().strftime('%I:%M %p, %b %d')}\n\n"
        f"*Customer Email:* {customer_info.get('email', 'Not provided')}\n\n"
        f"*Conversation History:*\n"
        f"```{conversation_history}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"*Latest Message:*\n"
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

# VALIDATION HELPERS


def is_valid_email(text):
    return bool(re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', text.strip()))

# HEALTH & TEST ENDPOINTS


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


@app.route('/poll', methods=['GET'])
def poll():
    """Widget polls here for agent messages during handoff"""
    conversation_id = request.args.get('conversation_id')
    if not conversation_id:
        return jsonify({'messages': []})
    messages = AGENT_MESSAGES.pop(conversation_id, [])
    return jsonify({'messages': messages})

# TELEGRAM WEBHOOK (Handles button clicks and agent replies)


@app.route('/telegram-webhook', methods=['POST'])
def telegram_webhook():
    try:
        data = request.json

        # Handle button click: agent claims a customer
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

                # Mark handoff as active
                set_conversation_state(conversation_id, 'handoff_active', True)
                set_conversation_state(
                    conversation_id, 'agent_name', agent_name)
                set_conversation_state(
                    conversation_id, 'agent_telegram_id', from_user.get('id'))

                ACTIVE_HANDOFFS[conversation_id] = {
                    'team_member': from_user,
                    'team_member_name': agent_name,
                    'store_id': store_id,
                    'handled_at': datetime.now().isoformat()
                }

                # Acknowledge button press
                requests.post(
                    f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery",
                    json={
                        "callback_query_id": callback['id'],
                        "text": "You are now chatting with this customer!"
                    }
                )

                # Send confirmation to group
                requests.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    json={
                        "chat_id": group_chat_id,
                        "text": f"*{agent_name}* is now handling this customer.\n\n💬 Type your replies here — they'll appear in the customer's chat widget.\n📌 Conversation ID: `{conversation_id}`",
                        "parse_mode": "Markdown"
                    }
                )

                # Notify customer that an agent joined
                AGENT_MESSAGES[conversation_id].append({
                    'text': f"Hi! You're now connected with {agent_name} from our support team. How can I help you?",
                    'agent': agent_name,
                    'timestamp': datetime.now().isoformat()
                })

        # Handle agent reply message in Telegram group
        elif 'message' in data:
            msg = data['message']
            chat = msg.get('chat', {})
            text = msg.get('text', '')
            from_user = msg.get('from', {})
            is_bot = from_user.get('is_bot', False)

            if not is_bot and text and not text.startswith('/'):
                agent_id = from_user.get('id')
                agent_name = from_user.get('first_name', 'Support Agent')

                # Find which conversation this agent is handling
                matched_conv_id = None
                matched_store = None

                for conv_id, handoff in ACTIVE_HANDOFFS.items():
                    if handoff['team_member'].get('id') == agent_id:
                        matched_conv_id = conv_id
                        matched_store = handoff.get('store_id')
                        break

                if matched_conv_id:
                    store_config = get_store(
                        matched_store) if matched_store else {}
                    tg = store_config.get('telegram', {})
                    bot_token = tg.get('bot_token')
                    group_chat_id = chat.get('id')

                    # Send message to customer's widget
                    AGENT_MESSAGES[matched_conv_id].append({
                        'text': text,
                        'agent': agent_name,
                        'timestamp': datetime.now().isoformat()
                    })

                    # Confirm delivery in Telegram
                    if bot_token:
                        requests.post(
                            f"https://api.telegram.org/bot{bot_token}/sendMessage",
                            json={
                                "chat_id": group_chat_id,
                                "text": "✓ Delivered to customer",
                                "reply_to_message_id": msg.get('message_id')
                            }
                        )

        return "OK", 200

    except Exception as e:
        print(f"Webhook error: {e}")
        return "OK", 200


# MAIN CHAT ENDPOINT
URGENT_KEYWORDS = [
    'urgent', 'emergency', 'asap', 'immediately', 'quick',
    'speak to human', 'talk to person', 'real person', 'help me now',
    'right now', 'fast', 'quickly', 'problem', 'issue', 'serious',
    'critical', 'important', 'talk to someone', 'human', 'person',
    'agent', 'support team', 'contact someone', 'need help'
]


@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        message = data.get('message', '').strip()
        conversation_id = data.get('conversation_id', 'new')
        store_id = data.get('store_id', 'default')
        customer_email = data.get('email', '').strip()

        store_config = get_store(store_id)
        tg_config = store_config.get('telegram', {})
        contact = store_config.get('contact', {})
        store_name = store_config.get('name', 'Our Store')
        store_phone = contact.get('primary_phone', '')
        uses_telegram = tg_config.get('enabled', False)

        print(f"\n=== CHAT [{store_id}] ===")
        print(f"Message: {message}")
        print(f"Telegram enabled: {uses_telegram}")

        # STEP 1: Check if waiting for email
        if conversation_id != 'new':
            waiting = get_conversation_state(
                conversation_id, 'waiting_for_contact')
            if waiting:
                print("Waiting for email - processing...")
                email_in_msg = is_valid_email(message)

                if email_in_msg:
                    set_conversation_state(
                        conversation_id, 'waiting_for_contact', False)
                    urgent_msg = get_conversation_state(
                        conversation_id, 'urgent_message') or "URGENT: Please contact me"

                    # Get full conversation history
                    conversation_history = get_conversation_history(
                        conversation_id)

                    customer_info = {
                        'email': message,
                        'message': urgent_msg,
                        'conversation_id': conversation_id
                    }

                    if uses_telegram:
                        result = send_telegram_alert(
                            store_config, customer_info, conversation_history)
                        if result and result.get('ok'):
                            return jsonify({
                                'response': f"✅ Thank you! Our team has been notified and will join this chat shortly.",
                                'conversation_id': conversation_id,
                                'handoff_initiated': True
                            })
                else:
                    # Return a proper response asking for email again
                    return jsonify({
                        'response': "Please share your email address so we can reach you if needed.",
                        'conversation_id': conversation_id,
                        'ask_contact': True
                    })

        # STEP 2: Check if handoff already active
        if conversation_id != 'new':
            handoff_active = get_conversation_state(
                conversation_id, 'handoff_active')
            if handoff_active and uses_telegram:
                bot_token = tg_config.get('bot_token')
                group_chat_id = tg_config.get('group_chat_id')
                if bot_token and group_chat_id:
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
        print(f"Is urgent: {is_urgent}")

        # Handle urgent request (EMAIL ONLY)
        if is_urgent and uses_telegram:
            print("URGENT DETECTED - initiating handoff flow")

            if conversation_id == 'new':
                result = supabase.table('conversations') \
                    .insert({'messages': [{"role": "system", "content": "Support session."}], 'metadata': {}}) \
                    .execute()
                conversation_id = result.data[0]['id']

            set_conversation_state(
                conversation_id, 'waiting_for_contact', True)
            set_conversation_state(conversation_id, 'urgent_message', message)

            return jsonify({
                'response': "Our team will be with you shortly. In case we can't reach you in time, could you please share your email address?",
                'conversation_id': conversation_id,
                'ask_contact': True
            })

        # STEP 4: Normal AI conversation
        faqs_text = "\n".join(
            f"Q: {f['question']}\nA: {f['answer']}"
            for f in store_config.get('faqs', [])
        )
        products_text = ", ".join(store_config.get(
            'products', {}).get('top_products', []))

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
            "3. If someone asks for urgent help, ask for their EMAIL ONLY. Say: 'Our team will be with you shortly. In case we can't reach you in time, could you please share your email address?'",
            "4. Never ask for phone numbers.",
            f"5. Always stay in character as a support agent for {store_name}.",
            "6. Use markdown formatting: **bold** for emphasis, and line breaks for readability."
        ])

        system_prompt = "\n".join(system_prompt_parts)

        # Get or create conversation
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
            max_tokens=250
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
