class SupportWidget {
  constructor(storeId, options = {}) {
    this.storeId = storeId;
    this.apiUrl = "https://customer-support-agent-y6qb.onrender.com";
    this.conversationId = "new";
    this.isOpen = false;
    this.isTyping = false;

    this.awaitingContact = false;
    this.pendingUrgentMessage = "";
    this.handoffActive = false;
    this.pollInterval = null;
    this.clientEmail = null;

    this.storeName = options.storeName || "Support";
    this.primaryColor = options.primaryColor || "#2a5ff5";
    this.secondaryColor = options.secondaryColor || "#5b85ff";
    this.accentColor = "#5b85ff";
    this.position = options.position || "bottom-right";
    this.greeting = options.greeting || "Welcome! How can I help you today?";

    this.init();
  }

  init() {
    this.injectStyles();
    this.createButton();
    this.createChatWindow();

    document
      .getElementById("sw-chat-input")
      .addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          this.sendMessage();
        }
      });
    document
      .getElementById("sw-send-btn")
      .addEventListener("click", () => this.sendMessage());
  }

  formatMarkdown(text) {
    text = text.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    text = text.replace(/__(.*?)__/g, "<strong>$1</strong>");
    text = text.replace(/\*(.*?)\*/g, "<em>$1</em>");
    text = text.replace(/_(.*?)_/g, "<em>$1</em>");
    text = text.replace(/\n/g, "<br>");
    return text;
  }

  injectStyles() {
    if (document.getElementById("sw-styles")) return;
    const p = this.primaryColor;
    const s = this.secondaryColor;
    const a = this.accentColor;
    const pos =
      this.position === "bottom-left"
        ? "left: 24px; right: auto;"
        : "right: 24px; left: auto;";

    const style = document.createElement("style");
    style.id = "sw-styles";
    style.textContent = `
      @import url('https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,300;14..32,400;14..32,500;14..32,600;14..32,700&display=swap');

      /* ── LAUNCH BUTTON ──────────────────────────────────── */
      #sw-btn {
        position: fixed;
        bottom: 24px;
        ${pos}
        width: 56px;
        height: 56px;
        background: linear-gradient(135deg, ${p}, ${a});
        border: none;
        border-radius: 18px;
        cursor: pointer;
        z-index: 999999;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 10px 28px -5px rgba(0, 0, 0, 0.3), 0 0 0 1px rgba(255,255,255,0.08);
        transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
        backdrop-filter: blur(4px);
      }
      #sw-btn::before {
        content: '';
        position: absolute;
        inset: 0;
        border-radius: 18px;
        background: linear-gradient(135deg, rgba(255,255,255,0.2), transparent);
        opacity: 0;
        transition: opacity 0.3s;
        pointer-events: none;
      }
      #sw-btn:hover {
        transform: scale(1.08) translateY(-3px);
        box-shadow: 0 20px 40px -8px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(255,255,255,0.15);
        border-radius: 22px;
      }
      #sw-btn:hover::before { opacity: 1; }
      #sw-btn:active { transform: scale(0.96); }
      #sw-btn svg { 
        transition: all 0.35s cubic-bezier(0.34, 1.56, 0.64, 1); 
        position: absolute;
        filter: drop-shadow(0 2px 4px rgba(0,0,0,0.2));
      }
      #sw-btn .sw-icon-open { opacity: 1; transform: scale(1) rotate(0deg); }
      #sw-btn .sw-icon-close { opacity: 0; transform: scale(0.5) rotate(-90deg); }
      #sw-btn.open .sw-icon-open { opacity: 0; transform: scale(0.5) rotate(90deg); }
      #sw-btn.open .sw-icon-close { opacity: 1; transform: scale(1) rotate(0deg); }

      /* ── CHAT WINDOW ────────────────────────────────────── */
      #sw-window {
        position: fixed;
        bottom: 96px;
        ${pos}
        width: 380px;
        height: 560px;
        background: rgba(8, 8, 26, 0.92);
        backdrop-filter: blur(24px);
        border-radius: 24px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 32px 80px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(255, 255, 255, 0.05);
        display: none;
        flex-direction: column;
        z-index: 999998;
        overflow: hidden;
        opacity: 0;
        transform: translateY(20px) scale(0.96);
        transition: opacity 0.35s cubic-bezier(0.16, 1, 0.3, 1), transform 0.35s cubic-bezier(0.16, 1, 0.3, 1);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      }
      #sw-window.open { opacity: 1; transform: translateY(0) scale(1); }

      @media (max-width: 480px) {
        #sw-window {
          left: 50% !important;
          right: auto !important;
          transform: translateX(-50%) translateY(20px) scale(0.96);
          width: calc(100vw - 28px);
        }
        #sw-window.open { transform: translateX(-50%) translateY(0) scale(1); }
      }

      /* ── HEADER ─────────────────────────────────────────── */
      #sw-header {
        background: rgba(12, 12, 34, 0.95);
        padding: 18px 20px;
        display: flex;
        align-items: center;
        gap: 12px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.06);
        flex-shrink: 0;
        position: relative;
      }
      #sw-header::after {
        content: '';
        position: absolute;
        bottom: -1px;
        left: 20px;
        right: 20px;
        height: 1px;
        background: linear-gradient(90deg, transparent, ${p}, ${a}, transparent);
      }

      .sw-h-avatar {
        width: 40px;
        height: 40px;
        border-radius: 14px;
        background: linear-gradient(135deg, ${p}, ${a});
        border: 1px solid rgba(255, 255, 255, 0.12);
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.2);
      }

      .sw-h-name {
        font-size: 15px;
        font-weight: 600;
        color: #eef0ff;
        letter-spacing: -0.01em;
      }
      .sw-h-status {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 11px;
        color: rgba(255, 255, 255, 0.4);
        margin-top: 3px;
      }
      .sw-status-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: #3ddc84;
        animation: sw-blink 2.5s ease-in-out infinite;
        box-shadow: 0 0 6px rgba(61, 220, 132, 0.6);
      }
      .sw-status-dot.live {
        background: #3ddc84;
        animation: sw-blink 0.9s ease-in-out infinite;
        box-shadow: 0 0 10px rgba(61, 220, 132, 0.8);
      }
      @keyframes sw-blink { 0%,100%{opacity:1}50%{opacity:0.3} }

      #sw-close-btn {
        margin-left: auto;
        width: 30px;
        height: 30px;
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        background: rgba(255, 255, 255, 0.03);
        color: rgba(255, 255, 255, 0.4);
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.25s;
      }
      #sw-close-btn:hover {
        background: rgba(255, 255, 255, 0.1);
        color: #fff;
        border-color: rgba(255, 255, 255, 0.2);
      }

      /* ── AGENT BANNER ───────────────────────────────────── */
      #sw-agent-banner {
        background: linear-gradient(135deg, rgba(42, 95, 245, 0.15), rgba(139, 92, 246, 0.1));
        color: #a0bcff;
        font-size: 11px;
        text-align: center;
        padding: 8px 14px;
        letter-spacing: 0.05em;
        border-bottom: 1px solid rgba(42, 95, 245, 0.2);
        flex-shrink: 0;
        display: none;
        font-weight: 500;
      }
      #sw-agent-banner.visible { display: block; }

      /* ── MESSAGES ───────────────────────────────────────── */
      #sw-messages {
        flex: 1;
        padding: 18px 16px;
        overflow-y: auto;
        display: flex;
        flex-direction: column;
        gap: 12px;
        background: transparent;
      }
      #sw-messages::-webkit-scrollbar { width: 3px; }
      #sw-messages::-webkit-scrollbar-track { background: transparent; }
      #sw-messages::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.08); border-radius: 4px; }

      .sw-msg {
        display: flex;
        gap: 10px;
        animation: sw-in 0.3s cubic-bezier(0.16, 1, 0.3, 1);
      }
      @keyframes sw-in { from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none} }
      .sw-msg.client { flex-direction: row-reverse; }

      .sw-msg-av {
        width: 28px;
        height: 28px;
        border-radius: 10px;
        flex-shrink: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-top: 2px;
      }
      .sw-msg.bot .sw-msg-av {
        background: linear-gradient(135deg, ${p}, ${a});
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
      }
      .sw-msg.client .sw-msg-av {
        background: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(255, 255, 255, 0.08);
      }

      .sw-bubble {
        max-width: 78%;
        padding: 10px 14px;
        font-size: 13px;
        line-height: 1.55;
        font-weight: 400;
        word-break: break-word;
      }
      .sw-msg.bot .sw-bubble {
        background: rgba(18, 18, 40, 0.9);
        color: #cdd0ee;
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 4px 16px 16px 16px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
      }
      .sw-msg.client .sw-bubble {
        background: linear-gradient(135deg, ${p}, ${a});
        color: #fff;
        border-radius: 16px 4px 16px 16px;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.2);
      }

      /* ── TYPING INDICATOR ───────────────────────────────── */
      #sw-typing { display: none; gap: 10px; }
      #sw-typing.visible { display: flex; }
      .sw-typing-bubble {
        background: rgba(18, 18, 40, 0.9);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 4px 16px 16px 16px;
        padding: 12px 18px;
        display: flex;
        gap: 5px;
        align-items: center;
      }
      .sw-typing-dot {
        width: 5px;
        height: 5px;
        border-radius: 50%;
        background: rgba(91, 133, 255, 0.6);
        animation: sw-dot 1.4s ease-in-out infinite;
      }
      .sw-typing-dot:nth-child(2){animation-delay:.2s}
      .sw-typing-dot:nth-child(3){animation-delay:.4s}
      @keyframes sw-dot {
        0%,60%,100%{transform:translateY(0);opacity:0.4}
        30%{transform:translateY(-6px);opacity:1}
      }

      /* ── CONFIRMATION CARD ───────────────────────────────── */
      .sw-confirm-card {
        background: linear-gradient(135deg, rgba(42, 95, 245, 0.12), rgba(139, 92, 246, 0.08));
        border: 1px solid rgba(42, 95, 245, 0.25);
        border-radius: 14px;
        padding: 14px 18px;
        font-size: 13px;
        line-height: 1.6;
        text-align: center;
        margin: 6px 0;
        color: #a0bcff;
      }

      /* ── INPUT AREA ─────────────────────────────────────── */
      #sw-input-area {
        padding: 14px 16px;
        border-top: 1px solid rgba(255, 255, 255, 0.05);
        background: rgba(12, 12, 34, 0.95);
        flex-shrink: 0;
      }
      #sw-input-row {
        display: flex;
        align-items: center;
        gap: 10px;
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 6px 6px 6px 16px;
        transition: all 0.25s;
      }
      #sw-chat-input {
        flex: 1;
        background: none;
        border: 1px solid transparent;
        outline: none;
        color: #eef0ff;
        font-family: 'Inter', sans-serif;
        font-size: 13.5px;
        line-height: 1.4;
        border-radius: 12px;
        padding: 12px 16px;
        transition: border-color 0.25s;
      }
      #sw-chat-input:focus {
        border-color: ${p};
      }
      #sw-chat-input::placeholder {
        color: rgba(255, 255, 255, 0.25);
        border-color: ${p};
      }
      #sw-send-btn {
        width: 34px;
        height: 34px;
        border-radius: 12px;
        background: linear-gradient(135deg, ${p}, ${a});
        border: none;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
      }
      #sw-send-btn:hover {
        transform: scale(1.08);
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.3);
      }
      #sw-send-btn:active { transform: scale(0.94); }
      #sw-send-btn:disabled { opacity: 0.35; cursor: not-allowed; transform: none; }

      .sw-footer-note {
        text-align: center;
        font-size: 10px;
        color: rgba(255, 255, 255, 0.18);
        margin-top: 10px;
        letter-spacing: 0.06em;
        text-transform: uppercase;
      }
      .sw-footer-note span { 
        background: linear-gradient(135deg, ${p}, ${a});
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
      }
    `;
    document.head.appendChild(style);
  }

  createButton() {
    const btn = document.createElement("button");
    btn.id = "sw-btn";
    btn.setAttribute("aria-label", `Open ${this.storeName} support chat`);
    btn.innerHTML = `
      <svg class="sw-icon-open" width="20" height="20" viewBox="0 0 24 24" fill="none"
          stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
      </svg>
      <svg class="sw-icon-close" width="16" height="16" viewBox="0 0 24 24" fill="none"
          stroke="white" stroke-width="2.5" stroke-linecap="round">
          <line x1="18" y1="6" x2="6" y2="18"/>
          <line x1="6" y1="6" x2="18" y2="18"/>
      </svg>`;
    btn.addEventListener("click", () => this.toggleChat());
    document.body.appendChild(btn);
    this.btn = btn;
  }

  createChatWindow() {
    const wrap = document.createElement("div");
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
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none"
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
            <div class="sw-msg-av" style="background:linear-gradient(135deg,${this.primaryColor},${this.accentColor});
            border-radius:10px; 
            width:28px;
            height:28px;
            display:flex;
            align-items:center;
            justify-content:center;
            flex-shrink:0;
            margin-top:2px;">
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
                placeholder="Ask me anything…" autocomplete="off"/>
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

    this.win = document.getElementById("sw-window");
    document
      .getElementById("sw-close-btn")
      .addEventListener("click", () => this.toggleChat());
  }

  toggleChat() {
    this.isOpen = !this.isOpen;
    this.win.style.display = this.isOpen ? "flex" : "";
    if (this.isOpen) {
      requestAnimationFrame(() => this.win.classList.add("open"));
      this.btn.classList.add("open");
      setTimeout(() => document.getElementById("sw-chat-input").focus(), 300);
    } else {
      this.win.classList.remove("open");
      this.btn.classList.remove("open");
      setTimeout(() => {
        this.win.style.display = "none";
      }, 350);
    }
  }

  escapeHtml(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  addMessage(sender, text) {
    if (!text) return;
    const msgs = document.getElementById("sw-messages");
    const typing = document.getElementById("sw-typing");
    const div = document.createElement("div");
    div.className = `sw-msg ${sender}`;

    const botIcon = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="4"/><path d="M20 21a8 8 0 1 0-16 0"/></svg>`;
    const clientIcon = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.4)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="4"/><path d="M20 21a8 8 0 1 0-16 0"/></svg>`;

    const formattedText =
      sender === "bot" ? this.formatMarkdown(text) : this.escapeHtml(text);
    div.innerHTML = `
      <div class="sw-msg-av">${sender === "bot" ? botIcon : clientIcon}</div>
      <div class="sw-bubble">${formattedText}</div>`;
    msgs.insertBefore(div, typing);
    msgs.scrollTop = msgs.scrollHeight;
  }

  showTyping(show) {
    const el = document.getElementById("sw-typing");
    el.classList.toggle("visible", show);
    if (show) document.getElementById("sw-messages").scrollTop = 999999;
  }

  showConfirmation() {
    const msgs = document.getElementById("sw-messages");
    const typing = document.getElementById("sw-typing");
    const div = document.createElement("div");
    div.className = "sw-confirm-card";
    div.innerHTML = `
      <p style="margin:0 0 4px;font-weight:600;color:#eef0ff;">✅ Team Notified</p>
      <p style="margin:0;font-size:12px;color:#a0bcff;">Our team will join this chat shortly.</p>`;
    msgs.insertBefore(div, typing);
    msgs.scrollTop = msgs.scrollHeight;
  }

  setLiveMode(agentName) {
    this.handoffActive = true;
    const banner = document.getElementById("sw-agent-banner");
    if (banner) banner.classList.add("visible");
    const dot = document.getElementById("sw-status-dot");
    const text = document.getElementById("sw-status-text");
    const inp = document.getElementById("sw-chat-input");
    if (dot) dot.classList.add("live");
    if (text) text.textContent = `Chatting with ${agentName || "support"}`;
    if (inp) inp.placeholder = "Reply to agent…";
  }

  looksLikeEmail(v) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.trim());
  }

  startPolling() {
    if (this.pollInterval) return;
    console.log('Polling started for conv:', this.conversationId);
    this.pollInterval = setInterval(async () => {
      if (this.conversationId === "new") return;
      try {
        const res = await fetch(
          `${this.apiUrl}/poll?conversation_id=${this.conversationId}`,
        );
        const data = await res.json();
        if (data.messages && data.messages.length > 0) {
          data.messages.forEach((msg) => {
            this.addMessage("bot", msg.text);
            this.setLiveMode(msg.agent);
          });
        }
      } catch (e) {
        /* silent */
      }
    }, 2500);
  }

  async callAPI(message) {
    this.showTyping(true);
    document.getElementById("sw-send-btn").disabled = true;

    try {
      const res = await fetch(`${this.apiUrl}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message,
          conversation_id: this.conversationId,
          store_id: this.storeId,
          email: this.clientEmail || "",
        }),
      });
      const data = await res.json();
      this.showTyping(false);

      if (data.conversation_id) this.conversationId = data.conversation_id;

      if (data.ask_contact) {
        // Urgency detected — start polling IMMEDIATELY so agent messages appear
        // even before the customer submits their email
        this.awaitingContact = true;
        this.pendingUrgentMessage = message;
        this.addMessage("bot", data.response);
        this.startPolling(); // ← FIX: Start polling right away
      } else if (data.handoff_initiated) {
        this.addMessage("bot", data.response);
        this.showConfirmation();
        this.awaitingContact = false;
        this.pendingUrgentMessage = "";
        this.startPolling();
      } else if (data.handoff_active) {
        this.startPolling();
      } else if (data.response) {
        this.addMessage("bot", data.response);
      } else if (data.error) {
        this.addMessage(
          "bot",
          "Sorry, something went wrong. Please try again.",
        );
      }
    } catch (err) {
      this.showTyping(false);
      this.addMessage(
        "bot",
        "Something went wrong. Please try again in a moment.",
      );
      console.error("SupportWidget error:", err);
    } finally {
      this.isTyping = false;
      document.getElementById("sw-send-btn").disabled = false;
    }
  }

  async sendMessage() {
    const input = document.getElementById("sw-chat-input");
    const msg = input.value.trim();

    // Guard against rapid submissions
    if (!msg || this.isTyping) return;
    this.isTyping = true;
    document.getElementById("sw-send-btn").disabled = true;

    input.value = "";
    this.addMessage("client", msg);

    if (this.awaitingContact) {
      if (!this.looksLikeEmail(msg)) {
        this.addMessage(
          "bot",
          "Please provide a valid email address (e.g. you@example.com).",
        );
        this.isTyping = false;
        document.getElementById("sw-send-btn").disabled = false;
        return;
      }
      this.clientEmail = msg;
      this.awaitingContact = false;
      await this.callAPI(msg);
    } else {
      await this.callAPI(msg);
    }
  }
}
