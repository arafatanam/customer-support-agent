# AI Customer Support Agent - Multi-Store Platform

A scalable, multi-tenant AI customer support agent built for e-commerce stores. One codebase serves unlimited clients with store-specific customization.

## Table of Contents
- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [File Descriptions](#file-descriptions)
- [Setup & Installation](#setup--installation)
- [Adding a New Client](#adding-a-new-client)
- [Deployment](#deployment)
- [API Reference](#api-reference)
- [Customization](#customization)
- [Troubleshooting](#troubleshooting)

## Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Client Site   │────▶│   Backend API   │────▶│     Groq AI    │
│   (Frontend)    │     │   (Render)      │     │   (Llama 3.3)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                       │                        │
         │                       │                        │
         ▼                       ▼                        ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Chat Widget   │     │   Supabase      │     │   Store Config  │
│   (Vercel)      │     │   (Database)    │     │   (JSON)        │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Backend** | Python/Flask | API server handling chat requests |
| **AI Engine** | Groq (Llama 3.3 70B) | Free, fast AI responses |
| **Database** | Supabase | Conversation storage |
| **Frontend** | Vanilla JavaScript | Embeddable chat widget |
| **Hosting** | Render (backend) + Vercel (frontend) | Free tier hosting |
| **Configuration** | JSON | Store-specific settings |

## Project Structure

```
customer-support-agent/
│
├── backend/
│   ├── app.py                  # Main Flask application
│   └── stores_config.json      # All client configurations
│
├── frontend/
│   ├── widget.js               # Universal chat widget
│   └── index.html              # Demo page for testing
│
├── .gitignore                  # Git ignore rules
├── requirements.txt            # Python dependencies
├── render.yaml                 # Render deployment config
└── README.md                    
```

## File Descriptions

### 1. **`backend/app.py`** - Main Application Server
**Purpose**: Handles all API requests, manages conversations, interfaces with Groq AI.

**Key Functionalities**:
- `/chat` (POST) - Process user messages and return AI responses
- `/health` (GET) - Health check endpoint
- `/order-status` (POST) - Mock order status endpoint
- `/test-groq` (GET) - Test Groq API connectivity

**How it works**:
1. Receives message with `store_id`
2. Loads store-specific configuration from `stores_config.json`
3. Creates custom system prompt with store policies and FAQs
4. Fetches conversation history from Supabase
5. Sends to Groq AI for response
6. Stores conversation and returns response

### 2. **`backend/stores_config.json`** - Client Configuration
**Purpose**: Central configuration file for all clients.

**Structure**:
```json
{
  "store_id_001": {
    "store_id": "unique_identifier",
    "name": "Store Name",
    "website": "storeurl.com",
    "brand": {
      "voice": "brand personality",
      "primary_color": "#HEX",
      "secondary_color": "#HEX",
      "greeting": "Welcome message"
    },
    "platform": "WordPress/Shopify/etc",
    "products": {
      "categories": ["cat1", "cat2"],
      "top_products": ["product1", "product2"]
    },
    "policies": {
      "privacy": "Privacy policy text",
      "terms": "Terms text",
      "shipping": "Shipping policy",
      "international": true/false
    },
    "contact": {
      "email": "support@store.com",
      "phone": "+1234567890",
      "support_hours": "9 AM to 5 PM"
    },
    "faqs": [
      {"question": "Q1?", "answer": "A1"},
      {"question": "Q2?", "answer": "A2"}
    ],
    "escalation": {
      "human_handoff": true,
      "escalation_phrase": "Connecting to human..."
    }
  }
}
```

### 3. **`frontend/widget.js`** - Universal Chat Widget
**Purpose**: Embeddable JavaScript widget that works on any website.

**Features**:
- Store-specific branding (colors, name)
- Position configurable (bottom-left/bottom-right)
- Persistent conversation history
- Typing indicators
- Smooth animations
- Mobile responsive
- Error handling

**Usage**:
```javascript
new SupportWidget('store_id_001', {
    storeName: 'Store Name',
    primaryColor: '#HEX',
    secondaryColor: '#HEX',
    position: 'bottom-left'
});
```

### 4. **`frontend/index.html`** - Demo Page
**Purpose**: Test page to verify widget functionality before client installation.

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

### Initial Setup

1. **Clone Repository**
```bash
git clone https://github.com/yourusername/customer-support-agent.git
cd customer-support-agent
```

2. **Install Dependencies**
```bash
pip install -r requirements.txt
```

3. **Set Up Environment Variables** (in Render dashboard)
```
GROQ_API_KEY=your_groq_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
PYTHON_VERSION=3.11.11
```

4. **Deploy Backend** (Render)
- Connect GitHub repository
- Use `render.yaml` configuration
- Auto-deploys on push

5. **Deploy Frontend** (Vercel)
- Import GitHub repository
- Root directory: `frontend`
- Auto-deploys on push

## Adding a New Client

### Step 1: Gather Client Information
- Store name and website
- Brand colors (primary/secondary)
- Brand voice description
- Product categories and top products
- Policies (privacy, terms, shipping)
- Contact information
- Top 10 FAQs with answers
- Preferred chat position

### Step 2: Add to `stores_config.json`
Add a new entry with unique store ID:
```json
"new_store_002": {
    "store_id": "new_store_002",
    "name": "New Store",
    // ... all gathered information
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
            position: 'bottom-left'
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
Provide client with install code for their platform:
- WordPress (footer.php)
- Elementor (HTML widget)
- Shopify (theme.liquid)
- Any website (just before `</body>`)

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
    "store_id": "store_identifier"
}
```

**Response**
```json
{
    "response": "AI answer",
    "conversation_id": "123"
}
```

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

## Customization

### Widget Appearance
Modify `frontend/widget.js` to change:
- Button styles
- Animation effects
- Message bubbles
- Font families
- Positioning

### AI Behavior
Modify system prompt in `app.py` to change:
- Response length
- Temperature (creativity)
- Brand voice enforcement
- Escalation triggers

### Database
Supabase stores:
- Conversation history
- Message threads
- Timestamps

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| 500 Error | Check Groq API key in Render |
| Model not found | Update model name in `app.py` |
| No response | Check Supabase connection |
| Widget not showing | Verify store ID matches config |
| CSP errors | Normal on some sites, test on actual site |

### Debug Steps
1. Test endpoint: `https://your-api.onrender.com/test-groq`
2. Check Render logs in dashboard
3. Test with curl:
```bash
curl -X POST https://your-api.onrender.com/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello","store_id":"test_store"}'
```

## Scaling

- **One repository** serves unlimited clients
- **Add clients** by updating `stores_config.json`
- **No code changes** needed for new clients
- **Automatic updates** for all clients on push

## Contributing

1. Fork repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Open pull request