/**
 * Renders a single reminder item with controls.
 * @param {object} reminderData - The reminder message object from the DB.
 * @param {object} api - The pywebview API object.
 * @param {function} onUpdate - Callback function to refresh the list after an update.
 * @returns {HTMLElement} - The list item element.
 */
export function renderReminderItem(reminderData, api, onUpdate) {
    const li = document.createElement('li');
    li.style.border = '1px solid #444';
    li.style.borderRadius = '6px';
    li.style.marginBottom = '10px';
    li.style.padding = '10px 12px';
    li.style.background = reminderData.done ? '#3a3f4b' : '#2c313a'; // Dim if done
    li.style.opacity = reminderData.done ? 0.7 : 1;
    li.style.display = 'flex';
    li.style.flexDirection = 'column';
    li.style.gap = '8px';
    li.style.position = 'relative'; // Needed for positioning edit form later if desired

    const mainContentDiv = document.createElement('div'); // Wrap non-edit content
    mainContentDiv.style.display = 'flex';
    mainContentDiv.style.flexDirection = 'column';
    mainContentDiv.style.gap = '8px';

    const contentDiv = document.createElement('div');
    contentDiv.textContent = reminderData.content;
    contentDiv.style.color = '#eee';
    contentDiv.style.flex = '1';

    const detailsDiv = document.createElement('div');
    detailsDiv.style.fontSize = '0.9em';
    detailsDiv.style.color = '#bbb';
    const timeSpan = document.createElement('span');
    let currentRemindTime = null; // Store parsed date object
    let currentRecurrence = null;
    try {
        const parts = reminderData.remind?.match(/(\d{4})-(\d{2})-(\d{2})-(\d{2}):(\d{2})/);
        if (parts) {
            currentRemindTime = new Date(parts[1], parts[2] - 1, parts[3], parts[4], parts[5]);
            timeSpan.textContent = `⏰ ${currentRemindTime.toLocaleString()}`;
        } else {
            const remindDate = new Date(reminderData.remind); // Fallback
            if (!isNaN(remindDate)) {
                currentRemindTime = remindDate;
                timeSpan.textContent = `⏰ ${currentRemindTime.toLocaleString()} (Parsed as fallback)`;
                timeSpan.style.fontStyle = 'italic';
            } else {
                timeSpan.textContent = reminderData.remind ? `⏰ Invalid Date: ${reminderData.remind}` : '⏰ No reminder set';
            }
        }
        if (reminderData.reoccurences) {
            try {
                currentRecurrence = JSON.parse(reminderData.reoccurences);
                if (currentRecurrence?.type === 'daily') {
                    timeSpan.textContent += ' (Daily)';
                } else if (currentRecurrence?.type === 'weekly') {
                    timeSpan.textContent += ` (Weekly: ${currentRecurrence.days?.join(',') || 'N/A'})`;
                }
            } catch { /* ignore parsing error */ }
        }

    } catch (e) {
        timeSpan.textContent = `⏰ Error parsing date: ${reminderData.remind}`;
        timeSpan.style.color = '#ff8888';
    }
    detailsDiv.appendChild(timeSpan);

    const controlsDiv = document.createElement('div');
    controlsDiv.style.display = 'flex';
    controlsDiv.style.alignItems = 'center';
    controlsDiv.style.gap = '10px';

    // --- Done Checkbox ---
    const doneLabel = document.createElement('label');
    doneLabel.style.display = 'flex';
    doneLabel.style.alignItems = 'center';
    doneLabel.style.cursor = 'pointer';
    doneLabel.style.color = '#ccc';

    const doneCheckbox = document.createElement('input');
    doneCheckbox.type = 'checkbox';
    doneCheckbox.checked = reminderData.done;
    doneCheckbox.style.marginRight = '5px';
    doneCheckbox.addEventListener('change', async () => {
        try {
            // Call new API endpoint (to be created)
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

    // --- Edit Time Button (now toggles edit form) ---
    const editTimeBtn = document.createElement('button');
    editTimeBtn.textContent = 'Edit'; // Shorter name
    editTimeBtn.style.padding = '3px 8px';
    editTimeBtn.style.fontSize = '0.85em';
    editTimeBtn.style.cursor = 'pointer';

    // --- Clear Reminder Button (remains mostly the same) ---
    const clearReminderBtn = document.createElement('button');
    clearReminderBtn.textContent = 'Clear Reminder';
    clearReminderBtn.onclick = async () => {
        if (confirm("Are you sure you want to remove the reminder time and recurrence for this message?")) {
            try {
                await api.edit_message(reminderData.id, { remind: null, reoccurences: null }); // Clear both
                onUpdate();
            } catch (error) {
                console.error("Failed to clear reminder:", error);
                alert(`Error clearing reminder: ${error.message || error}`);
            }
        }
    };

    controlsDiv.appendChild(doneLabel);
    controlsDiv.appendChild(editTimeBtn);
    controlsDiv.appendChild(clearReminderBtn);

    mainContentDiv.appendChild(contentDiv);
    mainContentDiv.appendChild(detailsDiv);
    mainContentDiv.appendChild(controlsDiv);
    li.appendChild(mainContentDiv);

    // --- Edit Form (Initially Hidden) ---
    const editFormDiv = document.createElement('div');
    editFormDiv.style.display = 'none'; // Initially hidden
    editFormDiv.style.marginTop = '10px';
    editFormDiv.style.paddingTop = '10px';
    editFormDiv.style.borderTop = '1px solid #555';
    editFormDiv.style.flexDirection = 'column';
    editFormDiv.style.gap = '8px';

    // Helper to format date/time for input fields
    const formatDateForInput = (date) => date ? date.toISOString().split('T')[0] : '';
    const formatTimeForInput = (date) => date ? date.toTimeString().substring(0, 5) : '';

    editFormDiv.innerHTML = `
        <div style="display: flex; gap: 8px; align-items: center;">
            <label style="color:#ccc;" for="remindDate_${reminderData.id}">Date:</label>
            <input type="date" id="remindDate_${reminderData.id}" style="flex-grow: 1;" />
            <label style="color:#ccc;" for="remindTime_${reminderData.id}">Time:</label>
            <input type="time" id="remindTime_${reminderData.id}" />
        </div>
        <div style="display: flex; gap: 8px; align-items: center;">
            <label style="color:#ccc;" for="recurrenceType_${reminderData.id}">Repeat:</label>
            <select id="recurrenceType_${reminderData.id}">
                <option value="none">None</option>
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
            </select>
        </div>
        <div id="weeklyDays_${reminderData.id}" style="display: none; gap: 5px; flex-wrap: wrap; margin-left: 50px;">
            ${['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((day, index) => `
                <label style="color:#bbb; font-size: 0.9em;">
                    <input type="checkbox" name="weekday_${reminderData.id}" value="${index + 1}" /> ${day}
                </label>
            `).join('')}
        </div>
        <div style="display: flex; gap: 8px; justify-content: flex-end; margin-top: 5px;">
            <button type="button" class="save-reminder-btn">Save</button>
            <button type="button" class="cancel-reminder-btn">Cancel</button>
        </div>
    `;
    li.appendChild(editFormDiv);

    // Get form elements
    const dateInput = editFormDiv.querySelector(`#remindDate_${reminderData.id}`);
    const timeInput = editFormDiv.querySelector(`#remindTime_${reminderData.id}`);
    const recurrenceSelect = editFormDiv.querySelector(`#recurrenceType_${reminderData.id}`);
    const weeklyDaysDiv = editFormDiv.querySelector(`#weeklyDays_${reminderData.id}`);
    const dayCheckboxes = editFormDiv.querySelectorAll(`input[name='weekday_${reminderData.id}']`);
    const saveBtn = editFormDiv.querySelector('.save-reminder-btn');
    const cancelBtn = editFormDiv.querySelector('.cancel-reminder-btn');

    // Toggle Edit Form Visibility
    editTimeBtn.onclick = () => {
        // Populate form before showing
        dateInput.value = formatDateForInput(currentRemindTime);
        timeInput.value = formatTimeForInput(currentRemindTime);
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
        editFormDiv.style.display = 'flex';
        mainContentDiv.style.display = 'none'; // Hide main content when editing
    };

    // Cancel Button Logic
    cancelBtn.onclick = () => {
        editFormDiv.style.display = 'none';
        mainContentDiv.style.display = 'flex'; // Show main content again
    };

    // Show/Hide Weekly Days Checkboxes
    recurrenceSelect.onchange = () => {
        weeklyDaysDiv.style.display = (recurrenceSelect.value === 'weekly') ? 'flex' : 'none';
    };

    // Save Button Logic
    saveBtn.onclick = async () => {
        const dateVal = dateInput.value;
        const timeVal = timeInput.value;

        if (!dateVal || !timeVal) {
            alert("Please select both date and time.");
            return;
        }

        // Format date and time to YYYY-MM-DD-HH:MM
        const remindStr = `${dateVal}-${timeVal.replace(':', ':')}`.replace('T', '-'); // Should match YYYY-MM-DD-HH:MM

        // Construct recurrence object
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
            // Call API with remind and reoccurences
            await api.edit_message(reminderData.id, { remind: remindStr, reoccurences: recurrenceJson });
            onUpdate(); // Refresh list
        } catch (error) {
            console.error("Failed to save reminder changes:", error);
            alert(`Error saving reminder: ${error.message || error}`);
        }
    };

    return li;
} 