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
    if (this.done) {
      li.classList.add('message-is-done');
    }

    // Define styles here for better encapsulation or ensure they are in style.css
    // For .message-is-done and .done-status-bubble and .popout-menu z-index

    li.innerHTML = `
      <style>
        .list-item.message-is-done > .message-body {
          opacity: 0.6;
        }
        .bubble.done-status-bubble {
          background-color: #5cb85c; /* Green */
          color: white;
          padding: 2px 6px;
          border-radius: 4px;
          font-size: 0.8em;
        }
        .popout-menu {
          position: absolute; /* Needed for z-index to properly stack */
          z-index: 9999; /* Extremely high z-index to ensure it's always on top */
          /* other styles like background, border, etc., should be in existing CSS */
        }
        /* Add styles for the meta container */
        .message-meta {
          display: flex;
          align-items: center; /* Vertically align items in the center */
          flex-wrap: wrap;     /* Allow bubbles to wrap on smaller screens */
          gap: 8px;            /* Consistent spacing between bubbles */
          margin-top: 5px;     /* Add some space above the bubbles line */
        }
        /* Add styles for individual bubbles for consistency */
        .message-meta .bubble {
          padding: 2px 6px; /* Consistent vertical (2px) and horizontal (6px) padding */
          display: inline-flex; /* Use flex to help center content within the bubble itself */
          align-items: center;
          justify-content: center;
          line-height: 1.2; /* Adjust line height for better vertical centering of text/icons */
          /* Existing bubble styles like border-radius, font-size should be inherited or defined globally */
        }
      </style>
      <div class="message-body cool-message">
        <div class="message-header" ${this.extra ? `title="Context: ${this.extra}"` : ''}>${this.content}</div>
        <div class="message-meta">
          <span class="bubble time-bubble">
            <time datetime="${new Date(this.timestamp).toISOString()}">${new Date(this.timestamp).toLocaleString()}</time>
          </span>
          ${this.project ? `<span class="bubble project-bubble">${this.project}</span>` : ''}
          ${this.remind ? `<span class="bubble remind-bubble">🔔 ${this.remind}</span>` : ''}
          ${this.extra ? `<span class="bubble context-bubble" title="Context: ${this.extra}" data-tooltip="${this.extra}">extra</span>` : ''}
          ${this.done ? '<span class="bubble done-status-bubble">DONE</span>' : ''}
          ${typeof this.importance === 'string' ? `<span class="bubble importance-bubble importance-${this.importance.toLowerCase()}">${this.importance}</span>` : ''}
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
            <li class="done-action-item">${this.done ? '🟡 Mark as Not Done' : '🟢 Mark as Done'}</li>
            <li class="delete-item">🗑️ Delete</li>
          </ul>
        </div>
      </div>
    `;

    // Add image previews if they exist
    if (this.images && this.images.length > 0) {
      const messageBody = li.querySelector('.message-body');
      if (messageBody) {
        const previewsContainer = document.createElement('div');
        previewsContainer.className = 'message-image-previews';
        previewsContainer.style.marginTop = '8px'; // Keep some space from message text
        previewsContainer.style.marginBottom = '8px'; // Add space before bubbles
        previewsContainer.style.display = 'flex';
        // previewsContainer.style.flexWrap = 'wrap'; // Remove for horizontal scrolling
        previewsContainer.style.overflowX = 'auto';   // Enable horizontal scroll
        previewsContainer.style.whiteSpace = 'nowrap'; // Keep images in one line for scrolling
        previewsContainer.style.gap = '8px';

        this.images.forEach(image => {
          const imgContainer = document.createElement('div');
          imgContainer.style.display = 'inline-block';
          imgContainer.style.position = 'relative';
          imgContainer.style.marginRight = '8px';
          
          const imgThumb = document.createElement('img');
          // Ensure path is properly formed - we need to make sure it starts with a slash
          // but doesn't have double slashes
          let imagePath = image.file_path;
          if (!imagePath.startsWith('/')) {
            imagePath = '/' + imagePath;
          }
          
          imgThumb.src = imagePath;
          imgThumb.alt = image.description || 'Message image';
          imgThumb.style.width = '60px';
          imgThumb.style.height = '60px';
          imgThumb.style.objectFit = 'cover';
          imgThumb.style.border = '1px solid #555';
          imgThumb.style.borderRadius = '4px';
          imgThumb.style.cursor = 'pointer';
          imgThumb.dataset.fullsrc = imagePath;
          
          // Add description indicator if available
          if (image.description) {
            imgThumb.title = image.description; // Add tooltip with description
            
            // Add a small info icon to indicate there's a description
            const infoIcon = document.createElement('div');
            infoIcon.innerHTML = 'ℹ️';
            infoIcon.style.position = 'absolute';
            infoIcon.style.bottom = '0';
            infoIcon.style.right = '0';
            infoIcon.style.backgroundColor = 'rgba(0,0,0,0.6)';
            infoIcon.style.color = 'white';
            infoIcon.style.padding = '2px';
            infoIcon.style.borderRadius = '3px';
            infoIcon.style.fontSize = '10px';
            infoIcon.style.zIndex = '1';
            infoIcon.title = image.description;
            
            imgContainer.appendChild(infoIcon);
          }
          
          // Add an error handler to help debug image loading issues
          imgThumb.onerror = function() {
            console.error(`Failed to load image: ${imagePath}`);
            // Provide a visual indication that the image failed to load
            this.style.border = '2px solid red';
            this.style.padding = '5px';
            this.alt = 'Image failed to load';
          };

          imgThumb.addEventListener('click', () => {
            if (window.openImageModal) {
              // Pass the description to the image modal
              window.openImageModal(imgThumb.dataset.fullsrc, image.description);
            }
          });
          
          imgContainer.appendChild(imgThumb);
          previewsContainer.appendChild(imgContainer);
        });
        
        // Insert previews before the message-meta div.
        const messageMeta = messageBody.querySelector('.message-meta');
        if (messageMeta) {
            messageBody.insertBefore(previewsContainer, messageMeta);
        } else {
            // Fallback: Insert before header if no meta (shouldn't happen often)
            const header = messageBody.querySelector('.message-header');
            if(header) {
                messageBody.insertBefore(previewsContainer, header.nextSibling); // Insert after header
            } else {
                 messageBody.prepend(previewsContainer); // Prepend if nothing else found
            }
        }
      }
    }

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
            <li class="done-action-item">${this.done ? '🟡 Mark as Not Done' : '🟢 Mark as Done'}</li>
            <li class="delete-item">🗑️ Delete</li>
          </ul>
        </div>
      </div>
    `;
  }

  attachMenuLogic(li) {
    const menuContainer = li.querySelector('.menu-container');
    const menuBtn = li.querySelector('.menu-btn');
    const popoutMenu = li.querySelector('.popout-menu');
    const editItem = li.querySelector('.edit-item');
    const deleteItem = li.querySelector('.delete-item');
    const changeItem = li.querySelector('.change-item');
    const projectSublist = li.querySelector('.project-sublist');
    const doneActionItem = li.querySelector('.done-action-item');
    let projectsLoaded = false;

    // --- Auto-close logic ---
    const AUTO_CLOSE_MS = 3000; // 3 seconds
    let closeTimer = null;
    function startCloseTimer() {
      clearCloseTimer();
      closeTimer = setTimeout(() => {
        closeMenu();
      }, AUTO_CLOSE_MS);
    }
    function clearCloseTimer() {
      if (closeTimer) {
        clearTimeout(closeTimer);
        closeTimer = null;
      }
    }
    function closeMenu() {
      menuContainer.classList.remove('open');
      li.classList.remove('submenu-open');
      li.style.zIndex = '';
      clearCloseTimer();
      if (popoutMenu) {
        popoutMenu.style.display = '';
        popoutMenu.style.opacity = '';
        popoutMenu.style.pointerEvents = '';
        popoutMenu.style.zIndex = '';
      }
    }

    // Store references to event listeners so we can remove them later
    const documentClickHandler = (e) => {
      if (!menuContainer.contains(e.target) && !menuBtn.contains(e.target)) { 
        closeMenu();
      }
    };
    const documentKeyHandler = (e) => {
      if (e.key === 'Escape') {
        closeMenu();
      }
    };

    // Add event listener for menu button click to toggle submenu-open class on parent list-item
    menuBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      // Close all other open submenus
      document.querySelectorAll('.list-item.submenu-open').forEach(item => {
        if (item !== li) {
          item.classList.remove('submenu-open');
          const otherContainer = item.querySelector('.menu-container');
          if (otherContainer) otherContainer.classList.remove('open');
          item.style.zIndex = '';
          // Also clear any timers on other menus
          if (item._closeTimer) {
            clearTimeout(item._closeTimer);
            item._closeTimer = null;
          }
        }
      });
      // Toggle the submenu-open class on this list-item
      const isCurrentlyOpen = li.classList.contains('submenu-open');
      if (isCurrentlyOpen) {
        closeMenu();
        document.removeEventListener('click', documentClickHandler);
        document.removeEventListener('keydown', documentKeyHandler);
      } else {
        li.classList.add('submenu-open');
        menuContainer.classList.add('open');
        li.style.zIndex = '1000';
        if (popoutMenu) {
          popoutMenu.style.display = 'block';
          popoutMenu.style.opacity = '1';
          popoutMenu.style.pointerEvents = 'auto';
          popoutMenu.style.zIndex = '1001';
        }
        document.addEventListener('click', documentClickHandler);
        document.addEventListener('keydown', documentKeyHandler);
        startCloseTimer();
      }
    });
    // Pause/Reset timer on interaction
    if (popoutMenu) {
      popoutMenu.addEventListener('mouseenter', clearCloseTimer);
      popoutMenu.addEventListener('mouseleave', startCloseTimer);
      popoutMenu.addEventListener('mousedown', clearCloseTimer);
      popoutMenu.addEventListener('mouseup', startCloseTimer);
    }
    menuBtn.addEventListener('mouseenter', clearCloseTimer);
    menuBtn.addEventListener('mouseleave', startCloseTimer);

    // Try to get the latest API reference in case it became available
    const currentApi = this.api || window.pywebview?.api;

    // Edit and delete actions
    editItem.addEventListener('click', e => { 
        e.stopPropagation(); 
        window.actions.editMessageWithProject(this.id, this.project||''); 
        menuContainer.classList.remove('open'); // Close menu
        li.classList.remove('submenu-open'); // Remove submenu-open class
    });
    deleteItem.addEventListener('click', e => { 
        e.stopPropagation(); 
        window.actions.deleteMessage(this.id); 
        menuContainer.classList.remove('open'); // Close menu
        li.classList.remove('submenu-open'); // Remove submenu-open class
    });

    // New Done Action Item Handler
    if (doneActionItem) {
      doneActionItem.addEventListener('click', e => {
        e.stopPropagation();
        this.done = !this.done; // Toggle local state

        if (currentApi) {
          currentApi.edit_message(this.id, undefined, undefined, undefined, undefined, undefined, this.done)
            .then(() => {
                // Successfully updated on backend
                // Update UI
                doneActionItem.textContent = this.done ? '🟡 Mark as Not Done' : '🟢 Mark as Done';
                li.classList.toggle('message-is-done', this.done);
                
                // Update or add/remove the status bubble
                let statusBubble = li.querySelector('.message-meta .done-status-bubble');
                if (this.done) {
                  if (!statusBubble) {
                    statusBubble = document.createElement('span');
                    statusBubble.className = 'bubble done-status-bubble';
                    statusBubble.textContent = 'DONE';
                    // Find a good place to insert it, e.g., after context bubble or at the end of meta
                    const metaDiv = li.querySelector('.message-meta');
                    const contextBubble = metaDiv.querySelector('.context-bubble');
                    if (contextBubble) {
                        contextBubble.insertAdjacentElement('afterend', statusBubble);
                    } else {
                        metaDiv.appendChild(statusBubble);
                    }
                  }
                  statusBubble.style.display = ''; // Ensure visible
                } else {
                  if (statusBubble) {
                    statusBubble.style.display = 'none'; // Or statusBubble.remove();
                  }
                }
            })
            .catch(err => {
                console.error("Failed to update done status:", err);
                this.done = !this.done; // Revert on error
            });
        }
        menuContainer.classList.remove('open'); // Close menu
        li.classList.remove('submenu-open'); // Remove submenu-open class
      });
    }

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
                menuContainer.classList.remove('open'); // Close menu after selecting a project
                li.classList.remove('submenu-open'); // Remove submenu-open class
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
