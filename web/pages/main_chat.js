import { Message } from './message.js';

// Main Chat page, mirroring Tkinter MainChatWindow
export function renderMainChat(container, api) {
    container.innerHTML = `
        <style scoped>
            .chat-container{display:flex;flex-direction:column;flex:1;min-height:0;}
            .scrollable-list{flex:1;min-height:0;overflow-y:auto;margin:0;padding:0;list-style:none;}
            .form-container{display:flex;gap:8px;align-items:center;margin-top:8px;}
            .form-container textarea{flex:1;resize:none;font:inherit;padding:6px 8px;}
            button[disabled]{opacity:0.5;cursor:not-allowed;}
            .loading{text-align:center;padding:1em;color:#888;}
        </style>
        <div class="chat-container">
            <h2>Main Chat</h2>
            <div id="messagesLoading" class="loading" hidden>Loading…</div>
            <ul id="messagesList" class="scrollable-list"></ul>
            <div id="mainChatError" style="color:#ff5252;margin:8px 0 0 0;"></div>
            <div class="form-container">
                <textarea id="messageContent" placeholder="Type a message… (Shift+Enter for new line)" rows="2" autofocus></textarea>
                <button id="sendMessageBtn" disabled>Send</button>
            </div>
        </div>
    `;

    const textarea = container.querySelector('#messageContent');
    const sendBtn = container.querySelector('#sendMessageBtn');

    function updateSendBtnState() {
        sendBtn.disabled = textarea.value.trim().length === 0;
    }
    updateSendBtnState();

    textarea.addEventListener('input', updateSendBtnState);

    textarea.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendBtn.click();
        }
    });

    sendBtn.addEventListener('click', () => sendMessage(api, textarea, sendBtn));

    loadMessages(api);
}

async function sendMessage(api, textarea, sendBtn) {
    const content = textarea.value.trim();
    if (!content) return;
    sendBtn.disabled = true;
    try {
        const r = await api.add_message(content);
        if (r && r.success === false && r.error) {
            document.getElementById('mainChatError').textContent = r.error;
        } else {
            textarea.value = '';
            document.getElementById('mainChatError').textContent = '';
            loadMessages(api);
        }
    } catch (e) {
        document.getElementById('mainChatError').textContent = e.message || 'Failed to send message.';
    } finally {
        sendBtn.disabled = false;
        textarea.focus();
    }
}

function loadMessages(api) {
    const loadingDiv = document.getElementById('messagesLoading');
    if (loadingDiv) loadingDiv.hidden = false;

    if (!api || typeof api.get_all_messages !== 'function') {
        if (loadingDiv) loadingDiv.hidden = true;
        const list = document.getElementById('messagesList');
        list.innerHTML = '<div style="color:#ff5252">API not available. Retrying in 1s...</div>';
        setTimeout(() => loadMessages(api), 1000);
        return;
    }
    api.get_all_messages().then(messages => {
        const ul = document.getElementById('messagesList');
        ul.innerHTML = '';
        if (!messages || !Array.isArray(messages) || messages.length === 0) {
            ul.innerHTML = '<div style="color:#bbb;text-align:center;padding:2em 0">No messages found. Refreshing in 5s...</div>';
            if (loadingDiv) loadingDiv.hidden = true;
            setTimeout(() => loadMessages(api), 5000);
            return;
        }
        messages.forEach(msgData => {
            const msg = new Message(msgData, api);
            ul.appendChild(msg.render());
        });
        // Auto‑scroll to the latest message
        ul.scrollTop = ul.scrollHeight;
        if (loadingDiv) loadingDiv.hidden = true;
    }).catch(e => {
        if (loadingDiv) loadingDiv.hidden = true;
        const list = document.getElementById('messagesList');
        list.innerHTML = `<div style="color:#ff5252">Error loading messages: ${e.message || e}. Retrying every 0.5s...</div>`;
        const retryId = setInterval(() => {
            api.get_all_messages().then(msgs => { clearInterval(retryId); loadMessages(api); }).catch(() => {});
        }, 500);
    });
}

export const __testonly__ = { sendMessage, loadMessages };
