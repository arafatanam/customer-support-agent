class SupportWidget {
    constructor(storeId, options = {}) {
        this.storeId = storeId;
        this.apiUrl = 'https://customer-support-agent-y6qb.onrender.com';
        this.conversationId = 'new';
        this.isOpen = false;
        this.isTyping = false;
        
        // New properties for WhatsApp handoff
        this.customerEmail = null;
        this.customerPhone = null;
        this.awaitingContact = false;
        this.pendingUrgentMessage = null;
        
        this.init();
    }

    init() {
        this.injectStyles();
        this.createButton();
        this.createChatWindow();

        document.getElementById('chat-input').addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
    }

    injectStyles() {
        const style = document.createElement('style');
        style.textContent = `
            @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Serif+Display&display=swap');

            :root {
                --sw-bg: #0f0f13;
                --sw-surface: #16161d;
                --sw-surface2: #1e1e28;
                --sw-border: rgba(255,255,255,0.07);
                --sw-accent: #7c6af7;
                --sw-accent2: #a78bfa;
                --sw-glow: rgba(124, 106, 247, 0.35);
                --sw-text: #f0eeff;
                --sw-muted: #8b879e;
                --sw-user-bg: linear-gradient(135deg, #7c6af7, #a78bfa);
                --sw-bot-bg: #1e1e28;
                --sw-radius: 20px;
                --sw-font: 'DM Sans', sans-serif;
            }

            #sw-btn {
                position: fixed;
                bottom: 28px;
                right: 28px;
                width: 60px;
                height: 60px;
                background: linear-gradient(135deg, #7c6af7, #a78bfa);
                border: none;
                border-radius: 50%;
                cursor: pointer;
                z-index: 99999;
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 8px 32px var(--sw-glow), 0 2px 8px rgba(0,0,0,0.4);
                transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.3s ease;
                font-family: var(--sw-font);
                overflow: hidden;
            }
            #sw-btn::before {
                content: '';
                position: absolute;
                inset: 0;
                border-radius: 50%;
                background: rgba(255,255,255,0.15);
                opacity: 0;
                transition: opacity 0.2s;
            }
            #sw-btn:hover { transform: scale(1.1); box-shadow: 0 12px 40px var(--sw-glow), 0 4px 12px rgba(0,0,0,0.4); }
            #sw-btn:hover::before { opacity: 1; }
            #sw-btn:active { transform: scale(0.95); }
            #sw-btn svg { transition: transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.25s ease; }
            #sw-btn .sw-icon-open { position: absolute; }
            #sw-btn .sw-icon-close { position: absolute; opacity: 0; transform: rotate(-90deg) scale(0.7); }
            #sw-btn.open .sw-icon-open { opacity: 0; transform: rotate(90deg) scale(0.7); }
            #sw-btn.open .sw-icon-close { opacity: 1; transform: rotate(0deg) scale(1); }

            /* Pulse ring */
            #sw-btn::after {
                content: '';
                position: absolute;
                inset: -4px;
                border-radius: 50%;
                border: 2px solid var(--sw-accent2);
                opacity: 0;
                animation: sw-pulse 2.8s ease-out infinite;
            }
            @keyframes sw-pulse {
                0% { transform: scale(0.95); opacity: 0.6; }
                70% { transform: scale(1.25); opacity: 0; }
                100% { transform: scale(1.25); opacity: 0; }
            }

            #sw-window {
                position: fixed;
                bottom: 104px;
                right: 28px;
                width: 380px;
                height: 560px;
                background: var(--sw-bg);
                border-radius: var(--sw-radius);
                border: 1px solid var(--sw-border);
                box-shadow: 0 32px 80px rgba(0,0,0,0.6), 0 0 0 1px rgba(124,106,247,0.12), inset 0 1px 0 rgba(255,255,255,0.06);
                display: flex;
                flex-direction: column;
                z-index: 99998;
                font-family: var(--sw-font);
                overflow: hidden;
                opacity: 0;
                transform: translateY(16px) scale(0.97);
                pointer-events: none;
                transition: opacity 0.3s cubic-bezier(0.16, 1, 0.3, 1), transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            }
            #sw-window.open {
                opacity: 1;
                transform: translateY(0) scale(1);
                pointer-events: all;
            }

            /* Header */
            #sw-header {
                padding: 18px 20px 16px;
                background: var(--sw-surface);
                border-bottom: 1px solid var(--sw-border);
                display: flex;
                align-items: center;
                gap: 12px;
                position: relative;
                flex-shrink: 0;
            }
            #sw-header::after {
                content: '';
                position: absolute;
                bottom: 0; left: 20px; right: 20px;
                height: 1px;
                background: linear-gradient(90deg, transparent, rgba(124,106,247,0.4), transparent);
            }
            .sw-avatar {
                width: 40px;
                height: 40px;
                border-radius: 12px;
                background: linear-gradient(135deg, #7c6af7, #a78bfa);
                display: flex;
                align-items: center;
                justify-content: center;
                flex-shrink: 0;
                box-shadow: 0 4px 12px var(--sw-glow);
            }
            .sw-header-info { flex: 1; }
            .sw-header-name {
                font-size: 15px;
                font-weight: 600;
                color: var(--sw-text);
                letter-spacing: -0.01em;
            }
            .sw-header-status {
                display: flex;
                align-items: center;
                gap: 5px;
                font-size: 12px;
                color: var(--sw-muted);
                margin-top: 2px;
            }
            .sw-status-dot {
                width: 6px; height: 6px;
                background: #34d399;
                border-radius: 50%;
                animation: sw-blink 2s ease-in-out infinite;
            }
            @keyframes sw-blink {
                0%, 100% { opacity: 1; } 50% { opacity: 0.4; }
            }
            #sw-close {
                width: 32px; height: 32px;
                border-radius: 8px;
                border: 1px solid var(--sw-border);
                background: var(--sw-surface2);
                color: var(--sw-muted);
                cursor: pointer;
                display: flex; align-items: center; justify-content: center;
                transition: all 0.2s;
                flex-shrink: 0;
            }
            #sw-close:hover { color: var(--sw-text); background: rgba(124,106,247,0.15); border-color: rgba(124,106,247,0.3); }

            /* Messages area */
            #chat-messages {
                flex: 1;
                padding: 20px 16px;
                overflow-y: auto;
                display: flex;
                flex-direction: column;
                gap: 12px;
                scroll-behavior: smooth;
            }
            #chat-messages::-webkit-scrollbar { width: 4px; }
            #chat-messages::-webkit-scrollbar-track { background: transparent; }
            #chat-messages::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 4px; }

            .sw-msg {
                display: flex;
                gap: 8px;
                animation: sw-msg-in 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            }
            @keyframes sw-msg-in {
                from { opacity: 0; transform: translateY(8px); }
                to { opacity: 1; transform: translateY(0); }
            }
            .sw-msg.user { flex-direction: row-reverse; }
            .sw-msg-avatar {
                width: 28px; height: 28px;
                border-radius: 8px;
                flex-shrink: 0;
                display: flex; align-items: center; justify-content: center;
                font-size: 12px;
                margin-top: 2px;
            }
            .sw-msg.bot .sw-msg-avatar { background: linear-gradient(135deg, #7c6af7, #a78bfa); }
            .sw-msg.user .sw-msg-avatar { background: var(--sw-surface2); border: 1px solid var(--sw-border); }
            .sw-bubble {
                max-width: 78%;
                padding: 11px 14px;
                border-radius: 16px;
                font-size: 14px;
                line-height: 1.55;
                word-break: break-word;
            }
            .sw-msg.bot .sw-bubble {
                background: var(--sw-bot-bg);
                color: var(--sw-text);
                border: 1px solid var(--sw-border);
                border-bottom-left-radius: 4px;
            }
            .sw-msg.user .sw-bubble {
                background: var(--sw-user-bg);
                color: #fff;
                border-bottom-right-radius: 4px;
                box-shadow: 0 4px 16px rgba(124,106,247,0.3);
            }

            /* Typing indicator */
            #sw-typing {
                display: none;
                gap: 8px;
                animation: sw-msg-in 0.3s ease;
            }
            #sw-typing.visible { display: flex; }
            .sw-typing-bubble {
                background: var(--sw-bot-bg);
                border: 1px solid var(--sw-border);
                border-radius: 16px;
                border-bottom-left-radius: 4px;
                padding: 14px 16px;
                display: flex; gap: 4px; align-items: center;
            }
            .sw-typing-dot {
                width: 6px; height: 6px;
                border-radius: 50%;
                background: var(--sw-muted);
                animation: sw-dot 1.4s ease-in-out infinite;
            }
            .sw-typing-dot:nth-child(2) { animation-delay: 0.2s; }
            .sw-typing-dot:nth-child(3) { animation-delay: 0.4s; }
            @keyframes sw-dot {
                0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
                30% { transform: translateY(-5px); opacity: 1; }
            }

            /* Input area */
            #sw-footer {
                padding: 14px 16px;
                background: var(--sw-surface);
                border-top: 1px solid var(--sw-border);
                flex-shrink: 0;
            }
            #sw-input-row {
                display: flex;
                gap: 10px;
                align-items: center;
                background: var(--sw-surface2);
                border: 1px solid var(--sw-border);
                border-radius: 14px;
                padding: 6px 6px 6px 14px;
                transition: border-color 0.2s, box-shadow 0.2s;
            }
            #sw-input-row:focus-within {
                border-color: rgba(124,106,247,0.5);
                box-shadow: 0 0 0 3px rgba(124,106,247,0.1);
            }
            #chat-input {
                flex: 1;
                background: none;
                border: none;
                outline: none;
                color: var(--sw-text);
                font-family: var(--sw-font);
                font-size: 14px;
                font-weight: 400;
                line-height: 1.4;
                resize: none;
                height: 20px;
                max-height: 80px;
                overflow-y: hidden;
            }
            #chat-input::placeholder { color: var(--sw-muted); }
            #sw-send {
                width: 36px; height: 36px;
                border-radius: 10px;
                background: linear-gradient(135deg, #7c6af7, #a78bfa);
                border: none;
                cursor: pointer;
                display: flex; align-items: center; justify-content: center;
                flex-shrink: 0;
                transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.2s;
                box-shadow: 0 4px 12px rgba(124,106,247,0.4);
            }
            #sw-send:hover { transform: scale(1.08); box-shadow: 0 6px 16px rgba(124,106,247,0.5); }
            #sw-send:active { transform: scale(0.94); }
            #sw-send:disabled { opacity: 0.4; cursor: not-allowed; transform: none; }

            .sw-footer-note {
                text-align: center;
                font-size: 11px;
                color: var(--sw-muted);
                margin-top: 10px;
                letter-spacing: 0.02em;
            }
            .sw-footer-note span { color: var(--sw-accent2); }

            /* WhatsApp handoff styles */
            .sw-contact-form {
                background: var(--sw-surface2);
                padding: 16px;
                border-radius: 16px;
                margin: 8px 0;
                border: 1px solid var(--sw-border);
                animation: sw-msg-in 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            }
            .sw-contact-form p {
                color: var(--sw-text);
                font-size: 14px;
                margin-bottom: 12px;
                font-weight: 500;
            }
            .sw-contact-input {
                width: 100%;
                padding: 10px 12px;
                background: var(--sw-bg);
                border: 1px solid var(--sw-border);
                border-radius: 10px;
                color: var(--sw-text);
                font-family: var(--sw-font);
                font-size: 14px;
                margin-bottom: 10px;
                box-sizing: border-box;
            }
            .sw-contact-input:focus {
                outline: none;
                border-color: var(--sw-accent);
                box-shadow: 0 0 0 3px rgba(124,106,247,0.1);
            }
            .sw-contact-button {
                width: 100%;
                padding: 12px;
                background: linear-gradient(135deg, #7c6af7, #a78bfa);
                border: none;
                border-radius: 10px;
                color: white;
                font-family: var(--sw-font);
                font-size: 14px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.2s;
                box-shadow: 0 4px 12px rgba(124,106,247,0.3);
                margin-bottom: 8px;
            }
            .sw-contact-button:hover {
                transform: scale(1.02);
                box-shadow: 0 6px 16px rgba(124,106,247,0.4);
            }
            .sw-contact-note {
                font-size: 11px;
                color: var(--sw-muted);
                text-align: center;
                margin-top: 8px;
            }
            .sw-confirmation {
                background: linear-gradient(135deg, #10b981, #34d399);
                color: white;
                padding: 16px;
                border-radius: 16px;
                margin: 8px 0;
                text-align: center;
                animation: pulse 1s;
            }
            .sw-confirmation p {
                margin: 4px 0;
            }
            .sw-confirmation p:first-child {
                font-size: 24px;
                margin-bottom: 8px;
            }
            .sw-confirmation p:last-child {
                font-size: 12px;
                opacity: 0.9;
            }
        `;
        document.head.appendChild(style);
    }

    createButton() {
        const btn = document.createElement('button');
        btn.id = 'sw-btn';
        btn.setAttribute('aria-label', 'Open support chat');
        btn.innerHTML = `
            <svg class="sw-icon-open" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
            <svg class="sw-icon-close" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round">
                <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
        `;
        btn.onclick = () => this.toggleChat();
        document.body.appendChild(btn);
        this.btn = btn;
    }

    createChatWindow() {
        const container = document.createElement('div');
        container.innerHTML = `
            <div id="sw-window" role="dialog" aria-label="Customer Support">
                <div id="sw-header">
                    <div class="sw-avatar">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <circle cx="12" cy="8" r="4"/><path d="M20 21a8 8 0 1 0-16 0"/>
                        </svg>
                    </div>
                    <div class="sw-header-info">
                        <div class="sw-header-name">Support Assistant</div>
                        <div class="sw-header-status">
                            <div class="sw-status-dot"></div>
                            Online · Typically replies instantly
                        </div>
                    </div>
                    <button id="sw-close" aria-label="Close chat">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
                            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                        </svg>
                    </button>
                </div>

                <div id="chat-messages">
                    <div class="sw-msg bot">
                        <div class="sw-msg-avatar">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <circle cx="12" cy="8" r="4"/><path d="M20 21a8 8 0 1 0-16 0"/>
                            </svg>
                        </div>
                        <div class="sw-bubble">Hi there! I'm here to help. Ask me anything about your orders, shipping, or returns.</div>
                    </div>
                    <div id="sw-typing">
                        <div class="sw-msg-avatar">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <circle cx="12" cy="8" r="4"/><path d="M20 21a8 8 0 1 0-16 0"/>
                            </svg>
                        </div>
                        <div class="sw-typing-bubble">
                            <div class="sw-typing-dot"></div>
                            <div class="sw-typing-dot"></div>
                            <div class="sw-typing-dot"></div>
                        </div>
                    </div>
                </div>

                <div id="sw-footer">
                    <div id="sw-input-row">
                        <input id="chat-input" type="text" placeholder="Ask me anything…" autocomplete="off" />
                        <button id="sw-send" aria-label="Send message">
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                                <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
                            </svg>
                        </button>
                    </div>
                    <div class="sw-footer-note">Powered by <span>AI</span> · We reply instantly</div>
                </div>
            </div>
        `;
        document.body.appendChild(container);

        this.window = document.getElementById('sw-window');
        document.getElementById('sw-close').onclick = () => this.toggleChat();
        document.getElementById('sw-send').onclick = () => this.sendMessage();
    }

    async sendMessage() {
        const input = document.getElementById('chat-input');
        const message = input.value.trim();
        if (!message || this.isTyping) return;

        // If we're awaiting contact info
        if (this.awaitingContact) {
            this.handleContactInput(message);
            return;
        }

        // Check for urgency
        const urgentKeywords = [
            'urgent', 'emergency', 'asap', 'immediately', 'quick',
            'speak to human', 'talk to person', 'real person',
            'help me now', 'right now', 'joldi', 'fast', 'quickly',
            'problem', 'issue', 'serious', 'critical', 'important'
        ];
        
        const isUrgent = urgentKeywords.some(keyword => 
            message.toLowerCase().includes(keyword)
        );

        // Show user message
        this.addMessage('user', message);
        input.value = '';
        input.style.height = '20px';

        const sendBtn = document.getElementById('sw-send');
        sendBtn.disabled = true;
        this.isTyping = true;
        this.showTyping(true);

        // If urgent but no contact info, we'll let the API handle it
        // The API will respond with ask_contact if needed
        await this.callAPI(message, isUrgent);

        sendBtn.disabled = false;
    }

    async callAPI(message, isUrgent) {
        try {
            const response = await fetch(`${this.apiUrl}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    message, 
                    conversation_id: this.conversationId,
                    store_id: this.storeId,
                    email: this.customerEmail,
                    phone: this.customerPhone,
                    urgent: isUrgent
                })
            });
            
            const data = await response.json();
            this.conversationId = data.conversation_id;
            
            this.showTyping(false);
            
            // If asking for contact info
            if (data.ask_contact) {
                this.awaitingContact = true;
                this.pendingUrgentMessage = message;
                this.addMessage('bot', data.response);
                this.showContactForm();
            }
            // If handoff initiated
            else if (data.handoff_initiated) {
                this.addMessage('bot', data.response);
                this.showConfirmation();
            }
            else {
                this.addMessage('bot', data.response);
            }
            
        } catch (error) {
            this.showTyping(false);
            this.addMessage('bot', 'Something went wrong. Please try again in a moment or call us directly.');
            console.error('Chat error:', error);
        } finally {
            this.isTyping = false;
            document.getElementById('sw-send').disabled = false;
        }
    }

    showContactForm() {
        const messages = document.getElementById('chat-messages');
        const typing = document.getElementById('sw-typing');
        
        const formDiv = document.createElement('div');
        formDiv.className = 'sw-contact-form';
        formDiv.innerHTML = `
            <p>📞 How should our team contact you urgently?</p>
            <input type="email" id="contact-email" class="sw-contact-input" placeholder="Your email address" />
            <input type="tel" id="contact-phone" class="sw-contact-input" placeholder="Your WhatsApp number (with country code, e.g., +8801XXXXXXXXX)" />
            <button id="submit-contact" class="sw-contact-button">🚀 Notify Team Now</button>
            <div class="sw-contact-note">Or call us directly: +8801729103420</div>
        `;
        
        messages.insertBefore(formDiv, typing);
        messages.scrollTop = messages.scrollHeight;
        
        document.getElementById('submit-contact').onclick = () => {
            const email = document.getElementById('contact-email').value;
            const phone = document.getElementById('contact-phone').value;
            
            if (email || phone) {
                this.customerEmail = email;
                this.customerPhone = phone;
                this.awaitingContact = false;
                formDiv.remove();
                this.sendMessage(); // This will use the pending message
            } else {
                alert('Please provide at least one contact method');
            }
        };
    }

    showConfirmation() {
        const messages = document.getElementById('chat-messages');
        const typing = document.getElementById('sw-typing');
        
        const confirmDiv = document.createElement('div');
        confirmDiv.className = 'sw-confirmation';
        confirmDiv.innerHTML = `
            <p>✅</p>
            <p style="font-weight:600;">Team Notified!</p>
            <p style="margin:8px 0;">Someone will contact you within 15 minutes.</p>
            <p style="font-size:11px;">Need faster? Call: +8801729103420</p>
        `;
        
        messages.insertBefore(confirmDiv, typing);
        messages.scrollTop = messages.scrollHeight;
    }

    handleContactInput(message) {
        // Check if message looks like an email
        const isEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(message);
        // Check if message looks like a phone number (with or without +)
        const isPhone = /^[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}$/.test(message);
        
        if (isEmail) {
            this.customerEmail = message;
            this.awaitingContact = false;
            this.addMessage('user', message);
            document.getElementById('chat-input').value = '';
            this.callAPI(this.pendingUrgentMessage || "URGENT: Please contact me", true);
        } 
        else if (isPhone) {
            this.customerPhone = message;
            this.awaitingContact = false;
            this.addMessage('user', message);
            document.getElementById('chat-input').value = '';
            this.callAPI(this.pendingUrgentMessage || "URGENT: Please contact me", true);
        }
        else {
            this.addMessage('bot', "Please provide a valid email or phone number (with country code, e.g., +8801XXXXXXXXX) so our team can contact you urgently.");
        }
    }

    showTyping(show) {
        const el = document.getElementById('sw-typing');
        if (show) {
            el.classList.add('visible');
            const msgs = document.getElementById('chat-messages');
            msgs.scrollTop = msgs.scrollHeight;
        } else {
            el.classList.remove('visible');
        }
    }

    addMessage(sender, text) {
        const messages = document.getElementById('chat-messages');
        const typing = document.getElementById('sw-typing');

        const div = document.createElement('div');
        div.className = `sw-msg ${sender}`;

        const avatarIcon = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="4"/><path d="M20 21a8 8 0 1 0-16 0"/></svg>`;
        const userIcon = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#8b879e" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="4"/><path d="M20 21a8 8 0 1 0-16 0"/></svg>`;

        div.innerHTML = `
            <div class="sw-msg-avatar">${sender === 'bot' ? avatarIcon : userIcon}</div>
            <div class="sw-bubble">${this.escapeHtml(text)}</div>
        `;

        messages.insertBefore(div, typing);
        messages.scrollTop = messages.scrollHeight;
    }

    escapeHtml(text) {
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    toggleChat() {
        this.isOpen = !this.isOpen;
        this.window.classList.toggle('open', this.isOpen);
        this.btn.classList.toggle('open', this.isOpen);
        if (this.isOpen) {
            setTimeout(() => document.getElementById('chat-input').focus(), 300);
        }
    }
}

// Initialize widget when page loads
document.addEventListener('DOMContentLoaded', () => {
    // You can change store ID and options here
    window.supportWidget = new SupportWidget('prism_the_store_001', {
        storeName: 'Prism The Store',
        primaryColor: '#304237',
        secondaryColor: '#C4A467'
    });
});
