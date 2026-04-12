class SupportWidget {
    constructor(storeId, options = {}) {
        this.storeId        = storeId;
        this.apiUrl         = "https://customer-support-agent-y6qb.onrender.com";
        this.conversationId = "new";
        this.isOpen         = false;
        this.isTyping       = false;

        // Handoff state
        this.awaitingContact      = false;
        this.pendingUrgentMessage = '';
        this.handoffActive        = false;
        this.pollInterval         = null;
        this.customerEmail        = null;

        // Branding from options
        this.storeName      = options.storeName      || 'Support';
        this.primaryColor   = options.primaryColor   || '#304237';
        this.secondaryColor = options.secondaryColor || '#C4A467';
        this.position       = options.position       || 'bottom-right';
        this.greeting       = options.greeting       || 'Welcome! How can I help you today?';

        this.init();
    }

    init() {
        this.injectStyles();
        this.createButton();
        this.createChatWindow();

        document.getElementById('sw-chat-input').addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        document.getElementById('sw-send-btn').addEventListener('click', () => this.sendMessage());
    }

    injectStyles() {
        if (document.getElementById('sw-styles')) return;
        const p  = this.primaryColor;
        const s  = this.secondaryColor;
        const pos = this.position === 'bottom-left'
            ? 'left: 24px; right: auto;'
            : 'right: 24px; left: auto;';

        const style = document.createElement('style');
        style.id    = 'sw-styles';
        style.textContent = `
            #sw-btn {
                position: fixed; bottom: 24px; ${pos}
                width: 56px; height: 56px;
                background: ${p}; border: none; border-radius: 50%;
                cursor: pointer; z-index: 999999;
                display: flex; align-items: center; justify-content: center;
                box-shadow: 0 8px 32px rgba(0,0,0,0.28), 0 2px 8px rgba(0,0,0,0.2);
                transition: transform 0.3s cubic-bezier(0.34,1.56,0.64,1), box-shadow 0.3s;
            }
            #sw-btn:hover { transform: scale(1.1); box-shadow: 0 12px 40px rgba(0,0,0,0.35); }
            #sw-btn:active { transform: scale(0.95); }
            #sw-btn svg { transition: transform 0.3s, opacity 0.2s; position: absolute; }
            #sw-btn .sw-icon-open  { }
            #sw-btn .sw-icon-close { opacity: 0; transform: rotate(-90deg) scale(0.7); }
            #sw-btn.open .sw-icon-open  { opacity: 0; transform: rotate(90deg) scale(0.7); }
            #sw-btn.open .sw-icon-close { opacity: 1; transform: rotate(0) scale(1); }

            #sw-window {
                position: fixed; bottom: 96px; ${pos}
                width: 360px; height: 520px;
                background: #fafaf8;
                border-radius: 12px;
                border: 1px solid rgba(0,0,0,0.1);
                box-shadow: 0 24px 72px rgba(0,0,0,0.18), 0 0 0 1px rgba(0,0,0,0.04);
                display: none; flex-direction: column;
                z-index: 999998; overflow: hidden;
                opacity: 0; transform: translateY(12px) scale(0.97);
                transition: opacity 0.3s cubic-bezier(0.16,1,0.3,1), transform 0.3s cubic-bezier(0.16,1,0.3,1);
                font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            }
            #sw-window.open { opacity: 1; transform: translateY(0) scale(1); }
            @media (max-width: 480px) {
                #sw-window {
                    left: 50% !important; right: auto !important;
                    transform: translateX(-50%) translateY(12px) scale(0.97);
                    width: calc(100vw - 32px);
                }
                #sw-window.open { transform: translateX(-50%) translateY(0) scale(1); }
            }

            #sw-header {
                background: ${p}; padding: 16px 18px;
                display: flex; align-items: center; gap: 11px;
                border-bottom: 1px solid rgba(255,255,255,0.1); flex-shrink: 0;
            }
            .sw-h-avatar {
                width: 34px; height: 34px; border-radius: 8px;
                background: rgba(255,255,255,0.15);
                border: 1px solid rgba(255,255,255,0.2);
                display: flex; align-items: center; justify-content: center; flex-shrink: 0;
            }
            .sw-h-name { font-size: 15px; font-weight: 600; color: #fff; letter-spacing: -0.01em; }
            .sw-h-status {
                display: flex; align-items: center; gap: 5px;
                font-size: 11px; color: rgba(255,255,255,0.65); margin-top: 2px;
            }
            .sw-status-dot {
                width: 6px; height: 6px; border-radius: 50%; background: #4ade80;
                animation: sw-blink 2.5s ease-in-out infinite;
            }
            .sw-status-dot.live { background: #4ade80; animation: sw-blink 1s ease-in-out infinite; }
            @keyframes sw-blink { 0%,100%{opacity:1}50%{opacity:0.3} }
            #sw-close-btn {
                margin-left: auto; width: 28px; height: 28px; border-radius: 6px;
                border: 1px solid rgba(255,255,255,0.15); background: rgba(255,255,255,0.08);
                color: rgba(255,255,255,0.7); cursor: pointer;
                display: flex; align-items: center; justify-content: center; transition: all 0.2s;
            }
            #sw-close-btn:hover { background: rgba(255,255,255,0.18); color: #fff; }

            #sw-agent-banner {
                background: ${p}; color: ${s};
                font-size: 11px; text-align: center; padding: 5px 12px;
                letter-spacing: 0.06em; border-bottom: 1px solid rgba(255,255,255,0.1);
                flex-shrink: 0; display: none;
            }
            #sw-agent-banner.visible { display: block; }

            #sw-messages {
                flex: 1; padding: 16px 14px; overflow-y: auto;
                display: flex; flex-direction: column; gap: 10px; background: #fafaf8;
            }
            #sw-messages::-webkit-scrollbar { width: 3px; }
            #sw-messages::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.12); border-radius: 4px; }

            .sw-msg { display: flex; gap: 8px; animation: sw-in 0.3s cubic-bezier(0.16,1,0.3,1); }
            @keyframes sw-in { from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none} }
            .sw-msg.user { flex-direction: row-reverse; }
            .sw-msg-av {
                width: 26px; height: 26px; border-radius: 6px; flex-shrink: 0;
                display: flex; align-items: center; justify-content: center; margin-top: 2px;
            }
            .sw-msg.bot .sw-msg-av { background: ${p}; }
            .sw-msg.user .sw-msg-av { background: rgba(0,0,0,0.06); border: 1px solid rgba(0,0,0,0.08); }
            .sw-bubble {
                max-width: 80%; padding: 10px 13px;
                font-size: 13.5px; line-height: 1.6; font-weight: 400; word-break: break-word;
            }
            .sw-msg.bot .sw-bubble {
                background: #fff; color: #1a1a1a;
                border: 1px solid rgba(0,0,0,0.08); border-radius: 2px 12px 12px 12px;
                box-shadow: 0 1px 4px rgba(0,0,0,0.05);
            }
            .sw-msg.user .sw-bubble {
                background: ${p}; color: #fff;
                border-radius: 12px 2px 12px 12px;
            }

            #sw-typing { display: none; gap: 8px; }
            #sw-typing.visible { display: flex; }
            .sw-typing-bubble {
                background: #fff; border: 1px solid rgba(0,0,0,0.08);
                border-radius: 2px 12px 12px 12px;
                padding: 12px 16px; display: flex; gap: 4px; align-items: center;
            }
            .sw-typing-dot {
                width: 5px; height: 5px; border-radius: 50%;
                background: rgba(0,0,0,0.25); animation: sw-dot 1.4s ease-in-out infinite;
            }
            .sw-typing-dot:nth-child(2){animation-delay:.2s}
            .sw-typing-dot:nth-child(3){animation-delay:.4s}
            @keyframes sw-dot {
                0%,60%,100%{transform:translateY(0);opacity:0.4}
                30%{transform:translateY(-5px);opacity:1}
            }

            .sw-confirm-card {
                background: ${p}; color: #fff;
                border-radius: 10px; padding: 14px 16px;
                font-size: 13px; line-height: 1.6; text-align: center; margin: 4px 0;
                border: 1px solid rgba(255,255,255,0.15);
            }

            #sw-input-area {
                padding: 12px 14px; border-top: 1px solid rgba(0,0,0,0.07);
                background: #fff; flex-shrink: 0;
            }
            #sw-input-row {
                display: flex; align-items: center; gap: 8px;
                background: #f5f5f3; border: 1px solid rgba(0,0,0,0.1);
                border-radius: 10px; padding: 6px 6px 6px 12px;
                transition: border-color 0.2s, box-shadow 0.2s;
            }
            #sw-input-row:focus-within {
                border-color: ${p}55;
                box-shadow: 0 0 0 3px ${p}18;
            }
            #sw-chat-input {
                flex: 1; background: none; border: none; outline: none;
                color: #1a1a1a; font-family: inherit; font-size: 13.5px; line-height: 1.4;
            }
            #sw-chat-input::placeholder { color: #999; }
            #sw-send-btn {
                width: 32px; height: 32px; border-radius: 8px;
                background: ${p}; border: none; cursor: pointer;
                display: flex; align-items: center; justify-content: center; flex-shrink: 0;
                transition: transform 0.2s cubic-bezier(0.34,1.56,0.64,1), opacity 0.2s;
            }
            #sw-send-btn:hover { transform: scale(1.08); }
            #sw-send-btn:active { transform: scale(0.94); }
            #sw-send-btn:disabled { opacity: 0.4; cursor: not-allowed; transform: none; }
            .sw-footer-note {
                text-align: center; font-size: 10px; color: #bbb;
                margin-top: 8px; letter-spacing: 0.05em; text-transform: uppercase;
            }
            .sw-footer-note span { color: ${s}; }
        `;
        document.head.appendChild(style);
    }

    createButton() {
        const btn  = document.createElement('button');
        btn.id     = 'sw-btn';
        btn.setAttribute('aria-label', `Open ${this.storeName} support chat`);
        btn.innerHTML = `
            <svg class="sw-icon-open" width="22" height="22" viewBox="0 0 24 24" fill="none"
                stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
            <svg class="sw-icon-close" width="18" height="18" viewBox="0 0 24 24" fill="none"
                stroke="white" stroke-width="2.5" stroke-linecap="round">
                <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>`;
        btn.addEventListener('click', () => this.toggleChat());
        document.body.appendChild(btn);
        this.btn = btn;
    }

    createChatWindow() {
        const wrap = document.createElement('div');
        wrap.innerHTML = `
            <div id="sw-window" role="dialog" aria-label="${this.storeName} support chat">
                <div id="sw-agent-banner">● Live — connected with a support agent</div>
                <div id="sw-header">
                    <div class="sw-h-avatar">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
                            stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <circle cx="12" cy="8" r="4"/>
                            <path d="M20 21a8 8 0 1 0-16 0"/>
                        </svg>
                    </div>
                    <div>
                        <div class="sw-h-name">${this.storeName}</div>
                        <div class="sw-h-status">
                            <div class="sw-status-dot" id="sw-status-dot"></div>
                            <span id="sw-status-text">Available now</span>
                        </div>
                    </div>
                    <button id="sw-close-btn" aria-label="Close chat">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
                            stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
                            <line x1="18" y1="6" x2="6" y2="18"/>
                            <line x1="6" y1="6" x2="18" y2="18"/>
                        </svg>
                    </button>
                </div>
                <div id="sw-messages">
                    <div class="sw-msg bot">
                        <div class="sw-msg-av">
                            <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
                                stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <circle cx="12" cy="8" r="4"/>
                                <path d="M20 21a8 8 0 1 0-16 0"/>
                            </svg>
                        </div>
                        <div class="sw-bubble">${this.greeting}</div>
                    </div>
                    <div id="sw-typing">
                        <div class="sw-msg-av" style="background:${this.primaryColor};border-radius:6px;
                            width:26px;height:26px;display:flex;align-items:center;
                            justify-content:center;flex-shrink:0;margin-top:2px;">
                            <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
                                stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <circle cx="12" cy="8" r="4"/>
                                <path d="M20 21a8 8 0 1 0-16 0"/>
                            </svg>
                        </div>
                        <div class="sw-typing-bubble">
                            <div class="sw-typing-dot"></div>
                            <div class="sw-typing-dot"></div>
                            <div class="sw-typing-dot"></div>
                        </div>
                    </div>
                </div>
                <div id="sw-input-area">
                    <div id="sw-input-row">
                        <input type="text" id="sw-chat-input"
                            placeholder="Ask us anything…" autocomplete="off"/>
                        <button id="sw-send-btn" aria-label="Send message">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
                                stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                                <line x1="22" y1="2" x2="11" y2="13"/>
                                <polygon points="22 2 15 22 11 13 2 9 22 2"/>
                            </svg>
                        </button>
                    </div>
                    <div class="sw-footer-note">Powered by <span>Avion AI</span></div>
                </div>
            </div>`;
        document.body.appendChild(wrap);

        this.win = document.getElementById('sw-window');
        document.getElementById('sw-close-btn').addEventListener('click', () => this.toggleChat());
    }

    toggleChat() {
        this.isOpen = !this.isOpen;
        this.win.style.display = this.isOpen ? 'flex' : '';
        if (this.isOpen) {
            requestAnimationFrame(() => this.win.classList.add('open'));
            this.btn.classList.add('open');
            setTimeout(() => document.getElementById('sw-chat-input').focus(), 300);
        } else {
            this.win.classList.remove('open');
            this.btn.classList.remove('open');
            setTimeout(() => { this.win.style.display = 'none'; }, 300);
        }
    }

    escapeHtml(text) {
        return String(text)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;')
            .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    addMessage(sender, text) {
        if (!text) return;
        const msgs   = document.getElementById('sw-messages');
        const typing = document.getElementById('sw-typing');
        const div    = document.createElement('div');
        div.className = `sw-msg ${sender}`;

        const botIcon  = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="4"/><path d="M20 21a8 8 0 1 0-16 0"/></svg>`;
        const userIcon = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="rgba(0,0,0,0.4)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="4"/><path d="M20 21a8 8 0 1 0-16 0"/></svg>`;

        div.innerHTML = `
            <div class="sw-msg-av">${sender === 'bot' ? botIcon : userIcon}</div>
            <div class="sw-bubble">${this.escapeHtml(text)}</div>`;
        msgs.insertBefore(div, typing);
        msgs.scrollTop = msgs.scrollHeight;
    }

    showTyping(show) {
        const el = document.getElementById('sw-typing');
        el.classList.toggle('visible', show);
        if (show) document.getElementById('sw-messages').scrollTop = 999999;
    }

    showConfirmation() {
        const msgs   = document.getElementById('sw-messages');
        const typing = document.getElementById('sw-typing');
        const div    = document.createElement('div');
        div.className = 'sw-confirm-card';
        div.innerHTML = `
            <p style="margin:0 0 4px;font-weight:600;">✅ Team Notified!</p>
            <p style="margin:0 0 4px;font-size:12px;">
                A team member will be with you shortly.
            </p>`;
        msgs.insertBefore(div, typing);
        msgs.scrollTop = msgs.scrollHeight;
    }

    setLiveMode(agentName) {
        this.handoffActive = true;
        const banner = document.getElementById('sw-agent-banner');
        if (banner) banner.classList.add('visible');
        const dot  = document.getElementById('sw-status-dot');
        const text = document.getElementById('sw-status-text');
        const inp  = document.getElementById('sw-chat-input');
        if (dot)  dot.classList.add('live');
        if (text) text.textContent = `Chatting with ${agentName || 'support'}`;
        if (inp)  inp.placeholder = 'Reply to agent…';
    }

    looksLikeEmail(v) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v);
    }

    startPolling() {
        if (this.pollInterval) return;
        this.pollInterval = setInterval(async () => {
            if (this.conversationId === 'new') return;
            try {
                const res  = await fetch(`${this.apiUrl}/poll?conversation_id=${this.conversationId}`);
                const data = await res.json();
                if (data.messages && data.messages.length > 0) {
                    data.messages.forEach(msg => {
                        this.addMessage('bot', msg.text);
                        this.setLiveMode(msg.agent);
                    });
                }
            } catch (e) { /* silent */ }
        }, 2500);
    }

    showContactForm() {
        const msgs   = document.getElementById('sw-messages');
        const typing = document.getElementById('sw-typing');
        
        const formDiv = document.createElement('div');
        formDiv.className = 'sw-contact-form';
        formDiv.innerHTML = `
            <p>📧 Could you please provide your email address?</p>
            <input type="email" id="contact-email" class="sw-contact-input" placeholder="Your email address" />
            <button id="submit-contact" class="sw-contact-button">Notify Team →</button>
            <div class="sw-contact-note">We'll notify our team and they'll join this chat</div>
        `;
        
        msgs.insertBefore(formDiv, typing);
        msgs.scrollTop = msgs.scrollHeight;
        
        document.getElementById('submit-contact').onclick = () => {
            const email = document.getElementById('contact-email').value;
            
            if (email && email.includes('@')) {
                this.customerEmail = email;
                this.awaitingContact = false;
                formDiv.remove();
                this.callAPI(this.pendingUrgentMessage || "URGENT: Please contact me", email);
            } else {
                alert('Please provide a valid email address');
            }
        };
    }

    async callAPI(message, contactValue) {
        this.showTyping(true);
        document.getElementById('sw-send-btn').disabled = true;
        this.isTyping = true;

        const isEmail = contactValue && this.looksLikeEmail(contactValue);

        try {
            const res  = await fetch(`${this.apiUrl}/chat`, {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({
                    message,
                    conversation_id: this.conversationId,
                    store_id:        this.storeId,
                    email:           isEmail ? contactValue : this.customerEmail || ''
                })
            });
            const data = await res.json();
            this.showTyping(false);

            if (data.conversation_id) this.conversationId = data.conversation_id;

            if (data.ask_contact) {
                this.awaitingContact      = true;
                this.pendingUrgentMessage = message;
                this.addMessage('bot', data.response);
                this.showContactForm();

            } else if (data.handoff_initiated) {
                this.addMessage('bot', data.response);
                this.showConfirmation();
                this.awaitingContact      = false;
                this.pendingUrgentMessage = '';
                this.startPolling();

            } else if (data.handoff_active) {
                this.startPolling();

            } else {
                this.addMessage('bot', data.response);
            }

        } catch (err) {
            this.showTyping(false);
            this.addMessage('bot', 'Something went wrong. Please try again in a moment.');
            console.error('SupportWidget error:', err);
        } finally {
            this.isTyping = false;
            document.getElementById('sw-send-btn').disabled = false;
        }
    }

    async sendMessage() {
        const input = document.getElementById('sw-chat-input');
        const msg   = input.value.trim();
        if (!msg || this.isTyping) return;

        input.value = '';
        this.addMessage('user', msg);

        if (this.awaitingContact) {
            if (!this.looksLikeEmail(msg)) {
                this.addMessage('bot', 'Please provide a valid email address.');
                return;
            }
            this.awaitingContact = false;
            await this.callAPI(msg, msg);
        } else {
            await this.callAPI(msg, null);
        }
    }
}
