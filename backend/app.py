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

# Get environment variables
supabase_url = os.environ.get('SUPABASE_URL')
supabase_key = os.environ.get('SUPABASE_KEY')
groq_api_key = os.environ.get('GROQ_API_KEY')

# Initialize Groq client
groq_client = Groq(api_key=groq_api_key)

# Free Supabase setup
supabase = create_client(supabase_url, supabase_key)

# Store active handoffs
ACTIVE_HANDOFFS = {}

# Load store configurations
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
    """Store conversation state in Supabase"""
    try:
        # First get existing metadata
        result = supabase.table('conversations')\
            .select('metadata')\
            .eq('id', conversation_id)\
            .execute()
        
        existing_metadata = result.data[0].get('metadata', {}) if result.data else {}
        existing_metadata[state] = value
        
        # Update with new metadata
        supabase.table('conversations')\
            .update({'metadata': existing_metadata})\
            .eq('id', conversation_id)\
            .execute()
    except Exception as e:
        print(f"Error setting state: {e}")

def get_conversation_state(conversation_id, state):
    """Get conversation state from Supabase"""
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
    """Send urgent alert to Telegram group"""
    
    keyboard = {
        "inline_keyboard": [[
            {"text": "✅ I'll handle this", "callback_data": f"handle_{customer_info['conversation_id']}"},
            {"text": "📞 Call customer", "callback_data": f"call_{customer_info['conversation_id']}"}
        ]]
    }
    
    message = f"""
🔴 **URGENT CUSTOMER SUPPORT NEEDED** 🔴
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
        return response.json()
    except Exception as e:
        print(f"Telegram error: {e}")
        return None

@app.route('/')
def home():
    return jsonify({
        'status': 'online',
        'message': 'Customer Support Agent API is running',
        'endpoints': {
            '/chat': 'POST - Send messages to the support agent',
            '/health': 'GET - Health check',
            '/order-status': 'POST - Check order status',
            '/test-groq': 'GET - Test Groq connection',
            '/telegram-webhook': 'POST - Telegram bot webhook'
        }
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})

@app.route('/telegram-webhook', methods=['POST'])
def telegram_webhook():
    """Handle Telegram button clicks"""
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
                
                # Acknowledge
                answer_url = f"https://api.telegram.org/bot8651304807:AAHfdlnbPZr0sOKHc6RuA0MHVOGoDC-hWM4/answerCallbackQuery"
                answer_data = {"callback_query_id": callback['id'], "text": "You are now handling this customer!"}
                requests.post(answer_url, json=answer_data)
        
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
        
        print(f"\n=== CHAT REQUEST ===")
        print(f"Message: {message}")
        print(f"Store ID: {store_id}")
        print(f"Telegram enabled: {store_config.get('telegram', {}).get('enabled', False)}")
        
        # Check if this conversation is waiting for contact info
        waiting_for_contact = False
        if conversation_id != 'new':
            waiting_for_contact = get_conversation_state(conversation_id, 'waiting_for_contact')
        print(f"Waiting for contact: {waiting_for_contact}")
        
        # If waiting for contact, capture the phone/email
        if waiting_for_contact and conversation_id != 'new':
            print("Capturing contact info from message")
            
            # Check if message is a phone number (Bangladesh format)
            is_phone = bool(re.match(r'^(?:\+8801|01)[3-9]\d{8}$|^\d{11}$', message))
            is_email = bool(re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', message))
            
            if is_phone or is_email:
                # Clear the waiting state
                set_conversation_state(conversation_id, 'waiting_for_contact', False)
                
                # Get the stored urgent message
                urgent_message = get_conversation_state(conversation_id, 'urgent_message') or "URGENT: Please contact me"
                
                # Send to Telegram with the contact info
                phone_number = message if is_phone else customer_phone
                email_address = message if is_email else customer_email
                
                telegram_config = store_config.get('telegram', {})
                if telegram_config.get('enabled'):
                    customer_info = {
                        'email': email_address or 'Not provided',
                        'phone': phone_number or 'Not provided',
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
                    
                    if result and result.get('ok'):
                        return jsonify({
                            'response': f"✅ Thank you! I've notified our team about your urgent request. Someone will contact you at {message} within 15 minutes. You can also call us directly at {store_config.get('contact', {}).get('primary_phone', '+8801729103420')} for immediate assistance.",
                            'conversation_id': conversation_id,
                            'handoff_initiated': True
                        })
            else:
                # Invalid contact format, ask again
                return jsonify({
                    'response': "Please provide a valid email address or phone number (e.g., 01713162795 or +8801713162795) so our team can contact you urgently.",
                    'conversation_id': conversation_id,
                    'ask_contact': True
                })
        
        # URGENCY DETECTION
        urgent_keywords = [
            'urgent', 'emergency', 'asap', 'immediately', 'quick',
            'speak to human', 'talk to person', 'real person',
            'help me now', 'right now', 'joldi', 'fast', 'quickly',
            'problem', 'issue', 'serious', 'critical', 'important',
            'talk to someone', 'human', 'person', 'agent', 'support team'
        ]
        
        is_urgent = any(keyword in message.lower() for keyword in urgent_keywords)
        
        # ORDER TRACKING detection
        order_keywords = ['order', 'track', 'where', 'parcel', 'delivery', 'shipping', 'received']
        is_order_query = any(word in message.lower() for word in order_keywords)
        
        # If urgent and Telegram enabled, set waiting state
        if is_urgent and store_config.get('telegram', {}).get('enabled'):
            if conversation_id == 'new':
                # First create conversation
                messages = [{"role": "system", "content": "Welcome to Prism The Store support."}]
                result = supabase.table('conversations')\
                    .insert({'messages': messages})\
                    .execute()
                conversation_id = result.data[0]['id']
            
            # Set state to wait for contact info
            set_conversation_state(conversation_id, 'waiting_for_contact', True)
            set_conversation_state(conversation_id, 'urgent_message', message)
            
            return jsonify({
                'response': "I understand you need assistance urgently. Please provide your email or phone number so our team can contact you right away:",
                'conversation_id': conversation_id,
                'ask_contact': True
            })
        
        # Handle order tracking (non-urgent)
        if is_order_query and not is_urgent:
            phone = store_config.get('contact', {}).get('primary_phone', '+8801729103420')
            return jsonify({
                'response': f"I'd be happy to help you with your order. For order tracking, please contact our Dhaka store at {phone}. They'll be able to provide you with the most up-to-date information on your order status. If you have any other questions or concerns, feel free to ask, and I'll do my best to assist you.",
                'conversation_id': conversation_id
            })
        
        # Normal conversation flow
        system_prompt = f"""You are a friendly, helpful customer support agent for {store_config.get('name', 'Prism The Store')}.

