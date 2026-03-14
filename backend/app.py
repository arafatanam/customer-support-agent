from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from supabase import create_client
import json
from groq import Groq  # Import Groq

app = Flask(__name__)
CORS(app)

# Get environment variables
supabase_url = os.environ.get('SUPABASE_URL')
supabase_key = os.environ.get('SUPABASE_KEY')
groq_api_key = os.environ.get('GROQ_API_KEY')  # Changed from OPENAI_KEY

# Initialize Groq client
groq_client = Groq(api_key=groq_api_key)

# Free Supabase setup
supabase = create_client(supabase_url, supabase_key)

# Your custom prompt for e-commerce support
SYSTEM_PROMPT = """You are a friendly customer support agent for an e-commerce store.
Your goals:
- Answer questions about orders, shipping, returns, products
- Be helpful, concise, and warm
- If you don't know something, say you'll connect them with a human
- Collect order numbers when needed

Common topics:
- Order status: Ask for order number, check system
- Returns: Explain 30-day policy, guide through process
- Shipping: Standard 3-5 days, express 1-2 days
- Product questions: Describe features, check availability

Keep responses under 150 words. Be helpful but efficient."""

@app.route('/')
def home():
    return jsonify({
        'status': 'online',
        'message': 'Customer Support Agent API is running',
        'endpoints': {
            '/chat': 'POST - Send messages to the support agent',
            '/health': 'GET - Health check',
            '/order-status': 'POST - Check order status'
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

        # Get conversation history from Supabase
        if conversation_id != 'new':
            history = supabase.table('conversations')\
                .select('messages')\
                .eq('id', conversation_id)\
                .execute()
            messages = history.data[0]['messages'] if history.data else []
        else:
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            conversation_id = create_conversation()

        # Add user message
        messages.append({"role": "user", "content": message})

        # Get AI response from Groq
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",  # Free model, 70B parameters
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

def create_conversation():
    result = supabase.table('conversations')\
        .insert({'messages': [{"role": "system", "content": SYSTEM_PROMPT}]})\
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
