// web/main.js
import { renderMainChat }    from './pages/main_chat.js';
import { renderProjects }    from './pages/projects.js';
import { renderProjectChat } from './pages/project_chat.js';
import { showNotification }  from './utils/ui_helpers.js';
import { renderModelChatSidebar } from './components/model_chat_sidebar.js';
import { createEmojiPicker } from './components/emoji_picker.js';

// Constants and utilities
// Add emoji picker helper function

// Initialize API and nav globals 
let api = window.pywebview?.api;
let nav = {
  mainChat: () => { selectedProject = null; window.selectedProject = null; renderMainChat(app, api); },
  projects: () => renderProjects(app, api, proj => { selectedProject = proj; window.selectedProject = proj; nav.projectChat(proj); }),
  projectChat: proj => { window.selectedProject = proj; renderProjectChat(app, api, proj); },
};

const app = document.getElementById('app');
let selectedProject = null;

// Expose navigation globally so subcomponents can call nav properly
window.nav = nav;

window.actions = {
  editMessage: (id, project) => {
    const content = prompt('Edit message:', '');
    if (!content) return;
    const projName = project || (window.selectedProject?.name) || null;
    api.edit_message(id, content, projName)
      .then(() => window.selectedProject ? nav.projectChat(window.selectedProject) : nav.mainChat());
  },
  editMessageWithProject: (id, project) => {
    const content = prompt('Edit message:', '');
    if (content === null) return;
    let newProject = prompt('Change project (leave blank for none):', project || '');
    if (newProject !== null && newProject.trim() === '') newProject = null;
    api.edit_message(id, content, newProject).then(() => nav.mainChat());
  },
  deleteMessage: id => {
    if (!confirm('Delete this message?')) return;
    api.delete_message(id)
      .then(() => {
        // Remove the message element without navigation
        const li = document.querySelector(`li[data-msg-id="${id}"]`);
        if (li) li.remove();
      })
      .catch(e => showNotification(`Failed to delete message: ${e.message || e}`));
  },
  markProcessed: (id, processed) => {
    api.mark_message_processed(id, processed)
      .then(() => window.selectedProject ? nav.projectChat(window.selectedProject) : nav.mainChat());
  },
  changeProject: (id, newProject) => {
    // Only change the project assignment, do not navigate
    api.edit_message(id, undefined, newProject)
      .then(() => {
        // project changed; do nothing to preserve current view and scroll position
      });
  },
  editProject: (id, currentData = {}) => {
    // First get the basic info using prompts
    let name = prompt('New project name:', currentData.name || '');
    if (name === null) return;
    if (!name.trim()) {
      alert('Project name cannot be empty.');
      return;
    }

    const desc = prompt('New description:', currentData.description || '');
    if (desc === null) return;

    const color = prompt('New color (hex):', currentData.color || '#dddddd');
    if (color === null) return;
    if (!/^#[0-9A-F]{6}$/i.test(color) && !/^#[0-9A-F]{3}$/i.test(color)) {
        alert('Invalid color format. Please use hex (e.g., #RRGGBB or #RGB).');
        return;
    }

    // For emoji, create a temporary input and button for the picker
    const tempContainer = document.createElement('div');
    tempContainer.style.position = 'fixed';
    tempContainer.style.top = '50%';
    tempContainer.style.left = '50%';
    tempContainer.style.transform = 'translate(-50%, -50%)';
    tempContainer.style.zIndex = '10000';
    
    const emojiInput = document.createElement('input');
    emojiInput.type = 'text';
    emojiInput.value = currentData.emoji || '📁';
    emojiInput.readOnly = true;
    emojiInput.style.fontSize = '24px';
    emojiInput.style.textAlign = 'center';
    emojiInput.style.width = '50px';
    emojiInput.style.padding = '10px';
    emojiInput.style.marginRight = '10px';
    
    const emojiLabel = document.createElement('div');
    emojiLabel.textContent = 'Select emoji:';
    emojiLabel.style.marginBottom = '10px';
    emojiLabel.style.fontWeight = 'bold';
    emojiLabel.style.color = '#fff';
    
    const emojiButton = document.createElement('button');
    emojiButton.textContent = 'Choose Emoji';
    emojiButton.style.padding = '8px 15px';
    
    const panel = document.createElement('div');
    panel.style.backgroundColor = 'rgba(0,0,0,0.8)';
    panel.style.padding = '20px';
    panel.style.borderRadius = '8px';
    panel.style.boxShadow = '0 5px 15px rgba(0,0,0,0.3)';
    
    const buttonContainer = document.createElement('div');
    buttonContainer.style.display = 'flex';
    buttonContainer.style.justifyContent = 'center';
    buttonContainer.style.marginTop = '20px';
    
    const saveButton = document.createElement('button');
    saveButton.textContent = 'Save';
    saveButton.style.padding = '8px 20px';
    saveButton.style.backgroundColor = '#4CAF50';
    saveButton.style.color = 'white';
    saveButton.style.border = 'none';
    saveButton.style.borderRadius = '4px';
    saveButton.style.marginRight = '10px';
    
    const cancelButton = document.createElement('button');
    cancelButton.textContent = 'Cancel';
    cancelButton.style.padding = '8px 20px';
    cancelButton.style.backgroundColor = '#f44336';
    cancelButton.style.color = 'white';
    cancelButton.style.border = 'none';
    cancelButton.style.borderRadius = '4px';
    
    buttonContainer.appendChild(saveButton);
    buttonContainer.appendChild(cancelButton);
    
    panel.appendChild(emojiLabel);
    panel.appendChild(emojiInput);
    panel.appendChild(emojiButton);
    panel.appendChild(buttonContainer);
    
    tempContainer.appendChild(panel);
    document.body.appendChild(tempContainer);
    
    // Create the emoji picker
    const picker = createEmojiPicker(emojiInput, emojiButton);
    
    // Set up event handlers
    saveButton.addEventListener('click', () => {
      const emoji = emojiInput.value;
      document.body.removeChild(tempContainer);
      
      // Save the project with the selected emoji
      api.edit_project(id, name.trim(), desc, color, emoji)
        .then(() => {
          if (window.nav && window.nav.projects) window.nav.projects();
          else location.reload();
        })
        .catch(e => {
          console.error('Failed to edit project:', e);
          alert(`Failed to edit project: ${e.message || e}`);
        });
    });
    
    cancelButton.addEventListener('click', () => {
      document.body.removeChild(tempContainer);
    });
    
    // Open the picker automatically
    setTimeout(() => emojiButton.click(), 100);
  },
  deleteProject: id => {
    if (confirm('Delete this project?'))
      api.delete_project(id).then(nav.projects);
  }
};

