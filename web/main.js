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
  const li = document.querySelector(`li[data-msg-id="${msgId}"]`);
  console.log('[main.js] Found element:', li);
  if (li) {
    li.scrollIntoView({ behavior: 'smooth', block: 'center' });
    li.classList.add('highlighted');
    setTimeout(() => li.classList.remove('highlighted'), 2000);
  } else {
    console.warn(`[main.js] Message element not found for msgId: ${msgId}`);
    showNotification('Message not found in current view');
  }
};

// Show/hide model chat sidebar overlay
window.toggleModelChatSidebar = (show, context = {}) => {
  const overlay = document.getElementById('modelChatSidebarOverlay');
  if (!overlay) return;
  if (show) {
    overlay.style.display = 'block';
    import('./components/model_chat_sidebar.js').then(({ renderModelChatSidebar }) => {
      renderModelChatSidebar(overlay, context);
    });
  } else {
    overlay.style.display = 'none';
    overlay.innerHTML = '';
  }
};

// Example: open sidebar from anywhere
window.openModelChatSidebar = (context = {}) => window.toggleModelChatSidebar(true, context);
window.closeModelChatSidebar = () => window.toggleModelChatSidebar(false);

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

// refresh telegram
document.getElementById('refreshTelegramBtn').addEventListener('click', () => {
  api.refresh_telegram_messages().then(r => {
    showNotification(r.success ? 'Telegram refreshed' : 'Refresh failed: ' + r.error);
    nav.mainChat();
  });
});

// Fetch Telegram and Scrape WhatsApp buttons
const fetchTelegramBtn = document.getElementById('fetchTelegramBtn');
const scrapeWhatsappBtn = document.getElementById('scrapeWhatsappBtn');

if (fetchTelegramBtn) {
  fetchTelegramBtn.onclick = () => {
    fetchTelegramBtn.disabled = true;
    fetchTelegramBtn.textContent = 'Fetching...';
    api.run_telegram_fetch().then(r => {
      fetchTelegramBtn.textContent = 'Fetch Telegram';
      fetchTelegramBtn.disabled = false;
      showNotification(r.status === 'ok' ? 'Telegram messages fetched' : 'Fetch failed');
    }).catch(() => {
      fetchTelegramBtn.textContent = 'Fetch Telegram';
      fetchTelegramBtn.disabled = false;
      showNotification('Fetch failed');
    });
  };
}

if (scrapeWhatsappBtn) {
  scrapeWhatsappBtn.onclick = () => {
    scrapeWhatsappBtn.disabled = true;
    scrapeWhatsappBtn.textContent = 'Scraping...';
    api.run_whatsapp_scrape().then(r => {
      scrapeWhatsappBtn.textContent = 'Scrape WhatsApp';
      scrapeWhatsappBtn.disabled = false;
      showNotification(r.status === 'started' ? 'WhatsApp scraping started' : 'Scrape failed');
    }).catch(() => {
      scrapeWhatsappBtn.textContent = 'Scrape WhatsApp';
      scrapeWhatsappBtn.disabled = false;
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