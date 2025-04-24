// web/main.js
import { renderMainChat }    from './pages/main_chat.js';
import { renderProjects }    from './pages/projects.js';
import { renderProjectChat } from './pages/project_chat.js';
import { showNotification }  from './utils/ui_helpers.js';

const api = window.pywebview?.api;
const app = document.getElementById('app');
let selectedProject = null;

const nav = {
  mainChat:    () => renderMainChat(app, api),
  projects:    () => renderProjects(app, api, proj => { selectedProject = proj; window.selectedProject = proj; nav.projectChat(proj); }),
  projectChat: proj => { window.selectedProject = proj; renderProjectChat(app, api, proj); },
  modelChat:   () => { app.innerHTML = '<h2>Model Chat</h2><p>Coming soon…</p>'; }
};

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
      .then(() => window.selectedProject ? nav.projectChat(window.selectedProject) : nav.mainChat());
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

// bind nav bar
document.getElementById('navMainChat')   .addEventListener('click', nav.mainChat);
document.getElementById('navProjects')   .addEventListener('click', nav.projects);
document.getElementById('navProjectChat').addEventListener('click', () => {
  if (selectedProject) nav.projectChat(selectedProject);
  else showNotification('Please select a project first');
});
document.getElementById('navModelChat')  .addEventListener('click', nav.modelChat);

// refresh telegram
document.getElementById('refreshTelegramBtn').addEventListener('click', () => {
  api.refresh_telegram_messages().then(r => {
    showNotification(r.success ? 'Telegram refreshed' : 'Refresh failed: ' + r.error);
    nav.mainChat();
  });
});

// start app when pywebview API is ready
if (window.pywebview) {
  nav.mainChat();
} else {
  window.addEventListener('pywebviewready', () => nav.mainChat());
}