// Expose scroll-to-message helper for related messages
window.scrollToMessage = (msgId) => {
  console.log(`[main.js] scrollToMessage called for msgId: ${msgId}`);

  // Try to find the message element
  const findMessage = () => {
    return document.querySelector(`li[data-msg-id="${msgId}"]`);
  };

  // Check if we need to reload the messages first
  const checkAndReloadMessages = () => {
    // If we're in main chat or project chat, try to reload messages
    if (window.nav && (window.nav.mainChat || window.nav.projectChat)) {
      // Force a reload of messages if possible
      if (window.pywebview?.api?.get_all_messages) {
        showNotification('Reloading messages to locate message...');
        return window.pywebview.api.get_all_messages(window.selectedProject?.name || null)
          .then(() => {
            // Give the DOM time to update
            return new Promise(resolve => setTimeout(resolve, 500));
          })
          .catch(err => {
            console.error('Error reloading messages:', err);
            return Promise.resolve(); // Continue anyway
          });
      }
    }
    return Promise.resolve(); // No reload needed or possible
  };

  // Initial attempt
  let li = findMessage();
  console.log('[main.js] Found element:', li);

  if (li) {
    // Element found, scroll to it
    highlightAndScroll(li);
  } else {
    // Element not found, try again after a short delay
    console.log('[main.js] Message not found immediately, will retry...');
    showNotification('Locating message...');

    // Try multiple times with increasing delays
    let attempts = 0;
    const maxAttempts = 15; // Increased max attempts

    const retry = () => {
      li = findMessage();
      if (li) {
        console.log('[main.js] Found element on retry:', li);
        highlightAndScroll(li);
      } else if (attempts < maxAttempts) {
        attempts++;

        // On the 5th attempt, try reloading messages
        if (attempts === 5) {
          checkAndReloadMessages().then(() => {
            li = findMessage();
            if (li) {
              console.log('[main.js] Found element after reload:', li);
              highlightAndScroll(li);
            } else {
              setTimeout(retry, 300 * attempts);
            }
          });
        } else {
          setTimeout(retry, 300 * attempts); // Increasing delay
        }
      } else {
        console.warn(`[main.js] Message element not found for msgId: ${msgId} after ${maxAttempts} attempts`);
        showNotification('Message not found. Try refreshing the page.');
      }
    };

    setTimeout(retry, 300);
  }

  function highlightAndScroll(element) {
    // Ensure the element is visible
    element.scrollIntoView({ behavior: 'smooth', block: 'center' });

    // Add highlight effect with more prominent styling
    element.classList.add('highlighted');
    element.style.boxShadow = '0 0 0 3px #3578e5, 0 0 15px rgba(53, 120, 229, 0.5)';
    element.style.transition = 'box-shadow 0.3s ease-in-out';
    element.style.backgroundColor = '#2a3142';

    // Remove highlight after delay
    setTimeout(() => {
      element.classList.remove('highlighted');
      element.style.boxShadow = '';

      // Fade out the background color change
      element.style.transition = 'background-color 1s ease-out';
      setTimeout(() => {
        element.style.backgroundColor = '';
        element.style.transition = '';
      }, 1000);
    }, 5000); // Longer highlight duration
  }
};

