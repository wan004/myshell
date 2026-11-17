import subprocess
import shutil

class WSL:
    def __init__(self, distro="Ubuntu", timeout=60):
        self.distro = distro
        self.timeout = timeout
        if not shutil.which("wsl.exe"):
            raise RuntimeError("wsl.exe was not found. This application requires Windows with WSL installed.")

    def run(self, script, cwd=None, timeout=None):
        import shlex
        prefix = f"cd -- {shlex.quote(cwd)} && " if cwd else ""
        args = ["wsl.exe", "-d", self.distro, "--", "bash", "-lc", prefix + script]
        try:
            p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=timeout or self.timeout)
            return p.stdout, p.stderr, p.returncode
        except subprocess.TimeoutExpired:
            return "", f"Command timed out after {timeout or self.timeout} seconds.", 124

    def home(self):
        out, err, code = self.run("printf '%s' \"$HOME\"")
        if code:
            raise RuntimeError(err or "Could not determine WSL home directory")
        return out.strip()

    def list_dir(self, path):
        # NUL-separated fields avoid breaking on spaces in filenames.
        script = r"""find . -mindepth 1 -maxdepth 1 -printf '%y\0%s\0%f\0'"""
        out, err, code = self.run(script, cwd=path)
        if code:
            raise RuntimeError(err.strip() or "Could not list directory")
        raw = out.split("\0")
        items = []
        for i in range(0, len(raw)-2, 3):
            kind, size, name = raw[i:i+3]
            if name:
                items.append({"type": "Directory" if kind == "d" else "File",
                              "size": int(size or 0), "name": name})
        return sorted(items, key=lambda x: (x["type"] != "Directory", x["name"].lower()))

    def read_file(self, path):
        out, err, code = self.run("cat -- " + __import__("shlex").quote(path))
        if code:
            raise RuntimeError(err.strip() or "Could not read file")
        return out

    def write_file(self, path, content):
        # Send content on stdin without interpolating it into a shell command.
        import subprocess, shlex
        args = ["wsl.exe", "-d", self.distro, "--", "bash", "-lc",
                "cat > " + shlex.quote(path)]
        p = subprocess.run(args, input=content, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=self.timeout)
        if p.returncode:
            raise RuntimeError(p.stderr.strip() or "Could not save file")

    def system_info(self):
        script = "printf 'UPTIME '; cat /proc/uptime; printf '\\nMEMORY\\n'; free -h; printf '\\nDISK\\n'; df -h /"
        return self.run(script)
