# Avion AI - AI Customer Support Agents

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
- [Telegram Handoff Setup](#telegram-handoff-setup)
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
| **Frontend** | Vanilla JavaScript | Embeddable chat widget |
| **Landing Page** | HTML/CSS (Chakra Petch, Space Grotesk fonts) | Marketing site with live demo widget |
| **Hosting** | Render (backend) + Vercel (frontend) | Free tier hosting |
| **Escalation** | Telegram API / Resend | Human handoff notifications & contact form |

## Project Structure

```
customer-support-agent/
│
├── backend/
│   ├── app.py                  # Main Flask application
│
├── frontend/
│   ├── widget.js               # Universal chat widget
│   └── index.html              # Avion AI landing page
│   └── favicon.ico             # Favicon of Avion AI
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
| `/health` | GET | Health check endpoint (used for cron job to keep Render alive) |
| `/test-groq` | GET | Test Groq API connectivity |
| `/telegram-webhook` | POST | Receive Telegram button clicks and agent replies |
| `/api/contact` | POST | Contact form submission (Resend email) |
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
      "enabled": true,
      "bot_token": "your_bot_token",
      "group_chat_id": -1003552610562,
      "team_handoff": true,
      "response_time": "5 minutes"
    },
    "escalation": {
      "mode": "telegram",
      "human_handoff": true
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

### 4. **`frontend/index.html`** - Avion AI Landing Page

**Purpose**: Marketing website for Avion AI with embedded demo widget using the `avion_demo` store configuration (email escalation). Features:
- Techy aesthetic with grid background, glassmorphism effects
- Animated counters and scroll reveals
- Smart Handoff section explaining Telegram flow
- Contact form integrated with backend `/api/contact` endpoint

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
- Telegram account (for handoff)
- Resend account (for contact form)

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
RESEND_KEY=your_resend_key
```

4. **Keep Render Alive (Free Tier)**
   - Set up a cron job to ping `/health` every 10-15 minutes
   - Use cron-job.org (free) or UptimeRobot
   - Target: `https://your-render-url.onrender.com/health`

5. **Deploy Backend** (Render)
- Connect GitHub repository
- Use `render.yaml` configuration
- Auto-deploys on push to main branch

6. **Deploy Frontend** (Vercel)
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
- **Escalation preference** (Telegram)

### Step 2: Set Up Telegram for the Client
Follow the [Telegram Handoff Setup](#telegram-handoff-setup) section below.

### Step 3: Add to `stores_config.json`
Add a new entry with unique store ID:

```json
"new_store_002": {
    "store_id": "new_store_002",
    "name": "New Store",
    "website": "newstore.com",
    "telegram": {
      "enabled": true,
      "bot_token": "your_bot_token",
      "group_chat_id": -1003552610562,
      "team_handoff": true,
      "response_time": "5 minutes"
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

### Step 4: Generate Install Code
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

### Step 5: Deploy
```bash
git add stores_config.json
git commit -m "Add new client: New Store"
git push
```

### Step 6: Send Install Instructions
Provide client with install code for their platform.

## Deployment

### Automatic Deployment
- **Render**: Auto-deploys on push to `main` branch
- **Vercel**: Auto-deploys on push to `main` branch

### Keep Render Free Tier Alive
Render free tier spins down after 15 minutes of inactivity. To prevent this:

1. Sign up for a free account at [cron-job.org](https://cron-job.org) or [UptimeRobot](https://uptimerobot.com)
2. Create a cron job that pings `/health` endpoint every 10-15 minutes
3. Target URL: `https://your-render-url.onrender.com/health`

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

### Contact Form
```http
POST /api/contact
Content-Type: application/json

{
    "name": "John Doe",
    "email": "john@example.com",
    "company": "Example Corp",
    "message": "I'm interested in your service"
}
```

## Escalation Modes

### Telegram Mode (Recommended)
- Real-time two-way chat between customer and agent
- Agent receives alert with inline buttons
- Agent can reply directly from Telegram
- Best for businesses needing instant response

### Email Mode (Legacy)
- Customer's urgent request is emailed to the store
- No two-way chat; store contacts customer directly
- Best for simple lead capture or slower response needs

## Telegram Handoff Setup

Complete step-by-step guide to set up Telegram handoff for a new client.

### Step 1 — Create your Telegram bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Choose a name (e.g. "Avion AI Support Bot")
4. Choose a username ending in `bot` (e.g. `avionai_support_bot`)
5. BotFather gives you a **bot token** — save it immediately
   - Format: `8651304807:AAHfdlnbPZr0sOKHc6RuA0MHVOGoDC-hWM4`

### Step 2 — Disable bot privacy mode

> ⚠️ **Critical** — Without this, the bot cannot read group messages.

1. In BotFather send `/mybots`
2. Select your bot
3. Go to **Bot Settings** → **Group Privacy** → **Turn OFF**
4. You should see "Privacy mode is disabled"

**Note:** If you disable privacy mode after adding the bot to a group, you must remove the bot and re-add it for changes to take effect.

### Step 3 — Create Telegram group and get the real chat ID

1. Create a new Telegram group (e.g. "Store Name Support Team")
2. Add your bot to the group and make it **admin with all permissions**
3. Send any message in the group (e.g. "hello")
4. Open this URL in your browser (replace with your bot token):
   ```
   https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   ```
5. In the JSON response, find the `chat` object — the `id` field is your real chat ID
   - Format: `-1003552610562`
   - Note the `-100` prefix — this is required for supergroups and is different from what the Telegram web URL shows

### Step 4 — Add config to `stores_config.json`

```json
"telegram": {
  "enabled": true,
  "bot_token": "YOUR_BOT_TOKEN",
  "group_chat_id": -1003552610562,
  "team_handoff": true,
  "response_time": "5 minutes"
},
"escalation": {
  "mode": "telegram"
}
```

**Use the exact number from Step 3 including the minus sign.**

### Step 5 — Register the webhook

This tells Telegram where to send button clicks and group messages.

Paste this in your browser (replace both placeholders):
```
https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=https://<YOUR_RENDER_URL>/telegram-webhook
```

Example:
```
https://api.telegram.org/bot8651304807:AAHfdlnb.../setWebhook?url=https://customer-support-agent-y6qb.onrender.com/telegram-webhook
```

**Expected response:**
```json
{"ok": true, "result": true, "description": "Webhook was set"}
```

### Step 6 — Verify everything is connected

Paste this in your browser:
```
https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo
```

Check that:
- `url` points to your Render endpoint (`/telegram-webhook`)
- `pending_update_count` is `0`
- `has_custom_certificate` is `false`

### Step 7 — Test the full flow

1. Open your website's chat widget
2. Type something with an urgent keyword (e.g. "I need to speak to a human")
3. Check your Telegram group — alert should appear with the **"I'll handle this"** button
4. Click the button — group gets a confirmation message and the customer widget shows "You're now connected with [Name]"
5. Type a reply in the Telegram group — it appears in the customer's widget within 2.5 seconds
6. Customer types in the widget — it appears in the Telegram group as "💬 Customer says: ..."

### ⚠️ Things that will silently break it

| Problem | Solution |
|---------|----------|
| Using chat ID from Telegram web URL instead of from `getUpdates` | Always use the `-100` prefixed ID from `getUpdates` |
| Not disabling privacy mode before adding bot to group | Remove bot from group, disable privacy mode, then re-add |
| Forgetting to re-register webhook after `deleteWebhook` | Always re-run the `setWebhook` command |
| Bot not being admin in the group | Add bot as admin with all permissions |
| Wrong webhook URL (typo or missing `/telegram-webhook`) | Ensure URL ends with `/telegram-webhook` |

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| 500 Error | Check Groq API key in Render environment variables |
| Telegram not sending | Verify bot token and group chat ID; ensure bot is group admin |
| Widget not showing | Check store_id matches exactly in config and widget init |
| Contact not captured | Verify phone/email format in widget.js validation |
| Handoff not working | Check Render logs for "URGENT DETECTED" and Telegram response |
| Webhook not working | Run `getWebhookInfo` to verify URL and pending updates |
| Contact form failing | Check RESEND_KEY environment variable and recipient email |

### Debug Steps
1. Test Groq: `https://your-api.onrender.com/test-groq`
2. Check Render logs in dashboard
3. Test webhook: `https://api.telegram.org/bot<TOKEN>/getWebhookInfo`
4. Test with curl:
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

-- View conversation with Telegram handoff status
SELECT 
    id,
    created_at,
    metadata->>'handoff_active' as handoff_active,
    metadata->>'agent_name' as handled_by,
    metadata->>'waiting_for_contact' as waiting_for_contact
FROM conversations
WHERE metadata->>'handoff_active' = 'true'
ORDER BY created_at DESC;
```

---

**Built with ❤️ for businesses worldwide**
```

This README is fully formatted in Markdown and ready to be saved as `README.md` in your project root. It includes all the technical details, setup instructions, and the complete Telegram Handoff Setup guide you wrote.
