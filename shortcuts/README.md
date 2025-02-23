Desktop Shortcut Creator
==========================

This tool creates a desktop shortcut for a given Python script on Windows, macOS, and Linux (Ubuntu) using a single codebase. It leverages the pyshortcuts library to handle cross-platform shortcut creation and Typer for a clean command-line interface.

Requirements
------------
- Python 3.6+
- The dependencies listed in requirements.txt

Installation
------------
1. Clone or download the repository.

2. Install dependencies by running:
   pip install -r requirements.txt

Usage
-----
Run the create_shortcut.py script with the following arguments:

   python create_shortcut.py <SCRIPT_PATH> <APP_NAME> [ICON_PATH] [--terminal / -t]

Arguments:
- <SCRIPT_PATH>: Full path to the Python script for which you want to create a shortcut.
- <APP_NAME>: The name you want to give to the desktop shortcut.
- [ICON_PATH]: (Optional) Full path to an icon file (e.g., PNG or ICO) to be used for the shortcut.
- --terminal or -t: (Optional) Boolean flag to run the script in a terminal. Defaults to True.
   Set it to False if your application is a GUI app.

Examples:
---------
1. With an icon:
   python create_shortcut.py /path/to/your/script.py "My App" /path/to/your/icon.png

2. Without an icon:
   python create_shortcut.py /path/to/your/script.py "My App"

3. Specifying no terminal (for a GUI application):
   python create_shortcut.py /path/to/your/script.py "My App" /path/to/your/icon.png --terminal False

Troubleshooting
---------------
- Permission Issues:
  If you encounter permission errors (e.g., when removing or creating files on your Desktop),
  ensure that you have the necessary rights to modify the desktop directory or try deleting any
  existing conflicting shortcuts manually.

- Icon Not Found:
  If the provided icon path is incorrect, the script will warn you and create the shortcut without an icon.

License
-------
This project is provided as-is under the MIT License.

