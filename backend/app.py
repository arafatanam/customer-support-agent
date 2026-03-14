from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
import os
from supabase import create_client
import json

app = Flask(__name__)
CORS(app)

# Free Supabase setup
supabase = create_client(
    'https://snfzxgatepbeazffkbfm.supabase.co',  # Get from supabase.com
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNuZnp4Z2F0ZXBiZWF6ZmZrYmZtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM1MDMxODIsImV4cCI6MjA4OTA3OTE4Mn0.Hg9uWpE_T09MpOh-s_1RnZqVQqJc7mn8yByzj5MvAmg'      # Free account
)

# OpenAI setup (use your free credits)
openai.api_key = os.getenv(
    'OPENAI_KEY')  # Set in .env file, e.g. OPENAI_KEY="sk-xxxx"

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


@app.route('/chat', methods=['POST'])
def chat():
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

    # Get AI response
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
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


def create_conversation():
    result = supabase.table('conversations')\
        .insert({'messages': [{"role": "system", "content": SYSTEM_PROMPT}]})\
        .execute()
    return result.data[0]['id']


@app.route('/order-status', methods=['POST'])
def order_status():
    """Check real order status (mock for demo)"""
    order_number = request.json.get('order_number')
    # In reality, you'd connect to Shopify/WooCommerce API
    return jsonify({
        'status': 'shipped',
        'estimated_delivery': '3-5 business days'
    })


if __name__ == '__main__':
    app.run(port=5000)
