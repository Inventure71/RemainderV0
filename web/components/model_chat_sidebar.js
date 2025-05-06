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
            .view-original-link { color: #8af; cursor: pointer; text-decoration: underline; margin-left: 0.5em; font-size: 0.9em; display: block; margin-top: 4px; }
            .model-chat-input-row { display: flex; flex-wrap: nowrap; gap: 8px; align-items: center; margin-top: 0.7em; }
            .model-chat-input-row input { flex: 1; min-width: 150px; padding: 0.5em 0.8em; border-radius: 4px; border: 1px solid #44495a; background: #23272e; color: #fff; }
            .model-chat-input-row button { background: #3578e5; color: #fff; border: none; border-radius: 4px; padding: 0.5em 1.2em; font-weight: bold; cursor: pointer; white-space: nowrap; }
            .model-chat-input-row .toggle { display: flex; align-items: center; gap: 0.3em; font-size: 0.97em; color: #c9c9d9; }
            .sidebar-project-name { font-size: 0.85em; color: #b0b0c0; font-weight: normal; margin-left: 0.3em; }
            .selected-message-content-item { padding: 0.4em; border-radius: 4px; }
            .selected-message-item { border-radius: 5px; word-wrap: break-word; max-width: 100%; box-sizing: border-box; cursor: pointer; }
            .likelihood-high { background: #282c34; }
            .likelihood-low { background: #3a3f4b; border-left: 3px solid orange; padding-left: 0.5em; }
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

    function renderMessage(role, content, msgIdForLink = null, targetProjectNameForLink = null) {
        // Add to internal history *only* for generic chat context
        if (!msgIdForLink) { // Only track normal messages, not selected ones
            chatHistory.push({role, content});
        }

        const item = document.createElement('div');
        if (role === 'user') {
            item.classList.add('user-message', 'message-item');
            item.innerHTML = `
                <div class="user-icon">👤</div>
                <div class="message-content">${content}</div>
            `;
        } else if (role === 'model') {
            item.classList.add('model-message', 'message-item');
            let formattedContent = content;
            if (typeof content === 'string') {
                formattedContent = content.replace(/\n/g, '<br>');
            }
            item.innerHTML = `
                <div class="model-icon">🤖</div>
                <div class="message-content">${formattedContent}</div>
            `;
        } else if (role === 'selected') {
            // For selected messages from model_select_messages response
            item.classList.add('selected-message-item', 'message-item');
            item.innerHTML = `
                <div class="selected-message-content-item">${content}</div>
            `;
        }

        // Attach click handler for navigation if msgIdForLink is provided (for selected items)
        if (msgIdForLink) {
            item.style.cursor = 'pointer'; // Explicitly set cursor for the whole item
            item.addEventListener('click', () => {
                console.log(`[Sidebar] Clicked selected item for msgId: ${msgIdForLink}, target project: ${targetProjectNameForLink}`);
                const currentSidebarProjectName = context.project?.name;

                if (targetProjectNameForLink && targetProjectNameForLink !== "null" && targetProjectNameForLink !== "undefined") { // Message is in a specific project
                    if (currentSidebarProjectName !== targetProjectNameForLink) {
                        const projectToNav = window.ALL_PROJECTS_CACHE?.find(p => p.name === targetProjectNameForLink);
                        if (projectToNav) {
                            window.nav.projectChat(projectToNav);
                        } else {
                            console.warn(`Project object for '${targetProjectNameForLink}' not found for navigation. Cannot switch views.`);
                            // Attempt to scroll anyway if view switch fails but somehow context is right (unlikely)
                        }
                    } // else: already in the correct project view
                } else { // Message is in main chat (targetProjectNameForLink is null, undefined, or empty string)
                    if (currentSidebarProjectName) { // If sidebar is currently in a project view, switch to main chat
                        window.nav.mainChat();
                    }
                    // else: already in main chat view or main chat context in sidebar
                }
                setTimeout(() => window.scrollToMessage(msgIdForLink), 100); // Delay for view switch
            });
        }

        messagesDiv.appendChild(item);
        
        // Auto-scroll to the latest message (bottom)
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
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
                console.log("[Sidebar onClick] Context object:", context);
                if (context && context.project) {
                    console.log("[Sidebar onClick] context.project object:", context.project);
                    console.log("[Sidebar onClick] context.project.name:", context.project.name);
                } else {
                    console.log("[Sidebar onClick] context.project is null or undefined.");
                }
                const allMessages = await window.pywebview?.api?.get_all_messages(context.project?.name || null) || [];
                const msgText = allMessages.map(m => m.content).join('\n'); // msgText is still used by model_select_messages if prompt is empty
                const res = await window.pywebview?.api?.model_select_messages(prompt, msgText, null, context.project?.name || null);
                let related = [];
                if (res && res.result) {
                    try {
                        const data = JSON.parse(res.result);
                        related = data.messages || [];
                    } catch (e) { related = []; console.error('Error parsing related messages:', e); }
                }
                if (related.length > 0) {
                    related.forEach(m => {
                        const safeContentPreview = (m.content_preview || '').replace(/</g, "&lt;").replace(/>/g, "&gt;");
                        const safeExplanation = (m.explanation || '').replace(/</g, "&lt;").replace(/>/g, "&gt;");
                        
                        let likelihoodIndicator = '';
                        let likelihoodClass = 'likelihood-high';
                        if (m.likelihood === 'less likely') {
                            likelihoodIndicator = '<span style="color:orange; font-style:italic; font-size:0.9em;">(Less Likely)</span> ';
                            likelihoodClass = 'likelihood-low';
                        }
                        const displayContent = safeContentPreview.length > 120 ? safeContentPreview.substring(0, 120) + '...' : safeContentPreview;
                        const targetProjectName = m.original_message_data?.project || '';

                        // Simplified HTML for the selected message content
                        const messageInnerHtml = `
                            <div class="selected-message-content-item ${likelihoodClass}">
                                ${likelihoodIndicator}
                                <div>${displayContent}</div>
                                <div class="message-explanation">${safeExplanation}</div>
                            </div>
                        `;
                        // Pass the ID and project for navigation to renderMessage
                        renderMessage('model', messageInnerHtml, m.id, targetProjectName);
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
