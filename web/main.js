// web/main.js
import { renderMainChat }    from './pages/main_chat.js';
import { renderProjects }    from './pages/projects.js';
import { renderProjectChat } from './pages/project_chat.js';
import { showNotification }  from './utils/ui_helpers.js';
import { renderModelChatSidebar } from './components/model_chat_sidebar.js';

const api = window.pywebview?.api;
const app = document.getElementById('app');
let selectedProject = null;

const nav = {
  mainChat:    () => { selectedProject = null; window.selectedProject = null; renderMainChat(app, api); },
  projects:    () => renderProjects(app, api, proj => { selectedProject = proj; window.selectedProject = proj; nav.projectChat(proj); }),
  projectChat: proj => { window.selectedProject = proj; renderProjectChat(app, api, proj); },
};

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
  editProject: id => {
    const name = prompt('New project name:', '');
    if (!name) return;
    const desc = prompt('New description:', '');
    const color = prompt('New color (hex):', '#dddddd');
    api.edit_project(id, name, desc, color).then(nav.projects);
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

// Attach listeners (only once)
modalOkBtn.addEventListener('click', handleModalOk);
modalCancelBtn.addEventListener('click', handleModalCancel);
modalOverlay.addEventListener('click', handleModalCancel); // Close on overlay click
modalInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        handleModalOk();
    } else if (e.key === 'Escape') {
        handleModalCancel();
    }
});

// Expose the function globally (or pass it down)
window.showCustomPrompt = showCustomPrompt;
// --- End Custom Modal Logic ---

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
