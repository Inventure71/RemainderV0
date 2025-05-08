// Add API helpers for reminders
export async function getAllReminders() {
  const res = await fetch('/api/get_all_reminders');
  return res.json();
}

export async function updateReminder(id, data) {
  const res = await fetch(`/api/edit_message`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message_id: id, ...data })
  });
  return res.json();
}
