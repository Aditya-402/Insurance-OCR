import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sqlite3
import os

class SQLiteGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SQLite DB Viewer/Editor")
        self.conn = None
        self.current_table = None
        self.file_path = None
        self.data = []
        self.headers = []
        self.setup_ui()

    def setup_ui(self):
        # Menu
        menubar = tk.Menu(self.root)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Open DB", command=self.load_db)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=filemenu)
        
        # Manage Table menu
        tablemenu = tk.Menu(menubar, tearoff=0)
        tablemenu.add_command(label="Rename Columns", command=self.rename_columns_dialog)
        tablemenu.add_command(label="Add Column", command=self.add_column_dialog)
        tablemenu.add_command(label="Add New Table", command=self.add_table_dialog)
        tablemenu.add_command(label="Rename Table", command=self.rename_table_dialog)
        tablemenu.add_command(label="Delete Table", command=self.delete_table_dialog)
        menubar.add_cascade(label="Manage Table", menu=tablemenu)
        
        self.root.config(menu=menubar)

        # Browse Database button
        self.browse_btn = ttk.Button(self.root, text="Browse Database", command=self.load_db)
        self.browse_btn.pack(fill="x", padx=5, pady=(8, 2))

        # Table selection
        self.table_combo = ttk.Combobox(self.root, state="readonly")
        self.table_combo.bind("<<ComboboxSelected>>", lambda e: self.load_table())
        self.table_combo.pack(fill="x", padx=5, pady=5)

        # Export/Import buttons
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(fill="x", padx=5, pady=(0, 5))
        self.export_btn = ttk.Button(btn_frame, text="Export Table", command=self.export_table)
        self.export_btn.pack(side="left", padx=(0, 5))
        self.import_btn = ttk.Button(btn_frame, text="Import CSV", command=self.import_csv)
        self.import_btn.pack(side="left")

        # Improved style: zebra striping, readable selection, visible border
        style = ttk.Style(self.root)
        style.configure('Treeview', rowheight=22, borderwidth=1, relief='solid',
                        background='white', fieldbackground='white',
                        highlightthickness=1, highlightbackground='#888')
        style.map('Treeview', background=[('selected', '#3399ff')], foreground=[('selected', 'white')])
        style.configure('Treeview.Heading', borderwidth=1, relief='raised')

        # Frame for table and scrollbars
        table_frame = tk.Frame(self.root, bd=1, relief='solid')
        table_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Treeview for table data
        self.tree = ttk.Treeview(table_frame, show="headings")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind('<Double-1>', self.on_double_click)

        # Scrollbars
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        # Save button
        self.save_btn = ttk.Button(self.root, text="Save Changes", command=self.save_changes, state=tk.DISABLED)
        self.save_btn.pack(pady=5)

    def load_db(self):
        path = filedialog.askopenfilename(title="Select SQLite DB File", filetypes=[("SQLite DB", "*.db;*.sqlite;*.sqlite3"), ("All Files", "*.*")])
        if not path:
            return
        try:
            if self.conn:
                self.conn.close()
            self.conn = sqlite3.connect(path)
            self.file_path = path
            self.refresh_tables()
            self.save_btn["state"] = tk.DISABLED
            messagebox.showinfo("Loaded", f"Loaded DB: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load DB: {e}")

    def refresh_tables(self):
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cur.fetchall()]
            self.table_combo["values"] = tables
            if tables:
                self.table_combo.current(0)
                self.load_table()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to retrieve tables: {e}")

    def load_table(self):
        table = self.table_combo.get()
        if not table:
            return
        self.current_table = table
        cur = self.conn.cursor()
        try:
            cur.execute(f"SELECT * FROM {table}")
            self.data = cur.fetchall()
            self.headers = [desc[0] for desc in cur.description]
            self.display_table()
            self.save_btn["state"] = tk.NORMAL
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load table: {e}")

    def display_table(self):
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = self.headers
        for col in self.headers:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, stretch=True)
        # Zebra striping
        for i, row in enumerate(self.data):
            tag = 'oddrow' if i % 2 else 'evenrow'
            self.tree.insert("", "end", values=row, tags=(tag,))
        self.tree.tag_configure('evenrow', background='#ffffff')
        self.tree.tag_configure('oddrow', background='#f0f4f8')

    def on_double_click(self, event):
        item = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if not item or not col:
            return
        col_idx = int(col[1:]) - 1
        x, y, width, height = self.tree.bbox(item, col)
        value = self.tree.set(item, self.headers[col_idx])
        entry = tk.Entry(self.tree)
        entry.place(x=x, y=y, width=width, height=height)
        entry.insert(0, value)
        entry.focus()
        def save_edit(event=None):
            new_val = entry.get()
            self.tree.set(item, self.headers[col_idx], new_val)
            entry.destroy()
        entry.bind("<Return>", save_edit)
        entry.bind("<FocusOut>", lambda e: entry.destroy())

    def save_changes(self):
        rows = []
        for iid in self.tree.get_children():
            row = [self.tree.set(iid, col) for col in self.headers]
            rows.append(row)
        try:
            cur = self.conn.cursor()
            cur.execute(f"DELETE FROM {self.current_table}")
            placeholders = ",".join(["?"]*len(self.headers))
            cur.executemany(
                f"INSERT INTO {self.current_table} ({', '.join(self.headers)}) VALUES ({placeholders})",
                rows
            )
            self.conn.commit()
            messagebox.showinfo("Success", "Changes saved to database.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save changes: {e}")

    def export_table(self):
        if not self.current_table or not self.headers:
            messagebox.showerror("Error", "No table selected.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if not path:
            return
        try:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                import csv
                writer = csv.writer(f)
                writer.writerow(self.headers)
                for row in self.tree.get_children():
                    writer.writerow([self.tree.set(row, col) for col in self.headers])
            messagebox.showinfo("Exported", f"Table exported to {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Error", f"Export failed: {e}")

    def import_csv(self):
        if not self.current_table or not self.headers:
            messagebox.showerror("Error", "No table selected.")
            return
        path = filedialog.askopenfilename(title="Select CSV File", filetypes=[("CSV Files", "*.csv")])
        if not path:
            return
        try:
            with open(path, 'r', newline='', encoding='utf-8') as f:
                import csv
                reader = csv.reader(f)
                csv_header = next(reader)
                if [h.lower() for h in csv_header] != [h.lower() for h in self.headers]:
                    messagebox.showerror("Error", "CSV header does not match table columns.")
                    return
                cur = self.conn.cursor()
                placeholders = ",".join(["?"]*len(self.headers))
                insert_sql = f"INSERT OR IGNORE INTO {self.current_table} ({', '.join(self.headers)}) VALUES ({placeholders})"
                rows = [row for row in reader if len(row) == len(self.headers)]
                cur.executemany(insert_sql, rows)
                self.conn.commit()
                self.load_table()
                messagebox.showinfo("Imported", f"Imported {len(rows)} rows from {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Error", f"Import failed: {e}")

    def rename_columns_dialog(self):
        if not self.current_table or not self.headers:
            messagebox.showerror("Error", "No table selected.")
            return
        dlg = tk.Toplevel(self.root)
        dlg.title(f"Rename Columns - {self.current_table}")
        entries = []
        for i, col in enumerate(self.headers):
            tk.Label(dlg, text=col).grid(row=i, column=0, sticky="w", padx=5, pady=2)
            e = tk.Entry(dlg)
            e.insert(0, col)
            e.grid(row=i, column=1, padx=5, pady=2)
            entries.append((col, e))
        def apply():
            changed = False
            for old, entry in entries:
                new = entry.get().strip()
                if new and new != old:
                    try:
                        self.conn.execute(f'ALTER TABLE {self.current_table} RENAME COLUMN "{old}" TO "{new}"')
                        changed = True
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to rename column {old}: {e}")
                        dlg.destroy()
                        return
            if changed:
                self.conn.commit()
                self.refresh_tables()
                self.load_table()
                messagebox.showinfo("Success", "Column names updated.")
            dlg.destroy()
        tk.Button(dlg, text="Apply", command=apply).grid(row=len(entries), column=0, columnspan=2, pady=8)

    def add_table_dialog(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("Add New Table")
        tk.Label(dlg, text="Table Name:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        name_entry = tk.Entry(dlg)
        name_entry.grid(row=0, column=1, padx=5, pady=2)
        tk.Label(dlg, text="Columns (e.g. id INTEGER PRIMARY KEY, name TEXT):").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        cols_entry = tk.Entry(dlg, width=40)
        cols_entry.grid(row=1, column=1, padx=5, pady=2)
        def create_tbl():
            tname = name_entry.get().strip()
            cols = cols_entry.get().strip()
            if not tname or not cols:
                messagebox.showerror("Error", "Table name and columns required.")
                return
            try:
                self.conn.execute(f'CREATE TABLE {tname} ({cols})')
                self.conn.commit()
                self.refresh_tables()
                messagebox.showinfo("Success", f"Table '{tname}' created.")
                dlg.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create table: {e}")
        tk.Button(dlg, text="Create Table", command=create_tbl).grid(row=2, column=0, columnspan=2, pady=8)

    def add_column_dialog(self):
        if not self.current_table:
            messagebox.showerror("Error", "No table selected.")
            return
        dlg = tk.Toplevel(self.root)
        dlg.title(f"Add Column - {self.current_table}")
        tk.Label(dlg, text="Column Name:").grid(row=0, column=0, padx=5, pady=2)
        name_entry = tk.Entry(dlg)
        name_entry.grid(row=0, column=1, padx=5, pady=2)
        tk.Label(dlg, text="Type (e.g. TEXT, INTEGER):").grid(row=1, column=0, padx=5, pady=2)
        type_entry = tk.Entry(dlg)
        type_entry.grid(row=1, column=1, padx=5, pady=2)
        def add_col():
            cname = name_entry.get().strip()
            ctype = type_entry.get().strip().upper()
            if not cname or not ctype:
                messagebox.showerror("Error", "Column name and type required.")
                return
            try:
                self.conn.execute(f'ALTER TABLE {self.current_table} ADD COLUMN "{cname}" {ctype}')
                self.conn.commit()
                self.refresh_tables()
                self.load_table()
                messagebox.showinfo("Success", f"Column '{cname}' added.")
                dlg.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add column: {e}")
        tk.Button(dlg, text="Add Column", command=add_col).grid(row=2, column=0, columnspan=2, pady=8)

    def delete_table_dialog(self):
        if not self.conn:
            messagebox.showerror("Error", "No database loaded.")
            return
        dlg = tk.Toplevel(self.root)
        dlg.title("Delete Table")
        tk.Label(dlg, text="Select table to delete:").pack(padx=5, pady=5)
        tables = self.table_combo["values"]
        sel = tk.StringVar(value=tables[0] if tables else "")
        combo = ttk.Combobox(dlg, values=tables, textvariable=sel, state="readonly")
        combo.pack(padx=5, pady=5)
        def delete_tbl():
            tname = sel.get()
            if not tname:
                messagebox.showerror("Error", "No table selected.")
                return
            if messagebox.askyesno("Confirm", f"Delete table '{tname}'? This cannot be undone."):
                try:
                    self.conn.execute(f'DROP TABLE "{tname}"')
                    self.conn.commit()
                    self.refresh_tables()
                    self.load_table()
                    messagebox.showinfo("Success", f"Table '{tname}' deleted.")
                    dlg.destroy()
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to delete table: {e}")
        tk.Button(dlg, text="Delete Table", command=delete_tbl).pack(pady=8)

    def rename_table_dialog(self):
        if not self.conn:
            messagebox.showerror("Error", "No database loaded.")
            return
        dlg = tk.Toplevel(self.root)
        dlg.title("Rename Table")
        tk.Label(dlg, text="Select table to rename:").grid(row=0, column=0, padx=5, pady=2)
        tables = self.table_combo["values"]
        sel = tk.StringVar(value=tables[0] if tables else "")
        combo = ttk.Combobox(dlg, values=tables, textvariable=sel, state="readonly")
        combo.grid(row=0, column=1, padx=5, pady=2)
        tk.Label(dlg, text="New name:").grid(row=1, column=0, padx=5, pady=2)
        name_entry = tk.Entry(dlg)
        name_entry.grid(row=1, column=1, padx=5, pady=2)
        def rename_tbl():
            old = sel.get()
            new = name_entry.get().strip()
            if not old or not new:
                messagebox.showerror("Error", "Both table and new name required.")
                return
            try:
                self.conn.execute(f'ALTER TABLE "{old}" RENAME TO "{new}"')
                self.conn.commit()
                self.refresh_tables()
                self.load_table()
                messagebox.showinfo("Success", f"Table '{old}' renamed to '{new}'.")
                dlg.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to rename table: {e}")
        tk.Button(dlg, text="Rename Table", command=rename_tbl).grid(row=2, column=0, columnspan=2, pady=8)

if __name__ == "__main__":
    root = tk.Tk()
    app = SQLiteGUI(root)
    root.mainloop()