Brand Voice: {store_config.get('brand', {}).get('voice', 'Warm, professional, and helpful')}

Store Information:
- Name: {store_config.get('name', 'Prism The Store')}
- Phone: {store_config.get('contact', {}).get('primary_phone', '+8801729103420')}
- Email: {store_config.get('contact', {}).get('email', 'info@prismthestore.com')}
- Hours: {store_config.get('contact', {}).get('support_hours', '10 AM to 10 PM')}

Important Rules:
1. For order tracking, ALWAYS say: "For order tracking, please contact our Dhaka store at +8801729103420"
2. If someone wants to talk to a human, ALWAYS offer: "I'll connect you with human support. Please call us at +8801729103420"
3. Be warm and helpful, like a luxury boutique assistant
4. Keep responses concise but friendly

Start conversations warmly. Example opening: "Welcome to Prism. How may I assist you today?" """

        # Get conversation history
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

        # Add user message
        messages.append({"role": "user", "content": message})

        # Get AI response
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.7,
            max_tokens=200
        )

        ai_message = response.choices[0].message.content

        # Add AI response to history
        messages.append({"role": "assistant", "content": ai_message})

        # Save to Supabase
        supabase.table('conversations')\
            .update({'messages': messages})\
            .eq('id', conversation_id)\
            .execute()

        return jsonify({
            'response': ai_message,
            'conversation_id': conversation_id
        })
        
    except Exception as e:
        print(f"Chat error: {e}")
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
