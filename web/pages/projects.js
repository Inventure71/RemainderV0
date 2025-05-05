// Projects page, mirroring Tkinter ProjectsWindow with grid of colored boxes
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
                <input id="projectColor" type="color" value="#dddddd" aria-label="Color" />
                <button id="addProjectBtn" disabled>Add Project</button>
            </form>
        </div>
    `;

    const nameInput = container.querySelector('#projectName');
    const descInput = container.querySelector('#projectDescription');
    const colorInput = container.querySelector('#projectColor');
    const addBtn    = container.querySelector('#addProjectBtn');
    const form      = container.querySelector('#addProjectForm');

    function updateBtnState() {
        addBtn.disabled = nameInput.value.trim().length === 0;
    }
    updateBtnState();
    nameInput.addEventListener('input', updateBtnState);

    form.addEventListener('submit', (e) => {
        e.preventDefault();
        addProject(api, nameInput, descInput, colorInput, addBtn, onProjectSelect);
    });

    loadProjects(api, onProjectSelect);
}

async function addProject(api, nameInput, descInput, colorInput, addBtn, onProjectSelect) {
    const name = nameInput.value.trim();
    if (!name) return;
    addBtn.disabled = true;

    // Try to get the latest API reference in case it became available
    const currentApi = api || window.pywebview?.api;

    try {
        const r = await currentApi.add_project(name, descInput.value.trim(), colorInput.value);
        if (r && r.success === false && r.error) {
            document.getElementById('projectsError').textContent = r.error;
        } else {
            nameInput.value = '';
            descInput.value = '';
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
    if (!currentApi || typeof currentApi.get_all_projects !== 'function') {
        if (loadingDiv) loadingDiv.hidden = true;
        grid.innerHTML = '<div style="color:#ff5252">API not available. Retrying in 1s...</div>';
        setTimeout(() => loadProjects(currentApi, onProjectSelect), 1000);
        return;
    }

    // Promise.allSettled to load both regular projects and reminders concurrently
    Promise.allSettled([
        currentApi.get_all_projects(),
        currentApi.get_reminder_messages() // Assumes this new API function exists
    ]).then(results => {
        // Clear loading/error messages
        if (loadingDiv) loadingDiv.hidden = true;
        // grid.innerHTML = ''; // Already cleared above

        let hasRegularContent = false;

        // --- Render Reminders Project (if successful and reminders exist) ---
        const reminderResult = results[1];
        if (reminderResult.status === 'fulfilled' && reminderResult.value && Array.isArray(reminderResult.value)) {
            // Always show the box, even if empty for now, or check length > 0
            const reminders = reminderResult.value;
             if (reminders.length > 0) { // Only show if there are reminders
                const box = document.createElement('div');
                box.className = 'project-box reminders-box'; // Add specific class for styling
                box.style.background = '#f0e68c'; // Khaki color for distinction
                box.setAttribute('role', 'button');
                box.setAttribute('tabindex', '0');
                box.innerHTML = `
                    <div class="project-icon">⏰</div>
                    <div class="project-name">Reminders (${reminders.length})</div>
                    <div class="project-actions"></div>
                `;
                box.addEventListener('click', () => onProjectSelect({ id: '__reminders__', name: 'Reminders' })); // Special ID
                specialContainer.appendChild(box); // Append to special container
            }
        } else if (reminderResult.status === 'rejected') {
            console.error("Failed to load reminders:", reminderResult.reason);
            specialContainer.innerHTML = '<div style="color:#ffcc00; flex-basis: 100%;">Failed to load reminders.</div>'; // Show error in special container
        }
        // Add other special projects here if needed in the future

        // --- Render Regular Projects (if successful) ---
        const projectResult = results[0];
        if (projectResult.status === 'fulfilled' && projectResult.value && Array.isArray(projectResult.value)) {
            const projects = projectResult.value;
            if (projects.length > 0) {
                hasRegularContent = true;
                projects.forEach(proj => {
                    const box = document.createElement('div');
                    box.className = 'project-box';
                    box.style.background = proj.color || '#dddddd';
                    box.setAttribute('role', 'button');
                    box.setAttribute('tabindex', '0');
                    box.innerHTML = `
                        <div class="project-icon"></div>
                        <div class="project-name">${proj.name}</div>
                        <div class="project-actions">
                            <button class="edit-btn" aria-label="Edit project">✏️</button>
                            <button class="delete-btn" aria-label="Delete project">🗑️</button>
                        </div>
                    `;
                    box.addEventListener('click', () => onProjectSelect(proj));
                    box.querySelector('.edit-btn').addEventListener('click', e => {
                        e.stopPropagation();
                        window.actions?.editProject(proj.id);
                    });
                    box.querySelector('.delete-btn').addEventListener('click', e => {
                        e.stopPropagation();
                        window.actions?.deleteProject(proj.id);
                    });
                    grid.appendChild(box); // Append to regular grid
                });
            }
        } else if (projectResult.status === 'rejected') {
            console.error("Failed to load projects:", projectResult.reason);
            grid.innerHTML += '<div style="color:#ff5252; grid-column: 1 / -1;">Failed to load projects.</div>'; // Span full grid width
        }

        // --- Handle Empty State for Regular Projects ---
        if (!hasRegularContent) {
             grid.innerHTML = '<div style="color:#bbb;text-align:center;padding:2em 0; grid-column: 1 / -1;">No user projects found.</div>'; // Span full grid width
        }

    }).catch(e => { // Catch errors from Promise.allSettled itself (unlikely)
        if (loadingDiv) loadingDiv.hidden = true;
        specialContainer.innerHTML = ''; // Clear on major error
        grid.innerHTML = '<div style="color:#ff5252; grid-column: 1 / -1;">An unexpected error occurred while loading data.</div>';
        console.error("Error in loadProjects Promise.allSettled:", e);
    });
}

export const __testonly__ = { addProject, loadProjects };
