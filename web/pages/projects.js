// Projects page, mirroring Tkinter ProjectsWindow with grid of colored boxes
export function renderProjects(container, api, onProjectSelect) {
    container.innerHTML = `
        <style scoped>
            .projects-wrapper{display:flex;flex-direction:column;height:100%;}
            .grid-container{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;flex:1;overflow-y:auto;margin-top:12px;}
            .project-box{position:relative;border-radius:8px;color:#000;padding:16px;cursor:pointer;box-shadow:0 1px 3px rgba(0,0,0,.15);transition:transform .1s;}
            .project-box:hover{transform:translateY(-2px);}
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
    if (loadingDiv) loadingDiv.hidden = false;

    // Try to get the latest API reference in case it became available
    const currentApi = api || window.pywebview?.api;

    // Defensive: check api exists
    if (!currentApi || typeof currentApi.get_all_projects !== 'function') {
        if (loadingDiv) loadingDiv.hidden = true;
        document.getElementById('projectsGrid').innerHTML = '<div style="color:#ff5252">API not available. Retrying in 1s...</div>';
        setTimeout(() => loadProjects(currentApi, onProjectSelect), 1000);
        return;
    }
    currentApi.get_all_projects().then(projects => {
        const grid = document.getElementById('projectsGrid');
        grid.innerHTML = '';
        if (!projects || !Array.isArray(projects) || projects.length === 0) {
            if (loadingDiv) loadingDiv.hidden = true;
            grid.innerHTML = '<div style="color:#bbb;text-align:center;padding:2em 0">No projects found.</div>';
            return;
        }
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
                window.actions.editProject(proj.id);
            });
            box.querySelector('.delete-btn').addEventListener('click', e => {
                e.stopPropagation();
                window.actions.deleteProject(proj.id);
            });
            grid.appendChild(box);
        });
        if (loadingDiv) loadingDiv.hidden = true;
    }).catch(e => {
        if (loadingDiv) loadingDiv.hidden = true;
        document.getElementById('projectsGrid').innerHTML = '<div style="color:#ff5252">Failed to load projects</div>';
    });
}

export const __testonly__ = { addProject, loadProjects };