// Show/hide model chat sidebar overlay
window.toggleModelChatSidebar = (show, context = {}) => {
  const overlay = document.getElementById('modelChatSidebarOverlay');
  const body = document.body; // Get the body element
  if (!overlay) return;
  if (show) {
    overlay.style.display = 'block';
    body.classList.add('model-sidebar-visible'); // Add class to body
    import('./components/model_chat_sidebar.js').then(({ renderModelChatSidebar }) => {
      renderModelChatSidebar(overlay, context);
    });
  } else {
    overlay.style.display = 'none';
    body.classList.remove('model-sidebar-visible'); // Remove class from body
    overlay.innerHTML = '';
  }
};

// Example: open sidebar from anywhere
window.openModelChatSidebar = (context = {}) => window.toggleModelChatSidebar(true, context);
window.closeModelChatSidebar = () => window.toggleModelChatSidebar(false);

// --- Custom Modal Logic ---
let modalResolve = null;
const modalOverlay = document.getElementById('customModalOverlay');
const modal = document.getElementById('customModal');
const modalTitle = document.getElementById('modalTitle');
const modalLabel = document.getElementById('modalLabel');
const modalInput = document.getElementById('modalInput');
const modalColorInput = document.getElementById('modalColorInput'); // Get color input
const modalOkBtn = document.getElementById('modalOkBtn');
const modalCancelBtn = document.getElementById('modalCancelBtn');

let currentInputType = 'text'; // Track current input type

function showCustomPrompt(options) {
  // options = { title: string, label: string, initialValue: string, type: 'text' | 'color' }
  const { title, label, initialValue = '', type = 'text' } = options;

  return new Promise((resolve) => {
    modalResolve = resolve; // Store the resolve function
    currentInputType = type;

    modalTitle.textContent = title;
    modalLabel.textContent = label;

    if (type === 'color') {
        modalInput.style.display = 'none';
        modalInput.style.marginBottom = '0';
        modalColorInput.style.display = 'block';
        modalColorInput.value = initialValue || '#ffffff'; // Default color if empty
        modalLabel.htmlFor = 'modalColorInput';
    } else {
        modalColorInput.style.display = 'none';
        modalInput.style.display = 'block';
        modalInput.style.marginBottom = '20px';
        modalInput.value = initialValue;
        modalLabel.htmlFor = 'modalInput';
        modalInput.focus();
        modalInput.select();
    }

    document.body.classList.add('modal-open');
  });
}

