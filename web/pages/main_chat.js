import { Message } from './message.js';

// Main Chat page, mirroring Tkinter MainChatWindow
export function renderMainChat(container, api) {
    let selectedImageFiles = []; // Store selected file paths

    container.innerHTML = `
        <div style="display:flex;height:100%;min-height:0;">
            <div style="flex:1;min-width:0;display:flex;flex-direction:column;min-height:0;background:#23272e;">
                <style scoped>
                    .chat-container{display:flex;flex-direction:column;flex:1;min-height:0;}
                    .scrollable-list{flex:1;min-height:0;overflow-y:auto;margin:0;padding:0 10px 80px 10px;list-style:none;background:#23272e;}
                    .chat-options{margin-bottom: 8px; padding-left: 5px; color: #ccc; font-size: 0.9em;}
                    .form-container{display:flex;gap:8px;align-items:stretch;margin-top:8px;} /* Align items stretch */
                    .input-area{display:flex;flex-direction:column;flex:1;gap:8px;}
                    .form-container textarea{flex:1;resize:none;font:inherit;padding:6px 8px;background:#23272e;color:#fff;border:1px solid #444;}
                    .form-buttons{display:flex;flex-direction:column;gap:8px;} /* Column for send and attach */
                    button{padding:8px 12px; cursor:pointer; border:none; border-radius:4px;}
                    button#sendMessageBtn{background:#3578e5;color:black;}
                    button#attachFileBtn{background:#44495a;color:white;}
                    button[disabled]{opacity:0.5;cursor:not-allowed;}
                    .loading{text-align:center;padding:1em;color:#888;}
                    #selectedFilesPreview{font-size:0.8em;color:#aaa;margin-top:4px;max-height:50px;overflow-y:auto;}
                    #selectedFilesPreview div{padding:2px 0;}
                </style>
                <div class="chat-container">
                    <h2 style="color:#f7f7fa;">Main Chat</h2>
                    <div class="chat-options">
                        <input type="checkbox" id="showClipsFilter" />
                        <label for="showClipsFilter">Show Saved Clips in Main Chat</label>
                        <label for="includeImageDescriptionsCheckbox" style="margin-left: 10px;">
                            <input type="checkbox" id="includeImageDescriptionsCheckbox" checked />
                            Include image descriptions
                        </label>
                    </div>
                    <div id="messagesLoading" class="loading" hidden>Loading…</div>
                    <ul id="messagesList" class="scrollable-list"></ul>
                    <div id="mainChatError" style="color:#ff5252;margin:8px 0 0 0;"></div>
                    <div class="form-container">
                        <div class="input-area">
                            <textarea id="messageContent" placeholder="Type a message… (Shift+Enter for new line)" rows="2" autofocus></textarea>
                            <textarea id="messageContext" placeholder="Additional context (optional, will be shown on hover)" rows="1"></textarea>
                            <div id="selectedFilesPreview"></div>
                        </div>
                        <div class="form-buttons">
                            <button id="attachFileBtn">Attach</button>
                            <button id="sendMessageBtn" disabled>Send</button>
                        </div>
                    </div>
                </div>
            </div>
            <div id="modelChatSidebar" style="width:320px;min-width:320px;background:#262a34;border-left:1px solid #363b47;display:flex;flex-direction:column;height:100%;"></div>
        </div>
    `;

    // Render the model chat sidebar in context
    import('../components/model_chat_sidebar.js').then(({ renderModelChatSidebar }) => {
        const sidebar = container.querySelector('#modelChatSidebar');
        renderModelChatSidebar(sidebar, {}); // No project context in main chat
    });

    const textarea = container.querySelector('#messageContent');
    const sendBtn = container.querySelector('#sendMessageBtn');
    const attachFileBtn = container.querySelector('#attachFileBtn');
    const selectedFilesPreview = container.querySelector('#selectedFilesPreview');
    const inputArea = container.querySelector('.input-area');
    const showClipsCheckbox = container.querySelector('#showClipsFilter'); // Get checkbox

    // Helper function to handle files from various sources (dialog, drag-drop, paste)
    function handleFiles(files) {
        if (!files || files.length === 0) return;
        
        const filePaths = Array.from(files).map(file => file.path).filter(Boolean);
        if (filePaths.length > 0) {
            selectedImageFiles = selectedImageFiles.concat(filePaths);
            renderSelectedFilesPreview();
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
            if (!sendBtn.disabled) sendBtn.click(); // Check if not disabled
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
                                renderSelectedFilesPreview();
                                updateSendBtnState();
                            } else {
                                console.error("Failed to save clipboard image", response);
                                document.getElementById('mainChatError').textContent = 'Failed to process pasted image.';
                            }
                        } catch (err) {
                            console.error("Error saving clipboard image:", err);
                            document.getElementById('mainChatError').textContent = 'Error processing pasted image.';
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

    // Modify existing attach button click handler to use our new handleFiles function
    attachFileBtn.addEventListener('click', async () => {
        try {
            const filePaths = await api.getFileDialog({
                allow_multiple: true,
                file_types: ['Image files (*.png;*.jpg;*.jpeg;*.gif;*.webp)', 'All files (*.*)']
            });

            if (filePaths && filePaths.length > 0) {
                selectedImageFiles = selectedImageFiles.concat(filePaths);
                renderSelectedFilesPreview();
                updateSendBtnState();
            }
        } catch (e) {
            console.error("Error opening file dialog:", e);
            document.getElementById('mainChatError').textContent = 'Failed to open file dialog.';
        }
    });

    function renderSelectedFilesPreview() {
        selectedFilesPreview.innerHTML = '';
        if (selectedImageFiles.length > 0) {
            selectedImageFiles.forEach(filePath => {
                const fileDiv = document.createElement('div');
                // Display only filename
                fileDiv.textContent = filePath.split(/[\/]/).pop();
                selectedFilesPreview.appendChild(fileDiv);
            });
        }
    }

    sendBtn.addEventListener('click', () => sendMessage(api, textarea, sendBtn, selectedImageFiles, () => {
        selectedImageFiles = []; // Clear selected files array
        renderSelectedFilesPreview(); // Clear preview
        updateSendBtnState(); // Update button state after clearing files
    }));

    // Initialize clipboard filter state and load initial messages
    if (api && typeof api.get_clipboard_filter_state === 'function') {
        api.get_clipboard_filter_state().then(response => {
            if (response && typeof response.show_clips_in_main_chat === 'boolean') {
                showClipsCheckbox.checked = response.show_clips_in_main_chat;
            }
        }).catch(err => {
            console.error("Error getting initial clipboard filter state:", err);
        }).finally(() => {
            loadMessages(api); // Load messages after attempting to set filter state
        });
    } else {
        console.warn("API for clipboard filter not available, loading messages with default state.");
        loadMessages(api); // Fallback if API is not ready or method doesn't exist
    }

    // Add event listener for the checkbox
    showClipsCheckbox.addEventListener('change', async () => {
        try {
            if (api && typeof api.toggle_clipboard_filter_state === 'function') {
                await api.toggle_clipboard_filter_state(showClipsCheckbox.checked);
                loadMessages(api); // Reload messages with the new filter state
            } else {
                console.error("API to toggle clipboard filter not available.");
            }
        } catch (err) {
            console.error("Error toggling clipboard filter state:", err);
            // Optionally, revert checkbox state or show an error to the user
        }
    });

    // Get the image description checkbox and initialize it from settings
    const includeImageDescriptionsCheckbox = document.getElementById('includeImageDescriptionsCheckbox');
    if (api && typeof api.get_app_settings === 'function') {
        api.get_app_settings().then(settings => {
            if (settings && typeof settings.include_image_descriptions === 'boolean') {
                includeImageDescriptionsCheckbox.checked = settings.include_image_descriptions;
            }
        }).catch(err => {
            console.error("Error getting app settings:", err);
        });
    }

    // Add event listener for the image descriptions checkbox
    includeImageDescriptionsCheckbox.addEventListener('change', async () => {
        try {
            if (api && typeof api.update_setting === 'function') {
                await api.update_setting('include_image_descriptions', includeImageDescriptionsCheckbox.checked);
                loadMessages(api); // Reload messages to apply the new setting
            } else {
                console.error("API to update settings not available.");
            }
        } catch (err) {
            console.error("Error updating include_image_descriptions setting:", err);
        }
    });
}

async function sendMessage(api, textarea, sendBtn, imageFiles, clearFilesCallback) {
    const content = textarea.value.trim();
    if (!content && (!imageFiles || imageFiles.length === 0)) { // Also check if there are images
        // If no content and no images, don't send
        return;
    }
    sendBtn.disabled = true;
    document.getElementById('attachFileBtn').disabled = true; // Disable attach while sending

    const contextTextarea = document.getElementById('messageContext');
    const context = contextTextarea ? contextTextarea.value.trim() : '';

    try {
        // Backend expects: content, project=None, files=None (old field), extra=None, remind=None, importance=None, reoccurences=None, done=False, image_files=None
        const r = await api.add_message(
            content,      // content
            null,         // project
            null,         // files (old field)
            context,      // extra
            null,         // remind
            null,         // importance
            null,         // reoccurences
            false,        // done
            imageFiles    // image_files (new field for actual image paths)
        );
        if (r && r.success === false && r.error) {
            document.getElementById('mainChatError').textContent = r.error;
        } else {
            textarea.value = '';
            if (contextTextarea) contextTextarea.value = '';
            document.getElementById('mainChatError').textContent = '';
            if (clearFilesCallback) clearFilesCallback(); // Clears selectedImageFiles and calls updateSendBtnState
            loadMessages(api); // Reload messages to show the new one (with images)
        }
    } catch (e) {
        document.getElementById('mainChatError').textContent = e.message || 'Failed to send message.';
    } finally {
        sendBtn.disabled = false;
        document.getElementById('attachFileBtn').disabled = false; // Re-enable attach button
        textarea.focus();
        // Update send button state finally
        updateSendBtnState();
    }
}

function loadMessages(api) {
    const loadingDiv = document.getElementById('messagesLoading');
    if (loadingDiv) loadingDiv.hidden = false;

    // Try to get the latest API reference in case it became available
    const currentApi = api || window.pywebview?.api;

    if (!currentApi || typeof currentApi.get_all_messages !== 'function') {
        if (loadingDiv) loadingDiv.hidden = true;
        const list = document.getElementById('messagesList');
        list.innerHTML = '<div style="color:#ff5252">API not available. Retrying in 1s...</div>';
        setTimeout(() => loadMessages(currentApi), 1000);
        return;
    }
    currentApi.get_all_messages().then(messages => {
        const ul = document.getElementById('messagesList');
        ul.innerHTML = '';
        if (!messages || !Array.isArray(messages) || messages.length === 0) {
            ul.innerHTML = '<div style="color:#bbb;text-align:center;padding:2em 0">No messages found. Refreshing in 5s...</div>';
            if (loadingDiv) loadingDiv.hidden = true;
            setTimeout(() => loadMessages(api), 5000);
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
        const list = document.getElementById('messagesList');
        list.innerHTML = `<div style="color:#ff5252">Error loading messages: ${e.message || e}. Retrying every 0.5s...</div>`;
        const retryId = setInterval(() => {
            api.get_all_messages().then(msgs => { clearInterval(retryId); loadMessages(api); }).catch(() => {});
        }, 500);
    });
}

export const __testonly__ = { sendMessage, loadMessages };
