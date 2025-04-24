import tkinter as tk
from tkinter import messagebox

from UI.window_project_chat import ProjectChatWindow
from UI.window_projects import ProjectsWindow
from UI.window_main_chat import MainChatWindow

import webview
from Utils import telegram_utils
from DatabaseUtils.database_messages import MessageDatabaseHandler
from DatabaseUtils.database_projects import ProjectsDatabaseHandler

# --- App Setup ---
class App(tk.Tk):
    def __init__(self):
        """
        Initialize the main application window.

        The main window is setup with a title of "Remainder" and a size of 1080x720.
        A container frame is created to stack pages and is packed to fill the window.
        The container frame is configured to expand in both the x and y directions.

        The frames dictionary is created to store pages by name.
        Each page is created and packed into the container frame.
        The show_frame method is then called to raise the MainChatWindow frame to the top.
        """
        super().__init__()

        self.title("Remainder")
        self.geometry("1080x720")

        self.current_page = None

        # Create a container frame to stack pages
        container = tk.Frame(self)
        container.pack(fill="both", expand=True)

        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        # Dictionary to store pages by name
        self.frames = {}

        for F in (MainChatWindow, ProjectsWindow, ProjectChatWindow):
            page_name = F.__name__  # e.g., "MainChatWindow"
            frame = F(parent=container, controller=self)
            frame.grid(row=0, column=0, sticky="nsew")
            self.frames[page_name] = frame

        self.show_frame("MainChatWindow")

    def show_frame(self, page_name: str):
        """Raise the frame to the top by string name"""
        frame = self.frames[page_name]
        frame.refresh()
        self.current_page = page_name
        frame.tkraise()

    def select_project(self, project_dictionary):
        self.frames["ProjectChatWindow"].change_project(project_dictionary)
        self.show_frame("ProjectChatWindow")


class Api:
    def refresh_telegram_messages(self):
        try:
            telegram_utils.retrive_messages(save_to_file=False)
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_all_projects(self):
        db = ProjectsDatabaseHandler()
        projects = db.get_all_projects()
        db.close()
        return projects

    def get_all_messages(self, project=None):
        db = MessageDatabaseHandler()
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
        db = MessageDatabaseHandler()
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
        db = ProjectsDatabaseHandler()
        db.add_project(name, datetime.now().isoformat(), description, extra="", user_created=1, color=color)
        db.close()
        return {'success': True}

    def edit_project(self, project_id, name=None, description=None, color=None):
        db = ProjectsDatabaseHandler()
        db.update_project(project_id, new_name=name, new_description=description, color=color)
        db.close()
        return {'success': True}

    def delete_project(self, project_id):
        db = ProjectsDatabaseHandler()
        db.delete_project(project_id)
        db.close()
        return {'success': True}

    def add_message(self, content, project=None, files=None, extra=None, remind=None, importance=None, reoccurences=None):
        from datetime import datetime
        db = MessageDatabaseHandler()
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
        db = MessageDatabaseHandler()
        db.update_message(message_id, content=content, project=project, remind=remind, importance=importance, processed=processed)
        db.close()
        return {'success': True}

    def delete_message(self, message_id):
        db = MessageDatabaseHandler()
        db.delete_message(message_id)
        db.close()
        return {'success': True}

    def mark_message_processed(self, message_id, processed=True):
        db = MessageDatabaseHandler()
        db.update_message(message_id, processed=processed)
        db.close()
        return {'success': True}

    # Placeholder for model chat/AI integration
    def model_chat(self, prompt, use_history=False, project=None):
        # TODO: Integrate with your model handler
        return {'response': 'Model response (not implemented)'}

    def api_route(self, path):
        # Simple routing for web API
        from flask import request, jsonify
        if path == '/api/get_all_reminders':
            return jsonify(self.get_all_reminders())
        if path == '/api/edit_message':
            data = request.json
            return jsonify(self.edit_message(
                data['message_id'],
                project=data.get('project'),
                remind=data.get('remind'),
                importance=data.get('importance'),
                processed=data.get('processed'),
                content=data.get('content'),
                reoccurences=data.get('reoccurences')
            ))
        # ... (other routes)
        return '', 404


def start_webview():
    api = Api()
    window = webview.create_window('Remainder', 'web/index.html', width=1080, height=720, js_api=api)
    webview.start(debug=True, http_server=True)

# --- Start the App ---
if __name__ == "__main__":
    start_webview()
