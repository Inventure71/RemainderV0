import { Message } from './message.js';
import { renderReminderItem } from '../components/reminder_item.js';
import { createEmojiPicker } from '../components/emoji_picker.js';

export function renderProjectChat(container, api, project) {
    // --- Special Handling for Reminders Project ---
    if (project.id === '__reminders__') {
        renderRemindersView(container, api, project);
        return; // Don't render standard project chat
    }

    // Determine text color based on project background color
    const getTextColor = (bgColor) => {
        if (!bgColor) return '#fff'; // Default to white if no color
        bgColor = bgColor.replace("#", "");
        const r = parseInt(bgColor.substr(0,2),16);
        const g = parseInt(bgColor.substr(2,2),16);
        const b = parseInt(bgColor.substr(4,2),16);
        const yiq = ((r*299)+(g*587)+(b*114))/1000;
        return (yiq >= 128) ? '#000' : '#fff';
    };

    const bgColor = project.color || '#23272e';
    const textColor = getTextColor(bgColor.replace('#', ''));

    let selectedImageFiles = []; // Store selected file paths

    // --- Standard Project Chat Rendering ---
    container.innerHTML = `
        <div style="display:flex;height:100%;min-height:0;">
            <div style="flex:1;min-width:0;display:flex;flex-direction:column;min-height:0;background:${bgColor};">
                <style scoped>
                    .chat-wrapper{display:flex;flex-direction:column;flex:1;min-height:0;}
                    .project-chat-header{position: relative; z-index: 2; padding:16px 12px 10px 12px;border-radius:10px 10px 0 0;color:${textColor};display:flex;align-items:flex-start;}
                    .scrollable-list{flex:1;min-height:0;overflow-y:auto;margin:0;padding:0 10px 80px 10px;list-style:none;background:#23272e;}
                    .form-container{display:flex;gap:8px;align-items:stretch;margin-top:8px;padding:8px;background:#2a3142;border-top:1px solid #363b47;}
                    .input-area{display:flex;flex-direction:column;flex:1;gap:8px;}
                    .form-container textarea{flex:1;resize:none;font:inherit;padding:6px 8px;background:#23272e;color:#fff;border:1px solid #444;border-radius:4px;}
                    .form-buttons{display:flex;flex-direction:column;gap:8px;}
                    button{padding:8px 12px; cursor:pointer; border:none; border-radius:4px;font-weight:500;}
                    button#sendProjectMsgBtn{background:#3578e5;color:black;}
                    button#attachProjectFileBtn{background:#44495a;color:white;}
                    button[disabled]{opacity:0.5;cursor:not-allowed;}
                    .loading{text-align:center;padding:1em;color:#888;}
                    .header-actions{align-self:flex-start;display:flex;gap:6px; margin-top: 4px; /* Align slightly better with title */}
                    .header-actions button {
                        background: none;
                        border: none;
                        /* color: #8a8fa7; */ /* Use a lighter color */
                        color: ${textColor === '#fff' ? '#adb5bd' : '#555'};
                        padding: 0.4em 0.8em;
                        border-radius: 4px;
                        cursor: pointer;
                        font-size: 0.9em;
                        /* margin-right: 6px; Removed, using gap */
                        transition: background 0.2s, color 0.2s;
                    }
                    .header-actions button:hover {
                        /* background: #3a3f4b; */ /* Use slightly lighter hover */
                        background: ${textColor === '#fff' ? '#343a40' : '#e0e0e0'};
                        color: ${textColor === '#fff' ? '#f7f7fa' : '#222'};
                    }
                    /* Styles for Edit Form */
                    #projectEditForm { display: none; background: #3a3f4b; padding: 15px; border-radius: 5px; margin-top: 10px; }
                    #projectEditForm label { display: block; margin-bottom: 5px; font-weight: bold; color: #ccc; }
                    #projectEditForm input[type='text'], #projectEditForm textarea { width: 95%; background: #23272e; color: #fff; border: 1px solid #555; padding: 8px; margin-bottom: 10px; border-radius: 4px; }
                    #projectEditForm input[type='color'] { height: 35px; padding: 5px; border: 1px solid #555; border-radius: 4px; margin-bottom: 10px; cursor: pointer; }
                    #projectEditForm .edit-form-actions { display: flex; gap: 10px; justify-content: flex-end; }
                </style>
                <div class="chat-wrapper">
                    <div class="project-chat-header" style="border-top: 5px solid ${bgColor}; background: ${bgColor};">
                        <div style="flex:1">
                            <h2 style="margin:0; color:${textColor}">${project.emoji || '📁'} ${project.name}</h2>
                            <div id="projectEditForm">
                                <label for="projectEditName">Name:</label>
                                <input type="text" id="projectEditName" value="${project.name || ''}">
                                
                                <label for="projectEditDesc">Description:</label>
                                <textarea id="projectEditDesc" rows="3">${project.description || ''}</textarea>
                                
                                <label for="projectEditEmoji">Emoji:</label>
                                <div class="emoji-input-wrapper" style="width:100%;position:relative;margin-bottom:10px;">
                                    <input type="text" id="projectEditEmoji" value="${project.emoji || '📁'}" maxlength="2" readonly style="cursor:pointer;background:#23272e;color:#fff;border:1px solid #555;padding:8px;border-radius:4px;width:95%;">
                                    <button type="button" id="projectEditEmojiButton" style="position:absolute;right:8%;top:50%;transform:translateY(-50%);background:none;border:none;color:#aaa;cursor:pointer;font-size:12px;">▼</button>
                                </div>
                                
                                <label for="projectEditColor">Color:</label>
                                <input type="color" id="projectEditColor" value="${project.color || '#dddddd'}">
                                
                                <div class="edit-form-actions">
                                    <button type="button" id="cancelProjectEditBtn">Cancel</button>
                                    <button type="button" id="saveProjectEditBtn">Save</button>
                                </div>
                            </div>
                        </div>
                        <div class="header-actions">
                            <button type="button" id="editProjectBtn" aria-label="Edit project">✏️ Edit</button>
                            <button type="button" id="backToProjectsBtn" aria-label="Back to projects">← Back</button>
                        </div>
                    </div>
                    <div id="projectMsgLoading" class="loading" hidden>Loading…</div>
                    <ul id="projectMessages" class="scrollable-list"></ul>
                    <div id="projChatError" style="color:#ff5252;margin:8px 0 0 0;"></div>
                    <div class="form-container">
                        <div class="input-area">
                            <textarea id="messageContent" placeholder="Type a message… (Shift+Enter for new line)" rows="2" autofocus></textarea>
                            <textarea id="messageContext" placeholder="Additional context (optional, will be shown on hover)" rows="1"></textarea>
                            <div id="selectedProjectFilesPreview" style="font-size:0.8em;color:#aaa;margin-top:4px;max-height:50px;overflow-y:auto;"></div>
                        </div>
                        <div class="form-buttons">
                            <button id="attachProjectFileBtn">Attach</button>
                        <button id="sendProjectMsgBtn" disabled>Send</button>
                        </div>
                    </div>
                </div>
            </div>
            <div id="modelChatSidebar" style="width:350px;min-width:350px;background:#262a34;border-left:1px solid #363b47;display:flex;flex-direction:column;height:100%;"></div>
        </div>
    `;

    // Render the model chat sidebar in context, passing current project
    import('../components/model_chat_sidebar.js').then(({ renderModelChatSidebar }) => {
        const sidebar = container.querySelector('#modelChatSidebar');
        renderModelChatSidebar(sidebar, { project });
    });

    const textarea = container.querySelector('#messageContent');
    const sendBtn = container.querySelector('#sendProjectMsgBtn');
    const attachFileBtn = container.querySelector('#attachProjectFileBtn');
    const selectedFilesPreview = container.querySelector('#selectedProjectFilesPreview');
    const inputArea = container.querySelector('.input-area');

    function handleFiles(files) {
        if (!files || files.length === 0) return;
        
        const filePaths = Array.from(files).map(file => file.path).filter(Boolean);
        if (filePaths.length > 0) {
            selectedImageFiles = selectedImageFiles.concat(filePaths);
            renderSelectedProjectFilesPreview();
            updateSendBtnState();
        }
    }

    function updateSendBtnState() {
        // Enable send if textarea has content OR if there are files selected
        const hasContent = textarea.value.trim().length > 0;
        const hasFiles = selectedImageFiles.length > 0;
        sendBtn.disabled = !(hasContent || hasFiles);
    }
    updateSendBtnState();

    textarea.addEventListener('input', updateSendBtnState);

    textarea.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!sendBtn.disabled) sendBtn.click();
        }
    });

    // Setup drag and drop for the input area
    if (inputArea) {
        // Highlight drop area when dragging over it
        inputArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            inputArea.style.boxShadow = '0 0 10px rgba(0, 123, 255, 0.5)';
            inputArea.style.borderColor = '#007bff';
        });

        inputArea.addEventListener('dragenter', (e) => {
            e.preventDefault();
            inputArea.style.boxShadow = '0 0 10px rgba(0, 123, 255, 0.5)';
            inputArea.style.borderColor = '#007bff';
        });

        inputArea.addEventListener('dragleave', () => {
            inputArea.style.boxShadow = '';
            inputArea.style.borderColor = '';
        });

        // Handle the drop
        inputArea.addEventListener('drop', (e) => {
            e.preventDefault();
            inputArea.style.boxShadow = '';
            inputArea.style.borderColor = '';
            
            // Handle dropped files
            if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                handleFiles(e.dataTransfer.files);
            }
        });
    }

    // Setup paste handling for the textarea
    textarea.addEventListener('paste', (e) => {
        // Check if the paste event has any images
        const items = (e.clipboardData || e.originalEvent.clipboardData).items;
        
        if (!items) return;
        
        let hasImageItem = false;
        
        for (const item of items) {
            if (item.type.indexOf('image') === 0) {
                hasImageItem = true;
                const blob = item.getAsFile();
                
                // We need to save this temporary file to disk through the backend
                if (blob) {
                    // Create a temporary path for this image
                    const reader = new FileReader();
                    reader.onload = async function(event) {
                        try {
                            // Send the image data to the backend to save as a temp file
                            const response = await api.saveClipboardImage({
                                imageData: event.target.result
                            });
                            
                            if (response && response.success && response.filePath) {
                                selectedImageFiles.push(response.filePath);
                                renderSelectedProjectFilesPreview();
                                updateSendBtnState();
                            } else {
                                console.error("Failed to save clipboard image", response);
                                document.getElementById('projChatError').textContent = 'Failed to process pasted image.';
                            }
                        } catch (err) {
                            console.error("Error saving clipboard image:", err);
                            document.getElementById('projChatError').textContent = 'Error processing pasted image.';
                        }
                    };
                    reader.readAsDataURL(blob);
                }
            }
        }
        
        // If we found an image in the clipboard, prevent the default paste action
        // to avoid pasting the image as text
        if (hasImageItem) {
            e.preventDefault();
        }
    });

    attachFileBtn.addEventListener('click', async () => {
        try {
            const filePaths = await api.getFileDialog({
                allow_multiple: true,
                file_types: ['Image files (*.png;*.jpg;*.jpeg;*.gif;*.webp)', 'All files (*.*)']
            });
            if (filePaths && filePaths.length > 0) {
                selectedImageFiles = selectedImageFiles.concat(filePaths);
                renderSelectedProjectFilesPreview();
                updateSendBtnState();
            }
        } catch (e) {
            console.error("Error opening file dialog for project chat:", e);
            document.getElementById('projChatError').textContent = 'Failed to open file dialog.';
        }
    });

    function renderSelectedProjectFilesPreview() {
        selectedFilesPreview.innerHTML = '';
        if (selectedImageFiles.length > 0) {
            selectedImageFiles.forEach(filePath => {
                const fileDiv = document.createElement('div');
                fileDiv.textContent = filePath.split(/[\/]/).pop();
                selectedFilesPreview.appendChild(fileDiv);
            });
        }
    }

    sendBtn.addEventListener('click', () => sendProjectMessage(api, project, textarea, sendBtn, selectedImageFiles, () => {
        selectedImageFiles = [];
        renderSelectedProjectFilesPreview();
        updateSendBtnState(); // Update send button after clearing files
    }));

    // Bind back button
    const backBtn = container.querySelector('#backToProjectsBtn');
    if (backBtn) backBtn.addEventListener('click', () => window.nav.projects());

    loadProjectMessages(api, project);

    // Setup project edit functionality with the clean implementation
    const editBtn = container.querySelector('#editProjectBtn');
    const editForm = container.querySelector('#projectEditForm');
    const cancelEditBtn = container.querySelector('#cancelProjectEditBtn');
    const saveEditBtn = container.querySelector('#saveProjectEditBtn');
    
    // Setup form fields
    const editNameInput = container.querySelector('#projectEditName');
    const editDescInput = container.querySelector('#projectEditDesc');
    const editEmojiInput = container.querySelector('#projectEditEmoji');
    const editEmojiButton = container.querySelector('#projectEditEmojiButton'); 
    const editColorInput = container.querySelector('#projectEditColor');
    
    // Initialize emoji picker for the edit form
    createEmojiPicker(editEmojiInput, editEmojiButton);
    
    editBtn.addEventListener('click', () => {
        editForm.style.display = 'block';
    });
    
    cancelEditBtn.addEventListener('click', () => {
        editForm.style.display = 'none';
    });
    
    saveEditBtn.addEventListener('click', async () => {
        const newName = editNameInput.value.trim();
        if (!newName) {
            alert('Project name cannot be empty');
            return;
        }
        
        try {
            const result = await api.edit_project(
                project.id,
                newName,
                editDescInput.value.trim(),
                editColorInput.value,
                editEmojiInput.value.trim()
            );
            
            if (result && result.success) {
                // Update the local project object
                project.name = newName;
                project.description = editDescInput.value.trim();
                project.color = editColorInput.value;
                project.emoji = editEmojiInput.value.trim();
                
                // Refresh the current view
                nav.projectChat(project);
            } else {
                alert('Failed to update project: ' + (result?.error || 'Unknown error'));
            }
        } catch (error) {
            alert('Error updating project: ' + (error.message || error));
            console.error('Project update error:', error);
        } finally {
            editForm.style.display = 'none';
        }
    });
}

