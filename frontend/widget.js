async sendMessage() {
    const input = document.getElementById("chat-input");
    const message = input.value.trim();
    if (!message || this.isTyping) return;

    // If we're awaiting contact info, handle it directly
    if (this.awaitingContact) {
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

        // If asking for contact info
        if (data.ask_contact) {
            this.awaitingContact = true;
            this.pendingUrgentMessage = message;
            this.addMessage("bot", data.response);
        }
        // If handoff initiated
        else if (data.handoff_initiated) {
            this.addMessage("bot", data.response);
            this.showConfirmation();
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
    // Check if message looks like an email
    const isEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(message);
    // Check if message looks like a phone number (Bangladesh format)
    const isPhone = /^(?:\+8801|01)[3-9]\d{8}$/.test(message) || 
                    /^\d{11}$/.test(message) ||
                    /^\+?[0-9\s\-\(\)]{10,15}$/.test(message);
    
    if (isEmail) {
        this.customerEmail = message;
        this.addMessage("user", message);
        this.awaitingContact = false;
        document.getElementById("chat-input").value = "";
        // Send the original urgent message with contact info
        this.callAPI(this.pendingUrgentMessage || "URGENT: Please contact me", true);
    } 
    else if (isPhone) {
        this.customerPhone = message;
        this.addMessage("user", message);
        this.awaitingContact = false;
        document.getElementById("chat-input").value = "";
        // Send the original urgent message with contact info
        this.callAPI(this.pendingUrgentMessage || "URGENT: Please contact me", true);
    }
    else {
        // Not a valid email or phone, ask again
        this.addMessage("bot", "Please provide a valid email address or phone number (e.g., 01713162795 or +8801713162795) so our team can contact you urgently.");
    }
}
