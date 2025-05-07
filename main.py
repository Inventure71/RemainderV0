# --- REMOVE ALL TKINTER UI CODE ---
# The UI is now handled by the web frontend (HTML/JS/pywebview). This file now only exposes backend logic and APIs for the web UI.

import sys
import os
import json
import threading
import DatabaseUtils.database_messages as db_messages
import DatabaseUtils.database_projects as db_projects
import DatabaseUtils.database_clipboard as db_clipboard # Added for clipboard messages
from Utils.model_handler import ModelClient
from Utils import telegram_utils
from Utils.reminder_scheduler import ReminderScheduler
from datetime import datetime
from werkzeug.utils import secure_filename
import base64
import uuid
import re
from Utils.clipboard_monitor import initialize_clipboard_manager, shutdown_clipboard_manager

# --- Pywebview API glue ---
try:
    import webview
except ImportError:
    webview = None

# --- Model and DB logic ---
model_handler = ModelClient(mode="gemini", model_context_window=500000)
reminder_scheduler = ReminderScheduler()

CLIPBOARD_PROJECT_NAME = "Saved Clips"
CLIPBOARD_PROJECT_EMOJI = "📋"
CLIPBOARD_PROJECT_COLOR = "#A7C7E7"
CLIPBOARD_PROJECT_DESCRIPTION = "Messages automatically saved from clipboard."

# --- Settings File Configuration ---
SETTINGS_FILE_NAME = "settings.json"

def get_app_support_dir():
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', 'RemainderApp')
    else:
        # For development, place it in the workspace root for easier access.
        # Adjust if a "Databases" or similar subfolder is preferred for dev settings too.
        return os.getcwd() 

def get_settings_file_path():
    return os.path.join(get_app_support_dir(), SETTINGS_FILE_NAME)

DEFAULT_SETTINGS = {
    "clipboard_save_count": 5,
    "include_image_descriptions": True,  # Whether to include image descriptions in context
    # Add other future settings here
}
# --- End Settings File Configuration ---

