from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from supabase import create_client
import json
from groq import Groq

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
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
