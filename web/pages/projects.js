// Projects page, mirroring Tkinter ProjectsWindow with grid of colored boxes
import { createEmojiPicker } from '../components/emoji_picker.js';

// Helper function to determine text color based on background
function getContrastYIQ(hexcolor){
    if (!hexcolor) return '#fff'; // Default to white if no color
    hexcolor = hexcolor.replace("#", "");
    var r = parseInt(hexcolor.substr(0,2),16);
    var g = parseInt(hexcolor.substr(2,2),16);
    var b = parseInt(hexcolor.substr(4,2),16);
    var yiq = ((r*299)+(g*587)+(b*114))/1000;
    return (yiq >= 128) ? '#000' : '#fff';
}

export function renderProjects(container, api, onProjectSelect) {
    container.innerHTML = `
        <style scoped>
            .projects-wrapper{display:flex;flex-direction:column;height:100%;}
            /* NEW: Styles for the special projects row */
            .special-projects-container{display:flex;gap:12px;margin-top:12px;margin-bottom:18px; /* Add some space below */}
            /* Style for grid */
            .grid-container{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;flex:1;overflow-y:auto;}
            .project-box{position:relative;border-radius:8px;color:#000;padding:16px;cursor:pointer;box-shadow:0 1px 3px rgba(0,0,0,.15);transition:transform .1s;}
            .project-box:hover{transform:translateY(-2px);}
            /* NEW: Allow special project boxes to have defined width */
            .special-projects-container .project-box { flex-basis: 180px; /* Example fixed width */ }
            .project-name{font-weight:600;margin-bottom:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
            .project-actions{position:absolute;top:8px;right:8px;display:flex;gap:6px;opacity:0;transition:opacity .2s;}
            .project-box:hover .project-actions{opacity:1;}
            .project-actions button{background:none;border:none;font-size:16px;cursor:pointer;padding:2px;}
            .form-container{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px;align-items:flex-end;}
            .form-container input[type="text"]{flex:1 1 140px;padding:6px 8px;font:inherit;}
            .emoji-input-wrapper{position:relative;width:40px;}
            .emoji-input{width:100%;text-align:center;padding:6px 8px;font:inherit;cursor:pointer;}
            .emoji-picker-button{position:absolute;right:0;top:0;height:100%;width:20px;background:none;border:none;cursor:pointer;font-size:12px;opacity:0.5;display:flex;align-items:center;justify-content:center;}
            .emoji-picker-button:hover{opacity:1;}
            .form-container input[type="color"]{width:48px;height:34px;padding:0;border:none;background:none;}
            .loading{text-align:center;padding:1em;color:#888;}
            button[disabled]{opacity:0.5;cursor:not-allowed;}
        </style>
        <div class="projects-wrapper">
            <h2>Projects</h2>
            <div id="projectsLoading" class="loading" hidden>Loading…</div>
            <!-- NEW: Container for special projects -->
            <div id="specialProjectsContainer" class="special-projects-container"></div>
            <!-- Container for regular projects -->
            <div id="projectsGrid" class="grid-container" aria-live="polite"></div>
            <div id="projectsError" style="color:#ff5252;margin:8px 0 0 0;"></div>
            <form id="addProjectForm" class="form-container">
                <input id="projectName" type="text" placeholder="Project name" aria-label="Project name" required />
                <input id="projectDescription" type="text" placeholder="Description" aria-label="Description" />
                <div class="emoji-input-wrapper">
                    <input id="projectEmoji" type="text" class="emoji-input" placeholder="📁" aria-label="Emoji" maxlength="2" value="📁" readonly />
                    <button type="button" id="emojiPickerButton" class="emoji-picker-button" aria-label="Select emoji">▼</button>
                </div>
                <input id="projectColor" type="color" value="#dddddd" aria-label="Color" />
                <button id="addProjectBtn" disabled>Add Project</button>
            </form>
        </div>
    `;

    const nameInput = container.querySelector('#projectName');
    const descInput = container.querySelector('#projectDescription');
    const colorInput = container.querySelector('#projectColor');
    const emojiInput = container.querySelector('#projectEmoji');
    const emojiButton = container.querySelector('#emojiPickerButton');
    const addBtn = container.querySelector('#addProjectBtn');
    const form = container.querySelector('#addProjectForm');

    // Initialize emoji picker
    createEmojiPicker(emojiInput, emojiButton);

    function updateBtnState() {
        addBtn.disabled = nameInput.value.trim().length === 0;
    }
    updateBtnState();
    nameInput.addEventListener('input', updateBtnState);

    form.addEventListener('submit', (e) => {
        e.preventDefault();
        addProject(api, nameInput, descInput, colorInput, emojiInput, addBtn, onProjectSelect);
    });

    loadProjects(api, onProjectSelect);
}

