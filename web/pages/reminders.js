// Reminders page will use pywebview API directly
export default async function remindersPage(app, api) {
  app.innerHTML = `<h2>Reminders</h2><table class="reminders-table"><thead><tr><th>Project</th><th>Remind At</th><th>Recurrence</th><th>Actions</th></tr></thead><tbody></tbody></table>`;
  const tbody = app.querySelector('tbody');

  // Try to get the latest API reference in case it became available
  const currentApi = api || window.pywebview?.api;

  if (!currentApi || typeof currentApi.get_all_reminders !== 'function') {
    console.debug('API not available for reminders', currentApi);
    app.innerHTML = '<div style="color:#ff5252">API not available. Retrying in 1s...</div>';
    setTimeout(() => remindersPage(app, currentApi), 1000);
    return;
  }

  let reminders = [], projects = [];
  try {
    reminders = await currentApi.get_all_reminders();
    projects = await currentApi.get_all_projects();
  } catch (e) {
    console.error('Error fetching reminders or projects', e);
    app.innerHTML = `<div style="color:#ff5252">Error loading reminders: ${e.message}. Retrying in 1s...</div>`;
    setTimeout(() => remindersPage(app, currentApi), 1000);
    return;
  }

  if (!Array.isArray(reminders) || reminders.length === 0) {
    console.debug('No reminders returned', reminders);
    app.innerHTML = '<div style="color:#bbb;text-align:center;padding:2em 0">No reminders found. Refreshing in 5s...</div>';
    setTimeout(() => remindersPage(app, api), 5000);
    return;
  }

  async function handleUpdate(id, data) {
    try {
      await currentApi.edit_message(id, null, data.project, data.remind, null, null);
      return remindersPage(app, currentApi);
    } catch (e) {
      console.error('Error updating reminder', e);
      alert('Failed to update reminder');
    }
  }

  function createReminderRow(reminder, projects, onUpdate) {
    const tr = document.createElement('tr');
    // Project selector
    const projectTd = document.createElement('td');
    const projectSelect = document.createElement('select');
    projects.forEach(prj => {
      const opt = document.createElement('option');
      opt.value = prj.name;
      opt.textContent = prj.name;
      if (reminder.project === prj.name) opt.selected = true;
      projectSelect.appendChild(opt);
    });
    projectTd.appendChild(projectSelect);
    // Remind time
    const remindTd = document.createElement('td');
    const remindInput = document.createElement('input');
    remindInput.type = 'datetime-local';
    remindInput.value = reminder.remind ? new Date(reminder.remind).toISOString().slice(0, 16) : '';
    remindTd.appendChild(remindInput);
    // Recurrence
    const recurTd = document.createElement('td');
    const recurInput = document.createElement('input');
    recurInput.type = 'text';
    recurInput.placeholder = 'e.g. Mon,Wed,Fri';
    recurInput.value = reminder.reoccurences || '';
    recurTd.appendChild(recurInput);
    // Actions
    const actionsTd = document.createElement('td');
    const saveBtn = document.createElement('button');
    saveBtn.textContent = 'Save';
    saveBtn.onclick = async () => {
      await onUpdate(reminder.id, {
        project: projectSelect.value,
        remind: remindInput.value ? new Date(remindInput.value).toISOString() : null,
        reoccurences: recurInput.value
      });
    };
    actionsTd.appendChild(saveBtn);
    tr.appendChild(projectTd);
    tr.appendChild(remindTd);
    tr.appendChild(recurTd);
    tr.appendChild(actionsTd);
    return tr;
  }

  reminders.forEach(reminder => {
    tbody.appendChild(createReminderRow(reminder, projects, handleUpdate));
  });
}