// --- Function to render the dedicated Reminders view ---
function renderRemindersView(container, api, project) {
    container.innerHTML = `
        <div class="reminders-page-wrapper">
            <style scoped>
                .reminders-page-wrapper { display:flex; flex-direction:column; height:100%; min-height:0; background:#23272e; color: #e0e0e0; }
                .reminders-header { padding: 16px 20px 10px 20px; background: #2a3142; color: #f0f0f0; display:flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #3a3f4b; box-shadow: 0 1px 3px rgba(0,0,0,0.2); }
                .reminders-header h2 { margin:0; font-size: 1.4em; }
                .reminders-header button { background: none; border: 1px solid #4a5260; color: #adb5bd; padding: 0.4em 0.8em; border-radius: 4px; cursor: pointer; font-size: 0.9em; transition: background 0.2s, color 0.2s; }
                .reminders-header button:hover { background: #343a40; color: #f7f7fa; border-color: #5a6270; }
                .reminders-content-area { flex:1; min-height:0; overflow-y:auto; padding: 15px 20px; }
                .reminders-group { margin-bottom: 25px; }
                .reminders-group h3 { margin: 0 0 10px 0; font-size: 1.1em; color: #aab8c5; border-bottom: 1px solid #444; padding-bottom: 5px; }
                .reminders-list { list-style:none; padding:0; margin:0; }
                .loading { text-align:center; padding:2em; color:#888; font-size: 1.1em; }
                .empty-state { color:#777; text-align:center; padding:3em 1em; font-size: 1.1em; }
                .reminders-error { color:#ff5252; margin:8px; text-align:center; background: #442222; padding: 10px; border-radius: 4px; }
                .add-reminder-form { padding: 15px 20px; background: #2a3142; border-top: 1px solid #3a3f4b; display: flex; flex-direction: column; gap: 10px; }
                .add-reminder-form textarea { background: #23272e; color: #fff; border: 1px solid #444; border-radius: 4px; padding: 8px; font: inherit; resize: vertical; min-height: 40px; }
                .add-reminder-form input[type="datetime-local"] { background: #23272e; color: #fff; border: 1px solid #444; border-radius: 4px; padding: 8px; font: inherit; color-scheme: dark; /* Improves picker in dark mode */ }
                .add-reminder-form button { background: #3578e5; color: white; border: none; padding: 10px 15px; border-radius: 4px; cursor: pointer; font-weight: bold; }
                .add-reminder-form button:disabled { opacity: 0.5; cursor: not-allowed; }
                #addReminderError { color: #ff5252; font-size: 0.9em; margin-top: 5px; }
            </style>
            <div class="reminders-header">
                <h2>⏰ ${project.name}</h2>
                <button type="button" id="backToProjectsBtn">Back to Projects</button>
            </div>
            
            <div class="reminders-content-area">
                <div id="remindersLoading" class="loading" hidden>Loading Reminders…</div>
                <div id="remindersError" class="reminders-error" hidden></div>
                <div id="remindersContainer">
                    <!-- Groups will be injected here -->
                </div>
            </div>

            <div class="add-reminder-form">
                <textarea id="newReminderContent" placeholder="Enter reminder text..."></textarea>
                <input type="datetime-local" id="newReminderDateTime">
                <button id="addReminderBtn">Add Reminder</button>
                <div id="addReminderError"></div>
            </div>
        </div>
    `;

    // Set up back button
    container.querySelector('#backToProjectsBtn').addEventListener('click', () => {
        window.actions?.navigateToProjects();
    });

    // Set up the reminder creation form
    const contentInput = container.querySelector('#newReminderContent');
    const dateTimeInput = container.querySelector('#newReminderDateTime');
    const addBtn = container.querySelector('#addReminderBtn');
    const errorDiv = container.querySelector('#addReminderError');

    // Set default date/time (tomorrow at noon)
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    tomorrow.setHours(12, 0, 0, 0);
    dateTimeInput.value = tomorrow.toISOString().substring(0, 16);

    addBtn.addEventListener('click', async () => {
        const content = contentInput.value.trim();
        const dateTime = dateTimeInput.value;
        
        if (!content) {
            errorDiv.textContent = 'Please enter reminder text';
            return;
        }
        
        if (!dateTime) {
            errorDiv.textContent = 'Please select a date and time';
            return;
        }

        addBtn.disabled = true;
        errorDiv.textContent = '';
        
        try {
            const result = await api.add_reminder(content, dateTime);
            if (result && result.success) {
                contentInput.value = '';
                loadReminders(api, container); // Refresh the list
            } else {
                errorDiv.textContent = result?.error || 'Failed to add reminder';
            }
        } catch (error) {
            errorDiv.textContent = error.message || 'An error occurred';
            console.error('Add reminder error:', error);
        } finally {
            addBtn.disabled = false;
        }
    });

    // Load the existing reminders
    loadReminders(api, container);
}

