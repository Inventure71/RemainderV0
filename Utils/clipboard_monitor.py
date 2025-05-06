import AppKit
import objc # PyObjC bridge
import threading
import time
import sys
import uuid
import os # Keep for potential path ops if ever needed, though RUMPS_RESOURCES is gone
from Foundation import NSString  # <-- Add this import

# Attempt to import CLIPBOARD_PROJECT_NAME from main.py
try:
    from main import CLIPBOARD_PROJECT_NAME
except ImportError:
    CLIPBOARD_PROJECT_NAME = "Saved Clips" 
    print("[ClipboardManager] Warning: Could not import CLIPBOARD_PROJECT_NAME from main.py, using fallback.")

# Maximum size of clipboard text to process (in characters) to prevent performance issues.
MAX_CLIPBOARD_TEXT_SIZE = 1 * 1024 * 1024 # 1MB of characters (approx)

class ClipboardManager(AppKit.NSObject):
    # Explicitly define Objective-C instance variables if needed for outlets, not strictly necessary here
    # _api_client = objc.ivar() # Example, not used as outlet here
    # _status_item = objc.ivar() # etc.

    def init(self):
        self = objc.super(ClipboardManager, self).init()
        if self is None:
            return None

        self._api_client = None
        self._clipboard = AppKit.NSPasteboard.generalPasteboard()
        self._last_clipboard_content = ""
        self._consecutive_copies = 0
        self._last_change_count = self._clipboard.changeCount()
        
        self._status_item = None
        self._menu = None
        self._polling_thread = None
        self._is_running = False
        
        self._saved_notification_active = False
        self._saved_notification_time = 0
        self._clipboard_project_name_internal = CLIPBOARD_PROJECT_NAME
        
        return self

    # Setter for api_client, as it's not passed in init for NSObject subclass pattern
    def setApiClient_(self, client):
        self._api_client = client

    def setClipboardProjectName_(self, name_str):
        self._clipboard_project_name_internal = name_str

    # Renamed and made an ObjC method for performSelectorOnMainThread
    def _updateStatusItemTitle_(self, title_string_ns):
        if self._status_item:
            self._status_item.button().setTitle_(title_string_ns)

    @objc.python_method
    def _dispatch_title_update(self, new_title_py_str):
        ns_title = NSString.stringWithString_(str(new_title_py_str))  # <-- Use NSString
        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            b'_updateStatusItemTitle:',
            ns_title,
            False
        )

    @objc.python_method
    def check_clipboard_and_update(self):
        current_title = self._status_item.button().title() if self._status_item else "📋"
        
        if self._saved_notification_active and (time.time() - self._saved_notification_time > 1.5):
            self._dispatch_title_update("📋")
            self._saved_notification_active = False
            current_title = "📋" # Assume title changed

        current_change_count = self._clipboard.changeCount()
        new_title_to_set = None

        if current_change_count != self._last_change_count:
            self._last_change_count = current_change_count
            copied_items = self._clipboard.pasteboardItems()
            if not copied_items:
                return

            available_types = copied_items[0].types()
            
            # Prefer plain text if available
            text_priority_types = [AppKit.NSPasteboardTypeString, AppKit.NSPasteboardTypeRTF, AppKit.NSPasteboardTypeHTML]
            copied_text_ns = None
            actual_type_read = None

            for item_type in text_priority_types:
                if available_types.containsObject_(item_type):
                    text_candidate_ns = copied_items[0].stringForType_(item_type)
                    if text_candidate_ns:
                        copied_text_ns = text_candidate_ns
                        actual_type_read = item_type
                        # print(f"[ClipboardManager] Read clipboard as type: {actual_type_read}")
                        break
            
            if copied_text_ns is not None:
                copied_text_py = str(copied_text_ns) # Convert to Python string for logic

                if not copied_text_py.strip(): # Ignore if content is only whitespace
                    # print("[ClipboardManager] Clipboard content is whitespace, ignoring.")
                    if self._consecutive_copies > 0 : # Reset sequence if it was active
                         self._consecutive_copies = 0
                         self._last_clipboard_content = f"_whitespace_{uuid.uuid4()}_" # Break sequence
                         if not self._saved_notification_active and current_title != "📋":
                             new_title_to_set = "📋"
                    # Do not proceed further with whitespace-only content for saving
                    if new_title_to_set: self._dispatch_title_update(new_title_to_set)
                    return

                if len(copied_text_py) > MAX_CLIPBOARD_TEXT_SIZE:
                    # print(f"[ClipboardManager] Clipboard text too large ({len(copied_text_py)} chars), truncating.")
                    copied_text_py = copied_text_py[:MAX_CLIPBOARD_TEXT_SIZE] + "... (truncated)"
                
                if copied_text_py == self._last_clipboard_content:
                    self._consecutive_copies += 1
                else:
                    self._last_clipboard_content = copied_text_py
                    self._consecutive_copies = 1
                
                if 0 < self._consecutive_copies < 5:
                    new_title_to_set = str(5 - self._consecutive_copies)
                    self._saved_notification_active = False
                elif self._consecutive_copies == 5:
                    new_title_to_set = "✔"
                    self._saved_notification_active = True
                    self._saved_notification_time = time.time()
                    try:
                        if self._api_client:
                            # Changed to call a new specific API method for clipboard entries
                            self._api_client.add_clipboard_entry(content=self._last_clipboard_content)
                            print(f"[ClipboardManager] Saved to '{self._clipboard_project_name_internal}' (via add_clipboard_entry): {self._last_clipboard_content[:60].replace(os.linesep, ' ')}...")
                        else:
                            print("[ClipboardManager] ERROR: API client not set, cannot save message.")
                    except Exception as e:
                        print(f"[ClipboardManager] Error saving message: {e}")
                        # Could dispatch a system notification here if desired
                    self._consecutive_copies = 0 
                    self._last_clipboard_content = f"_saved_{uuid.uuid4()}_" # Make unique
                else: # consecutive_copies is 0 or content changed
                    if not self._saved_notification_active:
                        new_title_to_set = "📋"
            else: # Clipboard content is not text we can handle or is empty
                if self._last_clipboard_content != "": # If there was text before, reset
                    self._last_clipboard_content = ""
                    self._consecutive_copies = 0
                    if not self._saved_notification_active:
                         new_title_to_set = "📋"
        
        elif self._consecutive_copies == 0 and not self._saved_notification_active and current_title != "📋":
             new_title_to_set = "📋"

        if new_title_to_set is not None and new_title_to_set != current_title :
            self._dispatch_title_update(new_title_to_set)


    @objc.python_method
    def _polling_loop(self):
        self._is_running = True
        print("[ClipboardManager] Polling loop started.")
        while self._is_running:
            try:
                self.check_clipboard_and_update()
            except Exception as e:
                print(f"[ClipboardManager] Error in polling loop: {e}")
                import traceback
                traceback.print_exc() # Print full traceback for debugging
            time.sleep(1)
        print("[ClipboardManager] Polling loop stopped.")

    # This method will be scheduled to run on the main thread shortly after app init.
    @objc.IBAction # Making it an IBAction for ObjC visibility, argument is typical for performSelector:withObject:afterDelay:
    def setupUIAndStartPollingAction_(self, sender_or_nil_object):
        if not self._api_client:
            print("[ClipboardManager] Deferred setup: API Client not set. Cannot start.")
            return
        print("[ClipboardManager] Deferred UI setup: Initializing status bar item...")
        self._status_item = AppKit.NSStatusBar.systemStatusBar().statusItemWithLength_(AppKit.NSVariableStatusItemLength)
        self._status_item.button().setTitle_("📋")
        self._menu = AppKit.NSMenu.alloc().init()
        quit_menu_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Stop Clipboard Helper", self.requestStop_, ""
        )
        quit_menu_item.setTarget_(self)
        self._menu.addItem_(quit_menu_item)
        self._status_item.setMenu_(self._menu)
        self._polling_thread = threading.Thread(target=self._polling_loop, daemon=True)
        self._is_running = True
        self._polling_thread.start()
        print("[ClipboardManager] Deferred UI setup: Status bar initialized and polling thread started.")

    @objc.python_method
    def trigger_deferred_ui_setup(self):
        # Called from initialize_clipboard_manager on the main thread.
        # Schedules the actual UI setup.
        self.performSelector_withObject_afterDelay_(
            b'setupUIAndStartPollingAction:', # Correct selector format
            None, 
            0.0 # Delay of 0.0 schedules it for the next run loop iteration
        )
        print("[ClipboardManager] UI setup has been scheduled for deferred execution.")

    @objc.IBAction
    def requestStop_(self, sender):
        print("[ClipboardManager] Stop action triggered from menu.")
        self._is_running = False
        if self._polling_thread and self._polling_thread.is_alive():
            print("[ClipboardManager] Waiting for polling thread to join...")
            self._polling_thread.join(timeout=2.5)
            if self._polling_thread.is_alive():
                 print("[ClipboardManager] Polling thread did not join in time.")
        if self._status_item:
            AppKit.NSStatusBar.systemStatusBar().removeStatusItem_(self._status_item)
            self._status_item = None
            print("[ClipboardManager] Status item removed.")
        global _the_clipboard_manager_instance
        if _the_clipboard_manager_instance is self:
            _the_clipboard_manager_instance = None
            print("[ClipboardManager] Global instance cleared.")


