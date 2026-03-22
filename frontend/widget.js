class SupportWidget {
    constructor(storeId, options = {}) {
        this.storeId = storeId;
        this.apiUrl = "https://customer-support-agent-y6qb.onrender.com";
        this.conversationId = "new";
        this.isOpen = false;
        this.isTyping = false;

        // Properties for Telegram handoff
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

        document.getElementById("chat-input").addEventListener("keydown", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
    }

    injectStyles() {
        // ... (keep your existing styles)
    }

    createButton() {
        // ... (keep your existing button creation)
    }

    createChatWindow() {
        // ... (keep your existing chat window)
    }

    async sendMessage() {
        const input = document.getElementById("chat-input");
        const message = input.value.trim();
        if (!message || this.isTyping) return;

        console.log("sendMessage called, awaitingContact:", this.awaitingContact);
        console.log("Message:", message);

        // If we're awaiting contact info, handle it directly
        if (this.awaitingContact) {
            console.log("Handling as contact input");
            this.handleContactInput(message);
            return;
        }

        // Check for urgency
        const urgentKeywords = [
            "urgent", "emergency", "asap", "immediately", "quick",
            "speak to human", "talk to person", "real person",
            "help me now", "right now", "joldi", "fast", "quickly",
            "problem", "issue", "serious", "critical", "important",
            "talk to someone", "human", "person", "agent", "support team"
        ];

        const isUrgent = urgentKeywords.some((keyword) =>
            message.toLowerCase().includes(keyword)
        );

        // Show user message
        this.addMessage("user", message);
        input.value = "";
        input.style.height = "20px";

        const sendBtn = document.getElementById("sw-send");
        sendBtn.disabled = true;
        this.isTyping = true;
        this.showTyping(true);

        await this.callAPI(message, isUrgent);

        sendBtn.disabled = false;
    }

    async callAPI(message, isUrgent) {
        try {
            const response = await fetch(`${this.apiUrl}/chat`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: message,
                    conversation_id: this.conversationId,
                    store_id: this.storeId,
                    email: this.customerEmail,
                    phone: this.customerPhone,
                    urgent: isUrgent,
                }),
            });

            const data = await response.json();
            this.conversationId = data.conversation_id;

            this.showTyping(false);

            console.log("API Response:", data);

            // If asking for contact info
            if (data.ask_contact) {
                console.log("Setting awaitingContact to true");
                this.awaitingContact = true;
                this.pendingUrgentMessage = message;
                this.addMessage("bot", data.response);
            }
            // If handoff initiated
            else if (data.handoff_initiated) {
                this.addMessage("bot", data.response);
                this.showConfirmation();
                this.awaitingContact = false;
                this.customerEmail = null;
                this.customerPhone = null;
            }
            // If handoff already active
            else if (data.handoff_active) {
                this.addMessage("bot", data.response);
            }
            else {
                this.addMessage("bot", data.response);
            }
        } catch (error) {
            this.showTyping(false);
            this.addMessage(
                "bot",
                "Something went wrong. Please try again in a moment or call us directly at +8801729103420.",
            );
            console.error("Chat error:", error);
        } finally {
            this.isTyping = false;
            document.getElementById("sw-send").disabled = false;
        }
    }

    handleContactInput(message) {
        console.log("handleContactInput called with:", message);
        
        // Check if message looks like an email
        const isEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(message);
        // Check if message looks like a phone number (Bangladesh format)
        const isPhone = /^(?:\+8801|01)[3-9]\d{8}$/.test(message) || 
                        /^\d{11}$/.test(message) ||
                        /^\+?[0-9\s\-\(\)]{10,15}$/.test(message);
        
        console.log("isEmail:", isEmail, "isPhone:", isPhone);
        
        if (isEmail) {
            this.customerEmail = message;
            this.addMessage("user", message);
            this.awaitingContact = false;
            document.getElementById("chat-input").value = "";
            // Send the original urgent message with contact info
            console.log("Sending urgent request with email:", this.customerEmail);
            this.callAPI(this.pendingUrgentMessage || "URGENT: Please contact me", true);
        } 
        else if (isPhone) {
            this.customerPhone = message;
            this.addMessage("user", message);
            this.awaitingContact = false;
            document.getElementById("chat-input").value = "";
            // Send the original urgent message with contact info
            console.log("Sending urgent request with phone:", this.customerPhone);
            this.callAPI(this.pendingUrgentMessage || "URGENT: Please contact me", true);
        }
        else {
            // Not a valid email or phone, ask again
            this.addMessage("bot", "Please provide a valid email address or phone number (e.g., 01713162795 or +8801713162795) so our team can contact you urgently.");
        }
    }

    showConfirmation() {
        const messages = document.getElementById("chat-messages");
        const typing = document.getElementById("sw-typing");

        const confirmDiv = document.createElement("div");
        confirmDiv.className = "sw-confirmation";
        confirmDiv.innerHTML = `
            <p>✅</p>
            <p style="font-weight:600;">Team Notified!</p>
            <p style="margin:8px 0;">Someone will contact you within 15 minutes.</p>
            <p style="font-size:11px;">Need faster? Call: +8801729103420</p>
        `;

        messages.insertBefore(confirmDiv, typing);
        messages.scrollTop = messages.scrollHeight;
    }

    showTyping(show) {
        const el = document.getElementById("sw-typing");
        if (show) {
            el.classList.add("visible");
            const msgs = document.getElementById("chat-messages");
            msgs.scrollTop = msgs.scrollHeight;
        } else {
            el.classList.remove("visible");
        }
    }

    addMessage(sender, text) {
        const messages = document.getElementById("chat-messages");
        const typing = document.getElementById("sw-typing");

        const div = document.createElement("div");
        div.className = `sw-msg ${sender}`;

        const avatarIcon = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="4"/><path d="M20 21a8 8 0 1 0-16 0"/></svg>`;
        const userIcon = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#8b879e" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="4"/><path d="M20 21a8 8 0 1 0-16 0"/></svg>`;

        div.innerHTML = `
            <div class="sw-msg-avatar">${sender === "bot" ? avatarIcon : userIcon}</div>
            <div class="sw-bubble">${this.escapeHtml(text)}</div>
        `;

        messages.insertBefore(div, typing);
        messages.scrollTop = messages.scrollHeight;
    }

    escapeHtml(text) {
        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    toggleChat() {
        this.isOpen = !this.isOpen;
        this.window.classList.toggle("open", this.isOpen);
        this.btn.classList.toggle("open", this.isOpen);
        if (this.isOpen) {
            setTimeout(() => document.getElementById("chat-input").focus(), 300);
        }
    }
}

// Initialize widget when page loads
document.addEventListener("DOMContentLoaded", () => {
    window.supportWidget = new SupportWidget("prism_the_store_001", {
        storeName: "Prism The Store",
        primaryColor: "#304237",
        secondaryColor: "#C4A467",
    });
});
