import { Message } from './message.js';

export function renderProjectChat(container, api, project) {
    container.innerHTML = `
        <style scoped>
            .chat-wrapper{display:flex;flex-direction:column;flex:1;min-height:0;}
            .project-chat-header{padding:16px 12px 10px 12px;border-radius:10px 10px 0 0;color:#000;}
            .scrollable-list{flex:1;min-height:0;overflow-y:auto;margin:0;padding:0;list-style:none;}
            .form-container{display:flex;gap:8px;align-items:center;margin-top:8px;}
            .form-container textarea{flex:1;resize:none;font:inherit;padding:6px 8px;}
            button[disabled]{opacity:0.5;cursor:not-allowed;}
            .loading{text-align:center;padding:1em;color:#888;}
            .header-actions{display:flex;flex-wrap:wrap;gap:6px;margin-top:4px;}
        </style>
        <div class="chat-wrapper">
            <div class="project-chat-header" style="background:${project.color || '#dddddd'};">
                <h2 style="margin:0 0 4px 0;">${project.name}</h2>
                <span class="project-desc" style="display:block;margin:2px 0 8px 0;">${project.description || ''}</span>
                <div class="header-actions">
                    <button id="editDescBtn" aria-label="Edit description">Edit Description</button>
                    <button id="editColorBtn" aria-label="Edit color">Edit Color</button>
                    <button id="backToProjectsBtn" aria-label="Back to projects">Back</button>
                </div>
            </div>
            <div id="projectMsgLoading" class="loading" hidden>Loading…</div>
            <ul id="projectMessages" class="scrollable-list"></ul>
            <div id="projChatError" style="color:#ff5252;margin:8px 0 0 0;"></div>
            <div class="form-container">
                <textarea id="messageContent" placeholder="Type a message… (Shift+Enter for new line)" rows="2" autofocus></textarea>
                <button id="sendProjectMsgBtn" disabled>Send</button>
            </div>
        </div>
    `;

    const textarea = container.querySelector('#messageContent');
    const sendBtn  = container.querySelector('#sendProjectMsgBtn');

    function updateSendBtnState() {
        sendBtn.disabled = textarea.value.trim().length === 0;
    }
    updateSendBtnState();

    textarea.addEventListener('input', updateSendBtnState);
    textarea.addEventListener('keydown', e => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendBtn.click();
        }
    });

    sendBtn.addEventListener('click', () => sendProjectMessage(api, project, textarea, sendBtn));

    document.getElementById('editDescBtn').addEventListener('click', () => {
        const desc = prompt('Edit description:', project.description || '');
        if (desc !== null) {
            api.edit_project(project.id, project.name, desc, project.color)
               .then(() => window.nav.projectChat(project));
        }
    });

    document.getElementById('editColorBtn').addEventListener('click', () => {
        const color = prompt('Edit color (hex):', project.color || '#dddddd');
        if (color) {
            api.edit_project(project.id, project.name, project.description, color)
               .then(() => window.nav.projectChat(project));
        }
    });

    document.getElementById('backToProjectsBtn').addEventListener('click', () => window.nav.projects());

    loadProjectMessages(api, project);
}

async function sendProjectMessage(api, project, textarea, sendBtn) {
    const content = textarea.value.trim();
    if (!content) return;
    sendBtn.disabled = true;
    try {
        await api.add_message(content, project.name);
        textarea.value = '';
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
