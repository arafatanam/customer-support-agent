class SupportWidget {
  constructor(storeId, options = {}) {
    this.storeId = storeId;
    this.apiUrl = 'https://customer-support-agent-y6qb.onrender.com';
    this.conversationId = "new";
    this.init();
  }

  init() {
    // Create chat button
    const button = document.createElement("button");
    button.innerHTML = "💬 Support";
    button.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            padding: 15px 25px;
            background: #4F46E5;
            color: white;
            border: none;
            border-radius: 50px;
            cursor: pointer;
            font-size: 16px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 9999;
        `;

    // Create chat window (hidden initially)
    this.createChatWindow();

    button.onclick = () => this.toggleChat();
    document.body.appendChild(button);
  }

  createChatWindow() {
    this.window = document.createElement("div");
    this.window.innerHTML = `
            <div style="
                position: fixed;
                bottom: 90px;
                right: 20px;
                width: 350px;
                height: 500px;
                background: white;
                border-radius: 12px;
                box-shadow: 0 8px 24px rgba(0,0,0,0.2);
                display: none;
                flex-direction: column;
                z-index: 9999;
            ">
                <div style="
                    padding: 15px;
                    background: #4F46E5;
                    color: white;
                    border-radius: 12px 12px 0 0;
                ">
                    <strong>Customer Support</strong>
                    <span style="float: right; cursor: pointer;" onclick="widget.toggleChat()">✕</span>
                </div>
                <div id="chat-messages" style="
                    flex: 1;
                    padding: 15px;
                    overflow-y: auto;
                "></div>
                <div style="padding: 15px; border-top: 1px solid #eee;">
                    <input id="chat-input" type="text" placeholder="Type your message..." style="
                        width: 100%;
                        padding: 10px;
                        border: 1px solid #ddd;
                        border-radius: 6px;
                    ">
                    <button onclick="widget.sendMessage()" style="
                        width: 100%;
                        margin-top: 10px;
                        padding: 10px;
                        background: #4F46E5;
                        color: white;
                        border: none;
                        border-radius: 6px;
                        cursor: pointer;
                    ">Send</button>
                </div>
            </div>
        `;

    document.body.appendChild(this.window);
  }

  async sendMessage() {
    const input = document.getElementById("chat-input");
    const message = input.value;
    if (!message) return;

    // Add user message to chat
    this.addMessage("user", message);
    input.value = "";

    // Get AI response
    const response = await fetch(`${this.apiUrl}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: message,
        conversation_id: this.conversationId,
      }),
    });

    const data = await response.json();
    this.conversationId = data.conversation_id;
    this.addMessage("bot", data.response);
  }

  addMessage(sender, text) {
    const messages = document.getElementById("chat-messages");
    const div = document.createElement("div");
    div.style.cssText = `
            margin: 10px 0;
            padding: 10px;
            background: ${sender === "user" ? "#4F46E5" : "#f0f0f0"};
            color: ${sender === "user" ? "white" : "black"};
            border-radius: 10px;
            max-width: 80%;
            float: ${sender === "user" ? "right" : "left"};
            clear: both;
        `;
    div.textContent = text;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
  }

  toggleChat() {
    const chatWindow = this.window.firstChild;
    chatWindow.style.display =
      chatWindow.style.display === "none" ? "flex" : "none";
  }
}

// Initialize widget
const widget = new SupportWidget("store-123");
