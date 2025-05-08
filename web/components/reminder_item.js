/**
 * Renders a single reminder item with controls.
 * @param {object} reminderData - The reminder message object from the DB.
 * @param {object} api - The pywebview API object.
 * @param {function} onUpdate - Callback function to refresh the list after an update.
 * @returns {HTMLElement} - The list item element.
 */

const importanceMap = {
    low: [1, 2, 3],
    medium: [4, 5, 6, 7],
    high: [8, 9, 10]
};

const dayMap = { 1: 'Mon', 2: 'Tue', 3: 'Wed', 4: 'Thu', 5: 'Fri', 6: 'Sat', 7: 'Sun' };

function getImportanceLevel(score) {
    const numericScore = parseInt(score);
    if (isNaN(numericScore)) return 'medium'; // Default
    for (const level in importanceMap) {
        if (importanceMap[level].includes(numericScore)) {
            return level;
        }
    }
    return 'medium'; // Default if out of range
}

function formatRecurrence(recurrenceJson) {
    if (!recurrenceJson) return null;
    try {
        const rules = JSON.parse(recurrenceJson);
        if (rules.type === 'daily') {
            return "Repeats Daily";
        } else if (rules.type === 'weekly' && rules.days?.length > 0) {
            const dayNames = rules.days.map(d => dayMap[d] || '?').join(', ');
            return `Repeats Weekly (${dayNames})`;
        }
    } catch {}
    return null;
}

