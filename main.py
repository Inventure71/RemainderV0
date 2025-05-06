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
from Utils.reminder_scheduler import ReminderScheduler
from datetime import datetime
from werkzeug.utils import secure_filename
import base64
import uuid
import re

# --- Pywebview API glue ---
try:
    import webview
except ImportError:
    webview = None

# --- Model and DB logic ---
model_handler = ModelClient(mode="gemini", model_context_window=500000)
reminder_scheduler = ReminderScheduler()

class Api:
    def __init__(self):
        # Message cache: {context_key: {'messages': [...], 'cache_key': ...}}
        self._message_cache = {}
        # Chat history cache: {context_key: [history]}
        self._chat_history_cache = {}
        # Toggle state for checking projects
        self._check_projects = False
        # Start the reminder scheduler
        reminder_scheduler.start()

        # Ensure upload directory exists INSIDE web directory
        self.image_upload_folder_name = os.path.join("uploads", "message_images") # Relative to web root
        self.image_actual_save_path_base = os.path.join("web", self.image_upload_folder_name)
        if not os.path.exists(self.image_actual_save_path_base):
            os.makedirs(self.image_actual_save_path_base, exist_ok=True)

    def getFileDialog(self, options=None):
        """
        Open a native file dialog to select one or multiple files.
        
        Args:
            options (dict): Options for the file dialog, including:
                - allow_multiple (bool): Whether to allow multiple file selection
                - file_types (list): List of file type filters
                - directory (str): Initial directory
        
        Returns:
            list or str: List of selected file paths or a single path if multiple selection is disabled
        """
        try:
            if not webview:
                return []
                
            # Set defaults
            if options is None:
                options = {}
                
            allow_multiple = options.get('allow_multiple', True)
            file_types = options.get('file_types', ['All files (*.*)'])
            directory = options.get('directory', '')
            
            # Open the file dialog
            selected_files = webview.windows[0].create_file_dialog(
                webview.OPEN_DIALOG, 
                allow_multiple=allow_multiple,
                file_types=file_types,
                directory=directory
            )
            
            # If no files selected or dialog canceled, return empty list
            if not selected_files:
                return []
                
            return selected_files
            
        except Exception as e:
            import traceback
            print(f"[Error] getFileDialog failed: {e}")
            print(traceback.format_exc())
            return []

    def saveClipboardImage(self, options):
        """
        Save an image from clipboard data to a file.
        
        Args:
            options (dict): Options including:
                - imageData (str): Base64 data URL of the image
                
        Returns:
            dict: Response with success status and file path (relative to web root)
        """
        try:
            if not options or 'imageData' not in options:
                return {'success': False, 'error': 'No image data provided'}
                
            # Extract the base64 data from the data URL
            image_data = options['imageData']
            if not image_data.startswith('data:image/'):
                return {'success': False, 'error': 'Invalid image data format'}
                
            # Extract the image format (png, jpeg, etc.)
            format_match = re.match(r'data:image/([a-zA-Z]+);base64,', image_data)
            if not format_match:
                return {'success': False, 'error': 'Could not determine image format'}
                
            img_format = format_match.group(1).lower()
            if img_format == 'jpeg':
                img_format = 'jpg'  # Standardize extension
                
            # Remove the data URL prefix to get the pure base64
            base64_data = image_data.split(',', 1)[1]
            
            # Create a unique filename
            unique_id = str(uuid.uuid4())
            filename = f"clipboard_{unique_id}.{img_format}"
            
            # Actual disk path for saving
            actual_filepath_on_disk = os.path.join(self.image_actual_save_path_base, filename)
            
            # Ensure the directory exists
            os.makedirs(self.image_actual_save_path_base, exist_ok=True)
            
            # Decode and save the image
            with open(actual_filepath_on_disk, 'wb') as f:
                f.write(base64.b64decode(base64_data))
                
            # Path to be used in URLs and stored by frontend (relative to web root)
            path_for_url = os.path.join(self.image_upload_folder_name, filename)
                
            return {
                'success': True, 
                'filePath': path_for_url, # Return the web-relative path
                'message': 'Image saved successfully'
            }
            
        except Exception as e:
            import traceback
            print(f"[Error] saveClipboardImage failed: {e}")
            print(traceback.format_exc())
            return {'success': False, 'error': str(e)}

    def _get_context_key(self, project):
        return project if project else '__main__'

    def _get_messages_with_cache(self, project=None):
        context_key = self._get_context_key(project)
        db = db_messages.MessageDatabaseHandler()
        try:
            # Get last message timestamp for cache invalidation
            if project:
                messages_data = db.get_project_messages(project_name=project)
            else:
                messages_data = db.get_project_messages()
            
            # For each message, fetch its images
            for msg_data in messages_data:
                msg_data['images'] = db.get_message_images(msg_data['id'])

            if messages_data:
                last_msg_time = max(m.get('timestamp', '') for m in messages_data)
            else:
                last_msg_time = ''
            # Check cache
            cache = self._message_cache.get(context_key)
            if cache and cache['cache_key'] == last_msg_time:
                return cache['messages']
            # Update cache
            self._message_cache[context_key] = {
                'messages': messages_data, # Store messages with images
                'cache_key': last_msg_time
            }
            return messages_data
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
                messages_data = db.get_project_messages(project_name=project)
            else:
                messages_data = db.get_project_messages()
            
            # For each message, fetch its images
            for msg_data in messages_data:
                msg_data['images'] = db.get_message_images(msg_data['id'])

        except Exception as e:
            import traceback
            print("[Error] get_all_messages failed:", e)
            print(traceback.format_exc())
            messages_data = []
        finally:
            db.close()
        return messages_data # Return messages with images

    def get_all_reminders(self):
        db = db_messages.MessageDatabaseHandler()
        try:
            messages_data = db.get_project_messages()
            # For each message, fetch its images - though reminders might not typically show images, 
            # good to be consistent if the data structure is reused.
            for msg_data in messages_data:
                msg_data['images'] = db.get_message_images(msg_data['id'])
            reminders = [m for m in messages_data if m.get('remind')]
        except Exception as e:
            import traceback
            print("[Error] get_all_reminders failed:", e)
            print(traceback.format_exc())
            reminders = []
        finally:
            db.close()
        return reminders

    def get_reminder_messages(self):
        """API endpoint to get all non-done messages with reminders."""
        db = db_messages.MessageDatabaseHandler()
        try:
            messages_data = db.get_reminder_messages() # Use the new DB handler method
            # For each message, fetch its images
            for msg_data in messages_data:
                msg_data['images'] = db.get_message_images(msg_data['id'])
        except Exception as e:
            import traceback
            print("[Error] get_reminder_messages failed:", e)
            print(traceback.format_exc())
            messages_data = []
        finally:
            db.close()
        return messages_data # Return messages with images

    def add_message(self, content, project=None, files=None, extra=None, remind=None, importance=None, reoccurences=None, done=False, image_files=None):
        # image_files is expected to be a list of file paths if using pywebview file dialog
        # or could be adapted for actual file uploads if this were a standard web server
        db = db_messages.MessageDatabaseHandler()
        msg_payload = {
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'project': project,
            'files': files, # Existing files field, kept for now
            'extra': extra,
            'processed': 0,
            'remind': remind,
            'importance': importance,
            'reoccurences': reoccurences,
            'done': 0 if not done else 1
        }
        try:
            message_id = db.add_message(msg_payload)
            
            processed_image_paths_for_db = [] # Paths successfully processed and stored in DB

            if image_files and isinstance(image_files, list):
                for provided_path in image_files:
                    if not provided_path: # Skip empty paths
                        continue

                    path_to_store_in_db = None
                    is_absolute = os.path.isabs(provided_path)

                    if is_absolute:
                        # Case 1: Absolute path (from file dialog or drag-drop of local file)
                        if os.path.exists(provided_path):
                            try:
                                filename = secure_filename(os.path.basename(provided_path))
                                unique_filename = f"{message_id}_{filename}" # Ensure unique name related to message
                                
                                # Actual disk path for saving the file inside web/uploads/message_images
                                destination_path_on_disk = os.path.join(self.image_actual_save_path_base, unique_filename)
                                
                                import shutil
                                shutil.copy(provided_path, destination_path_on_disk)
                                
                                # Path to be stored in DB (relative to web root)
                                path_to_store_in_db = os.path.join(self.image_upload_folder_name, unique_filename)
                            except Exception as e:
                                print(f"[Error] Failed to copy/process absolute file path {provided_path}: {e}")
                        else:
                            print(f"[Warning] Provided absolute file path does not exist: {provided_path}")
                    else:
                        # Case 2: Relative path (likely from clipboard paste, already in web/uploads/message_images structure)
                        # The provided_path should be like "uploads/message_images/clipboard_xyz.png"
                        # We need to verify it exists at "web/" + provided_path
                        expected_disk_path = os.path.join("web", provided_path)
                        if os.path.exists(expected_disk_path):
                            path_to_store_in_db = provided_path # Already correct web-relative path
                        else:
                            print(f"[Warning] Provided relative path does not exist in web structure: {provided_path} (Checked: {expected_disk_path})")
                    
                    if path_to_store_in_db:
                        try:
                            db.add_message_image(message_id, path_to_store_in_db, datetime.now().isoformat())
                            processed_image_paths_for_db.append(path_to_store_in_db)
                        except Exception as e:
                            print(f"[Error] Failed to add image to DB ({path_to_store_in_db}): {e}")
            
            self._invalidate_message_cache(project)
            
            # Fetch the newly added message with its images to return
            # To do this efficiently, we'd ideally have a get_message_by_id in db_handler
            # For now, refetching project messages and finding it:
            messages_in_project = db.get_project_messages(project_name=project) 
            returned_message = None
            for m in reversed(messages_in_project): # Check recent messages first
                if m['id'] == message_id:
                    m['images'] = db.get_message_images(message_id) # Ensure images are attached for the response
                    returned_message = m
                    break
            
            return {
                'success': True, 
                'message_id': message_id, 
                'message': returned_message, 
                'saved_images': processed_image_paths_for_db # Return paths that were actually saved to DB
            }
        except Exception as e:
            import traceback
            print("[Error] add_message failed:", e)
            print(traceback.format_exc())
            return {'success': False, 'error': str(e)}
        finally:
            db.close()

    def edit_message(self, message_id, content=None, project=None, remind=None, importance=None, processed=None, done=None, reoccurences=None):
        """Edit message details, including recurrence."""
        db = db_messages.MessageDatabaseHandler()
        try:
            print(f"Editing message {message_id}: remind={remind}, reoccurences={reoccurences}")
            db.update_message(message_id, content=content, project=project, remind=remind, importance=importance, processed=processed, done=done, reoccurences=reoccurences)
            self._message_cache = {}
            reminder_scheduler.refresh_reminders()  # Refresh reminders after editing
            return {'success': True}
        except Exception as e:
            import traceback
            print(f"[Error] edit_message failed for ID {message_id}:", e)
            print(traceback.format_exc())
            return {'success': False, 'error': str(e)}
        finally:
            db.close()

    def delete_message(self, message_id):
        db = db_messages.MessageDatabaseHandler()
        db.delete_message(message_id)
        db.close()
        # Could not determine project, so clear all caches
        self._message_cache = {}
        return {'success': True}

    def toggle_reminder_done(self, message_id, done_status):
        """API endpoint to toggle the done status of a reminder message."""
        db = db_messages.MessageDatabaseHandler()
        try:
            print(f"Toggling reminder done status for ID {message_id} to {done_status}")
            # Use existing update_message, ensuring done_status is correctly interpreted (0 or 1)
            db.update_message(task_id=message_id, done=bool(done_status))
            # Invalidate cache if necessary - though reminders view fetches directly, maybe other views use cache?
            # For safety, let's invalidate the general cache. A more targeted approach might be possible.
            self._message_cache = {}
            return {'success': True}
        except Exception as e:
            import traceback
            print("[Error] toggle_reminder_done failed:", e)
            print(traceback.format_exc())
            return {'success': False, 'error': str(e)}
        finally:
            db.close()

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

            messages = "\n".join([f"ID: {msg['id']}, Content: {msg['content']}, Project: {msg['project']}{', Context: ' + msg['extra'] if msg.get('extra') else ''}" for msg in filtered_messages])

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
                    context_messages = "\n".join([f"ID: {msg['id']}, Content: {msg['content']}, Project: {msg['project']}{', Context: ' + msg['extra'] if msg.get('extra') else ''}" 
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
                    context_messages = "\n".join([f"ID: {msg['id']}, Content: {msg['content']}, Project: {msg['project']}{', Context: ' + msg['extra'] if msg.get('extra') else ''}" 
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
                    context_messages = "\n".join([f"ID: {msg['id']}, Content: {msg['content']}, Project: {msg['project']}{', Context: ' + msg['extra'] if msg.get('extra') else ''}" 
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

    def add_project(self, name, description, color="#dddddd", emoji="📁"):
        from datetime import datetime
        db = db_projects.ProjectsDatabaseHandler()
        db.add_project(name, datetime.now().isoformat(), description, extra="", user_created=1, color=color, emoji=emoji)
        db.close()
        return {'success': True}

    def edit_project(self, project_id, name=None, description=None, color=None, emoji=None):
        db = db_projects.ProjectsDatabaseHandler()
        db.update_project(project_id, new_name=name, new_description=description, color=color, emoji=emoji)
        db.close()
        return {'success': True}

    def delete_project(self, project_id):
        db = db_projects.ProjectsDatabaseHandler()
        db.delete_project(project_id)
        db.close()
        return {'success': True}

    def toggle_check_projects(self, checked):
        """
        Toggle the check_projects flag based on the checkbox state.

        Args:
            checked (bool): Whether the checkbox is checked
        """
        self._check_projects = checked
        print(f"Check projects toggled: {self._check_projects}")
        return {'success': True}

    def process_all_messages(self):
        """
        Process all unprocessed messages in the main chat.
        If check_projects is enabled, first check for new projects before processing messages.
        """
        try:
            print(f"Processing all messages with check_projects={self._check_projects}")
            model_handler.process_all_main_chat_messages(check_for_new_projects=self._check_projects)
            reminder_scheduler.refresh_reminders()  # Refresh reminders after processing
            return {'success': True}
        except Exception as e:
            import traceback
            print('process_all_messages error:', e)
            print(traceback.format_exc())
            return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}

if __name__ == '__main__':
    if webview:
        api = Api()
        window = webview.create_window('Remainder', 'web/index.html', js_api=api, width=1200, height=800)
        webview.start(debug=True)
    else:
        print('pywebview is not installed. Run `pip install pywebview` to use the web UI.')