function handleModalOk() {
  if (modalResolve) {
    const value = (currentInputType === 'color') ? modalColorInput.value : modalInput.value;
    modalResolve(value); // Resolve the promise with the correct input value
  }
  closeModal();
}

function handleModalCancel() {
  if (modalResolve) {
    modalResolve(null); // Resolve with null to indicate cancellation
  }
  closeModal();
}

function closeModal() {
  document.body.classList.remove('modal-open');
  modalResolve = null; // Clear the stored resolve function
  // Reset input display states if needed, though showCustomPrompt handles it
}

// Add event listeners for OK and Cancel buttons
modalOkBtn.addEventListener('click', handleModalOk);
modalCancelBtn.addEventListener('click', handleModalCancel);

// Allow Enter key to submit the modal, and Escape to cancel
document.addEventListener('keydown', (e) => {
  if (document.body.classList.contains('modal-open')) {
    if (e.key === 'Enter') {
      // Prevent Enter from submitting form if modalInput is textarea (not currently used)
      if (!(modalInput.tagName === 'TEXTAREA' && e.target === modalInput)) {
        e.preventDefault();
        handleModalOk();
      }
    } else if (e.key === 'Escape') {
      handleModalCancel();
    }
  }
});

// Expose the function globally (or pass it down)
window.showCustomPrompt = showCustomPrompt;
// --- End Custom Modal Logic ---

// --- Image Viewer Modal Logic ---
const imageViewerModal = document.getElementById('imageViewerModal');
const modalImageContent = document.getElementById('modalImageContent');
const modalImageLink = document.getElementById('modalImageLink');
const closeImageModalBtn = document.getElementById('closeImageModal');

window.openImageModal = function(imageSrc) {
  if (imageViewerModal && modalImageContent && modalImageLink) {
    // Show loading state
    imageViewerModal.style.display = 'flex';
    document.body.classList.add('image-modal-open');
    
    // Clear previous image if any
    modalImageContent.src = '';
    modalImageContent.style.display = 'none';
    
    // Show loading indicator
    let loader = imageViewerModal.querySelector('.modal-loader');
    if (!loader) {
      loader = document.createElement('div');
      loader.className = 'modal-loader';
      loader.innerHTML = 'Loading...';
      loader.style.color = 'white';
      loader.style.padding = '20px';
      loader.style.textAlign = 'center';
      imageViewerModal.insertBefore(loader, modalImageContent);
    } else {
      loader.style.display = 'block';
    }
    
    // Set up image load and error handlers
    modalImageContent.onload = function() {
      if (loader) loader.style.display = 'none';
      modalImageContent.style.display = 'block';
    };
    
    modalImageContent.onerror = function() {
      if (loader) {
        loader.innerHTML = 'Failed to load image.<br>The image may not exist or cannot be accessed.';
        loader.style.color = '#ff6b6b';
      }
      console.error('Failed to load image:', imageSrc);
    };
    
    // Set image source and link
    modalImageContent.src = imageSrc;
    modalImageLink.href = imageSrc;
    modalImageLink.textContent = 'Open image in new tab';
  }
};

function closeImageViewerModal() {
  if (imageViewerModal) {
    imageViewerModal.style.display = 'none';
    modalImageContent.src = ''; // Clear src to stop loading/free memory
    modalImageLink.href = '#';
    document.body.classList.remove('image-modal-open');
  }
}

if (closeImageModalBtn) {
  closeImageModalBtn.addEventListener('click', closeImageViewerModal);
}

if (imageViewerModal) {
  imageViewerModal.addEventListener('click', (event) => {
    // Close if clicked on the backdrop itself, not on the image or link
    if (event.target === imageViewerModal) {
      closeImageViewerModal();
    }
  });
}

