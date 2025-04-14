import time
import tkinter as tk
from UI.components.widget_top_nav_bar import TopBar
from UI.components.scrollable_messages_box import ScrollableMessageArea

from DatabaseUtils.database_messages import MessageDatabaseHandler
from DatabaseUtils.database_projects import ProjectsDatabaseHandler
from UI.window_main_chat import MainChatWindow


class ProjectChatWindow(MainChatWindow):
    def __init__(self, parent, controller, project_dictionary=None):
        self.project_dictionary = project_dictionary

        super().__init__(parent, controller)

        self.messages = self.message_db.get_project_messages(self.project_dictionary["name"])
        self.populate_chat_area(self.messages)

    def send_message(self, project_name=None):
        if self.project_dictionary:
            super().send_message(project_name=self.project_dictionary["name"])
        else:
            print("Select a project")


    def populate_chat_area(self, messages):
        """Populate the chat area with messages from the database"""
        if self.project_dictionary:
            for message in messages:
                self.scrollable_area.add_message(message['content'], message_id=message["id"] ,assigned_project=message.get('project'), project_list=[])

        else:
            self.scrollable_area.add_message("No Project Selected")