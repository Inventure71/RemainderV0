import sqlite3
import datetime
import subprocess
import os
import sys
import json # Import json module
from dateutil.relativedelta import relativedelta # Need dateutil for easier date math

# Adjust path to import from DatabaseUtils
# Ensure the project root is in the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from DatabaseUtils.database_messages import MessageDatabaseHandler

def get_next_reminder_time(current_remind_time, recurrence_rules):
    """Calculates the next reminder time based on recurrence rules."""
    if not recurrence_rules:
        return None

    try:
        rules = json.loads(recurrence_rules)
        rule_type = rules.get('type')

        if rule_type == 'daily':
            return current_remind_time + relativedelta(days=1)
        elif rule_type == 'weekly':
            days_of_week = rules.get('days') # Expecting list like [1, 3, 5] (Mon=1, Sun=7)
            if not days_of_week:
                return None

            # Sort days and find the next applicable day
            days_of_week.sort()
            current_weekday = current_remind_time.isoweekday() # Monday is 1, Sunday is 7

            # Find the next day in the list *after* the current day
            next_day_offset = -1
            for day in days_of_week:
                if day > current_weekday:
                    next_day_offset = day - current_weekday
                    break
            
            # If no day found later in *this* week, find the first day in the *next* week
            if next_day_offset == -1:
                first_day_next_week = days_of_week[0]
                days_until_next_occurrence = (7 - current_weekday) + first_day_next_week
                return current_remind_time + relativedelta(days=days_until_next_occurrence)
            else:
                return current_remind_time + relativedelta(days=next_day_offset)

        else:
            print(f"Unsupported recurrence type: {rule_type}")
            return None

    except json.JSONDecodeError:
        print(f"Error parsing recurrence JSON: {recurrence_rules}")
        return None
    except Exception as e:
        print(f"Error calculating next reminder time: {e}")
        return None

def check_reminders():
    """Checks for due reminders and sends notifications. Handles recurrence."""
    print("Checking for reminders...") # Add logging later
    db_handler = MessageDatabaseHandler()
    try:
        # Fetch reminders including reoccurences field
        db_handler.cursor.execute("SELECT id, content, remind, reoccurences FROM messages WHERE remind IS NOT NULL AND remind != '' AND done = 0")
        reminders = db_handler.cursor.fetchall()
        now = datetime.datetime.now()

        for reminder_id, content, remind_str, reoccurences_str in reminders:
            reminder_time = None
            try:
                # Attempt to parse the reminder time using the specific format
                try:
                    reminder_time = datetime.datetime.strptime(remind_str, "%Y-%m-%d-%H:%M")
                except ValueError:
                    try:
                        reminder_time = datetime.datetime.fromisoformat(remind_str)
                        print(f"Warning: Parsed reminder ID {reminder_id} using ISO format. Expected YYYY-MM-DD-HH:MM.")
                    except ValueError:
                         print(f"Warning: Could not parse reminder time '{remind_str}' for message ID {reminder_id}. Skipping.")
                         continue

                if reminder_time <= now:
                    print(f"Reminder due: ID={reminder_id}, Content='{content[:50]}...'")
                    send_macos_notification(f"Reminder: {content}", f"ID: {reminder_id}")

                    # Handle recurrence or marking as done
                    next_time = get_next_reminder_time(reminder_time, reoccurences_str)

                    if next_time:
                        # Format next time back to string
                        next_remind_str = next_time.strftime("%Y-%m-%d-%H:%M")
                        print(f"Rescheduling reminder ID {reminder_id} to {next_remind_str}")
                        db_handler.update_message(reminder_id, remind=next_remind_str, done=0) # Keep done=0 for recurring
                    else:
                        # No recurrence, mark as done
                        print(f"Marking non-recurring reminder ID {reminder_id} as done.")
                        db_handler.update_message(reminder_id, done=1)

            except Exception as e:
                print(f"Error processing reminder ID {reminder_id}: {e}")

    except sqlite3.Error as e:
        print(f"Database error while checking reminders: {e}")
    finally:
        db_handler.close()

def send_macos_notification(title, message):
    """Sends a notification on macOS using osascript."""
    try:
        script = f'''display notification "{message}" with title "{title}"'''
        subprocess.run(["osascript", "-e", script], check=True)
        print(f"Sent notification: Title='{title}'")
    except FileNotFoundError:
        print("Error: 'osascript' command not found. Is this macOS?")
    except subprocess.CalledProcessError as e:
        print(f"Error sending notification: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while sending notification: {e}")

if __name__ == "__main__":
    # Ensure python-dateutil is installed: pip install python-dateutil
    check_reminders() 