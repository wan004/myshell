import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import threading, queue, os, shlex
from pathlib import Path
from core.wsl import WSL
from core.shell import Shell
from core.history import History

class MyShellApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MyShell")
        self.geometry("1050x700")
        self.minsize(800, 520)
        self.configure(bg="#eeeeee")
        try:
            self.wsl = WSL()
            self.history = History(Path(__file__).resolve().parents[1] / "data" / "history.json")
            self.shell = Shell(self.wsl, self.history)
        except Exception as exc:
            messagebox.showerror("WSL initialization error", str(exc))
            raise
        self.results = queue.Queue()
        self.busy = False
        self.hist_index = None
        self._build()
        self.after(100, self._poll_queue)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _build(self):
        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")
        ttk.Label(top, text="MyShell", font=("Segoe UI", 16, "bold")).pack(side="left")
        ttk.Label(top, text="Ubuntu on WSL 2").pack(side="left", padx=14)
        self.status = tk.StringVar(value="Ready")
        ttk.Label(top, textvariable=self.status).pack(side="right")

        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=8, pady=(0,8))
        self.terminal_tab = ttk.Frame(self.tabs)
        self.files_tab = ttk.Frame(self.tabs)
        self.editor_tab = ttk.Frame(self.tabs)
        self.process_tab = ttk.Frame(self.tabs)
        self.monitor_tab = ttk.Frame(self.tabs)
        self.tabs.add(self.terminal_tab, text="Terminal")
        self.tabs.add(self.files_tab, text="File Manager")
        self.tabs.add(self.editor_tab, text="Text Editor")
        self.tabs.add(self.process_tab, text="Processes")
        self.tabs.add(self.monitor_tab, text="System Monitor")
        self._build_terminal()
        self._build_files()
        self._build_editor()
        self._build_processes()
        self._build_monitor()

    def _build_terminal(self):
        frame = self.terminal_tab
        self.output = tk.Text(frame, wrap="word", bg="#171717", fg="#eeeeee",
                              insertbackground="white", font=("Consolas", 11), state="disabled")
        self.output.pack(fill="both", expand=True, padx=6, pady=6)
        self.output.tag_config("prompt", foreground="#80cbc4")
        self.output.tag_config("error", foreground="#ff8a80")
        self.output.tag_config("system", foreground="#90caf9")
        bottom = ttk.Frame(frame, padding=6)
        bottom.pack(fill="x")
        self.prompt = tk.StringVar()
        self.prompt_label = ttk.Label(bottom, textvariable=self.prompt)
        self.prompt_label.pack(side="left")
        self.entry = ttk.Entry(bottom, font=("Consolas", 11))
        self.entry.pack(side="left", fill="x", expand=True, padx=6)
        self.entry.bind("<Return>", self._submit)
        self.entry.bind("<Up>", self._history_up)
        self.entry.bind("<Down>", self._history_down)
        ttk.Button(bottom, text="Run", command=self._submit).pack(side="left")
        ttk.Button(bottom, text="Clear", command=self._clear).pack(side="left", padx=(5,0))
        self._update_prompt()
        self._write("MyShell ready. Type 'help' to see built-in commands.\n", "system")
        self.entry.focus_set()

    def _update_prompt(self):
        self.prompt.set(f"{self.shell.cwd} $")

    def _write(self, text, tag=None):
        self.output.configure(state="normal")
        self.output.insert("end", text, tag)
        self.output.see("end")
        self.output.configure(state="disabled")

    def _submit(self, event=None):
        if self.busy:
            return "break"
        command = self.entry.get().strip()
        if not command:
            return "break"
        self.entry.delete(0, "end")
        self._write(f"{self.shell.cwd} $ {command}\n", "prompt")
        if command.split()[0] == "clear" and len(command.split()) == 1:
            self._clear()
            return "break"
        self.busy = True
        self.status.set("Executing...")
        self.entry.configure(state="disabled")
        threading.Thread(target=self._worker, args=(command,), daemon=True).start()
        return "break"

    def _worker(self, command):
        try:
            result = self.shell.execute(command)
            self.results.put(("command", result))
        except Exception as exc:
            self.results.put(("error", str(exc)))

    def _poll_queue(self):
        try:
            while True:
                kind, payload = self.results.get_nowait()
                if kind == "command":
                    out, err, code, should_exit = payload
                    if out:
                        self._write(out)
                        if not out.endswith("\n"): self._write("\n")
                    if err:
                        self._write(err + ("" if err.endswith("\n") else "\n"), "error")
                    if code:
                        self._write(f"[exit code: {code}]\n", "error")
                    if should_exit:
                        self.destroy()
                        return
                    self._update_prompt()
                else:
                    self._write(payload + "\n", "error")
                self.busy = False
                self.entry.configure(state="normal")
                self.entry.focus_set()
                self.status.set("Ready")
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    def _clear(self):
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.configure(state="disabled")

    def _history_up(self, event=None):
        items = self.history.items
        if not items: return "break"
        if self.hist_index is None: self.hist_index = len(items)
        self.hist_index = max(0, self.hist_index - 1)
        self.entry.delete(0, "end"); self.entry.insert(0, items[self.hist_index])
        return "break"

    def _history_down(self, event=None):
        items = self.history.items
        if self.hist_index is None: return "break"
        self.hist_index = min(len(items), self.hist_index + 1)
        self.entry.delete(0, "end")
        if self.hist_index < len(items): self.entry.insert(0, items[self.hist_index])
        else: self.hist_index = None
        return "break"

    def _build_files(self):
        bar = ttk.Frame(self.files_tab, padding=6); bar.pack(fill="x")
        self.file_path = tk.StringVar(value=self.shell.cwd)
        ttk.Entry(bar, textvariable=self.file_path).pack(side="left", fill="x", expand=True)
        ttk.Button(bar, text="Go", command=self._refresh_files).pack(side="left", padx=4)
        ttk.Button(bar, text="Up", command=self._parent_dir).pack(side="left")
        ttk.Button(bar, text="New folder", command=self._new_folder).pack(side="left", padx=4)
        ttk.Button(bar, text="New file", command=self._new_file).pack(side="left")
        ttk.Button(bar, text="Rename", command=self._rename_file).pack(side="left", padx=4)
        ttk.Button(bar, text="Delete", command=self._delete_file).pack(side="left")
        self.file_tree = ttk.Treeview(self.files_tab, columns=("type","size"), show="tree headings")
        self.file_tree.heading("#0", text="Name"); self.file_tree.heading("type", text="Type"); self.file_tree.heading("size", text="Size (bytes)")
        self.file_tree.pack(fill="both", expand=True, padx=6, pady=6)
        self.file_tree.bind("<Double-1>", self._open_selected)
        self._refresh_files()

    def _refresh_files(self):
        path = self.file_path.get().strip() or self.shell.cwd
        try:
            items = self.wsl.list_dir(path)
            self.file_path.set(path)
            self.file_tree.delete(*self.file_tree.get_children())
            for item in items:
                self.file_tree.insert("", "end", text=item["name"], values=(item["type"], item["size"]))
            self.status.set(f"{len(items)} items")
        except Exception as exc:
            messagebox.showerror("File Manager", str(exc))

    def _selected_path(self):
        selected = self.file_tree.selection()
        if not selected: return None
        name = self.file_tree.item(selected[0], "text")
        return self.file_path.get().rstrip("/") + "/" + name

    def _open_selected(self, event=None):
        path = self._selected_path()
        if not path: return
        values = self.file_tree.item(self.file_tree.selection()[0], "values")
        if values and values[0] == "Directory":
            self.file_path.set(path); self._refresh_files()
        else:
            self._load_editor(path)
            self.tabs.select(self.editor_tab)

    def _parent_dir(self):
        self.file_path.set(str(Path(self.file_path.get()).parent))
        self._refresh_files()

    def _new_folder(self):
        name = simpledialog.askstring("New folder", "Folder name:")
        if name:
            out, err, code = self.wsl.run("mkdir -- " + shlex.quote(name), cwd=self.file_path.get())
            if code: messagebox.showerror("New folder", err)
            self._refresh_files()

    def _new_file(self):
        name = simpledialog.askstring("New file", "File name:")
        if name:
            out, err, code = self.wsl.run("touch -- " + shlex.quote(name), cwd=self.file_path.get())
            if code: messagebox.showerror("New file", err)
            self._refresh_files()

    def _rename_file(self):
        old = self._selected_path()
        if not old: return
        new = simpledialog.askstring("Rename", "New name:")
        if new:
            target = self.file_path.get().rstrip("/") + "/" + new
            out, err, code = self.wsl.run("mv -- " + shlex.quote(old) + " " + shlex.quote(target))
            if code: messagebox.showerror("Rename", err)
            self._refresh_files()

    def _delete_file(self):
        path = self._selected_path()
        if path and messagebox.askyesno("Confirm delete", f"Delete this item?\n{path}"):
            out, err, code = self.wsl.run("rm -rf -- " + shlex.quote(path))
            if code: messagebox.showerror("Delete", err)
            self._refresh_files()

    def _build_editor(self):
        bar = ttk.Frame(self.editor_tab, padding=6); bar.pack(fill="x")
        self.editor_path = tk.StringVar(value="")
        ttk.Entry(bar, textvariable=self.editor_path).pack(side="left", fill="x", expand=True)
        ttk.Button(bar, text="Open", command=self._open_editor_dialog).pack(side="left", padx=4)
        ttk.Button(bar, text="Save", command=self._save_editor).pack(side="left")
        ttk.Button(bar, text="Save As", command=self._save_as).pack(side="left", padx=4)
        self.editor = tk.Text(self.editor_tab, wrap="none", undo=True, font=("Consolas", 11))
        self.editor.pack(fill="both", expand=True, padx=6, pady=6)

    def _open_editor_dialog(self):
        path = simpledialog.askstring("Open file", "Enter absolute WSL path:")
        if path: self._load_editor(path)

    def _load_editor(self, path):
        try:
            content = self.wsl.read_file(path)
            self.editor.delete("1.0", "end"); self.editor.insert("1.0", content)
            self.editor_path.set(path)
        except Exception as exc:
            messagebox.showerror("Editor", str(exc))

    def _save_editor(self):
        path = self.editor_path.get().strip()
        if not path: return self._save_as()
        try:
            self.wsl.write_file(path, self.editor.get("1.0", "end-1c"))
            self.status.set("File saved")
        except Exception as exc:
            messagebox.showerror("Save", str(exc))

    def _save_as(self):
        path = simpledialog.askstring("Save As", "Enter absolute WSL path:")
        if path:
            self.editor_path.set(path); self._save_editor()

    def _build_processes(self):
        bar = ttk.Frame(self.process_tab, padding=6); bar.pack(fill="x")
        ttk.Button(bar, text="Refresh", command=self._refresh_processes).pack(side="left")
        ttk.Button(bar, text="Terminate selected", command=self._kill_process).pack(side="left", padx=6)
        self.proc_tree = ttk.Treeview(self.process_tab, columns=("pid","user","state","command"), show="headings")
        for col, title, width in [("pid","PID",80),("user","User",100),("state","State",80),("command","Command",600)]:
            self.proc_tree.heading(col, text=title); self.proc_tree.column(col, width=width)
        self.proc_tree.pack(fill="both", expand=True, padx=6, pady=6)
        self.proc_tree["displaycolumns"] = ("pid","user","state","command")
        self._refresh_processes()

    def _refresh_processes(self):
        out, err, code = self.wsl.run("ps -eo pid=,user=,stat=,args= --sort=pid | head -n 250")
        if code:
            messagebox.showerror("Processes", err); return
        self.proc_tree.delete(*self.proc_tree.get_children())
        for line in out.splitlines():
            parts = line.strip().split(None, 3)
            if len(parts) == 4:
                self.proc_tree.insert("", "end", values=parts)

    def _kill_process(self):
        selected = self.proc_tree.selection()
        if not selected: return
        values = self.proc_tree.item(selected[0], "values")
        pid = values[0]
        if messagebox.askyesno("Terminate process", f"Send TERM to Linux process {pid}?"):
            out, err, code = self.wsl.run("kill -TERM -- " + shlex.quote(pid))
            if code: messagebox.showerror("Terminate", err)
            self._refresh_processes()

    def _build_monitor(self):
        bar = ttk.Frame(self.monitor_tab, padding=6); bar.pack(fill="x")
        ttk.Button(bar, text="Refresh metrics", command=self._refresh_monitor).pack(side="left")
        self.monitor = tk.Text(self.monitor_tab, wrap="word", font=("Consolas", 11), height=20)
        self.monitor.pack(fill="both", expand=True, padx=6, pady=6)
        self._refresh_monitor()

    def _refresh_monitor(self):
        out, err, code = self.wsl.system_info()
        self.monitor.delete("1.0", "end")
        self.monitor.insert("1.0", out if not code else err)