export function renderReminderItem(reminderData, api, onUpdate) {
    const li = document.createElement('li');
    li.className = 'reminder-card';
    const importanceLevel = getImportanceLevel(reminderData.importance);
    li.dataset.importance = importanceLevel; // Add data attribute for styling
    if (reminderData.done) {
        li.classList.add('done');
    }

    li.innerHTML = `
        <style scoped>
            .reminder-card {
                background: #2c313a;
                border: 1px solid #444;
                border-left-width: 5px; /* Importance indicator */
                border-radius: 6px;
                margin-bottom: 12px;
                padding: 12px 15px;
                display: flex;
                flex-direction: column;
                gap: 8px;
                position: relative;
                transition: background 0.2s, border-color 0.2s, transform 0.1s;
                overflow: hidden; /* Contain edit form */
            }
            .reminder-card:hover {
                background: #333a45;
                border-color: #555;
                transform: translateY(-1px);
            }
            .reminder-card.done {
                background: #3a3f4b;
                opacity: 0.65;
                border-left-color: #666 !important;
            }
            .reminder-card.done .reminder-content,
            .reminder-card.done .reminder-details {
                text-decoration: line-through;
                color: #999;
            }
            /* Importance Colors */
            .reminder-card[data-importance="low"] { border-left-color: #3b82f6; } /* Blue */
            .reminder-card[data-importance="medium"] { border-left-color: #fbbf24; } /* Amber */
            .reminder-card[data-importance="high"] { border-left-color: #ef4444; } /* Red */

            .reminder-main-content { display: flex; flex-direction: column; gap: 8px; transition: opacity 0.3s; }
            .reminder-card.editing .reminder-main-content { opacity: 0; pointer-events: none; max-height: 0; } /* Hide when editing */

            .reminder-content { color: #eee; flex: 1; line-height: 1.4; }
            .reminder-details { font-size: 0.9em; color: #bbb; display: flex; flex-wrap: wrap; gap: 5px 15px; align-items: center; }
            .reminder-details span { display: inline-flex; align-items: center; gap: 4px; }
            .reminder-controls { display: flex; align-items: center; gap: 10px; margin-top: 5px; }
            .reminder-controls label { display: flex; align-items: center; cursor: pointer; color: #ccc; font-size: 0.9em; }
            .reminder-controls input[type="checkbox"] { margin-right: 5px; cursor: pointer; }
            .reminder-controls button {
                background: #444b58; border: none; color: #ccc; padding: 4px 10px;
                border-radius: 4px; cursor: pointer; font-size: 0.85em;
                transition: background 0.2s, color 0.2s;
            }
            .reminder-controls button:hover { background: #525a69; color: #fff; }

            /* Edit Form Styles */
            .reminder-edit-form {
                display: flex; /* Changed from none initially */
                flex-direction: column;
                gap: 10px;
                padding-top: 10px;
                margin-top: 8px;
                border-top: 1px solid #555;
                transition: max-height 0.4s ease-out, opacity 0.4s ease-out;
                max-height: 0; /* Initially hidden */
                opacity: 0;    /* Initially hidden */
                overflow: hidden;
            }
             .reminder-card.editing .reminder-edit-form {
                 max-height: 300px; /* Adjust as needed */
                 opacity: 1;
             }
            .edit-form-row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
            .edit-form-row label { color:#ccc; font-size: 0.9em; margin-bottom: 2px; min-width: 40px; }
            .edit-form-row input[type="date"], .edit-form-row input[type="time"], .edit-form-row select {
                background: #3a3f4b; color: #eee; border: 1px solid #555; padding: 5px 8px; border-radius: 4px; font-size: 0.9em;
            }
            .edit-form-row input[type="date"] { flex-grow: 1; }
            .edit-form-row select { min-width: 100px; }
            .weekly-days { display: none; gap: 8px; flex-wrap: wrap; margin-left: 50px; margin-top: 5px; }
            .weekly-days label { color:#bbb; font-size: 0.9em; display: inline-flex; align-items: center; gap: 3px; }
            .weekly-days input { margin-right: 3px; }
            .edit-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 8px; }
             .edit-actions button { font-size: 0.9em; padding: 5px 12px; }
             .edit-actions .save-reminder-btn { background: #2563eb; color: white; }
             .edit-actions .save-reminder-btn:hover { background: #1d4ed8; }
             .edit-actions .cancel-reminder-btn { background: #666; }
             .edit-actions .cancel-reminder-btn:hover { background: #777; }
        </style>

        <div class="reminder-main-content">
            <div class="reminder-content">${reminderData.content}</div>
            <div class="reminder-details">
                <!-- Time and Recurrence will be added here -->
            </div>
            <div class="reminder-controls">
                <!-- Controls (Done, Edit, Clear) will be added here -->
            </div>
        </div>
        <div class="reminder-edit-form">
             <!-- Edit Form HTML will be added here -->
        </div>
    `;

    // --- Populate Details --- 
    const detailsDiv = li.querySelector('.reminder-details');
    let currentRemindTime = null;
    let remindTimeValid = false;
    try {
        const parts = reminderData.remind?.match(/(\d{4})-(\d{2})-(\d{2})-(\d{2}):(\d{2})/);
        if (parts) {
            currentRemindTime = new Date(parts[1], parts[2] - 1, parts[3], parts[4], parts[5]);
            if (!isNaN(currentRemindTime)) remindTimeValid = true;
        }
    } catch {}

    if (remindTimeValid) {
        const timeSpan = document.createElement('span');
        timeSpan.innerHTML = `⏰ ${currentRemindTime.toLocaleString()}`;
        detailsDiv.appendChild(timeSpan);
    } else if (reminderData.remind) {
        const timeSpan = document.createElement('span');
        timeSpan.innerHTML = `⏰ <span style="color:#ff8888;">Invalid: ${reminderData.remind}</span>`;
        detailsDiv.appendChild(timeSpan);
    }

    const recurrenceText = formatRecurrence(reminderData.reoccurences);
    if (recurrenceText) {
        const recurrenceSpan = document.createElement('span');
        recurrenceSpan.innerHTML = `🔁 ${recurrenceText}`;
        recurrenceSpan.style.color = '#aae'; // Subtle color
        detailsDiv.appendChild(recurrenceSpan);
    }

    // --- Populate Controls --- 
    const controlsDiv = li.querySelector('.reminder-controls');

    // Done Checkbox
    const doneLabel = document.createElement('label');
    const doneCheckbox = document.createElement('input');
    doneCheckbox.type = 'checkbox';
    doneCheckbox.checked = reminderData.done;
    doneCheckbox.title = reminderData.done ? 'Mark as not done' : 'Mark as done';
    doneCheckbox.addEventListener('change', async () => {
        try {
            await api.toggle_reminder_done(reminderData.id, doneCheckbox.checked);
            onUpdate(); // Refresh the list
        } catch (error) {
            console.error("Failed to toggle reminder status:", error);
            alert(`Error updating reminder: ${error.message || error}`);
            // Revert checkbox state on error
            doneCheckbox.checked = !doneCheckbox.checked;
        }
    });
    doneLabel.appendChild(doneCheckbox);
    doneLabel.appendChild(document.createTextNode('Done'));
    controlsDiv.appendChild(doneLabel);

    // Edit Button
    const editBtn = document.createElement('button');
    editBtn.textContent = 'Edit';
    editBtn.title = 'Edit reminder time and recurrence';
    controlsDiv.appendChild(editBtn);

    // Clear Button
    const clearBtn = document.createElement('button');
    clearBtn.textContent = 'Clear';
    clearBtn.title = 'Clear reminder time and recurrence';
    clearBtn.onclick = async () => {
        if (confirm("Clear reminder time and recurrence?")) {
            try {
                await api.edit_message(reminderData.id, { remind: null, reoccurences: null });
                onUpdate();
            } catch (error) {
                console.error("Failed to clear reminder:", error);
                alert(`Error clearing reminder: ${error.message || error}`);
            }
        }
    };
    controlsDiv.appendChild(clearBtn);

    // --- Populate Edit Form HTML --- 
    const editFormDiv = li.querySelector('.reminder-edit-form');
    const formatDateForInput = (date) => date ? date.toISOString().split('T')[0] : '';
    const formatTimeForInput = (date) => date ? date.toTimeString().substring(0, 5) : '';

    editFormDiv.innerHTML = `
        <div class="edit-form-row">
            <label for="remindDate_${reminderData.id}">Date:</label>
            <input type="date" id="remindDate_${reminderData.id}" value="${formatDateForInput(currentRemindTime)}" />
            <label for="remindTime_${reminderData.id}">Time:</label>
            <input type="time" id="remindTime_${reminderData.id}" value="${formatTimeForInput(currentRemindTime)}" />
        </div>
        <div class="edit-form-row">
            <label for="recurrenceType_${reminderData.id}">Repeat:</label>
            <select id="recurrenceType_${reminderData.id}">
                <option value="none">None</option>
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
            </select>
        </div>
        <div class="weekly-days" id="weeklyDays_${reminderData.id}">
            ${Object.entries(dayMap).map(([value, day]) => `
                <label><input type="checkbox" name="weekday_${reminderData.id}" value="${value}" /> ${day}</label>
            `).join('')}
        </div>
        <div class="edit-actions">
            <button type="button" class="save-reminder-btn">Save</button>
            <button type="button" class="cancel-reminder-btn">Cancel</button>
        </div>
    `;

    // --- Edit Form Logic --- 
    const dateInput = editFormDiv.querySelector(`#remindDate_${reminderData.id}`);
    const timeInput = editFormDiv.querySelector(`#remindTime_${reminderData.id}`);
    const recurrenceSelect = editFormDiv.querySelector(`#recurrenceType_${reminderData.id}`);
    const weeklyDaysDiv = editFormDiv.querySelector(`#weeklyDays_${reminderData.id}`);
    const dayCheckboxes = editFormDiv.querySelectorAll(`input[name='weekday_${reminderData.id}']`);
    const saveBtn = editFormDiv.querySelector('.save-reminder-btn');
    const cancelBtn = editFormDiv.querySelector('.cancel-reminder-btn');

    // Function to set initial/current form state
    const populateEditForm = () => {
        dateInput.value = formatDateForInput(currentRemindTime);
        timeInput.value = formatTimeForInput(currentRemindTime);
        let currentRecurrence = null;
        try { currentRecurrence = reminderData.reoccurences ? JSON.parse(reminderData.reoccurences) : null; } catch {}
        
        if (currentRecurrence) {
            recurrenceSelect.value = currentRecurrence.type || 'none';
            if (currentRecurrence.type === 'weekly') {
                weeklyDaysDiv.style.display = 'flex';
                dayCheckboxes.forEach(cb => {
                    cb.checked = currentRecurrence.days?.includes(parseInt(cb.value));
                });
            } else {
                weeklyDaysDiv.style.display = 'none';
            }
        } else {
            recurrenceSelect.value = 'none';
            weeklyDaysDiv.style.display = 'none';
        }
        // Ensure initial visibility state is correct based on select value
        weeklyDaysDiv.style.display = (recurrenceSelect.value === 'weekly') ? 'flex' : 'none';
    };

    editBtn.onclick = () => {
        populateEditForm();
        li.classList.add('editing');
    };

    cancelBtn.onclick = () => {
        li.classList.remove('editing');
    };

    recurrenceSelect.onchange = () => {
        weeklyDaysDiv.style.display = (recurrenceSelect.value === 'weekly') ? 'flex' : 'none';
    };

    saveBtn.onclick = async () => {
        const dateVal = dateInput.value;
        const timeVal = timeInput.value;
        if (!dateVal || !timeVal) {
            alert("Please select both date and time.");
            return;
        }
        const remindStr = `${dateVal}-${timeVal.replace(':', ':')}`;
        let newRecurrence = null;
        const recurrenceType = recurrenceSelect.value;
        if (recurrenceType === 'daily') {
            newRecurrence = { type: 'daily' };
        } else if (recurrenceType === 'weekly') {
            const selectedDays = Array.from(dayCheckboxes)
                .filter(cb => cb.checked)
                .map(cb => parseInt(cb.value));
            if (selectedDays.length > 0) {
                newRecurrence = { type: 'weekly', days: selectedDays };
            } else {
                alert("Please select at least one day for weekly recurrence.");
                return;
            }
        }
        const recurrenceJson = newRecurrence ? JSON.stringify(newRecurrence) : null;
        try {
            // Use positional arguments: id, content, project, remind, importance, processed, done, reoccurences
            await api.edit_message(reminderData.id, undefined, undefined, remindStr, undefined, undefined, undefined, recurrenceJson);
            onUpdate(); // Refresh list (will close edit form automatically)
        } catch (error) {
            console.error("Failed to save reminder changes:", error);
            alert(`Error saving reminder: ${error.message || error}`);
        }
    };

    return li;
} 