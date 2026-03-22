from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from supabase import create_client
import json
from groq import Groq
from datetime import datetime
import requests
import urllib.parse

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

# Store active handoffs {conversation_id: {team_member, handled_at, chat_id}}
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
                "brand": {"voice": "friendly"},
                "policies": {},
                "products": {"top_products": []},
                "contact": {},
                "faqs": [],
                "escalation": {"escalation_phrase": "I'll connect you with human support."}
            }
        }

STORE_CONFIGS = load_store_configs()

def send_telegram_alert(bot_token, group_chat_id, customer_info, store_name, store_phone):
    """Send urgent alert to Telegram group with inline buttons"""
    
    # Create inline keyboard buttons
    keyboard = {
        "inline_keyboard": [[
            {
                "text": "✅ I'll handle this",
                "callback_data": f"handle_{customer_info['conversation_id']}"
            },
            {
                "text": "📞 Call customer",
                "callback_data": f"call_{customer_info['conversation_id']}"
            }
        ]]
    }
    
    # Format message
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
    
    # Send to Telegram
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

def send_telegram_confirmation(bot_token, chat_id, message):
    """Send confirmation message to Telegram"""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=data, timeout=10)
    except Exception as e:
        print(f"Telegram confirmation error: {e}")

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
        
        # Check if it's a callback query (button click)
        if 'callback_query' in data:
            callback = data['callback_query']
            callback_data = callback['data']
            from_user = callback['from']
            message_id = callback['message']['message_id']
            chat_id = callback['message']['chat']['id']
            
            # Extract conversation_id from callback data
            if callback_data.startswith('handle_'):
                conversation_id = callback_data.replace('handle_', '')
                
                # Store who is handling this customer
                ACTIVE_HANDOFFS[conversation_id] = {
                    'team_member': from_user,
                    'team_member_name': from_user.get('first_name', 'Team Member'),
                    'handled_at': datetime.now().isoformat(),
                    'chat_id': chat_id,
                    'message_id': message_id
                }
                
                # Acknowledge the callback
                answer_url = f"https://api.telegram.org/bot{get_bot_token_for_store(conversation_id)}/answerCallbackQuery"
                answer_data = {
                    "callback_query_id": callback['id'],
                    "text": f"You are now handling this customer! They will be contacted.",
                    "show_alert": False
                }
                requests.post(answer_url, json=answer_data)
                
                # Update the message in group to show who is handling
                edit_url = f"https://api.telegram.org/bot{get_bot_token_for_store(conversation_id)}/editMessageText"
                original_text = callback['message']['text']
                edit_data = {
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": original_text + f"\n\n✅ **Being handled by: {from_user.get('first_name', 'Team Member')}**",
                    "parse_mode": "Markdown"
                }
                requests.post(edit_url, json=edit_data)
                
                # Send confirmation to group that handoff is complete
                confirm_message = f"✅ {from_user.get('first_name', 'Team Member')} is now handling customer {conversation_id}"
                send_telegram_confirmation(get_bot_token_for_store(conversation_id), chat_id, confirm_message)
                
            elif callback_data.startswith('call_'):
                conversation_id = callback_data.replace('call_', '')
                
                # Get store phone number from config
                store_config = get_store_config_by_conversation(conversation_id)
                phone = store_config.get('contact', {}).get('primary_phone', '+8801729103420')
                
                # Show phone number to team member
                answer_url = f"https://api.telegram.org/bot{get_bot_token_for_store(conversation_id)}/answerCallbackQuery"
                answer_data = {
                    "callback_query_id": callback['id'],
                    "text": f"Customer phone: {phone}",
                    "show_alert": True
                }
                requests.post(answer_url, json=answer_data)
        
        return "OK", 200
    except Exception as e:
        print(f"Telegram webhook error: {e}")
        return "OK", 200

def get_bot_token_for_store(conversation_id):
    """Get bot token for a conversation"""
    # For now, return Prism's bot token
    return "8651304807:AAHfdlnbPZr0sOKHc6RuA0MHVOGoDC-hWM4"

