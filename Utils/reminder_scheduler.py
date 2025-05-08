import threading
import time
import datetime
import os
import sys
import json
from dateutil.relativedelta import relativedelta

# Ensure the project root is in the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from DatabaseUtils.database_messages import MessageDatabaseHandler

def send_macos_notification(title, message):
    try:
        import subprocess
        script = f'''display notification "{message}" with title "{title}"'''
        subprocess.run(["osascript", "-e", script], check=True)
    except Exception as e:
        print(f"[ReminderScheduler] Notification error: {e}")


def get_next_reminder_time(current_remind_time, recurrence_rules):
    if not recurrence_rules:
        return None
    try:
        rules = json.loads(recurrence_rules)
        rule_type = rules.get('type')
        if rule_type == 'daily':
            return current_remind_time + relativedelta(days=1)
        elif rule_type == 'weekly':
            days_of_week = rules.get('days')
            if not days_of_week:
                return None
            days_of_week.sort()
            current_weekday = current_remind_time.isoweekday()
            next_day_offset = -1
            for day in days_of_week:
                if day > current_weekday:
                    next_day_offset = day - current_weekday
                    break
            if next_day_offset == -1:
                first_day_next_week = days_of_week[0]
                days_until_next = (7 - current_weekday) + first_day_next_week
                return current_remind_time + relativedelta(days=days_until_next)
            else:
                return current_remind_time + relativedelta(days=next_day_offset)
        else:
            return None
    except Exception as e:
        print(f"[ReminderScheduler] Error parsing recurrence: {e}")
        return None

class ReminderScheduler:
    def __init__(self):
        self.timers = {}  # {reminder_id: threading.Timer}
        self.lock = threading.Lock()
        self.running = False

    def start(self):
        self.running = True
        self.refresh_reminders()

    def stop(self):
        self.running = False
        self.cancel_all()

    def cancel_all(self):
        with self.lock:
            for t in self.timers.values():
                t.cancel()
            self.timers.clear()

    def refresh_reminders(self):
        """Cancel all timers and reschedule from DB."""
        self.cancel_all()
        db = MessageDatabaseHandler()
        try:
            reminders = db.get_reminder_messages()
            now = datetime.datetime.now()
            for r in reminders:
                if not r['remind'] or r['done']:
                    continue
                try:
                    parts = r['remind'].split('-')
                    if len(parts) == 5:
                        remind_time = datetime.datetime(int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4]))
                    else:
                        remind_time = datetime.datetime.fromisoformat(r['remind'])
                except Exception as e:
                    print(f"[ReminderScheduler] Could not parse reminder time: {r['remind']} (ID {r['id']}) - {e}")
                    continue
                delay = (remind_time - now).total_seconds()
                if delay < 0:
                    delay = 0.5  # Fire immediately if overdue
                timer = threading.Timer(delay, self._handle_reminder, args=(r['id'],))
                timer.daemon = True
                with self.lock:
                    self.timers[r['id']] = timer
                timer.start()
        finally:
            db.close()

    def _handle_reminder(self, reminder_id):
        db = MessageDatabaseHandler()
        try:
            r = next((x for x in db.get_reminder_messages() if x['id'] == reminder_id), None)
            if not r:
                return
            content = r['content']
            send_macos_notification("Reminder", content)
            # Handle recurrence
            remind_time = None
            try:
                parts = r['remind'].split('-')
                if len(parts) == 5:
                    remind_time = datetime.datetime(int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4]))
                else:
                    remind_time = datetime.datetime.fromisoformat(r['remind'])
            except Exception as e:
                print(f"[ReminderScheduler] Could not parse reminder time for recurrence: {e}")
            next_time = get_next_reminder_time(remind_time, r['reoccurences']) if remind_time else None
            if next_time:
                next_remind_str = next_time.strftime("%Y-%m-%d-%H:%M")
                db.update_message(reminder_id, remind=next_remind_str, done=0)
                # Reschedule
                self.refresh_reminders()
            else:
                db.update_message(reminder_id, done=1)
                self.refresh_reminders()
        finally:
            db.close()
        # Remove timer from dict
        with self.lock:
            if reminder_id in self.timers:
                del self.timers[reminder_id] 