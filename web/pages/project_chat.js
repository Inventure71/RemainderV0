import { Message } from './message.js';

export function renderProjectChat(container, api, project) {
    container.innerHTML = `
        <div style="display:flex;height:100%;min-height:0;">
            <div style="flex:1;min-width:0;display:flex;flex-direction:column;min-height:0;background:${project.color || '#23272e'};">
                <style scoped>
                    .chat-wrapper{display:flex;flex-direction:column;flex:1;min-height:0;}
                    .project-chat-header{padding:16px 12px 10px 12px;border-radius:10px 10px 0 0;color:#000;display:flex;align-items:flex-start;}
                    .scrollable-list{flex:1;min-height:0;overflow-y:auto;margin:0;padding:0;list-style:none;background:#23272e;}
                    .form-container{display:flex;gap:8px;align-items:center;margin-top:8px;}
                    .form-container textarea{flex:1;resize:none;font:inherit;padding:6px 8px;background:#23272e;color:#fff;border:1px solid #444;}
                    button[disabled]{opacity:0.5;cursor:not-allowed;}
                    .loading{text-align:center;padding:1em;color:#888;}
                    .header-actions{align-self:flex-start;display:flex;gap:6px;}
                    .header-actions button {
                        background: none;
                        border: none;
                        color: #8a8fa7;
                        padding: 0.4em 0.8em;
                        border-radius: 4px;
                        cursor: pointer;
                        font-size: 0.9em;
                        margin-right: 6px;
                        transition: background 0.2s, color 0.2s;
                    }
                    .header-actions button:hover {
                        background: #3a3f4b;
                        color: #f7f7fa;
                    }
                </style>
                <div class="chat-wrapper">
                    <div class="project-chat-header" style="background:${project.color || '#dddddd'};">
                        <div style="flex:1;">
                            <h2 style="margin:0 0 4px 0;">${project.name}</h2>
                            <span class="project-desc" style="display:block;margin:2px 0 8px 0;">${project.description || ''}</span>
                        </div>
                        <div class="header-actions">
                            <button type="button" id="editDescBtn">Edit Description</button>
                            <button type="button" id="editColorBtn">Edit Color</button>
                            <button type="button" id="backToProjectsBtn">Back</button>
                        </div>
                    </div>
                    <div id="projectMsgLoading" class="loading" hidden>Loading…</div>
                    <ul id="projectMessages" class="scrollable-list"></ul>
                    <div id="projChatError" style="color:#ff5252;margin:8px 0 0 0;"></div>
                    <div class="form-container">
                        <div style="display:flex;flex-direction:column;flex:1;gap:8px;">
                            <textarea id="messageContent" placeholder="Type a message… (Shift+Enter for new line)" rows="2" autofocus></textarea>
                            <textarea id="messageContext" placeholder="Additional context (optional, will be shown on hover)" rows="1"></textarea>
                        </div>
                        <button id="sendProjectMsgBtn" disabled>Send</button>
                    </div>
                </div>
            </div>
            <div id="modelChatSidebar" style="width:320px;min-width:320px;background:#262a34;border-left:1px solid #363b47;display:flex;flex-direction:column;height:100%;"></div>
        </div>
    `;

    // Render the model chat sidebar in context, passing current project
    import('../components/model_chat_sidebar.js').then(({ renderModelChatSidebar }) => {
        const sidebar = container.querySelector('#modelChatSidebar');
        renderModelChatSidebar(sidebar, { project });
    });

    const textarea = container.querySelector('#messageContent');
    const sendBtn = container.querySelector('#sendProjectMsgBtn');

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

    sendBtn.addEventListener('click', () => sendProjectMessage(api, project, textarea, sendBtn));

    // Bind header buttons directly
    const editDescBtn = container.querySelector('#editDescBtn');
    if (editDescBtn) {
        editDescBtn.addEventListener('click', async () => {
            const desc = prompt('Edit description:', project.description || '');
            if (desc !== null) {
                await api.edit_project(project.id, project.name, desc, project.color);
                project.description = desc;
                window.nav.projectChat(project);
            }
        });
    }
    const editColorBtn = container.querySelector('#editColorBtn');
    if (editColorBtn) {
        editColorBtn.addEventListener('click', async () => {
            const color = prompt('Edit color (hex):', project.color || '#dddddd');
            if (color) {
                await api.edit_project(project.id, project.name, project.description, color);
                project.color = color;
                window.nav.projectChat(project);
            }
        });
    }
    const backBtn = container.querySelector('#backToProjectsBtn');
    if (backBtn) backBtn.addEventListener('click', () => window.nav.projects());

    loadProjectMessages(api, project);
}

async function sendProjectMessage(api, project, textarea, sendBtn) {
    const content = textarea.value.trim();
    if (!content) return;
    sendBtn.disabled = true;

    // Get the context from the context textarea
    const contextTextarea = document.getElementById('messageContext');
    const context = contextTextarea ? contextTextarea.value.trim() : '';

    try {
        await api.add_message(content, project.name, null, context);
        textarea.value = '';
        if (contextTextarea) contextTextarea.value = '';
        document.getElementById('projChatError').textContent = '';
        loadProjectMessages(api, project);
    } catch (e) {
        document.getElementById('projChatError').textContent = e.message || 'Failed to send message.';
    } finally {
        sendBtn.disabled = false;
        textarea.focus();
    }
}

function loadProjectMessages(api, project) {
    const loadingDiv = document.getElementById('projectMsgLoading');
    if (loadingDiv) loadingDiv.hidden = false;

    api.get_all_messages(project.name).then(messages => {
        const ul = document.getElementById('projectMessages');
        ul.innerHTML = '';
        if (!messages || !Array.isArray(messages) || messages.length === 0) {
            ul.innerHTML = '<div style="color:#bbb;text-align:center;padding:2em 0">No messages yet.</div>';
            if (loadingDiv) loadingDiv.hidden = true;
            return;
        }
        messages.forEach(msgData => {
            const msg = new Message(msgData, api);
            ul.appendChild(msg.render());
        });
        ul.scrollTop = ul.scrollHeight;
        if (loadingDiv) loadingDiv.hidden = true;
    }).catch(e => {
        if (loadingDiv) loadingDiv.hidden = true;
        const ul = document.getElementById('projectMessages');
        ul.innerHTML = `<div style="color:#ff5252">Error loading messages: ${e.message || e}. Retrying every 0.5s...</div>`;
        const retryProjId = setInterval(() => {
            api.get_all_messages(project.name)
                .then(msgs => { clearInterval(retryProjId); loadProjectMessages(api, project); })
                .catch(() => {});
        }, 500);
    });
}


export const __testonly__ = { sendProjectMessage, loadProjectMessages };
