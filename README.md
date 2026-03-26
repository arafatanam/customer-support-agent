# Avion AI - Multi-Store Customer Support Platform

A scalable, multi-tenant AI customer support agent platform. One codebase serves unlimited clients with store-specific customization, human handoff capabilities, and conversation history tracking.

## Table of Contents
- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [File Descriptions](#file-descriptions)
- [Setup & Installation](#setup--installation)
- [Database Setup](#database-setup)
- [Adding a New Client](#adding-a-new-client)
- [Deployment](#deployment)
- [API Reference](#api-reference)
- [Escalation Modes](#escalation-modes)
- [Troubleshooting](#troubleshooting)

## Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Client Site   │────▶│   Backend API   │────▶│     Groq AI    │
│   (WordPress/   │     │   (Render)      │     │   (Llama 3.3)   │
│    Custom HTML) │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                       │                        │
         │                       │                        │
         ▼                       ▼                        ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Chat Widget   │     │   Supabase      │     │   Store Config  │
│   (Vercel)      │     │   (Database)    │     │   (JSON)        │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                  │
                                  ▼
                        ┌─────────────────┐
                        │   Telegram/     │
                        │   Email Alerts  │
                        └─────────────────┘
```

## Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Backend** | Python/Flask | API server handling chat requests |
| **AI Engine** | Groq (Llama 3.3 70B) | Free, fast AI responses |
| **Database** | Supabase (PostgreSQL) | Conversation storage & state management |
| **Frontend** | Vanilla JavaScript | Embeddable chat widget (2 versions: Avion AI Demo & Universal) |
| **Hosting** | Render (backend) + Vercel (frontend) | Free tier hosting |
| **Escalation** | Telegram API / SendGrid | Human handoff notifications |

## Project Structure

```
customer-support-agent/
│
├── backend/
│   ├── app.py                  # Main Flask application
│
├── frontend/
│   ├── widget.js               # Universal chat widget
│   └── index.html              # Avion AI demo landing page
│
├── stores_config.json           # All client configurations (root folder)
├── .gitignore                   # Git ignore rules
├── requirements.txt             # Python dependencies
├── render.yaml                  # Render deployment config
└── README.md                    # This file
```

## File Descriptions

### 1. **`backend/app.py`** - Main Application Server

**Purpose**: Handles all API requests, manages conversations, interfaces with Groq AI, and manages human handoff.

**Key Endpoints**:
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | API status and available endpoints |
| `/chat` | POST | Process user messages, return AI responses, handle handoffs |
| `/poll` | GET | Widget polling for agent messages during handoff |
| `/health` | GET | Health check endpoint |
| `/test-groq` | GET | Test Groq API connectivity |
| `/telegram-webhook` | POST | Receive Telegram button clicks and agent replies |
| `/order-status` | POST | Mock order status endpoint |

**How it works**:
1. Receives message with `store_id` and optional contact info
2. Checks for:
   - Active human handoff → forwards to Telegram
   - Waiting for contact info → captures email/phone
   - Urgent keywords → triggers escalation
   - Order tracking keywords → returns phone number
3. Loads store-specific configuration from `stores_config.json`
4. Creates custom system prompt with store policies and FAQs
5. Fetches conversation history from Supabase
6. Sends to Groq AI for response
7. Stores conversation and returns response

### 2. **`stores_config.json`** - Client Configuration (Root Folder)

**Purpose**: Central configuration file for all clients. Each store has its own configuration with escalation preferences.

**Structure**:
```json
{
  "store_id_001": {
    "store_id": "unique_identifier",
    "name": "Store Name",
    "website": "storeurl.com",
    "telegram": {
      "enabled": true/false,
      "bot_token": "telegram_bot_token",
      "group_chat_id": -123456789
    },
    "escalation": {
      "mode": "telegram" or "email",
      "human_handoff": true,
      "alert_email": "team@store.com"
    },
    "brand": {
      "voice": "brand personality",
      "primary_color": "#HEX",
      "secondary_color": "#HEX",
      "greeting": "Welcome message"
    },
    "contact": {
      "email": "support@store.com",
      "primary_phone": "+1234567890",
      "support_hours": "9 AM to 5 PM"
    },
    "products": {
      "categories": ["cat1", "cat2"],
      "top_products": ["product1", "product2"]
    },
    "faqs": [
      {"question": "Q1?", "answer": "A1"}
    ]
  }
}
```

### 3. **`frontend/widget.js`** - Universal Chat Widget

**Purpose**: Embeddable JavaScript widget that works on any website with full handoff support.

**Features**:
- Store-specific branding (colors, name, position)
- Urgent keyword detection
- Contact info collection (email/phone)
- Human handoff with polling for agent replies
- Typing indicators and smooth animations
- Mobile responsive
- Error handling

**Usage**:
```javascript
new SupportWidget('store_id_001', {
    storeName: 'Store Name',
    primaryColor: '#HEX',
    secondaryColor: '#HEX',
    position: 'bottom-right'  // or 'bottom-left'
});
```

### 4. **`frontend/index.html`** - Avion AI Demo Landing Page

**Purpose**: Marketing landing page for Avion AI with embedded demo widget using the `avion_demo` store configuration (email escalation).

### 5. **`requirements.txt`** - Python Dependencies

```
flask==2.3.3
flask-cors==4.0.0
groq==0.5.0
supabase==1.2.0
gunicorn==21.2.0
python-dotenv==1.0.0
requests==2.31.0
```

### 6. **`render.yaml`** - Render Deployment Config

```yaml
services:
  - type: web
    name: customer-support-agent-api
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn backend.app:app
```

## Setup & Installation

### Prerequisites
- GitHub account
- Render account (free)
- Vercel account (free)
- Supabase account (free)
- Groq account (free)
- (Optional) Telegram Bot for handoff

### Initial Setup

1. **Clone Repository**
```bash
git clone https://github.com/yourusername/customer-support-agent.git
cd customer-support-agent
```

2. **Install Dependencies Locally** (optional)
```bash
pip install -r requirements.txt
```

3. **Set Up Environment Variables** (in Render dashboard)
```
GROQ_API_KEY=your_groq_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
PYTHON_VERSION=3.11.11
SENDGRID_API_KEY=your_sendgrid_key  # Optional, for email escalation
```

4. **Deploy Backend** (Render)
- Connect GitHub repository
- Use `render.yaml` configuration
- Auto-deploys on push to main branch

5. **Deploy Frontend** (Vercel)
- Import GitHub repository
- Root directory: `frontend`
- Auto-deploys on push to main branch

## Database Setup

Run this SQL in Supabase SQL Editor:

```sql
-- Create conversations table with metadata support
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    messages JSONB NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW())
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at);
CREATE INDEX IF NOT EXISTS idx_conversations_metadata ON conversations USING gin (metadata);
CREATE INDEX IF NOT EXISTS idx_conversations_messages ON conversations USING gin (messages);
```

## Adding a New Client

### Step 1: Gather Client Information
- Store name and website
- Brand colors (primary/secondary)
- Brand voice description
- Product categories and top products
- Policies (shipping, returns, etc.)
- Contact information (email, phone)
- Top 10 FAQs with answers
- Preferred chat position
- **Escalation preference** (Telegram or Email)

### Step 2: Add to `stores_config.json`
Add a new entry with unique store ID:

```json
"new_store_002": {
    "store_id": "new_store_002",
    "name": "New Store",
    "website": "newstore.com",
    "telegram": {
      "enabled": true,
      "bot_token": "your_bot_token",
      "group_chat_id": -123456789
    },
    "escalation": {
      "mode": "telegram",
      "human_handoff": true
    },
    "contact": {
      "primary_phone": "+1234567890",
      "email": "support@newstore.com",
      "support_hours": "9 AM to 5 PM"
    },
    "brand": {
      "voice": "Friendly and professional",
      "primary_color": "#HEX",
      "secondary_color": "#HEX",
      "greeting": "Welcome to New Store!"
    },
    "products": {
      "categories": ["Category1", "Category2"],
      "top_products": ["Product1", "Product2"]
    },
    "faqs": [
      {"question": "Question 1?", "answer": "Answer 1"}
    ]
}
```

### Step 3: Generate Install Code
```html
<script>
(function() {
    const script = document.createElement('script');
    script.src = 'https://your-domain.vercel.app/widget.js';
    script.onload = () => {
        new SupportWidget('new_store_002', {
            storeName: 'New Store',
            primaryColor: '#their-color',
            secondaryColor: '#their-other-color',
            position: 'bottom-right'
        });
    };
    document.head.appendChild(script);
})();
</script>
```

### Step 4: Deploy
```bash
git add stores_config.json
git commit -m "Add new client: New Store"
git push
```

### Step 5: Send Install Instructions
Provide client with install code for their platform.

## Deployment

### Automatic Deployment
- **Render**: Auto-deploys on push to `main` branch
- **Vercel**: Auto-deploys on push to `main` branch

### Manual Deployment
```bash
git add .
git commit -m "Update"
git push origin main
```

## API Reference

### Chat Endpoint
```http
POST /chat
Content-Type: application/json

{
    "message": "User question",
    "conversation_id": "new or existing",
    "store_id": "store_identifier",
    "email": "optional@email.com",
    "phone": "+1234567890",
    "urgent": true/false
}
```

**Response Types**:
| Response Field | Meaning |
|----------------|---------|
| `response` | AI or system response text |
| `ask_contact` | True if system needs email/phone |
| `handoff_initiated` | True if team was notified |
| `handoff_active` | True if human agent is responding |

### Poll Endpoint (Widget)
```http
GET /poll?conversation_id=123
```
Returns pending agent messages during human handoff.

### Health Check
```http
GET /health
```
**Response** `{"status": "healthy"}`

### Test Groq
```http
GET /test-groq
```
**Response** `{"status": "success", "message": "Groq is working!"}`

## Escalation Modes

### Telegram Mode
- Real-time two-way chat between customer and agent
- Agent receives alert with inline buttons
- Agent can reply directly from Telegram
- Best for businesses needing instant response

### Email Mode
- Customer's urgent request is emailed to the store
- No two-way chat; store contacts customer directly
- Best for simple lead capture or slower response needs

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| 500 Error | Check Groq API key in Render environment variables |
| Telegram not sending | Verify bot token and group chat ID; ensure bot is group admin |
| Widget not showing | Check store_id matches exactly in config and widget init |
| Contact not captured | Verify phone/email format in widget.js validation |
| Handoff not working | Check Render logs for "URGENT DETECTED" and Telegram response |

### Debug Steps
1. Test Groq: `https://your-api.onrender.com/test-groq`
2. Check Render logs in dashboard
3. Test with curl:
```bash
curl -X POST https://your-api.onrender.com/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"urgent help","store_id":"your_store_id"}'
```

## Viewing Conversation History

All conversations are stored in Supabase. Query with:

```sql
-- View recent conversations with summaries
SELECT 
    id,
    created_at,
    jsonb_array_length(messages) as message_count,
    SUBSTRING((messages->1->>'content'), 1, 60) as customer_message,
    metadata->>'handoff_active' as handoff_active,
    metadata->>'agent_name' as handled_by
FROM conversations
ORDER BY created_at DESC;
```
