# RemainderV0

RemainderV0 is a desktop application designed to help users manage messages, notes, reminders, and projects, with AI-powered features for organization and content generation. It uses a Python backend with a `pywebview` frontend (HTML, CSS, JavaScript).

## Core Features

*   **Message Management:**
    *   Store and organize messages, notes, and ideas.
    *   Assign messages to user-defined projects.
    *   Attach images to messages.
*   **Project Organization:**
    *   Create, edit, and delete projects with custom names, descriptions, colors, and emojis.
    *   View messages filtered by project.
*   **AI Integration (Gemini Model):**
    *   **Chat:** Engage in conversations with an AI model, optionally using existing messages as context.
    *   **Message Processing:**
        *   Automatically assign messages to relevant projects.
        *   Identify messages that should become reminders.
    *   **Project Creation:** Suggest new projects based on unassigned messages.
    *   **Image Description:** Generate textual descriptions for uploaded images.
    *   **Message Selection:** Select messages relevant to a user's query.
*   **Reminders:**
    *   Set reminders for messages with specific dates and times.
    *   Support for recurring reminders (daily, weekly).
    *   Desktop notifications (macOS specific) for due reminders.
*   **Clipboard Integration (macOS specific):**
    *   Monitor the system clipboard.
    *   Automatically save copied text to a dedicated "Saved Clips" project after a configurable number of consecutive copies.
*   **Telegram Integration:**
    *   Fetch messages and attachments from a configured Telegram bot.
    *   Store fetched messages in the application's database and as JSON logs.
*   **WhatsApp Scraper Integration:**
    *   The application can trigger a utility script (`Utils/whatsapp_utils.py`) that uses Selenium to scrape messages from WhatsApp Web. The scraped messages are currently printed by the script.
*   **Image Handling:**
    *   Upload images and associate them with messages.
    *   View image descriptions generated by AI.

## Project Structure

The project is organized into the following main directories and files:

*   **`main.py`**:
    *   The main application entry point and backend server.
    *   Initializes `pywebview` and exposes the Python `Api` class to the JavaScript frontend.
    *   Handles all core logic, including database interactions, AI model calls, reminder scheduling, and clipboard monitoring.
*   **`web/`**:
    *   Contains the frontend code (HTML, CSS, JavaScript).
    *   `index.html`: Main application page.
    *   `main.js`: Core JavaScript logic for the UI.
    *   `api.js`: Facilitates communication between the JS frontend and Python backend.
    *   `pages/`: JavaScript modules for different views (main chat, project chat, projects, reminders).
    *   `components/`: Reusable UI components (e.g., model chat sidebar, reminder items, emoji picker).
    *   `style.css`: Main stylesheet.
    *   `uploads/message_images/`: In development, this directory is used to store and serve uploaded images. When bundled, images are stored in a user-specific application support directory (e.g., `~/Library/Application Support/RemainderApp/uploads/message_images`) and the frontend accesses them accordingly.
*   **`DatabaseUtils/`**:
    *   Python modules for managing SQLite database interactions.
    *   `database_messages.py`: Handles `messages.db` (stores messages, image metadata, reminders).
    *   `database_projects.py`: Handles `projects.db` (stores project details).
    *   `database_clipboard.py`: Handles `clipboard_messages.db` (stores clipboard captures).
*   **`Databases/`**:
    *   Default directory where SQLite database files (`messages.db`, `projects.db`, `clipboard_messages.db`) are stored during development. When bundled as an application, these are typically stored in the user's application support directory (e.g., `~/Library/Application Support/RemainderApp/Databases` on macOS).
*   **`Utils/`**:
    *   Contains various utility modules:
        *   `model_handler.py`: Interface for interacting with the Gemini AI model, including prompt management and context window handling.
        *   `clipboard_monitor.py`: macOS-specific clipboard monitoring service.
        *   `prompts.py`: Defines system prompts used for AI model interactions.
        *   `reminder_scheduler.py`: Manages scheduling and triggering of reminders with desktop notifications.
        *   `telegram_utils.py`: Script/module to fetch messages from a Telegram bot.
        *   `whatsapp_utils.py`: Selenium-based script to scrape WhatsApp messages.
        *   `reminder_manager.py`: An older/alternative script for reminder checking.
*   **`API_keys/`**:
    *   Intended to store API keys, specifically `gemini_api_key.json` for the Gemini model. This directory and its contents should be in `.gitignore`.
*   **`settings.json`**:
    *   Stores application settings, such as clipboard save count and image description preferences.
*   **Standalone Utility Scripts:**
    *   `show_image_descriptions.py`: CLI tool to display image descriptions from the database.
    *   `clean_descriptions.py`: CLI tool to clean up or clear image descriptions in the database.
    *   `testing.py`: Development script, e.g., for dropping database tables.
*   **`telegram_logs/`**:
    *   Directory used by `telegram_utils.py` to store downloaded attachments and `messages.json` log.
*   **`chrome-data/`**:
    *   User data directory for Chrome/Selenium when using the WhatsApp scraper.
*   **`.env`**:
    *   Used by `telegram_utils.py` to load `BOT_TOKEN`. Should be in `.gitignore`.
*   **`RemainderApp.spec`**:
    *   PyInstaller specification file for building a distributable application.
*   **`UI/`**:
    *   Appears to contain legacy Tkinter-based UI code, which has been replaced by the `web/` frontend.

## Setup and Running

(Instructions for setup would typically go here, e.g., Python version, dependencies, environment variables, running the app)

### Prerequisites
*   Python 3.x
*   Access to a Gemini API key (store in `API_keys/gemini_api_key.json`)
*   For Telegram integration: A Telegram Bot Token (set in `.env` or as an environment variable `BOT_TOKEN`)
*   For WhatsApp scraping: Google Chrome installed.
*   For macOS notifications and clipboard monitoring: Running on macOS.

### Installation
1.  Clone the repository.
2.  Install Python dependencies:
    ```bash
    pip install -r requirements.txt 
    # (Note: A requirements.txt file needs to be generated for this command)
    # Common dependencies likely include: pywebview, google-generativeai, requests, python-dotenv, AppKit (via pyobjc for macOS), selenium, python-dateutil
    ```
3.  Set up API keys:
    *   Create `API_keys/gemini_api_key.json` with your Gemini API key.
    *   Create `.env` file in the root directory with `BOT_TOKEN=<your_telegram_bot_token>`.

### Running the Application
```bash
python main.py
```

## Building
The application can be bundled into a standalone executable using PyInstaller with the `RemainderApp.spec` file.
```bash
pyinstaller RemainderApp.spec
```

## Key Technologies
*   **Backend:** Python
*   **Frontend:** HTML, CSS, JavaScript
*   **GUI Framework:** `pywebview`
*   **AI Model:** Google Gemini
*   **Database:** SQLite
*   **macOS specific features:** `AppKit` (for clipboard and status bar) and `osascript` (for notifications)
*   **Web Scraping:** Selenium (for WhatsApp)

## Future Considerations / TODOs
*   Generate `requirements.txt`.
*   Review and potentially remove legacy code in the `UI/` directory.
*   Improve WhatsApp scraping integration for direct data return to the app instead of console output.
*   Consider cross-platform solutions for notifications and clipboard if broader OS support is desired.
*   Add more robust error handling and logging.
*   Implement user authentication if needed.
*   Expand test coverage. 