# --- Global instance and setup function for main.py ---
_the_clipboard_manager_instance = None

def initialize_clipboard_manager(api_client_instance):
    global _the_clipboard_manager_instance
    if sys.platform == 'darwin':
        if _the_clipboard_manager_instance is not None:
            print("[ClipboardManager] Already initialized.")
            return _the_clipboard_manager_instance
        try:
            print("[ClipboardManager] Allocating and initializing manager object...")
            _the_clipboard_manager_instance = ClipboardManager.alloc().init()
            _the_clipboard_manager_instance.setApiClient_(api_client_instance)
            _the_clipboard_manager_instance.setClipboardProjectName_(CLIPBOARD_PROJECT_NAME)
            _the_clipboard_manager_instance.trigger_deferred_ui_setup() # This will schedule the UI parts
        except Exception as e:
            print(f"[ClipboardManager] Failed to initialize: {e}")
            import traceback
            traceback.print_exc()
            _the_clipboard_manager_instance = None
    else:
        print("[ClipboardManager] Not on macOS, clipboard manager will not start.")
    return _the_clipboard_manager_instance

def shutdown_clipboard_manager():
    global _the_clipboard_manager_instance
    if _the_clipboard_manager_instance:
        print("[ClipboardManager] Shutting down...")
        _the_clipboard_manager_instance.requestStop_(None)
        _the_clipboard_manager_instance = None 