// Model Chat Sidebar component for contextual model chat in Main Chat and Project Chat
// Mirrors Tkinter WidgetModelChat logic, but in web version

export function renderModelChatSidebar(container, context = {}) {
    container.innerHTML = `
        <style scoped>
            .model-chat-sidebar { width: 350px; min-width: 350px; background: #262a34; border-left: 1px solid #363b47; display: flex; flex-direction: column; height: 100%; position: absolute; top: 0; right: 0; bottom: 0; }
            .model-chat-sidebar-inner { display: flex; flex-direction: column; flex: 1; min-height: 0; padding: 1em; box-sizing: border-box; }
            .model-chat-sidebar h3 { margin: 0 0 0.7em 0; color: #f7f7fa; font-size: 1.25em; }
            .model-chat-mode-row { margin-bottom: 0.7em; display: flex; align-items: center; gap: 0.7em; }
            #modelChatMessages { flex: 1; overflow-y: auto; background: #23272e; border-radius: 6px; padding: 0.7em; font-size: 0.97em; color: #e3e3e3; min-height: 0; }
            .message-item { margin-bottom: 0.6em; padding: 0.5em 1em 0.5em 0.7em; border-radius: 5px; word-wrap: break-word; max-width: 100%; box-sizing: border-box; }
            .user-message { background: #303540; }
            .model-message { background: #282c34; }
            .message-role { font-weight: bold; margin-bottom: 0.3em; display: block; }
            .user-role { color: #6cf; }
            .model-role { color: #ffb347; }
            .message-explanation { color: #b5b5c7; margin-top: 0.3em; font-style: italic; }
            .view-original-link { color: #8af; cursor: pointer; text-decoration: underline; margin-left: 0.5em; font-size: 0.9em; }
            .model-chat-input-row { display: flex; flex-wrap: nowrap; gap: 8px; align-items: center; margin-top: 0.7em; }
            .model-chat-input-row input { flex: 1; min-width: 150px; padding: 0.5em 0.8em; border-radius: 4px; border: 1px solid #44495a; background: #23272e; color: #fff; }
            .model-chat-input-row button { background: #3578e5; color: #fff; border: none; border-radius: 4px; padding: 0.5em 1.2em; font-weight: bold; cursor: pointer; white-space: nowrap; }
            .model-chat-input-row .toggle { display: flex; align-items: center; gap: 0.3em; font-size: 0.97em; color: #c9c9d9; }
            .sidebar-project-name { font-size: 0.85em; color: #b0b0c0; font-weight: normal; margin-left: 0.3em; }
            .selected-message-item { padding: 0.5em 1em 0.5em 0.7em; border-radius: 5px; word-wrap: break-word; max-width: 100%; box-sizing: border-box; }
            .likelihood-high { background: #282c34; }
            .likelihood-low { background: #303540; }
        </style>
        <div class="model-chat-sidebar">
            <div class="model-chat-sidebar-inner">
                <h3>Model Chat${context.project ? ` <span class=\"sidebar-project-name\">– ${context.project.name}</span>` : ''}</h3>
                <div class="model-chat-mode-row">
                    <label for="modelModeSelect">Mode:</label>
                    <select id="modelModeSelect">
                        <option value="select">Select Messages</option>
                        <option value="generic">Generic Prompt</option>
                    </select>
                </div>
                <div id="modelChatMessages"></div>
                <div class="model-chat-input-row">
                    <input id="modelChatInput" type="text" placeholder="Ask the model...">
                    <button id="modelChatSendBtn">Send</button>
                    <span class="toggle"><input type="checkbox" id="useHistoryToggle"><label for="useHistoryToggle">Use History</label></span>
                </div>
            </div>
        </div>
    `;

    const messagesDiv = container.querySelector('#modelChatMessages');
    const input = container.querySelector('#modelChatInput');
    const sendBtn = container.querySelector('#modelChatSendBtn');
    const useHistoryToggle = container.querySelector('#useHistoryToggle');
    const modeSelect = container.querySelector('#modelModeSelect');

    let chatHistory = []; // Keep track of raw history for generic chat

    function renderMessage(role, content) {
        // Add to internal history *only* for generic chat context
        if (role === 'user' || (role === 'model' && modeSelect.value === 'generic')) {
             chatHistory.push({ role: role === 'user' ? 'user' : 'model', content: content });
        }

        const item = document.createElement('div');
        item.className = `message-item ${role}-message`;
        item.innerHTML = `<span class="message-role ${role}-role">${role === 'user' ? 'You' : 'Model'}:</span><div>${content}</div>`;

        // Attach click handler if it's a model message containing a link
        const link = item.querySelector('.view-original-link');
        if (link) {
            link.addEventListener('click', () => {
                const id = link.dataset.msgId;
                console.log(`[Sidebar] Link clicked for msgId: ${id}, context project:`, context.project);
                // Determine current chat context
                const inProjectChat = window.selectedProject && context.project && window.selectedProject.name === context.project.name;
                const inMainChat = !context.project && (!window.selectedProject || !window.selectedProject.name);
                // Navigate only if not already in the correct chat
                if (context.project && !inProjectChat) {
                    window.nav.projectChat(context.project);
                } else if (!context.project && !inMainChat) {
                    window.nav.mainChat();
                }
                // Use the improved scrollToMessage function directly
                window.scrollToMessage(id);
            });
        }

        messagesDiv.appendChild(item);
        messagesDiv.scrollTop = messagesDiv.scrollHeight; // Auto-scroll
    }

    sendBtn.onclick = async () => {
        const prompt = input.value.trim();
        if (!prompt) return;
        renderMessage('user', prompt);
        input.value = '';
        sendBtn.disabled = true;
        let responseContent = '';
        try {
            if (modeSelect.value === 'select') {
                // Call backend Gemini select messages
                const allMessages = await window.pywebview?.api?.get_all_messages(context.project?.name || null) || [];
                const msgText = allMessages.map(m => m.content).join('\n');
                const res = await window.pywebview?.api?.model_select_messages(prompt, msgText);
                let related = [];
                if (res && res.result) {
                    try {
                        const data = JSON.parse(res.result);
                        related = data.messages || [];
                    } catch (e) { related = []; console.error('Error parsing related messages:', e); }
                }
                if (related.length > 0) {
                    related.forEach(m => {
                        // m is now: { id, content_preview, first_words_model_raw, first_words_model_compared_segment, first_words_actual_compared_segment, explanation, likelihood, original_message_data }
                        const safeContentPreview = (m.content_preview || '').replace(/</g, "&lt;").replace(/>/g, "&gt;");
                        const safeExplanation = (m.explanation || '').replace(/</g, "&lt;").replace(/>/g, "&gt;");
                        const safeModelFirstWords = (m.first_words_model_raw || '').replace(/</g, "&lt;").replace(/>/g, "&gt;");
                        
                        let likelihoodIndicator = '';
                        let likelihoodClass = 'likelihood-high'; // CSS class for styling
                        if (m.likelihood === 'less likely') {
                            likelihoodIndicator = '<span style="color:orange; font-style:italic; font-size:0.9em;">(Less Likely Match)</span> ';
                            likelihoodClass = 'likelihood-low';
                        }

                        const displayContent = safeContentPreview.length > 150 ? safeContentPreview.substring(0, 150) + '...' : safeContentPreview;

                        const messageHtml = `
                            <div class="selected-message-item ${likelihoodClass}">
                                ${likelihoodIndicator}
                                <div><strong>ID:</strong> ${m.id}</div>
                                <div><strong>Preview:</strong> ${displayContent}</div>
                                <div class="message-explanation"><strong>Explanation:</strong> ${safeExplanation}</div>
                                <div><small><em>Model claimed first words: "${safeModelFirstWords}"</em></small></div>
                                <span class="view-original-link" data-msg-id="${m.id}">(view original)</span>
                            </div>
                        `;
                        
                        renderMessage('model', messageHtml); // Pass the HTML string to renderMessage
                    });
                } else {
                     renderMessage('model', 'No specific messages selected based on your prompt.');
                }
            } else {
                // Generic prompt
                const res = await window.pywebview?.api?.model_chat(prompt, context.project?.name || null, useHistoryToggle.checked, chatHistory.filter(m => m.role !== 'system'));
                responseContent = res?.response || 'No response received from model.';
                renderMessage('model', responseContent);
            }
        } catch (e) {
            responseContent = 'Error processing request: ' + (e.message || e);
            renderMessage('model', `<span style="color:#ff5252;">${responseContent}</span>`);
            console.error('Model chat error:', e);
        }
        sendBtn.disabled = false;
        input.focus();
    };

    input.addEventListener('keydown', e => {
        if (e.key === 'Enter') sendBtn.click();
    });
}