class Api:
    def __init__(self):
        self._message_cache = {}
        self._chat_history_cache = {}
        self._check_projects = False
        self._show_clips_in_main_chat = False # New filter state, default to false
        
        # --- Load Application Settings ---
        self.settings = self._load_settings()
        # --- End Load Application Settings ---

        reminder_scheduler.start()

        self.image_upload_folder_name = os.path.join("uploads", "message_images")
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            app_support_dir = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', 'RemainderApp')
            self.image_actual_save_path_base = os.path.join(app_support_dir, "uploads", "message_images")
        else:
            self.image_actual_save_path_base = os.path.join("web", self.image_upload_folder_name)
        if not os.path.exists(self.image_actual_save_path_base):
            os.makedirs(self.image_actual_save_path_base, exist_ok=True)
        self._ensure_clipboard_project_exists()

    def _ensure_clipboard_project_exists(self):
        db_handler = db_projects.ProjectsDatabaseHandler()
        try:
            projects = db_handler.get_all_projects()
            if not any(p['name'] == CLIPBOARD_PROJECT_NAME for p in projects):
                db_handler.add_project(
                    project_name=CLIPBOARD_PROJECT_NAME,
                    timestamp=datetime.now().isoformat(),
                    project_description=CLIPBOARD_PROJECT_DESCRIPTION,
                    user_created=0, 
                    color=CLIPBOARD_PROJECT_COLOR,
                    emoji=CLIPBOARD_PROJECT_EMOJI
                )
                print(f"System project '{CLIPBOARD_PROJECT_NAME}' created.")
        except Exception as e:
            print(f"Error ensuring clipboard project exists: {e}")
        finally:
            db_handler.close()

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

    # --- Clipboard Specific Endpoints ---
    def add_clipboard_entry(self, content):
        """Adds a new entry to the clipboard messages database."""
        db_clip = None
        try:
            db_clip = db_clipboard.ClipboardMessagesDatabaseHandler()
            timestamp = datetime.now().isoformat()
            message_id = db_clip.add_message(content, timestamp)
            if message_id:
                self._invalidate_message_cache(CLIPBOARD_PROJECT_NAME)
                main_chat_clips_on_key = self._get_context_key(None) # This key depends on _show_clips_in_main_chat
                if self._show_clips_in_main_chat and main_chat_clips_on_key in self._message_cache: # Only invalidate if clips are shown
                     del self._message_cache[main_chat_clips_on_key]
                     print(f"Invalidated main chat (clips on) cache due to new clipboard entry.")
                return {'success': True, 'id': f"clip_{message_id}"}
            else:
                return {'success': False, 'error': "Failed to add clipboard entry to DB."}
        except Exception as e:
            import traceback
            print(f"[Error] add_clipboard_entry failed: {e}")
            print(traceback.format_exc())
            return {'success': False, 'error': str(e)}
        finally:
            if db_clip:
                db_clip.close()

    def get_clipboard_filter_state(self):
        return {'show_clips_in_main_chat': self._show_clips_in_main_chat}

    def toggle_clipboard_filter_state(self, show_clips: bool):
        new_state = bool(show_clips)
        if self._show_clips_in_main_chat == new_state:
            return {'success': True, 'show_clips_in_main_chat': self._show_clips_in_main_chat, 'message': 'State unchanged.'}

        self._show_clips_in_main_chat = new_state
        print(f"Clipboard messages in main chat toggled to: {self._show_clips_in_main_chat}")
        
        # Invalidate both previous and new main chat cache states to be sure
        # Key for state when clips were OFF
        key_clips_off = f"__main_chat_clips_False"
        if key_clips_off in self._message_cache:
            del self._message_cache[key_clips_off]
            print(f"Invalidated cache for main chat (clips off).")
        # Key for state when clips were ON
        key_clips_on = f"__main_chat_clips_True"
        if key_clips_on in self._message_cache:
            del self._message_cache[key_clips_on]
            print(f"Invalidated cache for main chat (clips on).")
            
        return {'success': True, 'show_clips_in_main_chat': self._show_clips_in_main_chat}

    # --- Cache and Context Key Management ---
    def _get_context_key(self, project):
        if project == CLIPBOARD_PROJECT_NAME:
            return f"__project_{CLIPBOARD_PROJECT_NAME}"
        if project is None:
            return f"__main_chat_clips_{self._show_clips_in_main_chat}"
        return str(project) # Regular project name

    def _invalidate_message_cache(self, project=None):
        context_key = self._get_context_key(project)
        if context_key in self._message_cache:
            del self._message_cache[context_key]
            print(f"Cache invalidated for context key: {context_key}")
        # else:
            # print(f"Attempted to invalidate cache for {context_key}, but it was not found (this is often OK).")

    def _get_messages_with_cache(self, project=None):
        context_key = self._get_context_key(project)
        cached_entry = self._message_cache.get(context_key)

        # Simplified cache check: Rely on explicit invalidation.
        # If a more robust staleness check is needed, the 'cache_key' (version) can be used.
        # For now, if it's in cache, it's considered good.
        if cached_entry:
            return cached_entry['messages']

        messages_data = []
        db_msg_handler = None
        db_clip_handler = None
        
        try:
            if project == CLIPBOARD_PROJECT_NAME:
                db_clip_handler = db_clipboard.ClipboardMessagesDatabaseHandler()
                raw_clip_messages = db_clip_handler.get_all_messages()
                for msg in raw_clip_messages:
                    messages_data.append({
                        'id': f"clip_{msg['id']}",
                        'content': msg['content'],
                        'timestamp': msg['timestamp'],
                        'project': CLIPBOARD_PROJECT_NAME,
                        'images': [], 'files': None, 'extra': None, 'processed': 1,
                        'remind': None, 'importance': None, 'reoccurences': None, 'done': False
                    })
            elif project is None: # Main Chat
                db_msg_handler = db_messages.MessageDatabaseHandler()
                true_main_messages_raw = db_msg_handler.get_project_messages(project_name=None)
                for msg_raw in true_main_messages_raw:
                    msg_dict = dict(msg_raw)
                    msg_dict['images'] = db_msg_handler.get_message_images(msg_dict['id']) if db_msg_handler else []
                    messages_data.append(msg_dict)

                if self._show_clips_in_main_chat:
                    db_clip_handler = db_clipboard.ClipboardMessagesDatabaseHandler()
                    raw_clip_messages = db_clip_handler.get_all_messages()
                    for msg in raw_clip_messages:
                        messages_data.append({
                            'id': f"clip_{msg['id']}",
                            'content': msg['content'],
                            'timestamp': msg['timestamp'],
                            'project': CLIPBOARD_PROJECT_NAME,
                            'images': [], 'files': None, 'extra': None, 'processed': 1,
                            'remind': None, 'importance': None, 'reoccurences': None, 'done': False
                        })
                messages_data.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            else: # Regular project
                db_msg_handler = db_messages.MessageDatabaseHandler()
                raw_project_messages = db_msg_handler.get_project_messages(project_name=project)
                for msg_raw in raw_project_messages:
                    msg_dict = dict(msg_raw)
                    msg_dict['images'] = db_msg_handler.get_message_images(msg_dict['id']) if db_msg_handler else []
                    messages_data.append(msg_dict)
            
            # Use a simple timestamp of caching as the cache key for now.
            # More sophisticated versioning (e.g., based on content hash or count+latest_ts) can be added if needed.
            self._message_cache[context_key] = {
                'messages': messages_data,
                'cache_key': datetime.now().isoformat() 
            }
            return messages_data
        except Exception as e:
            import traceback
            print(f"[Error] _get_messages_with_cache failed for project '{project}': {e}")
            print(traceback.format_exc())
            return []
        finally:
            if db_msg_handler: db_msg_handler.close()
            if db_clip_handler: db_clip_handler.close()

    def _get_chat_history(self, project=None):
        context_key = self._get_context_key(project)
        return self._chat_history_cache.get(context_key, [])

    def _set_chat_history(self, history, project=None):
        context_key = self._get_context_key(project)
        self._chat_history_cache[context_key] = history

    def reset_model_chat_history(self, project=None):
        context_key = self._get_context_key(project)
        if context_key in self._chat_history_cache:
            del self._chat_history_cache[context_key]
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
        """Public API to get all messages for a project or main chat, using cache."""
        return self._get_messages_with_cache(project)

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
        db_messages_h = None
        try:
            db_messages_h = db_messages.MessageDatabaseHandler()
            msg_payload = {
                'content': content, 'timestamp': datetime.now().isoformat(), 'project': project,
                'files': files, 'extra': extra, 'processed': 0, 'remind': remind,
                'importance': importance, 'reoccurences': reoccurences, 'done': 0 if not done else 1
            }
            message_id = db_messages_h.add_message(msg_payload)
            processed_image_paths_for_db = []
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
                            db_messages_h.add_message_image(message_id, path_to_store_in_db, datetime.now().isoformat())
                            processed_image_paths_for_db.append(path_to_store_in_db)
                        except Exception as e:
                            print(f"[Error] Failed to add image to DB ({path_to_store_in_db}): {e}")
            
            self._invalidate_message_cache(project)
            
            # Fetch the newly added message with its images to return
            # To do this efficiently, we'd ideally have a get_message_by_id in db_handler
            # For now, refetching project messages and finding it:
            messages_in_project = db_messages_h.get_project_messages(project_name=project) 
            returned_message = None
            for m in reversed(messages_in_project): # Check recent messages first
                if m['id'] == message_id:
                    m['images'] = db_messages_h.get_message_images(message_id) # Ensure images are attached for the response
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
            if db_messages_h: db_messages_h.close()

    def edit_message(self, message_id, content=None, project=None, remind=None, importance=None, processed=None, done=None, reoccurences=None):
        """Edit message details, including recurrence."""
        db_messages_h = None
        try:
            print(f"Editing message {message_id}: remind={remind}, reoccurences={reoccurences}")
            db_messages_h = db_messages.MessageDatabaseHandler()
            db_messages_h.update_message(message_id, content=content, project=project, remind=remind, importance=importance, processed=processed, done=done, reoccurences=reoccurences)
            self._message_cache = {}
            reminder_scheduler.refresh_reminders()  # Refresh reminders after editing
            return {'success': True}
        except Exception as e:
            import traceback
            print(f"[Error] edit_message failed for ID {message_id}:", e)
            print(traceback.format_exc())
            return {'success': False, 'error': str(e)}
        finally:
            if db_messages_h: db_messages_h.close()

    def delete_message(self, message_id):
        if isinstance(message_id, str) and message_id.startswith("clip_"):
            actual_id_str = message_id.split("_", 1)[1]
            if not actual_id_str.isdigit():
                return {'success': False, 'error': f"Invalid clipboard message ID format: {message_id}"}
            actual_id = int(actual_id_str)
            
            db_clip_h = None
            try:
                db_clip_h = db_clipboard.ClipboardMessagesDatabaseHandler()
                deleted = db_clip_h.delete_message(actual_id)
                if deleted:
                    self._invalidate_message_cache(CLIPBOARD_PROJECT_NAME)
                    # Invalidate main chat if clips are shown
                    if self._show_clips_in_main_chat:
                         self._invalidate_message_cache(None) # Uses current state of _show_clips_in_main_chat
                    print(f"Clipboard message {message_id} (original ID: {actual_id}) deleted.")
                    return {'success': True}
                else:
                    return {'success': False, 'error': f"Failed to delete clipboard message {message_id} from DB."}
            except Exception as e:
                print(f"Error deleting clipboard message {message_id}: {e}")
                return {'success': False, 'error': str(e)}
            finally:
                if db_clip_h: db_clip_h.close()
        else: # Regular message
            db_messages_h = None
            try:
                db_messages_h = db_messages.MessageDatabaseHandler()
                # TODO: Get message details (esp. project) BEFORE deleting to invalidate specific cache.
                # For now, clear relevant caches broadly.
                db_messages_h.delete_message(message_id)
                print(f"Regular message {message_id} deleted. Invalidating potentially related caches.")
                # Broad invalidation as we don't know the project easily post-delete
                self._message_cache.clear() # Simplest broad approach for now
                self._chat_history_cache.clear()
                return {'success': True}
            except Exception as e:
                print(f"Error deleting regular message {message_id}: {e}")
                return {'success': False, 'error': str(e)}
            finally:
                if db_messages_h: db_messages_h.close()

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
        """
        Interact with the model, providing the appropriate context based on the project.
        """
        # Get history if using
        if use_history:
            chat_history = self._get_chat_history(project)
        else:
            chat_history = []

        # Get messages from cache/DB
        messages_data = self._get_messages_with_cache(project)
        include_image_descriptions = self.settings.get("include_image_descriptions", DEFAULT_SETTINGS["include_image_descriptions"])
        
        # Format messages into a context string for the model
        context_string = ""
        if not project:
            context_title = "Main Chat"
            if self._show_clips_in_main_chat:
                context_title += " (including Saved Clips)"
        else:
            context_title = f"Project: {project}"

        for msg in messages_data:
            # Core message information
            msg_content = msg.get('content', '')
            msg_id = msg.get('id', '')
            msg_timestamp = msg.get('timestamp', '')
            msg_project = msg.get('project', '')
            msg_extra = msg.get('extra', '')
            
            # Build the base context line
            context_line = f"ID: {msg_id}, Timestamp: {msg_timestamp}, Project: {msg_project}, Extra: {msg_extra}, Text: {msg_content}"
            
            # Add image descriptions if present and enabled
            if include_image_descriptions and 'images' in msg and msg['images']:
                for i, img in enumerate(msg['images']):
                    if img.get('description'):
                        context_line += f"\n[Image {i+1} Description: {img['description']}]"
            
            context_string += context_line + "\n\n"

        print(f"Generating model chat response in context: {context_title}")
        
        response, new_history = model_handler.generate(prompt=prompt, messages=context_string, json=0, history=chat_history)
        self._set_chat_history(new_history, project)
        
        return {"response": response}

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
        # The `messages` argument is deprecated for this function as it now fetches its own full context.
        # It's kept for signature compatibility but ignored if empty.
        print(f"[model_select_messages] Called for context: {project or 'Main Chat'} (Show Clips: {self._show_clips_in_main_chat}) for {prompt}")
        
        # Get history if it was passed
        if history is None:
            chat_history = []
        else:
            chat_history = history
        
        # Get comprehensive message list directly with proper project filtering
        messages_data = self._get_messages_with_cache(project)
        include_image_descriptions = self.settings.get("include_image_descriptions", DEFAULT_SETTINGS["include_image_descriptions"])
        
        # Format messages into a context string for the model
        context_string = ""
        for msg in messages_data:
            # Core message information
            msg_content = msg.get('content', '')
            msg_id = msg.get('id', '')
            msg_timestamp = msg.get('timestamp', '')
            msg_project = msg.get('project', '')
            msg_extra = msg.get('extra', '')
            
            # Build the context line
            context_line = f"ID: {msg_id}, Timestamp: {msg_timestamp}, Project: {msg_project}, Extra: {msg_extra}, Text: {msg_content}"
            
            # Add image descriptions if present and enabled
            if include_image_descriptions and 'images' in msg and msg['images']:
                for i, img in enumerate(msg['images']):
                    if img.get('description'):
                        context_line += f"\n[Image {i+1} Description: {img['description']}]"
            
            context_string += context_line + "\n\n"
        
        # Call the model handler with our prepared context
        response, new_history = model_handler.select_messages(
            user_text=prompt,
            project=project,
            use_history=False,
            history=chat_history,
            context_string=context_string  # Pass the prepared context string with image descriptions
        )
        
        # Create a more detailed response from the Gemini model response
        try:
            import json
            response_data = json.loads(response)
            model_selected_messages = response_data.get('messages', [])
            
            # Enhance the response with additional metadata
            for msg in model_selected_messages:
                msg_id = msg.get('id')
                if msg_id:
                    # Find the original message in our full messages_data collection
                    original_message = next((m for m in messages_data if str(m.get('id')) == str(msg_id)), None)
                    if original_message:
                        # Add original message data including image info
                        msg['original_message_data'] = {
                            'project': original_message.get('project', ''),
                            'has_images': bool(original_message.get('images') and len(original_message.get('images', [])) > 0)
                        }
                        # For debugging
                        print(f"Enhanced message {msg_id}: has_images={msg['original_message_data']['has_images']}")
            
            # Return enhanced response with our modifications
            enhanced_response = json.dumps(response_data)
            result = {"result": enhanced_response}
            return result
        except Exception as e:
            print(f"Error enhancing model_select_messages response: {e}")
            # Return original response if enhancement fails
            return {"result": response}

    def model_assign_projects(self, prompt, messages, projects, history=None):
        try:
            context_messages_str = messages
            if not messages or messages == "":
                print("[model_assign_projects] WARNING: Message fetching bypasses new cache logic. Fetches all from primary DB.")
                
                # Get messages with cache to ensure image data is included
                messages_data = self._get_messages_with_cache()
                include_image_descriptions = self.settings.get("include_image_descriptions", DEFAULT_SETTINGS["include_image_descriptions"])
                
                # Build context with image descriptions
                context_lines = []
                for msg in messages_data:
                    # Basic message info
                    msg_line = f"ID: {msg['id']}, Content: {msg['content']}, Project: {msg['project']}"
                    if msg.get('extra'):
                        msg_line += f", Context: {msg['extra']}"
                    
                    # Add image descriptions if present and enabled
                    if include_image_descriptions and 'images' in msg and msg['images']:
                        for i, img in enumerate(msg['images']):
                            if img.get('description'):
                                msg_line += f"\n[Image {i+1} Description: {img['description']}]"
                    
                    context_lines.append(msg_line)
                
                context_messages_str = "\n".join(context_lines)

            print("model assign projects requested")
            print("project:", projects)

            # Process history (only actual user prompts and model responses)
            gemini_history = None
            if history and isinstance(history, list):
                gemini_history = []
                for h in history:
                    if isinstance(h, dict) and 'role' in h and 'content' in h:
                        # Only include the actual chat history, not the context messages
                        gemini_history.append(h)

            # Generate response
            result, all_history = model_handler.generate(prompt, context_messages_str, json=2, history=gemini_history)
            return {'result': result, 'history': all_history}
        except Exception as e:
            import traceback
            print('model_assign_projects error:', e)
            print(traceback.format_exc())
            return {'result': None, 'history': [], 'error': str(e), 'traceback': traceback.format_exc()}

    def model_create_projects(self, prompt, messages, history=None):
        try:
            context_messages_str = messages
            if not messages or messages == "":
                print("[model_create_projects] WARNING: Message fetching bypasses new cache logic. Fetches all from primary DB.")
                
                # Get messages with cache to ensure image data is included
                messages_data = self._get_messages_with_cache()
                include_image_descriptions = self.settings.get("include_image_descriptions", DEFAULT_SETTINGS["include_image_descriptions"])
                
                # Build context with image descriptions
                context_lines = []
                for msg in messages_data:
                    # Basic message info
                    msg_line = f"ID: {msg['id']}, Content: {msg['content']}, Project: {msg['project']}"
                    if msg.get('extra'):
                        msg_line += f", Context: {msg['extra']}"
                    
                    # Add image descriptions if present and enabled
                    if include_image_descriptions and 'images' in msg and msg['images']:
                        for i, img in enumerate(msg['images']):
                            if img.get('description'):
                                msg_line += f"\n[Image {i+1} Description: {img['description']}]"
                    
                    context_lines.append(msg_line)
                
                context_messages_str = "\n".join(context_lines)

            print("model create projects requested")
            print("messages:", messages)

            # Process history (only actual user prompts and model responses)
            gemini_history = None
            if history and isinstance(history, list):
                gemini_history = []
                for h in history:
                    if isinstance(h, dict) and 'role' in h and 'content' in h:
                        # Only include the actual chat history, not the context messages
                        gemini_history.append(h)

            # Generate response
            result, all_history = model_handler.generate(prompt, context_messages_str, json=3, history=gemini_history)
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
        # TODO: Review if model_handler.process_all_main_chat_messages needs context of clipboard filter
        # Its internal logic fetches "unprocessed messages in the main chat". This needs clarification.
        try:
            print(f"[process_all_messages] (check_projects={self._check_projects}) - Current clipboard filter: {self._show_clips_in_main_chat}")
            print("[process_all_messages] WARNING: model_handler.process_all_main_chat_messages may need review for clipboard message handling.")
            model_handler.process_all_main_chat_messages(check_for_new_projects=self._check_projects)
            reminder_scheduler.refresh_reminders()  # Refresh reminders after processing
            return {'success': True}
        except Exception as e:
            import traceback
            print('process_all_messages error:', e)
            print(traceback.format_exc())
            return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}

    def process_unprocessed_images(self, max_images_per_batch=25):
        """
        Process unprocessed images by feeding them to Gemini for description generation.
        
        Args:
            max_images_per_batch (int): Maximum number of images to process in a single batch
            
        Returns:
            dict: Result of the operation including success status, number of images processed
        """
        try:
            db_handler = db_messages.MessageDatabaseHandler()
            
            # First, get all images that don't have descriptions
            self.cursor = db_handler.conn.cursor()
            self.cursor.execute("""
                SELECT mi.id, mi.message_id, mi.file_path, m.content 
                FROM message_images mi
                JOIN messages m ON mi.message_id = m.id
                WHERE mi.description IS NULL OR mi.description = ''
                LIMIT ?
            """, (max_images_per_batch,))
            
            unprocessed_images = self.cursor.fetchall()
            
            if not unprocessed_images:
                return {
                    'success': True,
                    'processed': 0,
                    'message': 'No unprocessed images found'
                }
            
            # Prepare the API request for Gemini
            image_data = []
            for img_id, msg_id, file_path, msg_content in unprocessed_images:
                full_path = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)), 
                    "web", 
                    file_path if not file_path.startswith('/') else file_path[1:]
                )
                
                if os.path.exists(full_path):
                    image_data.append({
                        'img_id': img_id,
                        'msg_id': msg_id,
                        'file_path': full_path,
                        'context': msg_content
                    })
                else:
                    print(f"Warning: Image file not found: {full_path}")
            
            if not image_data:
                return {
                    'success': False,
                    'processed': 0,
                    'message': 'No valid image files found among unprocessed images'
                }
            
            # Process the images with Gemini
            descriptions = self._process_images_with_gemini(image_data)
            if not descriptions:
                return {
                    'success': False,
                    'processed': 0,
                    'message': 'Failed to get descriptions from Gemini'
                }
            
            # Update the database with descriptions
            processed_count = 0
            for img_id, description in descriptions.items():
                db_handler.cursor.execute(
                    "UPDATE message_images SET description = ? WHERE id = ?",
                    (description, img_id)
                )
                processed_count += 1
            
            db_handler.conn.commit()
            
            # Clear cache to reflect the updated descriptions
            self._message_cache.clear()
            
            return {
                'success': True,
                'processed': processed_count,
                'total': len(unprocessed_images),
                'message': f'Successfully processed {processed_count} images'
            }
        
        except Exception as e:
            import traceback
            print(f"[Error] process_unprocessed_images failed: {e}")
            print(traceback.format_exc())
            return {'success': False, 'error': str(e)}
        finally:
            if 'db_handler' in locals():
                db_handler.close()

    def _process_images_with_gemini(self, image_data):
        """
        Process images with Gemini to get descriptions.
        
        Args:
            image_data (list): List of dicts with image info (img_id, file_path, context)
        
        Returns:
            dict: Mapping of image_id to description
        """
        try:
            # If no images, return empty dict
            if not image_data:
                return {}
            
            # Prepare prompt for Gemini
            system_prompt = """
You are an expert image analyzer. Your task is to:
1. Describe each image in detail
2. Transcribe any visible text in the image
3. Provide key information about what's shown

You MUST respond in JSON format ONLY with the following structure:
{
  "images": [
    {
      "image_id": 123,
      "description": "Detailed description of the image",
      "text_content": "Any text visible in the image, or null if none"
    },
    ...
  ]
}

Be thorough but concise. Focus on the most important details.
Do not include any extra text, explanations, or markdown formatting outside the JSON structure.
"""
            
            # Create multipart message for Gemini with images
            contents = [
                {
                    "role": "user",
                    "parts": [{"text": system_prompt}]
                },
                {
                    "role": "user",
                    "parts": [{"text": "Please analyze the following images:"}]
                }
            ]
            
            # Add image parts to the message
            user_parts = []
            for idx, img in enumerate(image_data):
                # Add context if available
                if img.get('context'):
                    user_parts.append({"text": f"Image {idx+1} (ID: {img['img_id']}) context: {img['context']}"})
                
                # Read and encode image
                with open(img['file_path'], 'rb') as image_file:
                    image_bytes = image_file.read()
                    mime_type = self._get_mime_type(img['file_path'])
                    
                    user_parts.append({
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": base64.b64encode(image_bytes).decode('utf-8')
                        }
                    })
            
            # Add the parts to the user message
            contents.append({
                "role": "user",
                "parts": user_parts
            })
            
            # Call Gemini with the multipart message
            response = model_handler.gemini_client.models.generate_content(
                model="gemini-2.5-flash-preview-04-17",
                contents=contents
            )
            
            # Process the response
            try:
                # First check if the response has a text attribute
                if hasattr(response, 'text'):
                    response_text = response.text
                # Next check if the response has parts with text
                elif hasattr(response, 'parts') and response.parts:
                    response_text = response.parts[0].text
                # Finally check if we can access it as a dictionary
                elif hasattr(response, 'candidates') and response.candidates:
                    response_text = response.candidates[0].content.parts[0].text
                else:
                    # Get as string
                    response_text = str(response)
                
                # Now extract and parse the JSON from the response text
                json_str = response_text
                
                # Handle case where JSON is within markdown code blocks
                if "```json" in response_text:
                    # Extract the JSON between ```json and ```
                    json_str = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    # Extract JSON from any code block
                    json_str = response_text.split("```")[1].strip()
                
                # Clean any leading/trailing spaces and quotes
                json_str = json_str.strip('" \n\t')
                
                # Parse the JSON
                try:
                    response_json = json.loads(json_str)
                except json.JSONDecodeError:
                    # If we can't parse the JSON, try to extract it with regex
                    import re
                    json_pattern = r'\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\}))*\}))*\}'
                    match = re.search(json_pattern, response_text)
                    if match:
                        try:
                            response_json = json.loads(match.group(0))
                        except:
                            # Fallback to empty structure
                            response_json = {"images": []}
                    else:
                        # Complete fallback
                        response_json = {"images": []}
                
                results = {}
                
                # Extract descriptions and map to image IDs
                for img_result in response_json.get('images', []):
                    img_id = img_result.get('image_id')
                    description = img_result.get('description', '')
                    text_content = img_result.get('text_content')
                    
                    # Build proper description without raw JSON
                    full_description = description if description else ""
                    
                    # Add text content if present and not null
                    if text_content and text_content.lower() != 'null':
                        if full_description:
                            full_description += "\n\nText content:\n"
                        else:
                            full_description += "Text content:\n"
                        full_description += text_content
                    
                    # Find the matching image data entry
                    for img in image_data:
                        if str(img['img_id']) == str(img_id):
                            results[img['img_id']] = full_description
                            break
                
                # If we couldn't match by ID, try to match by order
                if not results and response_json.get('images'):
                    for i, img_result in enumerate(response_json.get('images')):
                        if i < len(image_data):
                            img_id = image_data[i]['img_id']
                            description = img_result.get('description', '')
                            text_content = img_result.get('text_content')
                            
                            # Build proper description
                            full_description = description if description else ""
                            
                            # Add text content if present and not null
                            if text_content and text_content.lower() != 'null':
                                if full_description:
                                    full_description += "\n\nText content:\n"
                                else:
                                    full_description += "Text content:\n"
                                full_description += text_content
                                
                            results[img_id] = full_description
                
                return results
            except Exception as e:
                print(f"Error parsing Gemini response: {e}")
                # Fallback to direct text response if JSON parsing fails
                results = {}
                
                # Try to assign the response to images sequentially
                response_text = response.text
                for i, img in enumerate(image_data):
                    results[img['img_id']] = f"Auto-generated description: {response_text}"
                
                return results
            
        except Exception as e:
            print(f"Error in _process_images_with_gemini: {e}")
            return {}

    def _get_mime_type(self, file_path):
        """Determine MIME type based on file extension"""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.jpg' or ext == '.jpeg':
            return 'image/jpeg'
        elif ext == '.png':
            return 'image/png'
        elif ext == '.gif':
            return 'image/gif'
        elif ext == '.webp':
            return 'image/webp'
        elif ext == '.svg':
            return 'image/svg+xml'
        else:
            return 'application/octet-stream'

    # --- Settings Management ---
    def _load_settings(self):
        settings_path = get_settings_file_path()
        try:
            if os.path.exists(settings_path):
                with open(settings_path, 'r') as f:
                    loaded_settings = json.load(f)
                    # Ensure all default keys are present
                    final_settings = DEFAULT_SETTINGS.copy()
                    final_settings.update(loaded_settings)
                    return final_settings
            else:
                # If settings file doesn't exist, save default settings
                self._save_settings(DEFAULT_SETTINGS)
                return DEFAULT_SETTINGS.copy()
        except Exception as e:
            print(f"[Error] Failed to load settings from {settings_path}: {e}. Using default settings.")
            return DEFAULT_SETTINGS.copy()

    def _save_settings(self, settings_data):
        settings_path = get_settings_file_path()
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(settings_path), exist_ok=True)
            with open(settings_path, 'w') as f:
                json.dump(settings_data, f, indent=4)
            print(f"Settings saved to {settings_path}")
        except Exception as e:
            print(f"[Error] Failed to save settings to {settings_path}: {e}")

    def get_app_settings(self):
        """Returns all current application settings."""
        return {"success": True, "settings": self.settings}

    def update_setting(self, key, value):
        """Updates a specific application setting."""
        if key in self.settings:
            self.settings[key] = value
            self._save_settings(self.settings)
            
            # If the clipboard_save_count is updated, we might need to restart or update the monitor.
            # For now, the monitor will use the value at its initialization.
            # A more advanced implementation might signal the monitor to update its config.
            if key == "clipboard_save_count":
                print(f"Setting '{key}' updated to {value}. Restart clipboard monitor or app for changes to take full effect if already running.")
            
            return {"success": True, "message": f"Setting '{key}' updated to {value}."}
        else:
            return {"success": False, "error": f"Setting key '{key}' not found."}

    def get_image_descriptions(self):
        """Returns a list of all processed image descriptions for display/debugging purposes."""
        try:
            db_handler = db_messages.MessageDatabaseHandler()
            self.cursor = db_handler.conn.cursor()
            
            # Query all images with descriptions
            self.cursor.execute("""
                SELECT mi.id, mi.message_id, mi.file_path, mi.description, m.content
                FROM message_images mi
                JOIN messages m ON mi.message_id = m.id
                WHERE mi.description IS NOT NULL AND mi.description != ''
                ORDER BY m.timestamp DESC
            """)
            
            images_with_descriptions = []
            for img_id, msg_id, file_path, description, msg_content in self.cursor.fetchall():
                # Take only first 100 characters of message content for context
                short_content = (msg_content[:100] + '...') if len(msg_content) > 100 else msg_content
                
                images_with_descriptions.append({
                    "img_id": img_id,
                    "msg_id": msg_id,
                    "file_path": file_path,
                    "short_content": short_content,
                    "description": description
                })
            
            return {
                "success": True,
                "images": images_with_descriptions,
                "count": len(images_with_descriptions)
            }
            
        except Exception as e:
            import traceback
            print(f"[Error] get_image_descriptions failed: {e}")
            print(traceback.format_exc())
            return {'success': False, 'error': str(e)}
        finally:
            if 'db_handler' in locals():
                db_handler.close()

    def clean_image_descriptions(self):
        """Clean up existing image descriptions that contain raw JSON."""
        try:
            db_handler = db_messages.MessageDatabaseHandler()
            cursor = db_handler.conn.cursor()
            
            # Get all images with descriptions
            cursor.execute("""
                SELECT id, description FROM message_images 
                WHERE description IS NOT NULL AND description != ''
            """)
            
            updates = 0
            for row in cursor.fetchall():
                img_id, description = row
                
                if "Auto-generated description: ```json" in description:
                    try:
                        # Extract the JSON content
                        json_str = description.split("```json")[1].split("```")[0].strip()
                        json_data = json.loads(json_str)
                        
                        # Format the cleaned description
                        clean_description = ""
                        for img_data in json_data.get('images', []):
                            if clean_description:
                                clean_description += "\n\n"
                                
                            # Add the description
                            desc = img_data.get('description', '')
                            if desc:
                                clean_description += f"{desc}"
                            
                            # Add text content if present
                            text = img_data.get('text_content')
                            if text and text.lower() != 'null':
                                clean_description += f"\n\nText content:\n{text}"
                        
                        # Update the database
                        if clean_description:
                            cursor.execute(
                                "UPDATE message_images SET description = ? WHERE id = ?",
                                (clean_description, img_id)
                            )
                            updates += 1
                            
                    except Exception as e:
                        print(f"Error cleaning description for image ID {img_id}: {e}")
                        continue
            
            db_handler.conn.commit()
            return {"success": True, "cleaned": updates}
            
        except Exception as e:
            import traceback
            print(f"[Error] clean_image_descriptions failed: {e}")
            print(traceback.format_exc())
            return {'success': False, 'error': str(e)}
        finally:
            if 'db_handler' in locals():
                db_handler.close()
                
    def clear_image_descriptions(self):
        """Clear all image descriptions to allow reprocessing."""
        try:
            db_handler = db_messages.MessageDatabaseHandler()
            cursor = db_handler.conn.cursor()
            
            # Clear all descriptions
            cursor.execute("UPDATE message_images SET description = NULL")
            affected = cursor.rowcount
            db_handler.conn.commit()
            
            return {"success": True, "cleared": affected}
            
        except Exception as e:
            import traceback
            print(f"[Error] clear_image_descriptions failed: {e}")
            print(traceback.format_exc())
            return {'success': False, 'error': str(e)}
        finally:
            if 'db_handler' in locals():
                db_handler.close()

