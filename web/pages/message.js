// Message.js - encapsulates rendering and submenu logic for a message in main/project chat
export class Message {
  constructor(data, api) {
    Object.assign(this, data);
    this.api = api;
  }

  render() {
    const li = document.createElement('li');
    li.className = 'list-item';
    li.tabIndex = 0;
    li.dataset.msgId = this.id;

    li.innerHTML = `
      <div class="message-body cool-message">
        <div class="message-header" ${this.extra ? `title="Context: ${this.extra}"` : ''}>${this.content}</div>
        <div class="message-meta">
          <span class="bubble time-bubble">
            <time datetime="${new Date(this.timestamp).toISOString()}">${new Date(this.timestamp).toLocaleString()}</time>
          </span>
          ${this.project ? `<span class="bubble project-bubble">${this.project}</span>` : ''}
          ${this.remind ? `<span class="bubble remind-bubble">🔔 ${this.remind}</span>` : ''}
          ${this.extra ? `<span class="bubble context-bubble" title="Context: ${this.extra}" data-tooltip="${this.extra}">extra</span>` : ''}
          <label class="done-toggle">
            <input type="checkbox" class="done-checkbox" ${this.done ? 'checked' : ''}>
            <span class="done-label">DONE</span>
          </label>
        </div>
        <div class="message-tags">
          ${typeof this.importance === 'string' ? `<span class="tag importance-${this.importance.toLowerCase()}">${this.importance}</span>` : ''}
        </div>
      </div>
      <div class="menu-container">
        <button class="menu-btn" aria-label="Message options">⋮</button>
        <div class="popout-menu">
          <ul class="menu-list">
            <li class="edit-item">✏️ Edit</li>
            <li class="change-item">Change project ▸
              <ul class="project-sublist"></ul>
            </li>
            <li class="delete-item">🗑️ Delete</li>
          </ul>
        </div>
      </div>
    `;
    this.attachMenuLogic(li);
    return li;
  }

  renderSubmenu() {
    return `
      <div class="menu-container">
        <button class="menu-btn" aria-label="Message options">⋮</button>
        <div class="popout-menu">
          <ul class="menu-list">
            <li class="edit-item">✏️ Edit</li>
            <li class="change-item">Change project ▸
              <ul class="project-sublist"></ul>
            </li>
            <li class="delete-item">🗑️ Delete</li>
          </ul>
        </div>
      </div>
    `;
  }

  attachMenuLogic(li) {
    const menuContainer = li.querySelector('.menu-container');
    const editItem = li.querySelector('.edit-item');
    const deleteItem = li.querySelector('.delete-item');
    const changeItem = li.querySelector('.change-item');
    const projectSublist = li.querySelector('.project-sublist');
    const doneCheckbox = li.querySelector('.done-checkbox');
    let projectsLoaded = false;

    // Try to get the latest API reference in case it became available
    const currentApi = this.api || window.pywebview?.api;

    // Add event listener for the done checkbox
    if (doneCheckbox) {
      doneCheckbox.addEventListener('change', (e) => {
        const done = e.target.checked;
        if (currentApi) {
          currentApi.edit_message(this.id, undefined, undefined, undefined, undefined, undefined, done);
          this.done = done; // Update the local state
        }
      });
    }

    // Shift the pop‑out menu slightly upward for better positioning
    const popoutMenu = menuContainer.querySelector('.popout-menu');
    if (popoutMenu) {
      // Negative margin moves the submenu up; adjust the value to taste
      popoutMenu.style.marginTop = '-15px';
    }

    // Edit and delete actions
    editItem.addEventListener('click', e => { e.stopPropagation(); window.actions.editMessageWithProject(this.id, this.project||''); });
    deleteItem.addEventListener('click', e => { e.stopPropagation(); window.actions.deleteMessage(this.id); });

    // Lazy-load projects on hover of "Change project"
    changeItem.addEventListener('mouseenter', () => {
      if (!projectsLoaded) {
        // Try to get the latest API reference in case it became available
        const currentApi = this.api || window.pywebview?.api;

        if (currentApi && typeof currentApi.get_all_projects === 'function') {
          currentApi.get_all_projects().then(projects => {
            projects.forEach(proj => {
              const item = document.createElement('li');
              item.textContent = proj.name;
              item.tabIndex = 0;
              item.addEventListener('click', evt => {
                evt.stopPropagation();
                window.actions.changeProject(this.id, proj.name);
                // update the project bubble immediately for UX
                const projBubble = li.querySelector('.project-bubble');
                if (projBubble) {
                  projBubble.textContent = proj.name;
                  projBubble.style.background = proj.color;
                  projBubble.style.color = getContrast(proj.color);
                }
              });
              projectSublist.appendChild(item);
            });
            projectsLoaded = true;
          }).catch(err => {
            console.error('Error loading projects:', err);
          });
        } else {
          console.warn('API not available for loading projects');
        }
      }
    });

    // Close menu when clicking outside
    document.addEventListener('click', e => { if (!menuContainer.contains(e.target)) { menuContainer.classList.remove('open'); } });

    // Prevent context-menu override
    li.addEventListener('contextmenu', e => {
      e.preventDefault();
      document.querySelectorAll('.list-item.context-menu-active')
              .forEach(item => item.classList.remove('context-menu-active'));
      li.classList.add('context-menu-active');

      const closeMenu = (evt) => {
        if (!li.contains(evt.target)) {
          li.classList.remove('context-menu-active');
          document.removeEventListener('mousedown', closeMenu);
          document.removeEventListener('keydown', escClose);
        }
      };
      const escClose = (evt) => {
        if (evt.key === 'Escape') {
          li.classList.remove('context-menu-active');
          document.removeEventListener('mousedown', closeMenu);
          document.removeEventListener('keydown', escClose);
        }
      };
      document.addEventListener('mousedown', closeMenu);
      document.addEventListener('keydown', escClose);
    });

    // Hide context menu on scroll
    li.closest('.scrollable-list')?.addEventListener('scroll', () => {
      li.classList.remove('context-menu-active');
    });

    // Helper to get contrasting text color
    function getContrast(hex) {
      const c = hex.substring(1);
      const r = parseInt(c.substr(0,2),16);
      const g = parseInt(c.substr(2,2),16);
      const b = parseInt(c.substr(4,2),16);
      const yiq = (r*299 + g*587 + b*114) / 1000;
      return yiq >= 128 ? '#000' : '#fff';
    }
    const projBubble = li.querySelector('.project-bubble');
    if (projBubble) {
      // Try to get the latest API reference in case it became available
      const currentApi = this.api || window.pywebview?.api;

      if (currentApi && typeof currentApi.get_all_projects === 'function') {
        currentApi.get_all_projects().then(projs => {
          const pr = projs.find(p => p.name === this.project);
          if (pr) {
            projBubble.style.background = pr.color;
            projBubble.style.color = getContrast(pr.color);
          }
        }).catch(err => {
          console.error('Error loading projects for bubble styling:', err);
        });
      }
    }
  }
}

export const __testonly__ = { Message };
