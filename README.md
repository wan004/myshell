# MyShell

MyShell is a Windows Tkinter desktop application that provides a basic Linux-inspired shell interface backed by Ubuntu on WSL 2.

## Requirements
- Windows 10/11 with WSL 2
- Ubuntu distribution registered as `Ubuntu`
- Python 3.10+
- Tkinter (normally included with Windows Python)
- PyCharm or another Python IDE

## Setup
Open the project in PyCharm and install dependencies in its interpreter:

```powershell
python -m pip install -r requirements.txt
```

Run:

```powershell
python main.py
```

## Features
- Terminal with persistent `cd`, `pwd`, `clear`, `history`, `help`, `exit`
- External Linux commands through Ubuntu WSL
- Bash quoting, pipelines, command chaining and redirection for external commands
- Background-thread command execution to keep Tkinter responsive
- WSL file browser with create, rename and delete operations
- Basic WSL text editor
- Linux process listing and TERM signal
- WSL system information (uptime, memory, disk)
- Persistent command history

## Architecture
- `core/wsl.py`: WSL process and filesystem bridge
- `core/shell.py`: built-ins and shell state
- `core/history.py`: JSON command history
- `gui/main_window.py`: Tkinter views and event handling
- `main.py`: application entry point

## Notes and limitations
- External command syntax is interpreted by Bash inside WSL. This is a practical academic shell front-end, not a full independent Bash-compatible parser.
- Process IDs shown are Linux/WSL PIDs, not Windows PIDs.
- The process manager sends SIGTERM; it does not provide full job control.
- The editor is intended for text files. It loads file content into memory.
- File Manager delete is recursive; the app asks for confirmation first.
- The default WSL distribution name is `Ubuntu`. Change `WSL(distro="Ubuntu")` in `gui/main_window.py` if yours has another registered name.
- System metrics describe the WSL environment and may reflect WSL's virtualized resource view.
