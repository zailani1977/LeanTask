import os
import json
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageDraw
from tkinter import ttk, messagebox, simpledialog
from task_db import get_connection
from task_cli_submit import submit
from task_cli_workbench import state, priority, project, title, description, tags, due, comment, archive_tasks
from task_sync import sync_issues

def ensure_icons():
    import os
    from PIL import Image, ImageDraw
    icon_dir = ".tasks/icons"
    os.makedirs(icon_dir, exist_ok=True)
    
    colors = {
        "white": (255, 255, 255, 255),
        "dark": (60, 64, 67, 255),
        "light": (241, 243, 244, 255)
    }
    
    # 1. Plus Icon (Submit Task)
    plus_white_path = os.path.join(icon_dir, "plus_white.png")
    if not os.path.exists(plus_white_path):
        img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.line((16, 8, 16, 24), fill=colors["white"], width=4)
        draw.line((8, 16, 24, 16), fill=colors["white"], width=4)
        img.save(plus_white_path)
        
    # 2. Refresh Icons
    for suffix, color in [("dark", colors["dark"]), ("light", colors["light"])]:
        path = os.path.join(icon_dir, f"refresh_{suffix}.png")
        if not os.path.exists(path):
            img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.arc([6, 6, 26, 26], start=40, end=320, fill=color, width=3)
            draw.polygon([(24, 4), (24, 12), (16, 8)], fill=color)
            img.save(path)
            
    # 3. Archive Icons
    for suffix, color in [("dark", colors["dark"]), ("light", colors["light"])]:
        path = os.path.join(icon_dir, f"archive_{suffix}.png")
        if not os.path.exists(path):
            img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.rectangle([6, 12, 26, 25], outline=color, width=3)
            draw.rectangle([4, 7, 28, 12], outline=color, width=3, fill=color)
            draw.line((13, 18, 19, 18), fill=color, width=3)
            img.save(path)
            
    # 4. Folder Icons (View Archive)
    for suffix, color in [("dark", colors["dark"]), ("light", colors["light"])]:
        path = os.path.join(icon_dir, f"folder_{suffix}.png")
        if not os.path.exists(path):
            img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.rectangle([6, 11, 26, 25], outline=color, width=3)
            draw.polygon([(6, 11), (6, 7), (14, 7), (17, 11)], fill=color)
            img.save(path)

class TaskManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Task Management Dashboard")
        self.root.geometry("900x600")

        # Set root window background color
        self.root.configure(fg_color=("#F5F7FA", "#1A1C1E"))

        # Setup column headers metadata
        self.headers_def = [
            ("ID", 90, "center"),
            ("Status", 120, "center"),
            ("Priority", 90, "center"),
            ("Project", 120, "w"),
            ("Due", 120, "center"),
            ("Title", 0, "w")
        ]

        self.create_widgets()
        self.refresh_tasks()

    def get_status_style(self, status):
        status = status.lower()
        if status in ("open", "in_progress"):
            return ("#E6F4EA", "#10301D"), ("#137333", "#81C995")
        elif status == "blocked":
            return ("#FCE8E6", "#3C1818"), ("#C5221F", "#F28B82")
        else: # deferred, closed
            return ("#F1F3F4", "#2A2B2D"), ("#5F6368", "#9AA0A6")

    def get_priority_style(self, score):
        try:
            s = float(score)
        except (ValueError, TypeError):
            s = 0.0
        if s >= 3.5:
            return ("#FCE8E6", "#3C1818"), ("#C5221F", "#F28B82")
        elif s >= 1.5:
            return ("#FEF7E0", "#3A2E10"), ("#B06000", "#FDD663")
        else:
            return ("#F1F3F4", "#2A2B2D"), ("#5F6368", "#9AA0A6")

    def create_widgets(self):
        # Generate the PNG icons if they don't exist
        ensure_icons()
        icon_dir = ".tasks/icons"

        self.img_plus = ctk.CTkImage(
            light_image=Image.open(os.path.join(icon_dir, "plus_white.png")),
            dark_image=Image.open(os.path.join(icon_dir, "plus_white.png")),
            size=(16, 16)
        )
        self.img_refresh = ctk.CTkImage(
            light_image=Image.open(os.path.join(icon_dir, "refresh_dark.png")),
            dark_image=Image.open(os.path.join(icon_dir, "refresh_light.png")),
            size=(16, 16)
        )
        self.img_archive = ctk.CTkImage(
            light_image=Image.open(os.path.join(icon_dir, "archive_dark.png")),
            dark_image=Image.open(os.path.join(icon_dir, "archive_light.png")),
            size=(16, 16)
        )
        self.img_view_archive = ctk.CTkImage(
            light_image=Image.open(os.path.join(icon_dir, "folder_dark.png")),
            dark_image=Image.open(os.path.join(icon_dir, "folder_light.png")),
            size=(16, 16)
        )

        # Main layout parent container (provides outer window padding)
        parent_container = ctk.CTkFrame(self.root, fg_color=("#F5F7FA", "#1A1C1E"))
        parent_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Top Frame for Buttons
        top_frame = ctk.CTkFrame(parent_container, fg_color="transparent")
        top_frame.pack(fill=tk.X, pady=(0, 20))

        # Split Layout for Top Buttons
        left_bar = ctk.CTkFrame(top_frame, fg_color="transparent")
        left_bar.pack(side=tk.LEFT, fill=tk.Y)

        right_bar = ctk.CTkFrame(top_frame, fg_color="transparent")
        right_bar.pack(side=tk.RIGHT, fill=tk.Y)

        # Left Aligned Buttons (Primary/Secondary styles)
        self.btn_refresh = ctk.CTkButton(
            left_bar, 
            text="Refresh", 
            command=self.refresh_tasks,
            image=self.img_refresh,
            font=("Inter", 12, "bold"),
            border_width=1,
            border_color=("#BDC1C6", "#5F6368"),
            fg_color="transparent",
            text_color=("#3C4043", "#E8EAED"),
            hover_color=("#F1F3F4", "#3C4043")
        )
        self.btn_refresh.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_submit = ctk.CTkButton(
            left_bar, 
            text="Submit Task", 
            command=self.submit_task,
            image=self.img_plus,
            font=("Inter", 12, "bold"),
            fg_color=("#1A73E8", "#8AB4F8"),
            text_color="white",
            hover_color=("#1557B0", "#669DF6")
        )
        self.btn_submit.pack(side=tk.LEFT)

        # Right Aligned Buttons
        self.btn_archive = ctk.CTkButton(
            right_bar, 
            text="Archive", 
            command=self.archive_and_refresh,
            image=self.img_archive,
            font=("Inter", 12, "bold"),
            border_width=1,
            border_color=("#BDC1C6", "#5F6368"),
            fg_color="transparent",
            text_color=("#3C4043", "#E8EAED"),
            hover_color=("#F1F3F4", "#3C4043")
        )
        self.btn_archive.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_view_archive = ctk.CTkButton(
            right_bar, 
            text="View Archive", 
            command=self.open_view_archive,
            image=self.img_view_archive,
            font=("Inter", 12, "bold"),
            border_width=1,
            border_color=("#BDC1C6", "#5F6368"),
            fg_color="transparent",
            text_color=("#3C4043", "#E8EAED"),
            hover_color=("#F1F3F4", "#3C4043")
        )
        self.btn_view_archive.pack(side=tk.LEFT)

        # Table Main container frame (pop forward style background)
        main_frame = ctk.CTkFrame(
            parent_container, 
            fg_color=("#FFFFFF", "#242628"), 
            corner_radius=8,
            border_width=1,
            border_color=("#E0E2E6", "#2D3033")
        )
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Header bar frame
        headers_frame = ctk.CTkFrame(main_frame, fg_color=("#FFFFFF", "#242628"), corner_radius=0)
        headers_frame.pack(fill=tk.X, pady=(0, 5), padx=2)

        for i, (text, width, anchor) in enumerate(self.headers_def):
            headers_frame.columnconfigure(i, weight=1 if text == "Title" else 0, minsize=width)
            lbl = ctk.CTkLabel(
                headers_frame, 
                text=text, 
                font=("Inter", 12, "bold"),
                text_color=("#5F6368", "#9AA0A6"),
                anchor=anchor
            )
            lbl.grid(row=0, column=i, sticky="nsew", padx=10, pady=8)

        # Scrollable table container
        self.table_scroll = ctk.CTkScrollableFrame(
            main_frame, 
            fg_color="transparent",
            corner_radius=0
        )
        self.table_scroll.pack(fill=tk.BOTH, expand=True, padx=2, pady=(0, 2))

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
        archive_window.configure(fg_color=("#F5F7FA", "#1A1C1E"))

        parent_container = ctk.CTkFrame(archive_window, fg_color=("#F5F7FA", "#1A1C1E"))
        parent_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        main_frame = ctk.CTkFrame(
            parent_container, 
            fg_color=("#FFFFFF", "#242628"), 
            corner_radius=8,
            border_width=1,
            border_color=("#E0E2E6", "#2D3033")
        )
        main_frame.pack(fill=tk.BOTH, expand=True)

        headers_frame = ctk.CTkFrame(main_frame, fg_color=("#FFFFFF", "#242628"), corner_radius=0)
        headers_frame.pack(fill=tk.X, pady=(0, 5), padx=2)

        for i, (text, width, anchor) in enumerate(self.headers_def):
            headers_frame.columnconfigure(i, weight=1 if text == "Title" else 0, minsize=width)
            lbl = ctk.CTkLabel(
                headers_frame, 
                text=text, 
                font=("Inter", 12, "bold"),
                text_color=("#5F6368", "#9AA0A6"),
                anchor=anchor
            )
            lbl.grid(row=0, column=i, sticky="nsew", padx=10, pady=8)

        self.archive_scroll = ctk.CTkScrollableFrame(
            main_frame, 
            fg_color="transparent",
            corner_radius=0
        )
        self.archive_scroll.pack(fill=tk.BOTH, expand=True, padx=2, pady=(0, 2))

        self.refresh_archive_tasks()

    def refresh_archive_tasks(self):
        for widget in self.archive_scroll.winfo_children():
            widget.destroy()

        try:
            ARCHIVE_FILE = ".tasks/archive.jsonl"
            if not os.path.exists(ARCHIVE_FILE):
                return

            with open(ARCHIVE_FILE, 'r', encoding='utf-8') as f:
                idx = 0
                for line in f:
                    if not line.strip(): 
                        continue
                    task = json.loads(line)
                    task_id = task.get("task_id")
                    status = task.get("status", "").upper()
                    priority_score = task.get("priority_score", 0.0)
                    project_val = task.get("project", "")
                    due_date = task.get("due_date")
                    due_val = due_date if due_date else "None"
                    title_val = task.get("title", "")

                    # Alternate row backgrounds
                    row_color = ("#FFFFFF", "#242628") if idx % 2 == 0 else ("#F8FAFC", "#2D3033")
                    hover_color = ("#F1F3F4", "#2F3134") if idx % 2 == 0 else ("#F1F5F9", "#383B3E")

                    row_frame = ctk.CTkFrame(self.archive_scroll, fg_color=row_color, corner_radius=6)
                    row_frame.pack(fill=tk.X, pady=2, padx=2)

                    for i, (text, width, anchor) in enumerate(self.headers_def):
                        row_frame.columnconfigure(i, weight=1 if text == "Title" else 0, minsize=width)

                    # ID
                    lbl_id = ctk.CTkLabel(row_frame, text=task_id, font=("Inter", 11, "bold"), text_color=("#1A1C1E", "#E8EAED"), anchor="center")
                    lbl_id.grid(row=0, column=0, sticky="nsew", padx=10, pady=8)

                    # Status Badge
                    bg_c, text_c = self.get_status_style(status)
                    lbl_status = ctk.CTkLabel(
                        row_frame, 
                        text=status, 
                        fg_color=bg_c, 
                        text_color=text_c, 
                        corner_radius=12, 
                        font=("Inter", 10, "bold"),
                        width=100, 
                        height=24
                    )
                    lbl_status.grid(row=0, column=1, padx=10, pady=8)

                    # Priority Badge
                    bg_p, text_p = self.get_priority_style(priority_score)
                    lbl_priority = ctk.CTkLabel(
                        row_frame, 
                        text=f"{priority_score:.1f}", 
                        fg_color=bg_p, 
                        text_color=text_p, 
                        corner_radius=12, 
                        font=("Inter", 10, "bold"),
                        width=60, 
                        height=24
                    )
                    lbl_priority.grid(row=0, column=2, padx=10, pady=8)

                    # Project
                    lbl_project = ctk.CTkLabel(row_frame, text=project_val, font=("Inter", 11), text_color=("#1A1C1E", "#E8EAED"), anchor="w")
                    lbl_project.grid(row=0, column=3, sticky="nsew", padx=10, pady=8)

                    # Due
                    lbl_due = ctk.CTkLabel(row_frame, text=due_val, font=("Inter", 11), text_color=("#1A1C1E", "#E8EAED"), anchor="center")
                    lbl_due.grid(row=0, column=4, sticky="nsew", padx=10, pady=8)

                    # Title
                    lbl_title = ctk.CTkLabel(row_frame, text=title_val, font=("Inter", 11), text_color=("#1A1C1E", "#E8EAED"), anchor="w")
                    lbl_title.grid(row=0, column=5, sticky="nsew", padx=10, pady=8)

                    # Handlers
                    self.bind_archive_double_click(row_frame, task_id)
                    self.bind_hover_effect(row_frame, row_color, hover_color)

                    idx += 1

        except Exception as e:
            messagebox.showerror("Error", f"Could not load archived tasks: {str(e)}")

    def bind_archive_double_click(self, widget, task_id):
        handler = lambda event, t_id=task_id: self.open_archived_task_details(t_id)
        widget.bind("<Double-Button-1>", handler)
        for child in widget.winfo_children():
            child.bind("<Double-Button-1>", handler)

    def open_archived_task_details(self, task_id):
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
        details_window.geometry("600x560")

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
        for widget in self.table_scroll.winfo_children():
            widget.destroy()

        try:
            sync_issues()
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT task_id, status, priority_score, project, due_date, title FROM tasks")
            rows = cursor.fetchall()
            conn.close()

            for idx, row in enumerate(rows):
                task_id, status, priority_score, project_val, due_date, title_val = row
                due_val = due_date if due_date else "None"
                status_text = status.upper()

                # Alternate row backgrounds
                row_color = ("#FFFFFF", "#242628") if idx % 2 == 0 else ("#F8FAFC", "#2D3033")
                hover_color = ("#F1F3F4", "#2F3134") if idx % 2 == 0 else ("#F1F5F9", "#383B3E")

                row_frame = ctk.CTkFrame(self.table_scroll, fg_color=row_color, corner_radius=6)
                row_frame.pack(fill=tk.X, pady=2, padx=2)

                for i, (text, width, anchor) in enumerate(self.headers_def):
                    row_frame.columnconfigure(i, weight=1 if text == "Title" else 0, minsize=width)

                # ID
                lbl_id = ctk.CTkLabel(row_frame, text=task_id, font=("Inter", 11, "bold"), text_color=("#1A1C1E", "#E8EAED"), anchor="center")
                lbl_id.grid(row=0, column=0, sticky="nsew", padx=10, pady=8)

                # Status Badge
                bg_c, text_c = self.get_status_style(status)
                lbl_status = ctk.CTkLabel(
                    row_frame, 
                    text=status_text, 
                    fg_color=bg_c, 
                    text_color=text_c, 
                    corner_radius=12, 
                    font=("Inter", 10, "bold"),
                    width=100, 
                    height=24
                )
                lbl_status.grid(row=0, column=1, padx=10, pady=8)

                # Priority Badge
                bg_p, text_p = self.get_priority_style(priority_score)
                p_val = priority_score if priority_score is not None else 0.0
                lbl_priority = ctk.CTkLabel(
                    row_frame, 
                    text=f"{p_val:.1f}", 
                    fg_color=bg_p, 
                    text_color=text_p, 
                    corner_radius=12, 
                    font=("Inter", 10, "bold"),
                    width=60, 
                    height=24
                )
                lbl_priority.grid(row=0, column=2, padx=10, pady=8)

                # Project
                lbl_project = ctk.CTkLabel(row_frame, text=project_val, font=("Inter", 11), text_color=("#1A1C1E", "#E8EAED"), anchor="w")
                lbl_project.grid(row=0, column=3, sticky="nsew", padx=10, pady=8)

                # Due
                lbl_due = ctk.CTkLabel(row_frame, text=due_val, font=("Inter", 11), text_color=("#1A1C1E", "#E8EAED"), anchor="center")
                lbl_due.grid(row=0, column=4, sticky="nsew", padx=10, pady=8)

                # Title
                lbl_title = ctk.CTkLabel(row_frame, text=title_val, font=("Inter", 11), text_color=("#1A1C1E", "#E8EAED"), anchor="w")
                lbl_title.grid(row=0, column=5, sticky="nsew", padx=10, pady=8)

                # Handlers
                self.bind_double_click(row_frame, task_id)
                self.bind_hover_effect(row_frame, row_color, hover_color)

        except Exception as e:
            messagebox.showerror("Error", f"Could not load tasks: {str(e)}")

    def bind_double_click(self, widget, task_id):
        handler = lambda event, t_id=task_id: self.open_task_details(t_id)
        widget.bind("<Double-Button-1>", handler)
        for child in widget.winfo_children():
            child.bind("<Double-Button-1>", handler)

    def bind_hover_effect(self, row_frame, normal_color, hover_color):
        widgets = [row_frame] + list(row_frame.winfo_children())

        def on_enter(e):
            row_frame.configure(fg_color=hover_color)

        def on_leave(e):
            x, y = row_frame.winfo_pointerxy()
            rx = row_frame.winfo_rootx()
            ry = row_frame.winfo_rooty()
            rw = row_frame.winfo_width()
            rh = row_frame.winfo_height()
            if not (rx <= x <= rx + rw and ry <= y <= ry + rh):
                row_frame.configure(fg_color=normal_color)

        for w in widgets:
            w.bind("<Enter>", on_enter, add="+")
            w.bind("<Leave>", on_leave, add="+")

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
        details_window.geometry("600x600")

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

        # --- Comments Section ---
        ctk.CTkLabel(details_window, text="Comments:").grid(row=7, column=0, sticky=tk.NW, padx=10, pady=5)

        comments_listbox = ctk.CTkTextbox(details_window, width=300, height=120)
        comments_listbox.grid(row=7, column=1, sticky=tk.W, padx=10, pady=5)

        def load_comments():
            comments_listbox.delete("0.0", "end")
            try:
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

        ctk.CTkLabel(details_window, text="Add Comment:").grid(row=8, column=0, sticky=tk.NW, padx=10, pady=5)

        comment_frame = ctk.CTkFrame(details_window)
        comment_frame.grid(row=8, column=1, sticky=tk.W, padx=10, pady=5)

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

        btn_save = ctk.CTkButton(details_window, text="Update Task", command=save_changes)
        btn_save.grid(row=9, column=1, sticky=tk.E, padx=10, pady=(20, 20))

if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    root = ctk.CTk()
    app = TaskManagerApp(root)
    root.mainloop()
