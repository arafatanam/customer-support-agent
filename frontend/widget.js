class SupportWidget {
    constructor(storeId, options = {}) {
        this.storeId = storeId;
        this.apiUrl = 'https://customer-support-agent-y6qb.onrender.com'; // Your backend URL
        this.conversationId = 'new';
        this.init();
    }
    
    init() {
        // Create chat button
        const button = document.createElement('button');
        button.innerHTML = '💬 Support';
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
        // Create container for chat window
        const container = document.createElement('div');
        container.id = 'support-widget-container';
        container.innerHTML = `
            <div id="support-widget-window" style="
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
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            ">
                <div style="
                    padding: 15px;
                    background: #4F46E5;
                    color: white;
                    border-radius: 12px 12px 0 0;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                ">
                    <strong>Customer Support</strong>
                    <span style="cursor: pointer; font-size: 20px;" onclick="document.querySelector('.support-widget-btn').click()">✕</span>
                </div>
                <div id="chat-messages" style="
                    flex: 1;
                    padding: 15px;
                    overflow-y: auto;
                    display: flex;
                    flex-direction: column;
                "></div>
                <div style="padding: 15px; border-top: 1px solid #eee;">
                    <input id="chat-input" type="text" placeholder="Type your message..." style="
                        width: 100%;
                        padding: 10px;
                        border: 1px solid #ddd;
                        border-radius: 6px;
                        box-sizing: border-box;
                        margin-bottom: 10px;
                        font-size: 14px;
                    ">
                    <button onclick="window.supportWidget.sendMessage()" style="
                        width: 100%;
                        padding: 10px;
                        background: #4F46E5;
                        color: white;
                        border: none;
                        border-radius: 6px;
                        cursor: pointer;
                        font-size: 14px;
                    ">Send</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(container);
        this.window = document.getElementById('support-widget-window');
    }
    
    async sendMessage() {
        const input = document.getElementById('chat-input');
        const message = input.value.trim();
        if (!message) return;
        
        // Add user message to chat
        this.addMessage('user', message);
        input.value = '';
        
        try {
            // Get AI response
            const response = await fetch(`${this.apiUrl}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    conversation_id: this.conversationId
                })
            });
            
            const data = await response.json();
            this.conversationId = data.conversation_id;
            this.addMessage('bot', data.response);
        } catch (error) {
            this.addMessage('bot', 'Sorry, I encountered an error. Please try again.');
            console.error('Chat error:', error);
        }
    }
    
    addMessage(sender, text) {
        const messages = document.getElementById('chat-messages');
        const div = document.createElement('div');
        div.style.cssText = `
            margin: 5px 0;
            padding: 10px;
            background: ${sender === 'user' ? '#4F46E5' : '#f0f0f0'};
            color: ${sender === 'user' ? 'white' : 'black'};
            border-radius: 10px;
            max-width: 80%;
            align-self: ${sender === 'user' ? 'flex-end' : 'flex-start'};
            word-wrap: break-word;
        `;
        div.textContent = text;
        messages.appendChild(div);
        messages.scrollTop = messages.scrollHeight;
    }
    
    toggleChat() {
        if (this.window) {
            const isHidden = this.window.style.display === 'none' || this.window.style.display === '';
            this.window.style.display = isHidden ? 'flex' : 'none';
        }
    }
}

// Initialize widget when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.supportWidget = new SupportWidget('store-123');
});
