# Run with: python agency_manager.py
"""
Desktop application for managing a marketing agency workflow using Tkinter.
Data is stored in JSON (data.json) alongside this script.
"""
import json
import os
import uuid
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, ttk

DATA_FILE = "data.json"

PIPELINES = {
    "Script": ["Writing Script", "Script Review"],
    "Recording": ["Record date & New info", "Action Day", "Raw Footage Filtering"],
    "Editing Queue": ["Editing Progress", "Edit Reviewing"],
    "Design Tasks": ["Graphic Request", "Graphic Review"],
    "READY": ["Upload Day", "Done", "Revision & Followup"],
}

STATUS_OPTIONS = ["To Do", "In Progress", "Blocked", "Done"]
WORKFLOW_KEYS = ["record", "edit", "design", "marketing"]


def today_date() -> str:
    """Return today's date as YYYY-MM-DD."""
    return datetime.now().strftime("%Y-%m-%d")


class AgencyManagerApp:
    """Main application class handling UI and data logic."""

    def __init__(self, master: tk.Tk) -> None:
        self.master = master
        self.master.title("Agency Manager")
        self.clients = []
        self.current_client_index = None
        self.current_pipeline = "Script"
        self.selected_task_id = None

        self.load_data()
        self.build_ui()
        self.refresh_client_list()

    # -------------------------- Data Handling --------------------------
    def load_data(self) -> None:
        """Load clients from JSON file if it exists."""
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    self.clients = json.load(f)
            except (json.JSONDecodeError, OSError) as exc:
                messagebox.showerror("Error", f"Failed to load data: {exc}")
                self.clients = []
        else:
            self.clients = []

        for client in self.clients:
            self.ensure_client_structure(client)

    def save_data(self) -> None:
        """Persist current clients list to JSON file."""
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(self.clients, f, indent=2)
        except OSError as exc:
            messagebox.showerror("Error", f"Failed to save data: {exc}")

    @staticmethod
    def ensure_client_structure(client: dict) -> None:
        """Ensure required keys exist for workflow notes and pipelines."""
        if "workflowNotes" not in client or not isinstance(client.get("workflowNotes"), dict):
            client["workflowNotes"] = {}
        for key in WORKFLOW_KEYS:
            client["workflowNotes"].setdefault(key, "")

        if "pipelines" not in client or not isinstance(client.get("pipelines"), dict):
            client["pipelines"] = {}
        for pipeline in PIPELINES.keys():
            client["pipelines"].setdefault(pipeline.lower().replace(" ", "_"), [])

    # -------------------------- UI Building --------------------------
    def build_ui(self) -> None:
        """Build the main UI layout."""
        main_frame = tk.Frame(self.master)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left_frame = tk.Frame(main_frame, width=200)
        left_frame.pack(side=tk.LEFT, fill=tk.Y)

        tk.Label(left_frame, text="Clients", font=("Arial", 12, "bold")).pack(anchor=tk.W)
        self.client_listbox = tk.Listbox(left_frame, height=20)
        self.client_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        self.client_listbox.bind("<<ListboxSelect>>", self.on_client_select)

        btn_frame = tk.Frame(left_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        tk.Button(btn_frame, text="Add Client", command=self.new_client).pack(fill=tk.X, pady=2)
        tk.Button(btn_frame, text="Edit Client", command=self.edit_client).pack(fill=tk.X, pady=2)
        tk.Button(btn_frame, text="Delete Client", command=self.delete_client).pack(fill=tk.X, pady=2)

        right_frame = tk.Frame(main_frame)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.notebook = ttk.Notebook(right_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.build_overview_tab()
        self.build_workflow_notes_tab()
        self.build_task_board_tab()

    def build_overview_tab(self) -> None:
        """Create Overview tab widgets."""
        self.overview_tab = tk.Frame(self.notebook)
        self.notebook.add(self.overview_tab, text="Overview")

        form = tk.Frame(self.overview_tab)
        form.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        tk.Label(form, text="Client Name").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.name_entry = tk.Entry(form)
        self.name_entry.grid(row=0, column=1, sticky=tk.EW, pady=2)

        tk.Label(form, text="Business Name").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.business_entry = tk.Entry(form)
        self.business_entry.grid(row=1, column=1, sticky=tk.EW, pady=2)

        tk.Label(form, text="Phone / WhatsApp").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.phone_entry = tk.Entry(form)
        self.phone_entry.grid(row=2, column=1, sticky=tk.EW, pady=2)

        tk.Label(form, text="General Notes").grid(row=3, column=0, sticky=tk.NW, pady=2)
        self.notes_text = tk.Text(form, height=6)
        self.notes_text.grid(row=3, column=1, sticky=tk.EW, pady=2)

        form.columnconfigure(1, weight=1)

        button_row = tk.Frame(self.overview_tab)
        button_row.pack(fill=tk.X, padx=10, pady=10)
        tk.Button(button_row, text="Save Client", command=self.save_client).pack(side=tk.LEFT, padx=5)
        tk.Button(button_row, text="New Client", command=self.new_client).pack(side=tk.LEFT, padx=5)

    def build_workflow_notes_tab(self) -> None:
        """Create Workflow Notes tab with sub-tabs."""
        self.workflow_tab = tk.Frame(self.notebook)
        self.notebook.add(self.workflow_tab, text="Workflow Notes")

        self.workflow_notebook = ttk.Notebook(self.workflow_tab)
        self.workflow_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.workflow_texts = {}
        for key, label in zip(WORKFLOW_KEYS, ["Record", "Edit", "Design", "Marketing"]):
            frame = tk.Frame(self.workflow_notebook)
            self.workflow_notebook.add(frame, text=label)
            text_widget = tk.Text(frame, height=10)
            text_widget.pack(fill=tk.BOTH, expand=True)
            self.workflow_texts[key] = text_widget

    def build_task_board_tab(self) -> None:
        """Create Task Board tab UI components."""
        self.task_tab = tk.Frame(self.notebook)
        self.notebook.add(self.task_tab, text="Task Board")

        top_frame = tk.Frame(self.task_tab)
        top_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(top_frame, text="Pipeline:").pack(side=tk.LEFT)
        self.pipeline_combo = ttk.Combobox(top_frame, values=list(PIPELINES.keys()), state="readonly")
        self.pipeline_combo.set(self.current_pipeline)
        self.pipeline_combo.pack(side=tk.LEFT, padx=5)
        self.pipeline_combo.bind("<<ComboboxSelected>>", self.on_pipeline_change)

        self.task_tree = ttk.Treeview(
            self.task_tab,
            columns=("title", "sub_stage", "assignee", "status", "due_date"),
            show="headings",
        )
        for col, heading in zip(
            ["title", "sub_stage", "assignee", "status", "due_date"],
            ["Title", "Sub-stage", "Assignee", "Status", "Due Date"],
        ):
            self.task_tree.heading(col, text=heading)
            self.task_tree.column(col, width=120, anchor=tk.W)
        self.task_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.task_tree.bind("<<TreeviewSelect>>", self.on_task_select)

        form = tk.Frame(self.task_tab)
        form.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        tk.Label(form, text="Title").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.task_title_entry = tk.Entry(form)
        self.task_title_entry.grid(row=0, column=1, sticky=tk.EW, pady=2)

        tk.Label(form, text="Sub-stage").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.substage_combo = ttk.Combobox(form, state="readonly")
        self.substage_combo.grid(row=1, column=1, sticky=tk.EW, pady=2)

        tk.Label(form, text="Assignee").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.task_assignee_entry = tk.Entry(form)
        self.task_assignee_entry.grid(row=2, column=1, sticky=tk.EW, pady=2)

        tk.Label(form, text="Status").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.status_combo = ttk.Combobox(form, values=STATUS_OPTIONS, state="readonly")
        self.status_combo.grid(row=3, column=1, sticky=tk.EW, pady=2)

        tk.Label(form, text="Due Date (YYYY-MM-DD)").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.due_date_entry = tk.Entry(form)
        self.due_date_entry.grid(row=4, column=1, sticky=tk.EW, pady=2)

        tk.Label(form, text="Description").grid(row=5, column=0, sticky=tk.NW, pady=2)
        self.task_description_text = tk.Text(form, height=4)
        self.task_description_text.grid(row=5, column=1, sticky=tk.EW, pady=2)

        form.columnconfigure(1, weight=1)

        button_row = tk.Frame(self.task_tab)
        button_row.pack(fill=tk.X, padx=10, pady=5)
        tk.Button(button_row, text="New Task", command=self.new_task).pack(side=tk.LEFT, padx=5)
        tk.Button(button_row, text="Save Task", command=self.save_task).pack(side=tk.LEFT, padx=5)
        tk.Button(button_row, text="Delete Task", command=self.delete_task).pack(side=tk.LEFT, padx=5)

        self.update_substage_options()

    # -------------------------- UI Helpers --------------------------
    def refresh_client_list(self) -> None:
        """Refresh the listbox with current clients."""
        self.client_listbox.delete(0, tk.END)
        for client in self.clients:
            display = f"{client.get('name', 'Unknown')} – {client.get('business', '')}"
            self.client_listbox.insert(tk.END, display)

    def clear_overview_fields(self) -> None:
        self.name_entry.delete(0, tk.END)
        self.business_entry.delete(0, tk.END)
        self.phone_entry.delete(0, tk.END)
        self.notes_text.delete("1.0", tk.END)

    def clear_workflow_notes(self) -> None:
        for text_widget in self.workflow_texts.values():
            text_widget.delete("1.0", tk.END)

    def clear_tasks_view(self) -> None:
        for item in self.task_tree.get_children():
            self.task_tree.delete(item)
        self.new_task()

    # -------------------------- Client Logic --------------------------
    def on_client_select(self, event=None) -> None:
        """Handle client selection from list."""
        selection = self.client_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        self.current_client_index = index
        self.load_client_into_form(self.clients[index])

    def load_client_into_form(self, client: dict) -> None:
        """Load client data into all UI fields."""
        self.clear_overview_fields()
        self.clear_workflow_notes()
        self.clear_tasks_view()

        self.name_entry.insert(0, client.get("name", ""))
        self.business_entry.insert(0, client.get("business", ""))
        self.phone_entry.insert(0, client.get("phone", ""))
        self.notes_text.insert("1.0", client.get("notes", ""))

        notes = client.get("workflowNotes", {})
        for key in WORKFLOW_KEYS:
            self.workflow_texts[key].insert("1.0", notes.get(key, ""))

        self.load_tasks_to_tree(self.current_pipeline)

    def collect_overview_data(self) -> dict:
        return {
            "name": self.name_entry.get().strip(),
            "business": self.business_entry.get().strip(),
            "phone": self.phone_entry.get().strip(),
            "notes": self.notes_text.get("1.0", tk.END).strip(),
        }

    def collect_workflow_notes(self) -> dict:
        return {key: widget.get("1.0", tk.END).strip() for key, widget in self.workflow_texts.items()}

    def new_client(self) -> None:
        """Clear form to create a new client."""
        self.current_client_index = None
        self.clear_overview_fields()
        self.clear_workflow_notes()
        self.clear_tasks_view()
        self.current_pipeline = "Script"
        self.pipeline_combo.set(self.current_pipeline)
        self.update_substage_options()
        self.selected_task_id = None

    def edit_client(self) -> None:
        """Alias for selecting a client; ensures fields are editable."""
        self.on_client_select()

    def delete_client(self) -> None:
        """Delete the currently selected client."""
        selection = self.client_listbox.curselection()
        if not selection:
            messagebox.showinfo("Delete Client", "Please select a client to delete.")
            return
        index = selection[0]
        client = self.clients[index]
        confirm = messagebox.askyesno(
            "Confirm Delete", f"Delete client '{client.get('name', 'Unnamed')}'?"
        )
        if confirm:
            self.clients.pop(index)
            self.save_data()
            self.refresh_client_list()
            self.new_client()

    def save_client(self) -> None:
        """Save or update a client from UI data."""
        overview = self.collect_overview_data()
        if not overview["name"]:
            messagebox.showinfo("Validation", "Client name is required.")
            return

        workflow_notes = self.collect_workflow_notes()
        if self.current_client_index is None:
            # Create new client
            client = {
                "id": str(uuid.uuid4()),
                **overview,
                "workflowNotes": workflow_notes,
                "pipelines": {key.lower().replace(" ", "_"): [] for key in PIPELINES.keys()},
            }
            self.clients.append(client)
            self.current_client_index = len(self.clients) - 1
        else:
            client = self.clients[self.current_client_index]
            client.update(overview)
            client["workflowNotes"] = workflow_notes

        self.ensure_client_structure(client)
        self.save_data()
        self.refresh_client_list()
        self.load_tasks_to_tree(self.current_pipeline)
        messagebox.showinfo("Saved", "Client information saved.")

    # -------------------------- Task Logic --------------------------
    def on_pipeline_change(self, event=None) -> None:
        self.current_pipeline = self.pipeline_combo.get()
        self.update_substage_options()
        self.load_tasks_to_tree(self.current_pipeline)
        self.new_task()

    def get_pipeline_key(self, pipeline_name: str) -> str:
        return pipeline_name.lower().replace(" ", "_")

    def load_tasks_to_tree(self, pipeline_name: str) -> None:
        self.clear_tasks_view()
        if self.current_client_index is None:
            return
        client = self.clients[self.current_client_index]
        tasks = client.get("pipelines", {}).get(self.get_pipeline_key(pipeline_name), [])
        for task in tasks:
            self.task_tree.insert(
                "",
                tk.END,
                iid=task["id"],
                values=(
                    task.get("title", ""),
                    task.get("sub_stage", ""),
                    task.get("assignee", ""),
                    task.get("status", ""),
                    task.get("due_date", ""),
                ),
            )

    def new_task(self) -> None:
        self.selected_task_id = None
        self.task_title_entry.delete(0, tk.END)
        self.substage_combo.set("")
        self.task_assignee_entry.delete(0, tk.END)
        self.status_combo.set("")
        self.due_date_entry.delete(0, tk.END)
        self.task_description_text.delete("1.0", tk.END)
        self.task_tree.selection_remove(self.task_tree.selection())

    def on_task_select(self, event=None) -> None:
        selection = self.task_tree.selection()
        if not selection:
            return
        task_id = selection[0]
        self.selected_task_id = task_id
        task = self.find_task_by_id(task_id)
        if not task:
            return
        self.task_title_entry.delete(0, tk.END)
        self.task_title_entry.insert(0, task.get("title", ""))
        self.substage_combo.set(task.get("sub_stage", ""))
        self.task_assignee_entry.delete(0, tk.END)
        self.task_assignee_entry.insert(0, task.get("assignee", ""))
        self.status_combo.set(task.get("status", ""))
        self.due_date_entry.delete(0, tk.END)
        self.due_date_entry.insert(0, task.get("due_date", ""))
        self.task_description_text.delete("1.0", tk.END)
        self.task_description_text.insert("1.0", task.get("description", ""))

    def find_task_by_id(self, task_id: str) -> dict:
        if self.current_client_index is None:
            return {}
        client = self.clients[self.current_client_index]
        tasks = client.get("pipelines", {}).get(self.get_pipeline_key(self.current_pipeline), [])
        for task in tasks:
            if task.get("id") == task_id:
                return task
        return {}

    def save_task(self) -> None:
        if self.current_client_index is None:
            messagebox.showinfo("No Client", "Please select or create a client first.")
            return

        title = self.task_title_entry.get().strip()
        if not title:
            messagebox.showinfo("Validation", "Task title is required.")
            return

        task_data = {
            "title": title,
            "description": self.task_description_text.get("1.0", tk.END).strip(),
            "sub_stage": self.substage_combo.get(),
            "assignee": self.task_assignee_entry.get().strip(),
            "status": self.status_combo.get() or STATUS_OPTIONS[0],
            "due_date": self.due_date_entry.get().strip(),
            "last_updated": today_date(),
        }

        client = self.clients[self.current_client_index]
        tasks = client["pipelines"].setdefault(self.get_pipeline_key(self.current_pipeline), [])

        if self.selected_task_id:
            for task in tasks:
                if task.get("id") == self.selected_task_id:
                    task.update(task_data)
                    break
        else:
            task_data.update({
                "id": str(uuid.uuid4()),
                "created_at": today_date(),
            })
            tasks.append(task_data)

        self.save_data()
        self.load_tasks_to_tree(self.current_pipeline)
        self.selected_task_id = None
        self.new_task()

    def delete_task(self) -> None:
        if self.current_client_index is None:
            messagebox.showinfo("No Client", "Please select a client first.")
            return
        selection = self.task_tree.selection()
        if not selection:
            messagebox.showinfo("Delete Task", "Please select a task to delete.")
            return
        task_id = selection[0]
        confirm = messagebox.askyesno("Confirm Delete", "Delete selected task?")
        if not confirm:
            return
        client = self.clients[self.current_client_index]
        key = self.get_pipeline_key(self.current_pipeline)
        tasks = client.get("pipelines", {}).get(key, [])
        client["pipelines"][key] = [t for t in tasks if t.get("id") != task_id]
        self.save_data()
        self.load_tasks_to_tree(self.current_pipeline)
        self.new_task()

    def update_substage_options(self) -> None:
        stages = PIPELINES.get(self.current_pipeline, [])
        self.substage_combo["values"] = stages
        if stages:
            self.substage_combo.set(stages[0])
        else:
            self.substage_combo.set("")

    # -------------------------- Utility --------------------------
    def run(self) -> None:
        self.master.mainloop()


if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("900x600")
    app = AgencyManagerApp(root)
    app.run()
