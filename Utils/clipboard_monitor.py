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
    _consecutive_copies_needed: int

    def initWithAPIClient_consecutiveCopiesNeeded_(self, api_client_instance, copies_needed: int):
        self = objc.super(ClipboardManager, self).init()
        if self is None: return None

        self._api_client = api_client_instance
        self._consecutive_copies_needed = int(copies_needed) # Use the passed value
        self._last_clipboard_content = None
        self._consecutive_copy_count = 0
        self._statusItem = None
        self._mainMenu = None
        self._timer = None
        self._should_stop = False
        self._last_saved_content_to_prevent_rapid_resave = None
        
        # Attributes for managing the 'saved' (✔) notification state
        self._saved_notification_active = False
        self._saved_notification_time = 0

        # Attribute for clipboard access (should be initialized here)
        self._clipboard = AppKit.NSPasteboard.generalPasteboard()
        self._last_change_count = self._clipboard.changeCount()
        
        print(f"[ClipboardManager] Initialized. Consecutive copies needed to save: {self._consecutive_copies_needed}")

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
                # If pasteboard became empty, reset state
                if self._last_clipboard_content is not None: # If there was content before
                    self._last_clipboard_content = None
                    self._consecutive_copy_count = 0
                    if not self._saved_notification_active: new_title_to_set = "📋"
                if new_title_to_set: self._dispatch_title_update(new_title_to_set)
                return

            available_types = copied_items[0].types()
            
            # --- Enhanced Type Detection & Logging for WhatsApp Issue ---
            # Log all available types for debugging clipboard issues
            print(f"[ClipboardManager] Available pasteboard types: {list(available_types)}")
            # --- End Enhanced Type Detection ---

            text_priority_types = [AppKit.NSPasteboardTypeString, AppKit.NSPasteboardTypeRTF, AppKit.NSPasteboardTypeHTML]
            copied_text_ns = None
            
            for item_type in text_priority_types:
                if available_types.containsObject_(item_type):
                    text_candidate_ns = copied_items[0].stringForType_(item_type)
                    if text_candidate_ns:
                        copied_text_ns = text_candidate_ns
                        break
            
            if copied_text_ns is not None:
                copied_text_py = str(copied_text_ns)

                if not copied_text_py.strip():
                    if self._consecutive_copy_count > 0:
                         self._consecutive_copy_count = 0
                         self._last_clipboard_content = f"_whitespace_{uuid.uuid4()}_"
                         if not self._saved_notification_active and current_title != "📋":
                             new_title_to_set = "📋"
                    if new_title_to_set: self._dispatch_title_update(new_title_to_set)
                    return

                if len(copied_text_py) > MAX_CLIPBOARD_TEXT_SIZE:
                    copied_text_py = copied_text_py[:MAX_CLIPBOARD_TEXT_SIZE] + "... (truncated)"
                
                if copied_text_py == self._last_clipboard_content:
                    self._consecutive_copy_count += 1
                else:
                    self._last_clipboard_content = copied_text_py
                    self._consecutive_copy_count = 1 # Start new sequence
                
                # Logic for title update and saving, now using self._consecutive_copies_needed
                if self._consecutive_copy_count >= self._consecutive_copies_needed:
                    if copied_text_py != self._last_saved_content_to_prevent_rapid_resave:
                        new_title_to_set = "✔" # Saved!
                        self._saved_notification_active = True
                        self._saved_notification_time = time.time()
                        print(f"[ClipboardManager] {self._consecutive_copies_needed} consecutive copies of '{copied_text_py[:50].replace(os.linesep, ' ')}...' detected. Saving.")
                        if self._api_client:
                            try:
                                self._api_client.add_clipboard_entry(content=copied_text_py)
                                self._last_saved_content_to_prevent_rapid_resave = copied_text_py
                            except Exception as e:
                                print(f"[ClipboardManager] Error calling add_clipboard_entry: {e}")
                        self._consecutive_copy_count = 0 # Reset after saving
                        self._last_clipboard_content = f"_saved_{uuid.uuid4()}_" # Ensure next copy is different
                    else:
                        # Content was just saved, show ✔ briefly then reset.
                        # Don't re-save, but do acknowledge the threshold was met.
                        new_title_to_set = "✔" 
                        self._saved_notification_active = True # Keep ✔ for a bit
                        self._saved_notification_time = time.time()
                        print(f"[ClipboardManager] Content '{copied_text_py[:50].replace(os.linesep, ' ')}...' was just saved. Threshold met again, but skipping duplicate save.")
                        # Important: Reset count to prevent immediate re-trigger if user copies again.
                        self._consecutive_copy_count = 0 
                        self._last_clipboard_content = f"_saved_{uuid.uuid4()}_" 
                
                elif self._consecutive_copy_count > 0 : # In a sequence, but not yet enough to save
                    remaining_to_save = self._consecutive_copies_needed - self._consecutive_copy_count
                    new_title_to_set = str(remaining_to_save)
                    self._saved_notification_active = False
                else: # _consecutive_copy_count is 0 (e.g., after a save or a clear)
                     if not self._saved_notification_active: # If not in the 'saved ✔' state
                        new_title_to_set = "📋"

            else: # Clipboard content is not text we can handle or is empty
                if self._last_clipboard_content is not None: # If there was content before
                    self._last_clipboard_content = None
                    self._consecutive_copy_count = 0
                    if not self._saved_notification_active: new_title_to_set = "📋"
        
        elif self._consecutive_copy_count == 0 and not self._saved_notification_active and current_title != "📋":
            # This case handles when polling continues but clipboard hasn't changed
            # and we are not in a save cycle or recently saved notification.
            # Ensure title is the default if no sequence is active.
            new_title_to_set = "📋"

        if new_title_to_set is not None and new_title_to_set != current_title:
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

def initialize_clipboard_manager(api_client, consecutive_copies_needed):
    global _the_clipboard_manager_instance
    if sys.platform == 'darwin':
        if _the_clipboard_manager_instance is not None:
            print("[ClipboardManager] Already initialized.")
            return _the_clipboard_manager_instance
        try:
            print("[ClipboardManager] Allocating and initializing manager object...")
            _the_clipboard_manager_instance = ClipboardManager.alloc().initWithAPIClient_consecutiveCopiesNeeded_(api_client, consecutive_copies_needed)
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