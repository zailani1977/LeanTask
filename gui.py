import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from task_db import get_connection
from task_cli_submit import submit
from task_cli_workbench import state, priority, project, title, description, tags, due
from task_sync import sync_issues

class TaskManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Task Management Dashboard")
        self.root.geometry("900x600")

        self.create_widgets()
        self.refresh_tasks()

    def create_widgets(self):
        # Top Frame for Buttons
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=10, pady=10)

        self.btn_refresh = tk.Button(top_frame, text="Refresh", command=self.refresh_tasks)
        self.btn_refresh.pack(side=tk.LEFT, padx=5)

        self.btn_submit = tk.Button(top_frame, text="Submit Task", command=self.submit_task)
        self.btn_submit.pack(side=tk.LEFT, padx=5)

        # Main Frame for Treeview
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        columns = ("ID", "Status", "Priority", "Project", "Due", "Title")
        self.tree = ttk.Treeview(main_frame, columns=columns, show="headings")

        self.tree.heading("ID", text="ID")
        self.tree.heading("Status", text="Status")
        self.tree.heading("Priority", text="Priority")
        self.tree.heading("Project", text="Project")
        self.tree.heading("Due", text="Due")
        self.tree.heading("Title", text="Title")

        self.tree.column("ID", width=100)
        self.tree.column("Status", width=100)
        self.tree.column("Priority", width=80)
        self.tree.column("Project", width=100)
        self.tree.column("Due", width=100)
        self.tree.column("Title", width=300)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<Double-1>", self.on_task_double_click)

    def refresh_tasks(self):
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            sync_issues()
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT task_id, status, priority_score, project, due_date, title FROM tasks")
            rows = cursor.fetchall()

            for row in rows:
                due_val = row[4] if row[4] else "None"
                self.tree.insert("", tk.END, values=(row[0], row[1].upper(), row[2], row[3], due_val, row[5]))

            conn.close()
        except Exception as e:
            messagebox.showerror("Error", f"Could not load tasks: {str(e)}")

    def submit_task(self):
        task_text = simpledialog.askstring("Submit Task", "Enter task details:")
        if task_text:
            try:
                submit(task_text)
                self.refresh_tasks()
            except Exception as e:
                messagebox.showerror("Error", f"Could not submit task: {str(e)}")

    def on_task_double_click(self, event):
        selection = self.tree.selection()
        if not selection:
            return
        item = selection[0]
        task_id = self.tree.item(item, "values")[0]
        self.open_task_details(task_id)

    def open_task_details(self, task_id):
        try:
            sync_issues()
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT task_id, status, priority_score, project, title, description, tags, due_date
                FROM tasks WHERE task_id = ?
            """, (task_id,))
            row = cursor.fetchone()
            conn.close()

            if not row:
                messagebox.showerror("Error", "Task not found in DB.")
                return

        except Exception as e:
            messagebox.showerror("Error", f"Could not fetch task details: {str(e)}")
            return

        details_window = tk.Toplevel(self.root)
        details_window.title(f"Task Details - {task_id}")
        details_window.geometry("500x500")

        # UI Fields
        tk.Label(details_window, text="Title:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        entry_title = tk.Entry(details_window, width=50)
        entry_title.insert(0, row[4])
        entry_title.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(details_window, text="Description:").grid(row=1, column=0, sticky=tk.NW, padx=10, pady=5)
        text_desc = tk.Text(details_window, width=37, height=5)
        text_desc.insert(tk.END, row[5])
        text_desc.grid(row=1, column=1, padx=10, pady=5)

        tk.Label(details_window, text="Status:").grid(row=2, column=0, sticky=tk.W, padx=10, pady=5)
        status_var = tk.StringVar(value=row[1])
        status_dropdown = ttk.Combobox(details_window, textvariable=status_var, values=["open", "in_progress", "blocked", "deferred", "closed"])
        status_dropdown.grid(row=2, column=1, sticky=tk.W, padx=10, pady=5)

        tk.Label(details_window, text="Priority (0.0-5.0):").grid(row=3, column=0, sticky=tk.W, padx=10, pady=5)
        entry_priority = tk.Entry(details_window, width=10)
        entry_priority.insert(0, str(row[2]))
        entry_priority.grid(row=3, column=1, sticky=tk.W, padx=10, pady=5)

        tk.Label(details_window, text="Project:").grid(row=4, column=0, sticky=tk.W, padx=10, pady=5)
        entry_project = tk.Entry(details_window, width=20)
        entry_project.insert(0, row[3])
        entry_project.grid(row=4, column=1, sticky=tk.W, padx=10, pady=5)

        tk.Label(details_window, text="Due Date:").grid(row=5, column=0, sticky=tk.W, padx=10, pady=5)
        entry_due = tk.Entry(details_window, width=20)
        due_val = row[7] if row[7] else ""
        entry_due.insert(0, due_val)
        entry_due.grid(row=5, column=1, sticky=tk.W, padx=10, pady=5)

        tk.Label(details_window, text="Tags (comma separated):").grid(row=6, column=0, sticky=tk.W, padx=10, pady=5)
        entry_tags = tk.Entry(details_window, width=30)

        # Tags are stored as a JSON string in DB, but the CLI function `tags` expects a list of strings
        tags_str = row[6]
        if tags_str.startswith('[') and tags_str.endswith(']'):
            try:
                import json
                tags_list = json.loads(tags_str)
                tags_str = ",".join(tags_list)
            except:
                pass

        entry_tags.insert(0, tags_str)
        entry_tags.grid(row=6, column=1, sticky=tk.W, padx=10, pady=5)

        def save_changes():
            try:
                if entry_title.get() != row[4]:
                    title(task_id, entry_title.get())

                new_desc = text_desc.get("1.0", tk.END).strip()
                if new_desc != row[5]:
                    description(task_id, new_desc)

                if status_var.get() != row[1]:
                    state(task_id, status_var.get())

                if entry_priority.get() != str(row[2]):
                    priority(task_id, entry_priority.get())

                if entry_project.get() != row[3]:
                    project(task_id, entry_project.get())

                if entry_due.get() != due_val:
                    due(task_id, entry_due.get())

                new_tags_str = entry_tags.get()
                if new_tags_str != tags_str:
                    tags_list = [t.strip() for t in new_tags_str.split(",") if t.strip()]
                    tags(task_id, tags_list)

                messagebox.showinfo("Success", "Task updated successfully.")
                self.refresh_tasks()
                details_window.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update task: {str(e)}")

        btn_save = tk.Button(details_window, text="Update Task", command=save_changes)
        btn_save.grid(row=7, column=1, pady=20)

if __name__ == "__main__":
    root = tk.Tk()
    app = TaskManagerApp(root)
    root.mainloop()