if __name__ == '__main__':
    api = Api()
    
    # Initialize the clipboard manager (must be on main thread before webview.start)
    # The initialize_clipboard_manager itself handles sys.platform check.
    clipboard_save_count = api.settings.get("clipboard_save_count", DEFAULT_SETTINGS["clipboard_save_count"])
    clipboard_manager_instance = initialize_clipboard_manager(api_client=api, consecutive_copies_needed=clipboard_save_count)

    def on_window_closing(): # Renamed for clarity with pywebview event name
        print("Main window is closing. Initiating clipboard manager shutdown.")
        # shutdown_clipboard_manager() is designed to be callable globally
        shutdown_clipboard_manager() 
        # Note: Depending on how pywebview handles event processing during shutdown,
        # the main thread operations within shutdown_clipboard_manager (like removeStatusItem)
        # should ideally complete before the app fully terminates.

    if webview:
        window = webview.create_window('Remainder', 'web/index.html', js_api=api, width=1200, height=800)
        
        # Attempt to hook into the window closing event
        # pywebview's event system might vary slightly or have specific ways.
        # Common patterns include direct assignment or using += if it's a list-like dispatcher.
        # Let's assume a direct assignment or a robust way to add a listener if one exists.
        # Based on some pywebview usage, direct attribute assignment for certain events works.
        # Let's assume a direct assignment or a robust way to add a listener if one exists.
        # Based on some pywebview usage, direct attribute assignment for certain events works.
        if hasattr(window.events, 'closing'): # Check if the event exists
             window.events.closing += on_window_closing
        elif hasattr(window.events, 'closed'):
            window.events.closed += on_window_closing # Try 'closed' if 'closing' not present
        else:
            print("[main.py] Warning: Could not attach clipboard manager shutdown to window closing event.")
            # Fallback: use atexit for best-effort cleanup if window events are tricky
            import atexit
            atexit.register(shutdown_clipboard_manager)
            print("[main.py] Registered clipboard manager shutdown with atexit as a fallback.")

        webview.start(debug=True)
        
        # Code here might not be reached if webview.start() blocks until app quit
        # and doesn't return, unless in a specific GUI mode.
        # If webview.start() only returns after the window is closed, then cleanup can happen here too.
        # However, relying on the event or atexit is safer.
        # print("Webview has stopped. Performing final cleanup if any.")
        # shutdown_clipboard_manager() # Potentially redundant if event/atexit worked.

    else:
        print('pywebview is not installed. Run `pip install pywebview` to use the web UI.')
        # If the clipboard manager was started and there's no webview, ensure it's shut down
        # when the script/main function would otherwise exit.
        if sys.platform == 'darwin' and clipboard_manager_instance: # Check if it was meant to run
            print("No webview UI. Main script ending. Shutting down clipboard manager.")
            # This direct call is fine if the script is simply ending here.
            shutdown_clipboard_manager()