// --- Function to load and display reminder items, now with grouping ---
function loadReminders(api, container) {
    loadRemindersList(api);
}

// --- Function to load and display reminder items, now with grouping ---
function loadRemindersList(api) {
    const loadingDiv = document.getElementById('remindersLoading');
    const containerDiv = document.getElementById('remindersContainer');
    const errorDiv = document.getElementById('remindersError');

    if (loadingDiv) loadingDiv.hidden = false;
    if (errorDiv) errorDiv.hidden = true;
    containerDiv.innerHTML = ''; // Clear previous groups

    api.get_reminder_messages().then(reminders => {
        if (loadingDiv) loadingDiv.hidden = true;
        if (!reminders || !Array.isArray(reminders)) {
            throw new Error("Invalid response received for reminders.");
        }

        if (reminders.length === 0) {
            containerDiv.innerHTML = '<div class="empty-state">No reminders found. Add some from your messages!</div>';
            return;
        }

        // --- Grouping Logic ---
        const groups = {
            overdue: [],
            today: [],
            upcoming: [],
            completed: []
        };

        const now = new Date();
        const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        const tomorrowStart = new Date(todayStart); tomorrowStart.setDate(tomorrowStart.getDate() + 1);

        reminders.forEach(r => {
            if (r.done) {
                groups.completed.push(r);
                return;
            }

            let remindDate = null;
            try {
                const parts = r.remind?.match(/(\d{4})-(\d{2})-(\d{2})-(\d{2}):(\d{2})/);
                if (parts) {
                    remindDate = new Date(parts[1], parts[2] - 1, parts[3], parts[4], parts[5]);
                }
            } catch {}

            if (!remindDate || isNaN(remindDate)) {
                 // Treat invalid/missing dates as upcoming for now, or create separate group?
                 // Maybe put them in upcoming or a dedicated 'Unscheduled' group
                 groups.upcoming.push(r); 
                 return;
            }

            if (remindDate < todayStart) {
                groups.overdue.push(r);
            } else if (remindDate >= todayStart && remindDate < tomorrowStart) {
                groups.today.push(r);
            } else {
                groups.upcoming.push(r);
            }
        });

        // --- Render Groups ---
        let contentRendered = false;
        const renderGroup = (title, groupReminders, groupId) => {
            if (groupReminders.length > 0) {
                contentRendered = true;
                const groupDiv = document.createElement('div');
                groupDiv.className = 'reminders-group';
                groupDiv.innerHTML = `<h3>${title} (${groupReminders.length})</h3>`;
                const listUl = document.createElement('ul');
                listUl.className = 'reminders-list';
                listUl.id = groupId;
                groupReminders.sort((a, b) => { // Sort within group by date
                     try { return new Date(a.remind) - new Date(b.remind); } catch { return 0; }
                });
                groupReminders.forEach(reminderData => {
                    const reminderElement = renderReminderItem(reminderData, api, () => loadRemindersList(api));
                    listUl.appendChild(reminderElement);
                });
                groupDiv.appendChild(listUl);
                containerDiv.appendChild(groupDiv);
            }
        };

        renderGroup('Overdue', groups.overdue, 'list-overdue');
        renderGroup('Today', groups.today, 'list-today');
        renderGroup('Upcoming', groups.upcoming, 'list-upcoming');
        renderGroup('Completed', groups.completed, 'list-completed');
        
        if (!contentRendered) { // Should not happen if initial check passed, but safeguard
             containerDiv.innerHTML = '<div class="empty-state">No reminders to display in categories.</div>';
        }

    }).catch(e => {
        console.error("Error loading reminders:", e);
        if (loadingDiv) loadingDiv.hidden = true;
        if (errorDiv) {
             errorDiv.textContent = `Failed to load reminders: ${e.message || e}`;
             errorDiv.hidden = false;
        }
        containerDiv.innerHTML = ''; // Clear container on error
    });
}

