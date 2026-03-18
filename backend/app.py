
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from supabase import create_client
import json
from groq import Groq
from whatsapp_handler import whatsapp_handler
import threading
from datetime import datetime
import time

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

# Load store configurations
def load_store_configs():
    try:
        with open('stores_config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Fallback to default configs
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

@app.route('/')
def home():
    return jsonify({
        'status': 'online',
        'message': 'Customer Support Agent API is running',
        'endpoints': {
            '/chat': 'POST - Send messages to the support agent',
            '/health': 'GET - Health check',
            '/order-status': 'POST - Check order status',
            '/test-groq': 'GET - Test Groq connection'
        }
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        message = data.get('message', '')
        conversation_id = data.get('conversation_id', 'new')
        store_id = data.get('store_id', 'default')
        
        # Get store configuration
        store_config = STORE_CONFIGS.get(store_id, STORE_CONFIGS.get('default', {}))
        
        # Create store-specific system prompt
        system_prompt = f"""You are a luxury customer support agent for {store_config.get('name', 'Prism The Store')}.

Brand Voice: {store_config.get('brand', {}).get('voice', 'Luxury & Premium')}

Store Policies:
- Privacy: {store_config.get('policies', {}).get('privacy', 'Available on website')}
- Terms: {store_config.get('policies', {}).get('terms', 'Available on website')}
- Shipping: {store_config.get('policies', {}).get('shipping', 'International shipping available')}

Products: {', '.join(store_config.get('products', {}).get('top_products', []))}

Contact Information:
- Email: {store_config.get('contact', {}).get('email', 'info@prismthestore.com')}
- Phone: {store_config.get('contact', {}).get('phone', '+8801729103420')}
- Support Hours: {store_config.get('contact', {}).get('support_hours', '10 AM to 10 PM')}

Frequently Asked Questions:
{chr(10).join([f"Q: {faq['question']} A: {faq['answer']}" for faq in store_config.get('faqs', [])])}

Guidelines:
- Always be polite, helpful, and maintain a luxury brand voice
- If asked about delivery, provide the phone number for updates
- If you don't know something, offer to connect with human support
- For complex issues, use the escalation phrase: {store_config.get('escalation', {}).get('escalation_phrase', '')}

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
            'order_number': order_number
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

# Initialize WhatsApp on startup
def init_whatsapp():
    """Initialize WhatsApp web on server start"""
    if whatsapp_handler.start_driver():
        if whatsapp_handler.wait_for_login():
            print("✅ WhatsApp ready!")
            
            # Create groups for all stores
            for store_id, config in STORE_CONFIGS.items():
                if 'whatsapp' in config and config['whatsapp']['enabled']:
                    group_name = config['whatsapp']['group_name']
                    members = config['whatsapp']['team_members']
                    
                    # Create group if doesn't exist
                    if group_name not in whatsapp_handler.group_names.values():
                        whatsapp_handler.create_or_get_group(
                            store_id, 
                            group_name, 
                            members
                        )
            
            print("✅ All WhatsApp groups ready!")
        else:
            print("❌ Please scan QR code in the console")
    else:
        print("❌ Failed to start WhatsApp")

# Start WhatsApp in background thread
threading.Thread(target=init_whatsapp, daemon=True).start()

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        message = data.get('message', '')
        conversation_id = data.get('conversation_id', 'new')
        store_id = data.get('store_id', 'default')
        customer_email = data.get('email', '')
        customer_phone = data.get('phone', '')
        
        store_config = STORE_CONFIGS.get(store_id, {})
        
        # URGENCY DETECTION
        urgent_keywords = [
            'urgent', 'emergency', 'asap', 'immediately', 'quick',
            'speak to human', 'talk to person', 'real person',
            'help me now', 'right now', 'instant', 'immediate',
            'joldi', 'fast', 'quickly', 'problem', 'issue'
        ]
        
        is_urgent = any(keyword in message.lower() for keyword in urgent_keywords)
        
        # If urgent and WhatsApp is enabled
        if is_urgent and store_config.get('whatsapp', {}).get('enabled'):
            
            # If no email/phone provided, ask for it
            if not customer_email and not customer_phone:
                return jsonify({
                    'response': "I understand this is urgent! To connect you with our team immediately, please provide your email or phone number:",
                    'conversation_id': conversation_id,
                    'ask_contact': True
                })
            
            # Send to WhatsApp group
            customer_info = {
                'store_name': store_config['name'],
                'email': customer_email or 'Not provided',
                'phone': customer_phone or 'Not provided',
                'urgent_message': message,
                'conversation_id': conversation_id,
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Send to WhatsApp group
            group_name = store_config['whatsapp']['group_name']
            success = whatsapp_handler.send_urgent_alert(
                store_id, 
                group_name, 
                customer_info
            )
            
            if success:
                return jsonify({
                    'response': f"✅ Our team has been notified urgently! Someone from Prism will contact you at {customer_email or customer_phone} within {store_config['whatsapp']['response_time']}. You can also call us directly at {store_config['contact']['primary_phone']}",
                    'conversation_id': conversation_id,
                    'handoff_initiated': True
                })
            else:
                return jsonify({
                    'response': f"I'm trying to reach our team urgently. Please call us directly at {store_config['contact']['primary_phone']} for immediate help.",
                    'conversation_id': conversation_id,
                    'handoff_fallback': True
                })

    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
