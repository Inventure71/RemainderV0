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
    def __init__(self):
        # Message cache: {context_key: {'messages': [...], 'cache_key': ...}}
        self._message_cache = {}
        # Chat history cache: {context_key: [history]}
        self._chat_history_cache = {}

    def _get_context_key(self, project):
        return project if project else '__main__'

    def _get_messages_with_cache(self, project=None):
        context_key = self._get_context_key(project)
        db = db_messages.MessageDatabaseHandler()
        try:
            # Get last message timestamp for cache invalidation
            if project:
                messages = db.get_project_messages(project_name=project)
            else:
                messages = db.get_project_messages()
            if messages:
                last_msg_time = max(m.get('timestamp', '') for m in messages)
            else:
                last_msg_time = ''
            # Check cache
            cache = self._message_cache.get(context_key)
            if cache and cache['cache_key'] == last_msg_time:
                return cache['messages']
            # Update cache
            self._message_cache[context_key] = {
                'messages': messages,
                'cache_key': last_msg_time
            }
            return messages
        finally:
            db.close()

    def _invalidate_message_cache(self, project=None):
        context_key = self._get_context_key(project)
        if context_key in self._message_cache:
            del self._message_cache[context_key]

    def _get_chat_history(self, project=None):
        context_key = self._get_context_key(project)
        return self._chat_history_cache.get(context_key, [])

    def _set_chat_history(self, history, project=None):
        context_key = self._get_context_key(project)
        self._chat_history_cache[context_key] = history

    def reset_model_chat_history(self, project=None):
        context_key = self._get_context_key(project)
        self._chat_history_cache[context_key] = []
        return {'success': True}

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
        self._invalidate_message_cache(project)
        return {'success': True}

    def edit_message(self, message_id, content=None, project=None, remind=None, importance=None, processed=None):
        db = db_messages.MessageDatabaseHandler()
        db.update_message(message_id, content=content, project=project, remind=remind, importance=importance, processed=processed)
        db.close()
        self._invalidate_message_cache(project)
        return {'success': True}

    def delete_message(self, message_id):
        db = db_messages.MessageDatabaseHandler()
        db.delete_message(message_id)
        db.close()
        # Could not determine project, so clear all caches
        self._message_cache = {}
        return {'success': True}

    def model_chat(self, prompt, project=None, use_history=False, history=None):
        try:
            print(f"[model_chat] Received prompt: {prompt}")
            # Optimized message loading
            context_messages = self._get_messages_with_cache(project)
            # Defensive: filter strictly by project if specified
            if project:
                filtered_messages = [msg for msg in context_messages if (msg.get('project') or '') == project]
            else:
                # Main chat: include ALL messages (regardless of project)
                filtered_messages = context_messages

            print(f"[model_chat] Context: {'project=' + project if project else 'main chat'} | Messages fed to model: {len(filtered_messages)}")
            for msg in filtered_messages:
                print(f"  - ID: {msg['id']} | Project: {msg.get('project')} | Content: {msg['content'][:60]}")

            messages = "\n".join([f"ID: {msg['id']}, Content: {msg['content']}, Project: {msg['project']}" for msg in filtered_messages])

            # History: use in-memory chat history unless a new one is provided
            if use_history and history is not None:
                gemini_history = [h for h in history if isinstance(h, dict) and 'role' in h and 'content' in h]
            else:
                gemini_history = self._get_chat_history(project)

            # Generate response
            result, all_history = model_handler.generate(prompt, messages, json=0, history=gemini_history)
            self._set_chat_history(all_history, project)
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

    def model_select_messages(self, prompt, messages, history=None, project=None):
        try:
            # If messages is provided directly, use it
            # Otherwise, get all messages from the current context (project or main chat)
            context_messages = messages
            if not messages or messages == "":
                db = db_messages.MessageDatabaseHandler()
                try:
                    if project:
                        db_messages_list = db.get_project_messages(project_name=project)
                    else:
                        db_messages_list = db.get_project_messages()
                    
                    # Format messages for the model
                    context_messages = "\n".join([f"ID: {msg['id']}, Content: {msg['content']}, Project: {msg['project']}" 
                                         for msg in db_messages_list])
                except Exception as e:
                    print(f"Error getting context messages: {e}")
                finally:
                    db.close()
            
            # Process history (only actual user prompts and model responses)
            gemini_history = None
            if history and isinstance(history, list):
                gemini_history = []
                for h in history:
                    if isinstance(h, dict) and 'role' in h and 'content' in h:
                        # Only include the actual chat history, not the context messages
                        gemini_history.append(h)
            
            # Generate response
            result, all_history = model_handler.generate(prompt, context_messages, json=1, history=gemini_history)
            return {'result': result, 'history': all_history}
        except Exception as e:
            import traceback
            print('model_select_messages error:', e)
            print(traceback.format_exc())
            return {'result': None, 'history': [], 'error': str(e), 'traceback': traceback.format_exc()}

    def model_assign_projects(self, prompt, messages, projects, history=None):
        try:
            print("model assign projects requested")
            print("project:", projects)
            
            # If messages is provided directly, use it
            # Otherwise, get all messages from the current context
            context_messages = messages
            if not messages or messages == "":
                db = db_messages.MessageDatabaseHandler()
                try:
                    context_messages_list = db.get_project_messages(None)
                    # Format messages for the model
                    context_messages = "\n".join([f"ID: {msg['id']}, Content: {msg['content']}, Project: {msg['project']}" 
                                         for msg in context_messages_list])
                except Exception as e:
                    print(f"Error getting context messages: {e}")
                finally:
                    db.close()
            
            # Process history (only actual user prompts and model responses)
            gemini_history = None
            if history and isinstance(history, list):
                gemini_history = []
                for h in history:
                    if isinstance(h, dict) and 'role' in h and 'content' in h:
                        # Only include the actual chat history, not the context messages
                        gemini_history.append(h)
            
            # Generate response
            result, all_history = model_handler.generate(prompt, context_messages, json=2, history=gemini_history)
            return {'result': result, 'history': all_history}
        except Exception as e:
            import traceback
            print('model_assign_projects error:', e)
            print(traceback.format_exc())
            return {'result': None, 'history': [], 'error': str(e), 'traceback': traceback.format_exc()}

    def model_create_projects(self, prompt, messages, history=None):
        try:
            print("model create projects requested")
            print("messages:", messages)
            
            # If messages is provided directly, use it
            # Otherwise, get all messages from the current context
            context_messages = messages
            if not messages or messages == "":
                db = db_messages.MessageDatabaseHandler()
                try:
                    context_messages_list = db.get_project_messages(None)
                    # Format messages for the model
                    context_messages = "\n".join([f"ID: {msg['id']}, Content: {msg['content']}, Project: {msg['project']}" 
                                         for msg in context_messages_list])
                except Exception as e:
                    print(f"Error getting context messages: {e}")
                finally:
                    db.close()
            
            # Process history (only actual user prompts and model responses)
            gemini_history = None
            if history and isinstance(history, list):
                gemini_history = []
                for h in history:
                    if isinstance(h, dict) and 'role' in h and 'content' in h:
                        # Only include the actual chat history, not the context messages
                        gemini_history.append(h)
            
            # Generate response
            result, all_history = model_handler.generate(prompt, context_messages, json=3, history=gemini_history)
            return {'result': result, 'history': all_history}
        except Exception as e:
            import traceback
            print('model_create_projects error:', e)
            print(traceback.format_exc())
            return {'result': None, 'history': [], 'error': str(e), 'traceback': traceback.format_exc()}

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

if __name__ == '__main__':
    if webview:
        api = Api()
        window = webview.create_window('Remainder', 'web/index.html', js_api=api, width=1200, height=800)
        webview.start(debug=True)
    else:
        print('pywebview is not installed. Run `pip install pywebview` to use the web UI.')