async function sendProjectMessage(api, project, textarea, sendBtn, imageFiles, clearFilesCallback) {
    const content = textarea.value.trim();
    if (!content && (!imageFiles || imageFiles.length === 0)) {
        return;
    }

    sendBtn.disabled = true;
    const attachBtn = document.getElementById('attachProjectFileBtn');
    if(attachBtn) attachBtn.disabled = true;

    const contextTextarea = document.getElementById('messageContext');
    const contextValue = contextTextarea ? contextTextarea.value.trim() : '';

    try {
        const r = await api.add_message(
            content,
            project.name, // Pass project name
            null,         // files (old field)
            contextValue, // extra
            null,         // remind
            null,         // importance
            null,         // reoccurences
            false,        // done
            imageFiles    // image_files
        );

        if (r && r.success === false && r.error) {
            document.getElementById('projChatError').textContent = r.error;
        } else {
        textarea.value = '';
        if (contextTextarea) contextTextarea.value = '';
        document.getElementById('projChatError').textContent = '';
            if (clearFilesCallback) clearFilesCallback();
        loadProjectMessages(api, project);
        }
    } catch (e) {
        document.getElementById('projChatError').textContent = e.message || 'Failed to send message.';
    } finally {
        sendBtn.disabled = false;
        if(attachBtn) attachBtn.disabled = false;
        textarea.focus();
        // Update send button state after attempting to send
        const hasContent = textarea.value.trim().length > 0;
        const hasFiles = imageFiles && imageFiles.length > 0; // Check current state of imageFiles for this call
        if (!hasContent && !hasFiles) { // If both are empty (e.g. after successful send)
             sendBtn.disabled = true;
        } else {
            sendBtn.disabled = false;
        }
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
        
        // Reverse the messages array to display oldest first, newest last
        const sortedMessages = [...messages].reverse();
        
        sortedMessages.forEach(msgData => {
            const msg = new Message(msgData, api);
            ul.appendChild(msg.render());
        });
        
        // Auto-scroll to the latest message (bottom)
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

export const __testonly__ = { sendProjectMessage, loadProjectMessages, loadRemindersList };
