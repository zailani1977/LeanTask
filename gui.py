import tkinter as tk
import customtkinter as ctk
from tkinter import ttk, messagebox, simpledialog
from task_db import get_connection
from task_cli_submit import submit
from task_cli_workbench import state, priority, project, title, description, tags, due, comment, archive_tasks
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
        top_frame = ctk.CTkFrame(self.root)
        top_frame.pack(fill=tk.X, padx=10, pady=10)

        self.btn_refresh = ctk.CTkButton(top_frame, text="Refresh", command=self.refresh_tasks)
        self.btn_refresh.pack(side=tk.LEFT, padx=5)

        self.btn_submit = ctk.CTkButton(top_frame, text="Submit Task", command=self.submit_task)

        self.btn_submit.pack(side=tk.LEFT, padx=5)

        self.btn_archive = ctk.CTkButton(top_frame, text="Archive", command=self.archive_and_refresh)
        self.btn_archive.pack(side=tk.LEFT, padx=5)

        self.btn_view_archive = ctk.CTkButton(top_frame, text="View Archive", command=self.open_view_archive)
        self.btn_view_archive.pack(side=tk.LEFT, padx=5)


        # Main Frame for Treeview
        main_frame = ctk.CTkFrame(self.root)
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

        self.tree.tag_configure("open", background="#d4edda", foreground="black")
        self.tree.tag_configure("in_progress", background="#cce5ff", foreground="black")
        self.tree.tag_configure("blocked", background="#f8d7da", foreground="black")
        self.tree.tag_configure("deferred", background="#fff3cd", foreground="black")
        self.tree.tag_configure("closed", background="#e2e3e5", foreground="black")

        self.tree.bind("<Double-1>", self.on_task_double_click)


    def archive_and_refresh(self):
        try:
            count = archive_tasks()
            messagebox.showinfo("Archive", f"Successfully archived {count} tasks.")
            self.refresh_tasks()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to archive tasks: {str(e)}")


    def open_view_archive(self):
        archive_window = ctk.CTkToplevel(self.root)
        archive_window.title("Archived Tasks")
        archive_window.geometry("900x600")

        main_frame = ctk.CTkFrame(archive_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        columns = ("ID", "Status", "Priority", "Project", "Due", "Title")
        self.archive_tree = ttk.Treeview(main_frame, columns=columns, show="headings")

        self.archive_tree.heading("ID", text="ID")
        self.archive_tree.heading("Status", text="Status")
        self.archive_tree.heading("Priority", text="Priority")
        self.archive_tree.heading("Project", text="Project")
        self.archive_tree.heading("Due", text="Due")
        self.archive_tree.heading("Title", text="Title")

        self.archive_tree.column("ID", width=100)
        self.archive_tree.column("Status", width=100)
        self.archive_tree.column("Priority", width=80)
        self.archive_tree.column("Project", width=120)
        self.archive_tree.column("Due", width=100)
        self.archive_tree.column("Title", width=350)

        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.archive_tree.yview)
        self.archive_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.archive_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.archive_tree.bind("<Double-1>", self.on_archived_task_double_click)

        self.refresh_archive_tasks()

    def refresh_archive_tasks(self):
        for item in self.archive_tree.get_children():
            self.archive_tree.delete(item)

        try:
            import os
            import json
            ARCHIVE_FILE = ".tasks/archive.jsonl"
            if not os.path.exists(ARCHIVE_FILE):
                return

            with open(ARCHIVE_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip(): continue
                    task = json.loads(line)
                    due_val = task.get("due_date") if task.get("due_date") else "None"
                    status_tag = task.get("status", "").lower()
                    self.archive_tree.insert("", tk.END, values=(task.get("task_id"), task.get("status", "").upper(), task.get("priority_score"), task.get("project"), due_val, task.get("title")), tags=(status_tag,))

        except Exception as e:
            messagebox.showerror("Error", f"Could not load archived tasks: {str(e)}")


    def on_archived_task_double_click(self, event):
        selection = self.archive_tree.selection()
        if not selection:
            return
        item = selection[0]
        task_id = self.archive_tree.item(item, "values")[0]
        self.open_archived_task_details(task_id)

    def open_archived_task_details(self, task_id):
        import os
        import json
        ARCHIVE_FILE = ".tasks/archive.jsonl"
        found_task = None

        try:
            with open(ARCHIVE_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip(): continue
                    task = json.loads(line)
                    if task.get("task_id") == task_id:
                        found_task = task
                        break
        except Exception as e:
            messagebox.showerror("Error", f"Could not fetch archived task details: {str(e)}")
            return

        if not found_task:
            messagebox.showerror("Error", "Archived task not found.")
            return

        details_window = ctk.CTkToplevel(self.root)
        details_window.title(f"Archived Task Details - {task_id}")
        details_window.geometry("600x750")

        # UI Fields - Read Only
        ctk.CTkLabel(details_window, text="Title:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        entry_title = ctk.CTkEntry(details_window, width=300)
        entry_title.insert(0, found_task.get("title", ""))
        entry_title.configure(state="disabled")
        entry_title.grid(row=0, column=1, padx=10, pady=5)

        ctk.CTkLabel(details_window, text="Description:").grid(row=1, column=0, sticky=tk.NW, padx=10, pady=5)
        text_desc = ctk.CTkTextbox(details_window, width=300, height=80)
        text_desc.insert(tk.END, found_task.get("description", ""))
        text_desc.configure(state="disabled")
        text_desc.grid(row=1, column=1, padx=10, pady=5)

        ctk.CTkLabel(details_window, text="Status:").grid(row=2, column=0, sticky=tk.W, padx=10, pady=5)
        entry_status = ctk.CTkEntry(details_window, width=150)
        entry_status.insert(0, found_task.get("status", ""))
        entry_status.configure(state="disabled")
        entry_status.grid(row=2, column=1, sticky=tk.W, padx=10, pady=5)

        ctk.CTkLabel(details_window, text="Priority:").grid(row=3, column=0, sticky=tk.W, padx=10, pady=5)
        entry_priority = ctk.CTkEntry(details_window, width=60)
        entry_priority.insert(0, str(found_task.get("priority_score", "")))
        entry_priority.configure(state="disabled")
        entry_priority.grid(row=3, column=1, sticky=tk.W, padx=10, pady=5)

        ctk.CTkLabel(details_window, text="Project:").grid(row=4, column=0, sticky=tk.W, padx=10, pady=5)
        entry_project = ctk.CTkEntry(details_window, width=150)
        entry_project.insert(0, found_task.get("project", ""))
        entry_project.configure(state="disabled")
        entry_project.grid(row=4, column=1, sticky=tk.W, padx=10, pady=5)

        ctk.CTkLabel(details_window, text="Due Date:").grid(row=5, column=0, sticky=tk.W, padx=10, pady=5)
        entry_due = ctk.CTkEntry(details_window, width=150)
        due_val = found_task.get("due_date") if found_task.get("due_date") else ""
        entry_due.insert(0, due_val)
        entry_due.configure(state="disabled")
        entry_due.grid(row=5, column=1, sticky=tk.W, padx=10, pady=5)

        ctk.CTkLabel(details_window, text="Tags:").grid(row=6, column=0, sticky=tk.W, padx=10, pady=5)
        entry_tags = ctk.CTkEntry(details_window, width=200)
        tags_list = found_task.get("tags", [])
        entry_tags.insert(0, ",".join(tags_list))
        entry_tags.configure(state="disabled")
        entry_tags.grid(row=6, column=1, sticky=tk.W, padx=10, pady=5)

        # --- Comments Section ---
        ctk.CTkLabel(details_window, text="Comments:").grid(row=8, column=0, sticky=tk.NW, padx=10, pady=5)

        comments_listbox = ctk.CTkTextbox(details_window, width=300, height=120)
        comments_listbox.grid(row=8, column=1, sticky=tk.W, padx=10, pady=5)

        comments = found_task.get("comments", [])
        for c in comments:
            display_text = f"[{c.get('timestamp')[:10]}] {c.get('author')}: {c.get('text')}"
            comments_listbox.insert("end", display_text + "\n")
        comments_listbox.configure(state="disabled")



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
                status_tag = row[1].lower()
                self.tree.insert("", tk.END, values=(row[0], row[1].upper(), row[2], row[3], due_val, row[5]), tags=(status_tag,))

            conn.close()
        except Exception as e:
            messagebox.showerror("Error", f"Could not load tasks: {str(e)}")

    def submit_task(self):
        submit_window = ctk.CTkToplevel(self.root)
        submit_window.title("Submit Task")
        submit_window.geometry("400x300")

        ctk.CTkLabel(submit_window, text="Title:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        entry_title = ctk.CTkEntry(submit_window, width=250)
        entry_title.grid(row=0, column=1, padx=10, pady=5)

        ctk.CTkLabel(submit_window, text="Description (Optional):").grid(row=1, column=0, sticky=tk.NW, padx=10, pady=5)
        text_desc = ctk.CTkTextbox(submit_window, width=250, height=80)
        text_desc.grid(row=1, column=1, padx=10, pady=5)

        ctk.CTkLabel(submit_window, text="Due Date (Optional):").grid(row=2, column=0, sticky=tk.W, padx=10, pady=5)
        entry_due = ctk.CTkEntry(submit_window, width=250)
        entry_due.grid(row=2, column=1, padx=10, pady=5)

        submit_window.transient(self.root)
        submit_window.wait_visibility()
        submit_window.grab_set() # Make it modal

        def on_submit():
            title_text = entry_title.get().strip()
            if not title_text:
                messagebox.showerror("Error", "Title is required.")
                return

            try:
                task_id = submit(title_text)
            except Exception as e:
                messagebox.showerror("Error", f"Could not submit task: {str(e)}")
                return

            try:
                desc_text = text_desc.get("1.0", "end").strip()
                due_text = entry_due.get().strip()

                if desc_text:
                    description(task_id, desc_text)
                if due_text:
                    due(task_id, due_text)

                self.refresh_tasks()
                submit_window.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Task created but could not apply optional fields: {str(e)}")
                self.refresh_tasks()
                submit_window.destroy()

        btn_submit = ctk.CTkButton(submit_window, text="Submit", command=on_submit)
        btn_submit.grid(row=3, column=1, pady=20)

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

        details_window = ctk.CTkToplevel(self.root)
        details_window.title(f"Task Details - {task_id}")
        details_window.geometry("600x750")

        # UI Fields
        ctk.CTkLabel(details_window, text="Title:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        entry_title = ctk.CTkEntry(details_window, width=300)
        entry_title.insert(0, row[4])
        entry_title.grid(row=0, column=1, padx=10, pady=5)

        ctk.CTkLabel(details_window, text="Description:").grid(row=1, column=0, sticky=tk.NW, padx=10, pady=5)
        text_desc = ctk.CTkTextbox(details_window, width=300, height=80)
        text_desc.insert(tk.END, row[5])
        text_desc.grid(row=1, column=1, padx=10, pady=5)

        ctk.CTkLabel(details_window, text="Status:").grid(row=2, column=0, sticky=tk.W, padx=10, pady=5)
        status_var = tk.StringVar(value=row[1])
        status_dropdown = ctk.CTkComboBox(details_window, variable=status_var, values=["open", "in_progress", "blocked", "deferred", "closed"])
        status_dropdown.grid(row=2, column=1, sticky=tk.W, padx=10, pady=5)

        ctk.CTkLabel(details_window, text="Priority (0.0-5.0):").grid(row=3, column=0, sticky=tk.W, padx=10, pady=5)
        entry_priority = ctk.CTkEntry(details_window, width=60)
        entry_priority.insert(0, str(row[2]))
        entry_priority.grid(row=3, column=1, sticky=tk.W, padx=10, pady=5)

        ctk.CTkLabel(details_window, text="Project:").grid(row=4, column=0, sticky=tk.W, padx=10, pady=5)
        entry_project = ctk.CTkEntry(details_window, width=150)
        entry_project.insert(0, row[3])
        entry_project.grid(row=4, column=1, sticky=tk.W, padx=10, pady=5)

        ctk.CTkLabel(details_window, text="Due Date:").grid(row=5, column=0, sticky=tk.W, padx=10, pady=5)
        entry_due = ctk.CTkEntry(details_window, width=150)
        due_val = row[7] if row[7] else ""
        entry_due.insert(0, due_val)
        entry_due.grid(row=5, column=1, sticky=tk.W, padx=10, pady=5)

        ctk.CTkLabel(details_window, text="Tags (comma separated):").grid(row=6, column=0, sticky=tk.W, padx=10, pady=5)
        entry_tags = ctk.CTkEntry(details_window, width=200)

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

                new_desc = text_desc.get("0.0", "end").strip()
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

        btn_save = ctk.CTkButton(details_window, text="Update Task", command=save_changes)
        btn_save.grid(row=7, column=1, pady=20)

        # --- Comments Section ---
        ctk.CTkLabel(details_window, text="Comments:").grid(row=8, column=0, sticky=tk.NW, padx=10, pady=5)

        comments_listbox = ctk.CTkTextbox(details_window, width=300, height=120)
        comments_listbox.grid(row=8, column=1, sticky=tk.W, padx=10, pady=5)

        def load_comments():
            comments_listbox.delete("0.0", "end")
            try:
                # Sync might be needed if comments were added externally or just now
                sync_issues()
                c_conn = get_connection()
                c_cursor = c_conn.cursor()
                c_cursor.execute("SELECT timestamp, author, text FROM task_comments WHERE task_id = ? ORDER BY timestamp ASC", (task_id,))
                c_rows = c_cursor.fetchall()
                for cr in c_rows:
                    display_text = f"[{cr[0][:10]}] {cr[1]}: {cr[2]}"
                    comments_listbox.insert("end", display_text + "\n")
                c_conn.close()
            except Exception as e:
                print(f"Error loading comments: {e}")

        load_comments()

        ctk.CTkLabel(details_window, text="Add Comment:").grid(row=9, column=0, sticky=tk.NW, padx=10, pady=5)

        comment_frame = ctk.CTkFrame(details_window)
        comment_frame.grid(row=9, column=1, sticky=tk.W, padx=10, pady=5)

        entry_comment = ctk.CTkEntry(comment_frame, width=220)
        entry_comment.pack(side=tk.LEFT)

        def on_add_comment():
            new_c = entry_comment.get().strip()
            if new_c:
                try:
                    comment(task_id, new_c)
                    entry_comment.delete(0, "end")
                    load_comments()
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to add comment: {str(e)}")

        btn_add_comment = ctk.CTkButton(comment_frame, text="Add", command=on_add_comment)
        btn_add_comment.pack(side=tk.LEFT, padx=5)


if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    root = ctk.CTk()
    app = TaskManagerApp(root)
    root.mainloop()