async function addProject(api, nameInput, descInput, colorInput, emojiInput, addBtn, onProjectSelect) {
    const name = nameInput.value.trim();
    const emoji = emojiInput.value.trim() || '📁';
    if (!name) return;
    addBtn.disabled = true;

    // Try to get the latest API reference in case it became available
    const currentApi = api || window.pywebview?.api;

    try {
        const r = await currentApi.add_project(name, descInput.value.trim(), colorInput.value, emoji);
        if (r && r.success === false && r.error) {
            document.getElementById('projectsError').textContent = r.error;
        } else {
            nameInput.value = '';
            descInput.value = '';
            emojiInput.value = '';
            document.getElementById('projectsError').textContent = '';
            loadProjects(currentApi, onProjectSelect);
        }
    } catch (e) {
        document.getElementById('projectsError').textContent = e.message || 'Failed to add project.';
    } finally {
        addBtn.disabled = nameInput.value.trim().length === 0;
        nameInput.focus();
    }
}

function loadProjects(api, onProjectSelect) {
    const loadingDiv = document.getElementById('projectsLoading');
    const specialContainer = document.getElementById('specialProjectsContainer'); // Get new container
    const grid = document.getElementById('projectsGrid');
    if (loadingDiv) loadingDiv.hidden = false;

    specialContainer.innerHTML = ''; // Clear special projects
    grid.innerHTML = ''; // Clear existing projects first

    // Try to get the latest API reference in case it became available
    const currentApi = api || window.pywebview?.api;

    // Defensive: check api exists
    if (!currentApi || typeof currentApi.get_all_projects !== 'function' || typeof currentApi.get_reminder_messages !== 'function') { // Added check for get_reminder_messages
        if (loadingDiv) loadingDiv.hidden = true;
        grid.innerHTML = '<div style="color:#ff5252">API not available. Retrying in 1s...</div>';
        setTimeout(() => loadProjects(currentApi, onProjectSelect), 1000);
        return;
    }
    
    const CLIPBOARD_PROJECT_NAME = "Saved Clips"; // Name of the clipboard project

    // Promise.allSettled to load both regular projects and reminders concurrently
    Promise.allSettled([
        currentApi.get_all_projects(),
        currentApi.get_reminder_messages() // Assumes this new API function exists
    ]).then(results => {
        // Clear loading/error messages
        if (loadingDiv) loadingDiv.hidden = true;
        
        let hasAnyContentInSpecial = false;
        let hasRegularContent = false;

        // --- Render Reminders Project (if successful and reminders exist) ---
        const reminderResult = results[1];
        if (reminderResult.status === 'fulfilled' && reminderResult.value && Array.isArray(reminderResult.value)) {
            const reminders = reminderResult.value;
             if (reminders.length > 0) { 
                hasAnyContentInSpecial = true;
                const box = document.createElement('div');
                box.className = 'project-box reminders-box'; 
                const bgColor = '#f0e68c'; 
                const textColor = getContrastYIQ(bgColor);
                box.style.background = bgColor;
                box.style.color = textColor;
                box.setAttribute('role', 'button');
                box.setAttribute('tabindex', '0');
                box.innerHTML = `
                    <div class="project-icon">⏰</div>
                    <div class="project-name">Reminders (${reminders.length})</div>
                    <div class="project-actions"></div>
                `;
                box.addEventListener('click', () => onProjectSelect({ id: '__reminders__', name: 'Reminders' })); 
                specialContainer.appendChild(box);
            }
        } else if (reminderResult.status === 'rejected') {
            console.error("Failed to load reminders:", reminderResult.reason);
            // Create an error display for reminders in special container
            const errorDiv = document.createElement('div');
            errorDiv.style.color = '#ffcc00';
            errorDiv.style.flexBasis = '100%';
            errorDiv.textContent = 'Failed to load reminders.';
            specialContainer.appendChild(errorDiv);
            hasAnyContentInSpecial = true; // Still content (error message)
        }

        // --- Process All Projects (including Clipboard and Regular) ---
        const projectResult = results[0];
        let regularProjects = [];
        let clipboardProject = null;

        if (projectResult.status === 'fulfilled' && projectResult.value && Array.isArray(projectResult.value)) {
            const allFetchedProjects = projectResult.value;
            allFetchedProjects.forEach(proj => {
                if (proj.name === CLIPBOARD_PROJECT_NAME) {
                    clipboardProject = proj;
                } else {
                    regularProjects.push(proj);
                }
            });

            // --- Render Clipboard Project (if found) ---
            if (clipboardProject) {
                hasAnyContentInSpecial = true;
                const box = document.createElement('div');
                box.className = 'project-box clipboard-box'; // Add specific class for styling
                const bgColor = clipboardProject.color || '#A7C7E7'; // Use project's color or default
                const textColor = getContrastYIQ(bgColor);
                box.style.background = bgColor;
                box.style.color = textColor;
                box.setAttribute('role', 'button');
                box.setAttribute('tabindex', '0');
                box.innerHTML = `
                    <div class="project-icon">${clipboardProject.emoji || '📋'}</div>
                    <div class="project-name">${clipboardProject.name}</div>
                    <div class="project-actions"></div>
                `;
                box.addEventListener('click', () => onProjectSelect(clipboardProject));
                specialContainer.appendChild(box);
            }
        } else if (projectResult.status === 'rejected') {
            console.error("Failed to load projects:", projectResult.reason);
             // Error for all projects will be handled below with regular projects grid
        }


        // --- Render Regular Projects (if successful) ---
        if (projectResult.status === 'fulfilled') { // Check status again for clarity
            if (regularProjects.length > 0) {
                hasRegularContent = true;
                regularProjects.forEach(proj => {
                    const box = document.createElement('div');
                    box.className = 'project-box';
                    const bgColor = proj.color || '#dddddd';
                    const textColor = getContrastYIQ(bgColor);
                    box.style.background = bgColor;
                    box.style.color = textColor;
                    box.setAttribute('role', 'button');
                    box.setAttribute('tabindex', '0');
                    box.innerHTML = `
                        <div class="project-icon">${proj.emoji || '📁'}</div>
                        <div class="project-name" style="color: ${textColor};">${proj.name}</div>
                        <div class="project-actions">
                            <button class="edit-btn" aria-label="Edit project">✏️</button>
                            <button class="delete-btn" aria-label="Delete project">🗑️</button>
                        </div>
                    `;
                    box.addEventListener('click', () => onProjectSelect(proj));
                    box.querySelector('.edit-btn').addEventListener('click', e => {
                        e.stopPropagation();
                        window.actions?.editProject(proj.id, { 
                            name: proj.name, 
                            description: proj.description, 
                            color: proj.color, 
                            emoji: proj.emoji 
                        });
                    });
                    box.querySelector('.delete-btn').addEventListener('click', e => {
                        e.stopPropagation();
                        window.actions?.deleteProject(proj.id);
                    });
                    grid.appendChild(box); // Append to regular grid
                });
            }
        }
        
        // --- Handle Error for All Projects (if projectResult failed) ---
        if (projectResult.status === 'rejected') {
             grid.innerHTML = '<div style="color:#ff5252; grid-column: 1 / -1;">Failed to load projects.</div>';
        }


        // --- Handle Empty State for Regular Projects Grid ---
        if (!hasRegularContent && projectResult.status === 'fulfilled') { // Only show if projects loaded successfully but were empty
             grid.innerHTML = '<div style="color:#bbb;text-align:center;padding:2em 0; grid-column: 1 / -1;">No user projects found. Add one below!</div>';
        }
        
        // If special container is empty, it just won't show anything, which is fine.

    }).catch(e => { // Catch errors from Promise.allSettled itself (unlikely)
        if (loadingDiv) loadingDiv.hidden = true;
        specialContainer.innerHTML = ''; // Clear on major error
        grid.innerHTML = '<div style="color:#ff5252; grid-column: 1 / -1;">An unexpected error occurred while loading data.</div>';
        console.error("Error in loadProjects Promise.allSettled:", e);
    });
}

export const __testonly__ = { addProject, loadProjects };