def get_store_config_by_conversation(conversation_id):
    """Get store config for a conversation"""
    # For now, return Prism config
    return STORE_CONFIGS.get('prism_the_store_001', {})

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
        
        # Check if this conversation is already being handled by human
        if conversation_id in ACTIVE_HANDOFFS and conversation_id != 'new':
            handoff_info = ACTIVE_HANDOFFS[conversation_id]
            return jsonify({
                'response': f"✅ Our team member **{handoff_info['team_member_name']}** is now helping you. They will respond shortly. You can also call us at {store_config.get('contact', {}).get('primary_phone', '+8801729103420')} if urgent.",
                'conversation_id': conversation_id,
                'handoff_active': True
            })
        
        # URGENCY DETECTION
        urgent_keywords = [
            'urgent', 'emergency', 'asap', 'immediately', 'quick',
            'speak to human', 'talk to person', 'real person',
            'help me now', 'right now', 'instant', 'immediate',
            'joldi', 'fast', 'quickly', 'problem', 'issue',
            'complaint', 'frustrated', 'angry', 'not working',
            'broken', 'wrong item', 'incorrect', 'mistake',
            'not happy', 'disappointed', 'terrible', 'worst',
            'track order', 'where is my order', 'delivery', 'shipping status'
        ]
        
        is_urgent = any(keyword in message.lower() for keyword in urgent_keywords)
        
        # If urgent and Telegram is enabled
        if is_urgent and store_config.get('telegram', {}).get('enabled'):
            
            # If no contact info provided, ask for it
            if not customer_email and not customer_phone:
                return jsonify({
                    'response': "I understand this is urgent! To connect you with our team immediately, please provide your email or phone number so someone can reach you:",
                    'conversation_id': conversation_id,
                    'ask_contact': True
                })
            
            # Get Telegram config
            telegram_config = store_config['telegram']
            bot_token = telegram_config['bot_token']
            group_chat_id = telegram_config['group_chat_id']
            
            # Send to Telegram group
            customer_info = {
                'email': customer_email or 'Not provided',
                'phone': customer_phone or 'Not provided',
                'message': message,
                'conversation_id': conversation_id
            }
            
            result = send_telegram_alert(
                bot_token,
                group_chat_id,
                customer_info,
                store_config.get('name', 'Prism The Store'),
                store_config.get('contact', {}).get('primary_phone', '+8801729103420')
            )
            
            if result and result.get('ok'):
                return jsonify({
                    'response': f"✅ **Our team has been notified urgently!** Someone from {store_config.get('name', 'Prism')} will contact you within {telegram_config.get('response_time', '15 minutes')} at {customer_email or customer_phone}. You can also call us directly at {store_config.get('contact', {}).get('primary_phone', '+8801729103420')} for immediate help.",
                    'conversation_id': conversation_id,
                    'handoff_initiated': True
                })
            else:
                # Fallback if Telegram fails
                return jsonify({
                    'response': f"I'm trying to reach our team urgently. Please call us directly at {store_config.get('contact', {}).get('primary_phone', '+8801729103420')} for immediate help.",
                    'conversation_id': conversation_id,
                    'handoff_fallback': True
                })
        
        # Create store-specific system prompt
        system_prompt = f"""You are a luxury customer support agent for {store_config.get('name', 'Prism The Store')}.

Brand Voice: {store_config.get('brand', {}).get('voice', 'Luxury & Premium')}

Store Policies:
- Privacy: {store_config.get('policies', {}).get('privacy', 'Available on website')}
- Terms: {store_config.get('policies', {}).get('terms', 'Available on website')}
- Shipping: {store_config.get('policies', {}).get('shipping', 'International shipping available')}
- Returns: {store_config.get('policies', {}).get('returns', 'Contact store for returns')}

Products: {', '.join(store_config.get('products', {}).get('top_products', []))}

Contact Information:
- Email: {store_config.get('contact', {}).get('email', 'info@prismthestore.com')}
- Phone: {store_config.get('contact', {}).get('primary_phone', '+8801729103420')}
- Support Hours: {store_config.get('contact', {}).get('support_hours', '10 AM to 10 PM')}

Store Locations:
Dhaka: {store_config.get('locations', [{}])[0].get('address', 'Gulshan Pink City')}
Chattogram: {store_config.get('locations', [{}])[1].get('address', 'Arcadia Shopping Centre') if len(store_config.get('locations', [])) > 1 else 'Contact for address'}

Frequently Asked Questions:
{chr(10).join([f"Q: {faq['question']} A: {faq['answer']}" for faq in store_config.get('faqs', [])])}

Guidelines:
- Always be polite, helpful, and maintain a luxury brand voice
- If asked about delivery, provide the phone number for updates
- If someone asks for order tracking, say: "For order tracking, please contact our Dhaka store at +8801729103420"
- If you don't know something, offer to connect with human support
- For complex issues, use the escalation phrase: {store_config.get('escalation', {}).get('escalation_phrase', 'I will connect you with a human agent.')}

Answer questions specifically about {store_config.get('name')}. Be knowledgeable and maintain premium service standards."""

        # Get conversation history from Supabase
        if conversation_id != 'new':
            history = supabase.table('conversations')\
                .select('messages')\
                .eq('id', conversation_id)\
                .execute()
            messages = history.data[0]['messages'] if history.data else []
        else:
            messages = [{"role": "system", "content": system_prompt}]
            conversation_id = create_conversation(system_prompt)

        # Add user message
        messages.append({"role": "user", "content": message})

        # Get AI response from Groq
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.7,
            max_tokens=250
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
        return jsonify({'error': str(e)}), 500

def create_conversation(system_prompt):
    result = supabase.table('conversations')\
        .insert({'messages': [{"role": "system", "content": system_prompt}]})\
        .execute()
    return result.data[0]['id']

@app.route('/order-status', methods=['POST'])
def order_status():
    """Check real order status (mock for demo)"""
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
    """Test endpoint to verify Groq is working"""
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": "Say 'Groq is working!'"}],
            max_tokens=10
        )
        return jsonify({'status': 'success', 'message': response.choices[0].message.content})
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/telegram-set-webhook', methods=['GET'])
def set_webhook():
    """Set up Telegram webhook (run once)"""
    try:
        bot_token = "8651304807:AAHfdlnbPZr0sOKHc6RuA0MHVOGoDC-hWM4"
        webhook_url = "https://customer-support-agent-y6qb.onrender.com/telegram-webhook"
        
        url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
        data = {"url": webhook_url}
        
        response = requests.post(url, json=data)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
