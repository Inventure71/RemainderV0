# --- REMOVE ALL TKINTER UI CODE ---
# The UI is now handled by the web frontend (HTML/JS/pywebview). This file now only exposes backend logic and APIs for the web UI.

import sys
import os
import json
import threading
import DatabaseUtils.database_messages as db_messages
import DatabaseUtils.database_projects as db_projects
from Utils.model_handler import ModelClient
from Utils import telegram_utils

# --- Pywebview API glue ---
try:
    import webview
except ImportError:
    webview = None

# --- Model and DB logic ---
model_handler = ModelClient(mode="gemini", model_context_window=500000)

class Api:
    def refresh_telegram_messages(self):
        try:
            telegram_utils.retrive_messages(save_to_file=False)
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_all_projects(self):
        db = db_projects.ProjectsDatabaseHandler()
        projects = db.get_all_projects()
        db.close()
        return projects

    def get_all_messages(self, project=None):
        db = db_messages.MessageDatabaseHandler()
        try:
            if project:
                messages = db.get_project_messages(project_name=project)
            else:
                messages = db.get_project_messages()
        except Exception as e:
            import traceback
            print("[Error] get_all_messages failed:", e)
            print(traceback.format_exc())
            messages = []
        finally:
            db.close()
        return messages

    def get_all_reminders(self):
        db = db_messages.MessageDatabaseHandler()
        try:
            messages = db.get_project_messages()
            reminders = [m for m in messages if m.get('remind')]
        except Exception as e:
            import traceback
            print("[Error] get_all_reminders failed:", e)
            print(traceback.format_exc())
            reminders = []
        finally:
            db.close()
        return reminders

    def add_project(self, name, description, color="#dddddd"):
        from datetime import datetime
        db = db_projects.ProjectsDatabaseHandler()
        db.add_project(name, datetime.now().isoformat(), description, extra="", user_created=1, color=color)
        db.close()
        return {'success': True}

    def edit_project(self, project_id, name=None, description=None, color=None):
        db = db_projects.ProjectsDatabaseHandler()
        db.update_project(project_id, new_name=name, new_description=description, color=color)
        db.close()
        return {'success': True}

    def delete_project(self, project_id):
        db = db_projects.ProjectsDatabaseHandler()
        db.delete_project(project_id)
        db.close()
        return {'success': True}

    def add_message(self, content, project=None, files=None, extra=None, remind=None, importance=None, reoccurences=None):
        from datetime import datetime
        db = db_messages.MessageDatabaseHandler()
        msg = {
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'project': project,
            'files': files,
            'extra': extra,
            'processed': 0,
            'remind': remind,
            'importance': importance,
            'reoccurences': reoccurences
        }
        db.add_message(msg)
        db.close()
        return {'success': True}

    def edit_message(self, message_id, content=None, project=None, remind=None, importance=None, processed=None):
        db = db_messages.MessageDatabaseHandler()
        db.update_message(message_id, content=content, project=project, remind=remind, importance=importance, processed=processed)
        db.close()
        return {'success': True}

    def delete_message(self, message_id):
        db = db_messages.MessageDatabaseHandler()
        db.delete_message(message_id)
        db.close()
        return {'success': True}

    def mark_message_processed(self, message_id, processed=True):
        db = db_messages.MessageDatabaseHandler()
        db.update_message(message_id, processed=processed)
        db.close()
        return {'success': True}

    def model_chat(self, prompt, project=None, use_history=False, history=None):
        # Use the same logic as generate(..., json=0)
        try:
            # project and history are optional, but messages param must be a string
            messages = ""
            if history and isinstance(history, list):
                # If history is a list of dicts with 'content', join them
                messages = "\n".join([h.get('content', '') for h in history if isinstance(h, dict) and 'content' in h])
            result, all_history = model_handler.generate(prompt, messages, json=0)
            return {'response': result, 'history': all_history}
        except Exception as e:
            import traceback
            print('model_chat error:', e)
            print(traceback.format_exc())
            return {'response': None, 'history': [], 'error': str(e), 'traceback': traceback.format_exc()}

    def run_telegram_fetch(self):
        """Fetch new Telegram messages and store them in DB and JSON."""
        from Utils import telegram_utils
        telegram_utils.retrive_messages()
        return {'status': 'ok'}

    def run_whatsapp_scrape(self):
        """Launch WhatsApp scraping utility (headless browser)."""
        import subprocess
        try:
            subprocess.Popen(['python', 'Utils/whatsapp_utils.py'])
            return {'status': 'started'}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    def model_select_messages(self, prompt, messages):
        try:
            result, history = model_handler.generate(prompt, messages, json=1)
            return {'result': result, 'history': history}
        except Exception as e:
            import traceback
            print('model_select_messages error:', e)
            print(traceback.format_exc())
            return {'result': None, 'history': [], 'error': str(e), 'traceback': traceback.format_exc()}

    def model_assign_projects(self, prompt, messages, projects):
        try:
            result, history = model_handler.generate(prompt, messages, json=2)
            return {'result': result, 'history': history}
        except Exception as e:
            import traceback
            print('model_assign_projects error:', e)
            print(traceback.format_exc())
            return {'result': None, 'history': [], 'error': str(e), 'traceback': traceback.format_exc()}

    def model_create_projects(self, prompt, messages):
        try:
            result, history = model_handler.generate(prompt, messages, json=3)
            return {'result': result, 'history': history}
        except Exception as e:
            import traceback
            print('model_create_projects error:', e)
            print(traceback.format_exc())
            return {'result': None, 'history': [], 'error': str(e), 'traceback': traceback.format_exc()}

if __name__ == '__main__':
    if webview:
        api = Api()
        window = webview.create_window('Remainder', 'web/index.html', js_api=api, width=1200, height=800)
        webview.start(debug=True)
    else:
        print('pywebview is not installed. Run `pip install pywebview` to use the web UI.')
