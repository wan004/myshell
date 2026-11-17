import shlex
from core.wsl import WSL

class Shell:
    BUILTINS = {"help", "clear", "pwd", "cd", "history", "exit"}

    def __init__(self, wsl, history):
        self.wsl = wsl
        self.history = history
        self.cwd = wsl.home()

    def execute(self, command):
        command = command.strip()
        if not command:
            return "", "", 0, False
        self.history.add(command)

        # Built-ins are handled by the application so cd persists between commands.
        # Shell operators are left to Bash; built-ins with operators are executed by Bash.
        try:
            tokens = shlex.split(command, posix=True)
        except ValueError as e:
            return "", str(e), 2, False

        has_operators = any(op in command for op in ("|", ">", "<", "&&", "||", ";"))
        if tokens and not has_operators:
            name = tokens[0]
            args = tokens[1:]
            if name == "cd":
                target = args[0] if args else self.wsl.home()
                if target == "~":
                    target = self.wsl.home()
                elif target.startswith("~/"):
                    target = self.wsl.home().rstrip("/") + target[1:]
                if not target.startswith("/"):
                    target = self.cwd.rstrip("/") + "/" + target
                out, err, code = self.wsl.run("test -d " + shlex.quote(target), cwd=self.cwd)
                if code:
                    return "", f"cd: no such directory: {target}", 1, False
                self.cwd = target
                return "", "", 0, False
            if name == "pwd":
                return self.cwd + "\n", "", 0, False
            if name == "clear":
                return "", "", 0, False
            if name == "history":
                return "".join(f"{i+1:4}  {c}\n" for i, c in enumerate(self.history.items)), "", 0, False
            if name == "help":
                return ("MyShell built-ins: cd, pwd, clear, history, help, exit\n"
                        "External Linux commands run through Ubuntu on WSL.\n"
                        "Supports Bash quoting, pipes, &&, ||, ;, >, >>, < and 2>.\n"), "", 0, False
            if name == "exit":
                return "Closing MyShell...\n", "", 0, True

        return (*self.wsl.run(command, cwd=self.cwd), False)