document.addEventListener('keydown', (e) => {
    if (document.body.classList.contains('image-modal-open')) {
        if (e.key === 'Escape') {
            closeImageViewerModal();
        }
    }
});
// --- End Image Viewer Modal Logic ---

// Navbar: process all messages and check projects toggle
const processAllBtnNavbar = document.getElementById('processAllBtnNavbar');
const checkProjectsToggleNavbar = document.getElementById('checkProjectsToggleNavbar');

if (processAllBtnNavbar) {
  processAllBtnNavbar.onclick = () => {
    if (window.pywebview?.api?.process_all_messages) {
      processAllBtnNavbar.disabled = true;
      processAllBtnNavbar.textContent = 'Processing...';
      window.pywebview.api.process_all_messages().then(() => {
        processAllBtnNavbar.textContent = 'Process All Messages';
        processAllBtnNavbar.disabled = false;
      }).catch(() => {
        processAllBtnNavbar.textContent = 'Process All Messages';
        processAllBtnNavbar.disabled = false;
      });
    }
  };
}

if (checkProjectsToggleNavbar) {
  checkProjectsToggleNavbar.onchange = (e) => {
    window.pywebview?.api?.toggle_check_projects?.(e.target.checked);
  };
}

// bind nav bar
document.getElementById('navMainChat')   .addEventListener('click', nav.mainChat);
document.getElementById('navProjects')   .addEventListener('click', nav.projects);
document.getElementById('navProjectChat').addEventListener('click', () => {
  if (selectedProject) nav.projectChat(selectedProject);
  else showNotification('Please select a project first');
});
const navModelChatBtn = document.getElementById('navModelChat');
if (navModelChatBtn) {
  navModelChatBtn.onclick = () => window.openModelChatSidebar();
}

// No longer needed - removed refreshTelegramBtn

// Fetch Telegram and Scrape WhatsApp links in dropdown
const fetchTelegramBtn = document.getElementById('fetchTelegramBtn');
const scrapeWhatsappBtn = document.getElementById('scrapeWhatsappBtn');

if (fetchTelegramBtn) {
  fetchTelegramBtn.onclick = (e) => {
    e.preventDefault(); // Prevent default link behavior
    const originalText = fetchTelegramBtn.textContent;
    fetchTelegramBtn.textContent = 'Fetching...';
    fetchTelegramBtn.style.pointerEvents = 'none'; // Disable clicks

    api.run_telegram_fetch().then(r => {
      fetchTelegramBtn.textContent = originalText;
      fetchTelegramBtn.style.pointerEvents = 'auto'; // Re-enable clicks
      showNotification(r.status === 'ok' ? 'Telegram messages fetched' : 'Fetch failed');
    }).catch(() => {
      fetchTelegramBtn.textContent = originalText;
      fetchTelegramBtn.style.pointerEvents = 'auto'; // Re-enable clicks
      showNotification('Fetch failed');
    });
  };
}

if (scrapeWhatsappBtn) {
  scrapeWhatsappBtn.onclick = (e) => {
    e.preventDefault(); // Prevent default link behavior
    const originalText = scrapeWhatsappBtn.textContent;
    scrapeWhatsappBtn.textContent = 'Scraping...';
    scrapeWhatsappBtn.style.pointerEvents = 'none'; // Disable clicks

    api.run_whatsapp_scrape().then(r => {
      scrapeWhatsappBtn.textContent = originalText;
      scrapeWhatsappBtn.style.pointerEvents = 'auto'; // Re-enable clicks
      showNotification(r.status === 'started' ? 'WhatsApp scraping started' : 'Scrape failed');
    }).catch(() => {
      scrapeWhatsappBtn.textContent = originalText;
      scrapeWhatsappBtn.style.pointerEvents = 'auto'; // Re-enable clicks
      showNotification('Scrape failed');
    });
  };
}

// Always load main chat by default on reload
window.addEventListener('DOMContentLoaded', () => {
  nav.mainChat();
});

// start app when pywebview API is ready
if (window.pywebview) {
  nav.mainChat();
} else {
  window.addEventListener('pywebviewready', () => nav.mainChat());
}
