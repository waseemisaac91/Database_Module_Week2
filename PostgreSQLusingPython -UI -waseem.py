
#Database_Module_Week2
#Assigment-2
#PostgreSQL using Python  with Modern UI (Add,Update,Delete,Setect/Queries)
#Waseem Isaac

import sys
import os
import re
import csv
import json
import time
import psycopg2
from psycopg2 import Error
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QTabWidget, QComboBox, QHeaderView, QFrame, QDialog,
    QFormLayout, QDoubleSpinBox, QSpinBox, QDateEdit, QAbstractItemView,
    QPlainTextEdit, QScrollArea, QFileDialog, QCheckBox
)
from PyQt6.QtCore import Qt, QDate, QTimer
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont, QShortcut, QKeySequence

# ----------------------------------------------------------------------------
# Settings (saved next to this script; the password is NOT stored in the code)
# ----------------------------------------------------------------------------
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "db_settings.json")

DEFAULT_DB = {
    "host": "localhost",
    "port": "5432",
    "database": "emp_db",
    "user": "postgres",
    "password": "",
}

# Only used once to seed the "department_types" table if it is empty.
# After that, add / remove departments from the "Department Types" tab.
SEED_DEPARTMENTS = [
    ("Administrative", 11), ("Technology", 12), ("Operations", 13),
    ("Marketing", 14), ("Sales", 15), ("HR", 16), ("Finance", 17),
]

GENDERS = ["Male", "Female", "Other"]

MAX_RESULT_ROWS = 100000

# ----------------------------------------------------------------------------
# 10 Specific Queries (shown in the "Quick queries" dropdown of the SQL tab)
# ----------------------------------------------------------------------------
QUERY_TEMPLATES = {
    "1. Employees paid more than Rodney Weaver": (
        "SELECT first_name, last_name, salary FROM employees "
        "WHERE salary > (SELECT salary FROM employees "
        "WHERE first_name = 'Rodney' AND last_name = 'Weaver') ORDER BY salary DESC;"
    ),
    "2. Average, min, and max salaries": (
        "SELECT ROUND(AVG(salary), 2) AS average_salary, MIN(salary) AS min_salary, MAX(salary) AS max_salary FROM employees;"
    ),
    "3. Employees whose salary is more than 8700": (
        "SELECT first_name, last_name, salary FROM employees WHERE salary > 8700 ORDER BY salary DESC;"
    ),
    "4. Employees in Operations department": (
        "SELECT e.first_name, e.last_name FROM employees e "
        "JOIN departments d ON e.emp_id = d.emp_id WHERE d.dept_name = 'Operations';"
    ),
    "5. Employees in Technology department": (
        "SELECT e.first_name, e.last_name FROM employees e "
        "JOIN departments d ON e.emp_id = d.emp_id WHERE d.dept_name = 'Technology';"
    ),
    "6. Average salary of female employees": (
        "SELECT ROUND(AVG(salary), 2) AS average_female_salary FROM employees WHERE gender = 'Female';"
    ),
    "7. Average salary of each department": (
        "SELECT d.dept_name, ROUND(AVG(e.salary), 2) AS average_salary "
        "FROM employees e JOIN departments d ON e.emp_id = d.emp_id "
        "GROUP BY d.dept_name ORDER BY average_salary DESC;"
    ),
    "8. Oldest and newest employees": (
        "SELECT first_name, last_name, hire_date, 'Oldest' as type FROM employees "
        "WHERE hire_date = (SELECT MIN(hire_date) FROM employees) "
        "UNION ALL "
        "SELECT first_name, last_name, hire_date, 'Newest' as type FROM employees "
        "WHERE hire_date = (SELECT MAX(hire_date) FROM employees);"
    ),
    "9. Hiring date & dept of highest paid employee": (
        "SELECT e.first_name, e.last_name, e.hire_date, d.dept_name FROM employees e "
        "LEFT JOIN departments d ON e.emp_id = d.emp_id "
        "WHERE e.salary = (SELECT MAX(salary) FROM employees);"
    ),
    "10. Hiring date & dept of lowest paid employee": (
        "SELECT e.first_name, e.last_name, e.hire_date, COALESCE(d.dept_name, 'Unassigned') AS dept_name "
        "FROM employees e LEFT JOIN departments d ON e.emp_id = d.emp_id "
        "WHERE e.salary = (SELECT MIN(salary) FROM employees);"
    )
}


def load_config():
    cfg = dict(DEFAULT_DB)
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg.update(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    if os.environ.get("DB_PASSWORD"):
        cfg["password"] = os.environ["DB_PASSWORD"]
    return cfg


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


# ----------------------------------------------------------------------------
# Connection window (shown first, before the main window)
# ----------------------------------------------------------------------------
class SettingsDialog(QDialog):
    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connect to Database")
        self.setFixedWidth(460)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 24)
        layout.setSpacing(16)

        title = QLabel("🔌 Connect to Database")
        title.setObjectName("DialogTitle")
        subtitle = QLabel("Enter your PostgreSQL connection details to continue.")
        subtitle.setObjectName("SubHeader")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        self.host = QLineEdit(cfg["host"])
        self.port = QLineEdit(str(cfg["port"]))
        self.database = QLineEdit(cfg["database"])
        self.user = QLineEdit(cfg["user"])
        self.password = QLineEdit(cfg["password"])
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText("Password")
        form.addRow("🌐  Host", self.host)
        form.addRow("🔌  Port", self.port)
        form.addRow("🗄️  Database", self.database)
        form.addRow("👤  User", self.user)
        form.addRow("🔑  Password", self.password)
        layout.addLayout(form)

        self.remember = QCheckBox("Remember password on this computer")
        self.remember.setChecked(bool(cfg["password"]))
        layout.addWidget(self.remember)

        self.result_label = QLabel("")
        self.result_label.setWordWrap(True)
        layout.addWidget(self.result_label)

        buttons = QHBoxLayout()
        buttons.addStretch()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("SecondaryButton")
        btn_cancel.clicked.connect(self.reject)
        self.btn_connect = QPushButton("🔌 Connect")
        self.btn_connect.setDefault(True)
        self.btn_connect.clicked.connect(self.accept)
        buttons.addWidget(btn_cancel)
        buttons.addWidget(self.btn_connect)
        layout.addLayout(buttons)

        self.password.setFocus() if cfg["host"] and not cfg["password"] else self.btn_connect.setFocus()

    def values(self):
        return {
            "host": self.host.text().strip(),
            "port": self.port.text().strip(),
            "database": self.database.text().strip(),
            "user": self.user.text().strip(),
            "password": self.password.text(),
        }

    def saved_values(self):
        """Values written to db_settings.json (password only if 'remember' is ticked)."""
        v = self.values()
        if not self.remember.isChecked():
            v["password"] = ""
        return v

    def accept(self):
        """Only close the window when the connection really works."""
        self.btn_connect.setEnabled(False)
        self.btn_connect.setText("Connecting…")
        self.result_label.setStyleSheet("color: #8b93a7;")
        self.result_label.setText("⏳ Testing connection...")
        QApplication.processEvents()
        try:
            conn = psycopg2.connect(connect_timeout=5, **self.values())
            conn.close()
        except Error as e:
            self.result_label.setStyleSheet("color: #ef4444;")
            self.result_label.setText(f"❌ {str(e).strip()}")
            self.btn_connect.setEnabled(True)
            self.btn_connect.setText("🔌 Connect")
            return
        super().accept()


# ----------------------------------------------------------------------------
# SQL syntax highlighter for the query editor
# ----------------------------------------------------------------------------
class SqlHighlighter(QSyntaxHighlighter):
    KEYWORDS = (
        "SELECT FROM WHERE AND OR NOT IN IS NULL LIKE ILIKE BETWEEN ORDER BY GROUP HAVING LIMIT OFFSET "
        "JOIN LEFT RIGHT INNER OUTER FULL ON AS DISTINCT UNION ALL INSERT INTO VALUES UPDATE SET DELETE "
        "CREATE TABLE DROP ALTER ADD COLUMN INDEX VIEW COUNT SUM AVG MIN MAX ROUND CASE WHEN THEN ELSE END "
        "ASC DESC EXISTS WITH PRIMARY KEY FOREIGN REFERENCES DEFAULT TRUNCATE"
    ).split()

    def __init__(self, document):
        super().__init__(document)

        def fmt(color, bold=False):
            f = QTextCharFormat()
            f.setForeground(QColor(color))
            if bold:
                f.setFontWeight(QFont.Weight.Bold)
            return f

        self.rules = [
            (re.compile(r"\b(" + "|".join(self.KEYWORDS) + r")\b", re.IGNORECASE), fmt("#a5b4fc", True)),
            (re.compile(r"\b\d+(\.\d+)?\b"), fmt("#f59e0b")),
            (re.compile(r"'[^']*'"), fmt("#22c55e")),
            (re.compile(r"--[^\n]*"), fmt("#6b7280")),
        ]

    def highlightBlock(self, text):
        for rx, f in self.rules:
            for m in rx.finditer(text):
                self.setFormat(m.start(), m.end() - m.start(), f)


# ----------------------------------------------------------------------------
# Table with search filter + pagination
# ----------------------------------------------------------------------------
class PagedTable(QWidget):
    PAGE_SIZES = ["25", "50", "100", "250", "500", "All"]

    def __init__(self, headers, center_cols=(0,), right_cols=(), fit_columns=False, default_size="50"):
        super().__init__()
        self.center_cols = center_cols
        self.right_cols = right_cols
        self.fit_columns = fit_columns
        self.all_rows = []
        self.filtered = []
        self.page = 0
        self.filter_text = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.table = CRUDApp.make_table(headers)
        layout.addWidget(self.table, 1)

        # footer bar (fixed height so it never overlaps the table)
        self.bar = QFrame()
        self.bar.setObjectName("PagerBar")
        self.bar.setFixedHeight(56)
        bar = QHBoxLayout(self.bar)
        bar.setContentsMargins(14, 0, 14, 0)
        bar.setSpacing(6)

        lbl = QLabel("Rows per page")
        lbl.setObjectName("PagerInfo")
        self.size_combo = QComboBox()
        self.size_combo.addItems(self.PAGE_SIZES)
        self.size_combo.setCurrentText(default_size)
        self.size_combo.setFixedWidth(84)
        self.size_combo.currentIndexChanged.connect(self.on_size_changed)
        self.info = QLabel("")
        self.info.setObjectName("PagerInfo")

        self.btn_first = self._button("«", "First page", lambda: self.go(0))
        self.btn_prev = self._button("‹", "Previous page", lambda: self.go(self.page - 1))
        self.pages_box = QHBoxLayout()
        self.pages_box.setSpacing(4)
        self.btn_next = self._button("›", "Next page", lambda: self.go(self.page + 1))
        self.btn_last = self._button("»", "Last page", lambda: self.go(self.page_count() - 1))

        bar.addWidget(lbl)
        bar.addWidget(self.size_combo)
        bar.addSpacing(14)
        bar.addWidget(self.info)
        bar.addStretch()
        bar.addWidget(self.btn_first)
        bar.addWidget(self.btn_prev)
        bar.addLayout(self.pages_box)
        bar.addWidget(self.btn_next)
        bar.addWidget(self.btn_last)
        layout.addWidget(self.bar)
        self.render()

    def _button(self, text, tip, slot):
        b = QPushButton(text)
        b.setObjectName("PagerButton")
        b.setToolTip(tip)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.clicked.connect(slot)
        return b

    # ---- data
    def set_columns(self, headers):
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)

    def set_rows(self, rows):
        self.all_rows = [list(r) for r in rows]
        self.apply_filter()

    def set_filter(self, text):
        self.filter_text = text.lower().strip()
        self.page = 0
        self.apply_filter()

    def clear(self):
        self.set_columns([])
        self.set_rows([])

    def apply_filter(self):
        t = self.filter_text
        if t:
            self.filtered = [
                r for r in self.all_rows
                if any(t in ("" if v is None else str(v)).lower() for v in r)
            ]
        else:
            self.filtered = self.all_rows
        self.render()

    # ---- paging
    def page_size(self):
        text = self.size_combo.currentText()
        return None if text == "All" else int(text)

    def page_count(self):
        size = self.page_size()
        if size is None:
            return 1
        return max(1, -(-len(self.filtered) // size))

    def go(self, page):
        self.page = max(0, min(page, self.page_count() - 1))
        self.render()

    def on_size_changed(self):
        self.page = 0
        self.render()

    @staticmethod
    def page_numbers(count, current):
        """Page indexes to show, with None meaning an ellipsis: 1 … 4 5 6 … 20"""
        if count <= 7:
            return list(range(count))
        pages = {0, count - 1, current - 1, current, current + 1}
        if current <= 2:
            pages |= {1, 2, 3}
        if current >= count - 3:
            pages |= {count - 2, count - 3, count - 4}
        result, prev = [], None
        for p in sorted(x for x in pages if 0 <= x < count):
            if prev is not None and p - prev > 1:
                result.append(None)
            result.append(p)
            prev = p
        return result

    def rebuild_page_buttons(self, count):
        while self.pages_box.count():
            w = self.pages_box.takeAt(0).widget()
            if w:
                w.deleteLater()
        for p in self.page_numbers(count, self.page):
            if p is None:
                dots = QLabel("…")
                dots.setObjectName("PagerInfo")
                self.pages_box.addWidget(dots)
                continue
            b = QPushButton(str(p + 1))
            b.setObjectName("PagerNum")
            b.setProperty("active", p == self.page)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _checked=False, pg=p: self.go(pg))
            self.pages_box.addWidget(b)

    def render(self):
        total = len(self.filtered)
        size = self.page_size()
        count = self.page_count()
        self.page = max(0, min(self.page, count - 1))
        if size is None:
            start, end = 0, total
        else:
            start = self.page * size
            end = min(start + size, total)

        CRUDApp.fill_table(
            self.table, self.filtered[start:end],
            center_cols=self.center_cols, right_cols=self.right_cols,
        )
        if self.fit_columns:
            self.table.resizeColumnsToContents()

        text = f"Showing {start + 1 if total else 0}–{end} of {total}"
        if self.filter_text and total != len(self.all_rows):
            text += f"  (filtered from {len(self.all_rows)})"
        self.info.setText(text)

        self.rebuild_page_buttons(count)
        self.btn_first.setEnabled(self.page > 0)
        self.btn_prev.setEnabled(self.page > 0)
        self.btn_next.setEnabled(self.page < count - 1)
        self.btn_last.setEnabled(self.page < count - 1)


# ----------------------------------------------------------------------------
# Main window
# ----------------------------------------------------------------------------
class CRUDApp(QMainWindow):
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.emp_names = {}
        self.setWindowTitle("Employee & Department Manager")
        self.resize(1280, 920)
        self.emp_dept = {}
        self.last_error_code = None
        self.query_history = []
        self.last_result = ([], [])

        central = QWidget()
        central.setObjectName("Central")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(central)
        self.setCentralWidget(scroll)
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 20, 24, 12)
        root.setSpacing(16)

        root.addLayout(self.build_header())
        root.addLayout(self.build_stats())

        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_employees_tab(), "👨‍💼  Employees")
        self.tabs.addTab(self.create_departments_tab(), "🏢  Assign Departments")
        self.tabs.addTab(self.create_types_tab(), "🗂️  Department Types")
        self.tabs.addTab(self.create_query_tab(), "🧮  SQL Query")
        root.addWidget(self.tabs)

        self.statusBar().showMessage("Ready")
        QTimer.singleShot(0, self.startup)

    # ------------------------------------------------------------------ helpers
    def db(self, sql, params=(), fetch=False):
        """Run one statement (or a list of (sql, params)) in one transaction.
        Returns (ok, rows_or_error_message)."""
        statements = sql if isinstance(sql, list) else [(sql, params)]
        self.last_error_code = None
        conn = None
        try:
            conn = psycopg2.connect(connect_timeout=5, **self.cfg)
            rows = []
            with conn.cursor() as cur:
                for stmt, prm in statements:
                    cur.execute(stmt, prm)
                if fetch:
                    rows = cur.fetchall()
            conn.commit()
            return True, rows
        except Error as e:
            if conn:
                conn.rollback()
            code = getattr(e, "pgcode", None)
            self.last_error_code = code
            if code == "23505":
                msg = "This record already exists (duplicate key)."
            elif code == "23503":
                msg = "This record is linked to other data and cannot be changed or removed."
            elif code in ("22P02", "22007", "22008"):
                msg = "One of the values has an invalid format."
            else:
                msg = str(e).strip()
            return False, msg
        finally:
            if conn:
                conn.close()

    def notify(self, text):
        self.statusBar().showMessage(text, 5000)

    def error(self, text):
        QMessageBox.critical(self, "Error", text)

    def confirm(self, text):
        reply = QMessageBox.question(
            self, "Please confirm", text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes

    @staticmethod
    def labeled(text, widget):
        box = QVBoxLayout()
        box.setSpacing(4)
        lbl = QLabel(text)
        lbl.setObjectName("FieldLabel")
        box.addWidget(lbl)
        box.addWidget(widget)
        return box

    @staticmethod
    def make_table(headers):
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(38)
        table.setMinimumHeight(360)
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        return table

    @staticmethod
    def fill_table(table, rows, center_cols=(0,), right_cols=()):
        table.blockSignals(True)
        table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                item = QTableWidgetItem("" if value is None else str(value))
                if c in center_cols:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                elif c in right_cols:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                table.setItem(r, c, item)
        table.blockSignals(False)

    @staticmethod
    def filter_table(table, text):
        text = text.lower().strip()
        for r in range(table.rowCount()):
            match = any(
                table.item(r, c) and text in table.item(r, c).text().lower()
                for c in range(table.columnCount())
            )
            table.setRowHidden(r, not match)

    # ------------------------------------------------------------------ header / stats
    def build_header(self):
        row = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(2)
        h = QLabel("👥 Employee & Department Manager")
        h.setObjectName("Header")
        s = QLabel("Manage employees, assign departments and maintain department types")
        s.setObjectName("SubHeader")
        titles.addWidget(h)
        titles.addWidget(s)
        row.addLayout(titles)
        row.addStretch()

        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.setObjectName("SecondaryButton")
        btn_refresh.clicked.connect(self.refresh_all)
        row.addWidget(btn_refresh)
        return row

    def build_stats(self):
        row = QHBoxLayout()
        row.setSpacing(14)
        self.stat_labels = {}
        for key, icon, title in [
            ("employees", "👥", "Employees"),
            ("avg_salary", "💰", "Average Salary"),
            ("types", "🏢", "Department Types"),
            ("assigned", "✅", "Assigned Employees"),
        ]:
            card = QFrame()
            card.setObjectName("StatCard")
            lay = QVBoxLayout(card)
            lay.setContentsMargins(18, 14, 18, 14)
            lay.setSpacing(2)
            value = QLabel("0")
            value.setObjectName("StatValue")
            caption = QLabel(f"{icon}  {title}")
            caption.setObjectName("StatTitle")
            lay.addWidget(value)
            lay.addWidget(caption)
            self.stat_labels[key] = value
            row.addWidget(card)
        return row

    def refresh_stats(self):
        ok, rows = self.db("SELECT COUNT(*), COALESCE(AVG(salary), 0) FROM employees", fetch=True)
        if ok and rows:
            self.stat_labels["employees"].setText(str(rows[0][0]))
            self.stat_labels["avg_salary"].setText(f"{float(rows[0][1]):,.0f}")
        ok, rows = self.db("SELECT COUNT(*) FROM department_types", fetch=True)
        if ok:
            self.stat_labels["types"].setText(str(rows[0][0]))
        ok, rows = self.db("SELECT COUNT(DISTINCT emp_id) FROM departments", fetch=True)
        if ok:
            self.stat_labels["assigned"].setText(str(rows[0][0]))

    # ------------------------------------------------------------------ employees tab
    def create_employees_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        form_frame = QFrame()
        form_frame.setObjectName("FormFrame")
        form = QVBoxLayout(form_frame)
        form.setContentsMargins(18, 16, 18, 16)
        form.setSpacing(12)

        self.emp_id = QLineEdit(placeholderText="e.g. 12345")
        self.emp_first = QLineEdit(placeholderText="First name")
        self.emp_last = QLineEdit(placeholderText="Last name")
        self.emp_gender = QComboBox()
        self.emp_gender.addItems(GENDERS)

        self.emp_salary = QDoubleSpinBox()
        self.emp_salary.setRange(0, 1_000_000_000)
        self.emp_salary.setDecimals(2)
        self.emp_salary.setGroupSeparatorShown(True)
        self.emp_salary.setPrefix("💵 ")
        self.emp_job = QComboBox()
        self.emp_job.setEditable(True)
        self.emp_job.lineEdit().setPlaceholderText("Select or type a job title")
        self.emp_date = QDateEdit(QDate.currentDate())
        self.emp_date.setCalendarPopup(True)
        self.emp_date.setDisplayFormat("yyyy-MM-dd")

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(12)
        id_box = QWidget()
        id_row = QHBoxLayout(id_box)
        id_row.setContentsMargins(0, 0, 0, 0)
        id_row.setSpacing(6)
        self.btn_next_id = QPushButton("🎲")
        self.btn_next_id.setObjectName("SecondaryButton")
        self.btn_next_id.setToolTip("Suggest the next free employee ID")
        self.btn_next_id.setFixedWidth(46)
        self.btn_next_id.clicked.connect(self.suggest_emp_id)
        id_row.addWidget(self.emp_id)
        id_row.addWidget(self.btn_next_id)
        grid.addLayout(self.labeled("🆔 Employee ID", id_box), 0, 0)
        grid.addLayout(self.labeled("🙂 First Name", self.emp_first), 0, 1)
        grid.addLayout(self.labeled("🙂 Last Name", self.emp_last), 0, 2)
        grid.addLayout(self.labeled("⚧ Gender", self.emp_gender), 0, 3)
        grid.addLayout(self.labeled("💰 Salary", self.emp_salary), 1, 0)
        grid.addLayout(self.labeled("💼 Job Title", self.emp_job), 1, 1, 1, 2)
        grid.addLayout(self.labeled("📅 Hire Date", self.emp_date), 1, 3)
        for c in range(4):
            grid.setColumnStretch(c, 1)
        form.addLayout(grid)

        buttons = QHBoxLayout()
        self.emp_mode_label = QLabel("➕ New employee")
        self.emp_mode_label.setObjectName("ModeLabel")
        self.btn_add_emp = QPushButton("➕ Add")
        self.btn_add_emp.clicked.connect(self.add_employee)
        self.btn_update_emp = QPushButton("✏️ Update")
        self.btn_update_emp.setObjectName("WarnButton")
        self.btn_update_emp.clicked.connect(self.update_employee)
        self.btn_update_emp.setEnabled(False)
        self.btn_delete_emp = QPushButton("🗑️ Delete")
        self.btn_delete_emp.setObjectName("DeleteButton")
        self.btn_delete_emp.clicked.connect(self.delete_employee)
        btn_clear = QPushButton("🧹 Clear")
        btn_clear.setObjectName("SecondaryButton")
        btn_clear.clicked.connect(self.clear_emp_form)
        buttons.addWidget(self.emp_mode_label)
        buttons.addStretch()
        for b in (btn_clear, self.btn_add_emp, self.btn_update_emp, self.btn_delete_emp):
            buttons.addWidget(b)
        form.addLayout(buttons)
        layout.addWidget(form_frame)

        self.emp_search = QLineEdit(placeholderText="🔍 Search employees...")
        self.emp_search.textChanged.connect(lambda t: self.emp_pager.set_filter(t))
        layout.addWidget(self.emp_search)

        self.emp_pager = PagedTable(
            ["ID", "First Name", "Last Name", "Salary", "Job Title", "Gender", "Hire Date"],
            center_cols=(0, 5, 6), right_cols=(3,),
        )
        self.emp_table = self.emp_pager.table
        self.emp_table.itemSelectionChanged.connect(self.on_emp_selected)
        layout.addWidget(self.emp_pager)
        return page

    def set_emp_edit_mode(self, editing):
        self.emp_id.setReadOnly(editing)
        self.btn_next_id.setEnabled(not editing)
        self.btn_add_emp.setEnabled(not editing)
        self.btn_update_emp.setEnabled(editing)
        self.emp_mode_label.setText("✏️ Editing selected employee" if editing else "➕ New employee")

    def on_emp_selected(self):
        row = self.emp_table.currentRow()
        if row < 0 or not self.emp_table.selectedItems():
            return
        t = lambda c: self.emp_table.item(row, c).text()
        self.emp_id.setText(t(0))
        self.emp_first.setText(t(1))
        self.emp_last.setText(t(2))
        try:
            self.emp_salary.setValue(float(t(3).replace(",", "")))
        except ValueError:
            self.emp_salary.setValue(0)
        self.emp_job.setCurrentText(t(4))
        self.emp_gender.setCurrentText(t(5))
        d = QDate.fromString(t(6)[:10], "yyyy-MM-dd")
        self.emp_date.setDate(d if d.isValid() else QDate.currentDate())
        self.set_emp_edit_mode(True)

    def clear_emp_form(self):
        self.emp_table.clearSelection()
        self.emp_id.clear()
        self.emp_first.clear()
        self.emp_last.clear()
        self.emp_salary.setValue(0)
        self.emp_job.setCurrentText("")
        self.emp_gender.setCurrentIndex(0)
        self.emp_date.setDate(QDate.currentDate())
        self.set_emp_edit_mode(False)
        self.suggest_emp_id()

    def suggest_emp_id(self):
        """Fill the ID field with the next free numeric ID (silently skipped if IDs aren't numeric)."""
        ok, rows = self.db("SELECT COALESCE(MAX(emp_id::bigint), 0) + 1 FROM employees", fetch=True)
        if ok and rows:
            self.emp_id.setText(str(rows[0][0]))

    def emp_form_values(self):
        emp_id = self.emp_id.text().strip()
        first = self.emp_first.text().strip()
        last = self.emp_last.text().strip()
        if not emp_id or not first or not last:
            QMessageBox.warning(self, "Missing data", "Employee ID, first name and last name are required.")
            return None
        return (
            emp_id, first, last, self.emp_salary.value(),
            self.emp_job.currentText().strip(), self.emp_gender.currentText(),
            self.emp_date.date().toString("yyyy-MM-dd"),
        )

    def load_job_titles(self):
        ok, rows = self.db(
            "SELECT DISTINCT job_title FROM employees WHERE job_title IS NOT NULL ORDER BY job_title",
            fetch=True,
        )
        if not ok:
            return
        current = self.emp_job.currentText()
        self.emp_job.clear()
        self.emp_job.addItems([r[0] for r in rows])
        self.emp_job.setCurrentText(current)

    def load_employees(self):
        ok, rows = self.db(
            "SELECT emp_id, first_name, last_name, salary, job_title, gender, hire_date "
            "FROM employees ORDER BY emp_id",
            fetch=True,
        )
        if not ok:
            self.error(f"Failed to load employees:\n{rows}")
            return
        self.emp_names = {r[0]: f"{r[1]} {r[2]}" for r in rows}
        display = []
        for r in rows:
            r = list(r)
            try:
                r[3] = f"{float(r[3]):,.2f}"
            except (TypeError, ValueError):
                pass
            display.append(r)
        self.emp_pager.set_rows(display)

    def add_employee(self):
        values = self.emp_form_values()
        if not values:
            return
        emp_id, first, last = values[0], values[1], values[2]
        ok, rows = self.db(
            "SELECT first_name, last_name FROM employees WHERE emp_id::text = %s", (emp_id,), fetch=True
        )
        if ok and rows:
            QMessageBox.warning(
                self, "Duplicate ID",
                f"Employee ID {emp_id} is already used by {rows[0][0]} {rows[0][1]}.\n\n"
                "Please choose another ID (the 🎲 button suggests the next free one).",
            )
            return
        ok, rows = self.db(
            "SELECT emp_id FROM employees WHERE LOWER(TRIM(first_name)) = LOWER(%s) "
            "AND LOWER(TRIM(last_name)) = LOWER(%s)", (first, last), fetch=True,
        )
        if ok and rows:
            ids = ", ".join(str(r[0]) for r in rows)
            if not self.confirm(
                f"An employee named {first} {last} already exists (ID {ids}).\n\nAdd another one anyway?"
            ):
                return
        ok, res = self.db(
            "INSERT INTO employees (emp_id, first_name, last_name, salary, job_title, gender, hire_date) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            values,
        )
        if not ok:
            self.error(f"Failed to add employee:\n{res}")
            return
        self.notify("✅ Employee added successfully")
        self.clear_emp_form()
        self.refresh_all()

    def update_employee(self):
        values = self.emp_form_values()
        if not values:
            return
        emp_id, first, last, salary, job, gender, hire = values
        ok, rows = self.db(
            "SELECT emp_id FROM employees WHERE LOWER(TRIM(first_name)) = LOWER(%s) "
            "AND LOWER(TRIM(last_name)) = LOWER(%s) AND emp_id::text <> %s", (first, last, emp_id), fetch=True,
        )
        if ok and rows:
            ids = ", ".join(str(r[0]) for r in rows)
            if not self.confirm(
                f"Another employee named {first} {last} already exists (ID {ids}).\n\nSave anyway?"
            ):
                return
        ok, res = self.db(
            "UPDATE employees SET first_name=%s, last_name=%s, salary=%s, job_title=%s, "
            "gender=%s, hire_date=%s WHERE emp_id=%s",
            (first, last, salary, job, gender, hire, emp_id),
        )
        if not ok:
            self.error(f"Failed to update employee:\n{res}")
            return
        self.notify("✏️ Employee updated successfully")
        self.clear_emp_form()
        self.refresh_all()

    def delete_employee(self):
        row = self.emp_table.currentRow()
        if row < 0 or not self.emp_table.selectedItems():
            QMessageBox.warning(self, "Warning", "Please select an employee to delete.")
            return
        emp_id = self.emp_table.item(row, 0).text()
        if not self.confirm(
            f"Delete employee {emp_id}?\nTheir department assignments will be removed too."
        ):
            return
        ok, res = self.db([
            ("DELETE FROM departments WHERE emp_id = %s", (emp_id,)),
            ("DELETE FROM employees WHERE emp_id = %s", (emp_id,)),
        ])
        if not ok:
            self.error(f"Failed to delete employee:\n{res}")
            return
        self.notify("🗑️ Employee deleted")
        self.clear_emp_form()
        self.refresh_all()

    # ------------------------------------------------------------------ assign departments tab
    def create_departments_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        form_frame = QFrame()
        form_frame.setObjectName("FormFrame")
        form = QVBoxLayout(form_frame)
        form.setContentsMargins(18, 16, 18, 16)
        form.setSpacing(12)

        self.dept_emp_combo = QComboBox()
        self.dept_emp_name = QLabel("—")
        self.dept_emp_name.setObjectName("InfoLabel")
        self.dept_name_combo = QComboBox()
        self.dept_id_edit = QLineEdit()
        self.dept_id_edit.setReadOnly(True)

        self.dept_emp_combo.currentIndexChanged.connect(self.update_emp_name_label)
        self.dept_name_combo.currentIndexChanged.connect(self.update_dept_id)

        row = QHBoxLayout()
        row.setSpacing(14)
        row.addLayout(self.labeled("🆔 Employee ID", self.dept_emp_combo), 1)
        row.addLayout(self.labeled("🙂 Employee Name", self.dept_emp_name), 1)
        row.addLayout(self.labeled("🏢 Department", self.dept_name_combo), 1)
        row.addLayout(self.labeled("🔢 Dept ID", self.dept_id_edit), 1)
        form.addLayout(row)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.btn_add_dept = QPushButton("➕ Assign Department")
        self.btn_add_dept.clicked.connect(self.add_department)
        self.btn_delete_dept = QPushButton("🗑️ Remove Selected")
        self.btn_delete_dept.setObjectName("DeleteButton")
        self.btn_delete_dept.clicked.connect(self.delete_department)
        buttons.addWidget(self.btn_add_dept)
        buttons.addWidget(self.btn_delete_dept)
        form.addLayout(buttons)
        layout.addWidget(form_frame)

        self.dept_search = QLineEdit(placeholderText="🔍 Search assignments...")
        self.dept_search.textChanged.connect(lambda t: self.dept_pager.set_filter(t))
        layout.addWidget(self.dept_search)

        self.dept_pager = PagedTable(["Emp ID", "Employee", "Department", "Dept ID"], center_cols=(0, 3))
        self.dept_table = self.dept_pager.table
        layout.addWidget(self.dept_pager)
        return page

    def update_emp_name_label(self):
        emp_id = self.dept_emp_combo.currentData()
        if emp_id is None:
            self.dept_emp_name.setText("—")
            return
        name = self.emp_names.get(emp_id, "—")
        dept = self.emp_dept.get(str(emp_id))
        self.dept_emp_name.setText(f"{name}  ·  🏢 {dept}" if dept else f"{name}  ·  ⚪ no department")

    def update_dept_id(self):
        dept_id = self.dept_name_combo.currentData()
        self.dept_id_edit.setText("" if dept_id is None else str(dept_id))

    def refresh_emp_combo(self):
        previous = self.dept_emp_combo.currentData()
        self.dept_emp_combo.blockSignals(True)
        self.dept_emp_combo.clear()
        if not self.emp_names:
            self.dept_emp_combo.addItem("No employees found", None)
        else:
            for emp_id in self.emp_names:
                self.dept_emp_combo.addItem(str(emp_id), emp_id)
            idx = self.dept_emp_combo.findData(previous)
            if idx >= 0:
                self.dept_emp_combo.setCurrentIndex(idx)
        self.dept_emp_combo.blockSignals(False)
        self.update_emp_name_label()

    def refresh_dept_combo(self, types):
        previous = self.dept_name_combo.currentData()
        self.dept_name_combo.blockSignals(True)
        self.dept_name_combo.clear()
        if not types:
            self.dept_name_combo.addItem("No department types", None)
        else:
            for dept_id, name in types:
                self.dept_name_combo.addItem(name, dept_id)
            idx = self.dept_name_combo.findData(previous)
            if idx >= 0:
                self.dept_name_combo.setCurrentIndex(idx)
        self.dept_name_combo.blockSignals(False)
        self.update_dept_id()

    def load_departments(self):
        ok, rows = self.db(
            "SELECT d.emp_id, e.first_name || ' ' || e.last_name, d.dept_name, d.dept_id "
            "FROM departments d LEFT JOIN employees e ON e.emp_id::text = d.emp_id::text "
            "ORDER BY d.emp_id",
            fetch=True,
        )
        if not ok:
            self.error(f"Failed to load departments:\n{rows}")
            return
        self.dept_pager.set_rows(rows)
        self.emp_dept = {}
        for r in rows:
            key = str(r[0])
            self.emp_dept[key] = f"{self.emp_dept[key]}, {r[2]}" if key in self.emp_dept else str(r[2])
        self.update_emp_name_label()

    def add_department(self):
        emp_id = self.dept_emp_combo.currentData()
        dept_id = self.dept_name_combo.currentData()
        dept_name = self.dept_name_combo.currentText()
        if emp_id is None or dept_id is None:
            QMessageBox.warning(self, "Warning", "Please select a valid employee and department.")
            return
        ok, rows = self.db(
            "SELECT 1 FROM departments WHERE emp_id::text = %s AND dept_id::text = %s",
            (str(emp_id), str(dept_id)), fetch=True,
        )
        if ok and rows:
            QMessageBox.information(
                self, "Already assigned", f"Employee {emp_id} is already in {dept_name}."
            )
            return
        ok, res = self.db(
            "INSERT INTO departments (emp_id, dept_name, dept_id) VALUES (%s, %s, %s)",
            (emp_id, dept_name, dept_id),
        )
        if not ok:
            if self.last_error_code == "23505":
                self.handle_existing_assignment(emp_id, dept_id, dept_name)
            else:
                self.error(f"Failed to assign department:\n{res}")
            return
        self.notify(f"✅ {dept_name} assigned to employee {emp_id}")
        self.refresh_all()

    def handle_existing_assignment(self, emp_id, dept_id, dept_name):
        """The employee already has a department: offer to change it instead of failing."""
        ok, rows = self.db(
            "SELECT dept_name, dept_id FROM departments WHERE emp_id::text = %s",
            (str(emp_id),), fetch=True,
        )
        if not ok or not rows:
            self.error("This assignment already exists.")
            return
        if any(str(r[1]) == str(dept_id) for r in rows):
            QMessageBox.information(
                self, "Already assigned", f"Employee {emp_id} is already in {dept_name}."
            )
            return
        current = ", ".join(str(r[0]) for r in rows)
        name = self.emp_names.get(emp_id, "")
        if not self.confirm(
            f"Employee {emp_id} {name} is already in “{current}”.\n\n"
            f"Change their department to “{dept_name}”?"
        ):
            return
        ok, res = self.db(
            "UPDATE departments SET dept_name = %s, dept_id = %s WHERE emp_id::text = %s",
            (dept_name, dept_id, str(emp_id)),
        )
        if not ok:
            self.error(f"Failed to change department:\n{res}")
            return
        self.notify(f"🔁 Employee {emp_id} moved to {dept_name}")
        self.refresh_all()

    def delete_department(self):
        row = self.dept_table.currentRow()
        if row < 0 or not self.dept_table.selectedItems():
            QMessageBox.warning(self, "Warning", "Please select an assignment to remove.")
            return
        emp_id = self.dept_table.item(row, 0).text()
        dept_id = self.dept_table.item(row, 3).text()
        if not self.confirm(f"Remove department {dept_id} from employee {emp_id}?"):
            return
        ok, res = self.db(
            "DELETE FROM departments WHERE emp_id::text = %s AND dept_id::text = %s",
            (emp_id, dept_id),
        )
        if not ok:
            self.error(f"Failed to remove department:\n{res}")
            return
        self.notify("🗑️ Department assignment removed")
        self.refresh_all()

    # ------------------------------------------------------------------ department types tab
    def create_types_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        form_frame = QFrame()
        form_frame.setObjectName("FormFrame")
        form = QVBoxLayout(form_frame)
        form.setContentsMargins(18, 16, 18, 16)
        form.setSpacing(12)

        self.type_id = QSpinBox()
        self.type_id.setRange(1, 999999)
        self.type_name = QLineEdit(placeholderText="e.g. Legal, Research, Support")

        row = QHBoxLayout()
        row.setSpacing(14)
        row.addLayout(self.labeled("🔢 Department ID", self.type_id), 1)
        row.addLayout(self.labeled("🏢 Department Name", self.type_name), 3)
        form.addLayout(row)

        buttons = QHBoxLayout()
        hint = QLabel("💡 Types added here appear in the “Assign Departments” list.")
        hint.setObjectName("SubHeader")
        buttons.addWidget(hint)
        buttons.addStretch()
        btn_add = QPushButton("➕ Add Type")
        btn_add.clicked.connect(self.add_type)
        btn_delete = QPushButton("🗑️ Delete Selected")
        btn_delete.setObjectName("DeleteButton")
        btn_delete.clicked.connect(self.delete_type)
        buttons.addWidget(btn_add)
        buttons.addWidget(btn_delete)
        form.addLayout(buttons)
        layout.addWidget(form_frame)

        self.type_pager = PagedTable(["Dept ID", "Department Name", "Employees Assigned"], center_cols=(0, 2))
        self.type_table = self.type_pager.table
        layout.addWidget(self.type_pager)
        return page

    def load_types(self):
        ok, rows = self.db(
            "SELECT t.dept_id, t.dept_name, COUNT(d.emp_id) "
            "FROM department_types t "
            "LEFT JOIN departments d ON d.dept_id::text = t.dept_id::text "
            "GROUP BY t.dept_id, t.dept_name ORDER BY t.dept_id",
            fetch=True,
        )
        if not ok:
            self.error(f"Failed to load department types:\n{rows}")
            return
        self.type_pager.set_rows(rows)
        self.refresh_dept_combo([(r[0], r[1]) for r in rows])
        self.type_id.setValue((max((r[0] for r in rows), default=10)) + 1)

    def add_type(self):
        name = self.type_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing data", "Please enter a department name.")
            return
        dept_id = self.type_id.value()
        ok, rows = self.db(
            "SELECT dept_name FROM department_types WHERE dept_id = %s", (dept_id,), fetch=True
        )
        if ok and rows:
            ok2, mx = self.db("SELECT COALESCE(MAX(dept_id), 0) + 1 FROM department_types", fetch=True)
            nxt = mx[0][0] if ok2 and mx else dept_id + 1
            self.type_id.setValue(nxt)
            QMessageBox.warning(
                self, "Duplicate Department ID",
                f"Department ID {dept_id} is already used by “{rows[0][0]}”.\n\n"
                f"The ID was changed to the next free one ({nxt}). Click Add Type again.",
            )
            return
        ok, rows = self.db(
            "SELECT dept_id FROM department_types WHERE LOWER(TRIM(dept_name)) = LOWER(%s)",
            (name,), fetch=True,
        )
        if ok and rows:
            QMessageBox.warning(
                self, "Duplicate Department Name",
                f"A department named “{name}” already exists (ID {rows[0][0]}).",
            )
            return
        ok, res = self.db(
            "INSERT INTO department_types (dept_id, dept_name) VALUES (%s, %s)",
            (dept_id, name),
        )
        if not ok:
            self.error(f"Failed to add department type:\n{res}")
            return
        self.type_name.clear()
        self.notify(f"✅ Department type “{name}” added")
        self.refresh_all()

    def delete_type(self):
        row = self.type_table.currentRow()
        if row < 0 or not self.type_table.selectedItems():
            QMessageBox.warning(self, "Warning", "Please select a department type to delete.")
            return
        dept_id = self.type_table.item(row, 0).text()
        name = self.type_table.item(row, 1).text()
        used = int(self.type_table.item(row, 2).text() or 0)
        if used > 0:
            QMessageBox.warning(
                self, "In use",
                f"“{name}” is assigned to {used} employee(s).\nRemove those assignments first.",
            )
            return
        if not self.confirm(f"Delete department type “{name}” (ID {dept_id})?"):
            return
        ok, res = self.db("DELETE FROM department_types WHERE dept_id = %s", (dept_id,))
        if not ok:
            self.error(f"Failed to delete department type:\n{res}")
            return
        self.notify("🗑️ Department type deleted")
        self.refresh_all()

    # ------------------------------------------------------------------ SQL query tab
    def create_query_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        frame = QFrame()
        frame.setObjectName("FormFrame")
        box = QVBoxLayout(frame)
        box.setContentsMargins(18, 16, 18, 16)
        box.setSpacing(12)

        top = QHBoxLayout()
        top.setSpacing(12)
        self.query_templates = QComboBox()
        self.query_templates.addItem("📌 Quick queries...")
        self.query_templates.addItems(list(QUERY_TEMPLATES.keys()))
        self.query_templates.activated.connect(self.on_template_chosen)
        self.query_history_combo = QComboBox()
        self.query_history_combo.addItem("🕘 History...")
        self.query_history_combo.activated.connect(self.on_history_chosen)
        self.chk_readonly = QCheckBox("🔒 Read-only mode")
        self.chk_readonly.setChecked(True)
        self.chk_readonly.setToolTip("When on, only queries that read data are allowed.")
        top.addWidget(self.query_templates, 1)
        top.addWidget(self.query_history_combo, 1)
        top.addStretch()
        top.addWidget(self.chk_readonly)
        box.addLayout(top)

        self.query_edit = QPlainTextEdit()
        self.query_edit.setObjectName("QueryEditor")
        self.query_edit.setPlaceholderText("Write your SQL here...   (Ctrl+Enter or F5 to run)")
        self.query_edit.setPlainText(next(iter(QUERY_TEMPLATES.values())))
        self.query_edit.setMinimumHeight(170)
        mono = QFont("Consolas")
        mono.setStyleHint(QFont.StyleHint.Monospace)
        mono.setPointSize(11)
        self.query_edit.setFont(mono)
        self.query_highlighter = SqlHighlighter(self.query_edit.document())
        box.addWidget(self.query_edit)
        for key in ("Ctrl+Return", "Ctrl+Enter", "F5"):
            QShortcut(QKeySequence(key), self.query_edit, activated=self.run_query)

        buttons = QHBoxLayout()
        self.query_status = QLabel("Write a query and press Run.")
        self.query_status.setObjectName("SubHeader")
        buttons.addWidget(self.query_status)
        buttons.addStretch()
        btn_clear = QPushButton("🧹 Clear")
        btn_clear.setObjectName("SecondaryButton")
        btn_clear.clicked.connect(lambda: self.query_edit.clear())
        btn_export = QPushButton("📤 Export CSV")
        btn_export.setObjectName("SecondaryButton")
        btn_export.clicked.connect(self.export_csv)
        btn_run = QPushButton("▶️ Run Query")
        btn_run.clicked.connect(self.run_query)
        buttons.addWidget(btn_clear)
        buttons.addWidget(btn_export)
        buttons.addWidget(btn_run)
        box.addLayout(buttons)
        layout.addWidget(frame)

        self.result_pager = PagedTable([], center_cols=(), fit_columns=True, default_size="100")
        self.result_table = self.result_pager.table
        self.result_table.setMinimumHeight(360)
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.result_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.result_pager)
        return page

    def on_template_chosen(self, index):
        if index > 0:
            self.query_edit.setPlainText(QUERY_TEMPLATES[self.query_templates.itemText(index)])

    def on_history_chosen(self, index):
        if index > 0:
            self.query_edit.setPlainText(self.query_history[index - 1])

    def add_to_history(self, sql):
        if sql in self.query_history:
            self.query_history.remove(sql)
        self.query_history.insert(0, sql)
        del self.query_history[20:]
        self.query_history_combo.clear()
        self.query_history_combo.addItem("🕘 History...")
        for q in self.query_history:
            one_line = " ".join(q.split())
            self.query_history_combo.addItem(one_line[:90] + ("…" if len(one_line) > 90 else ""))

    def set_query_status(self, text, ok=True):
        self.query_status.setStyleSheet(f"color: {'#22c55e' if ok else '#ef4444'};")
        self.query_status.setText(text)

    def run_query(self):
        sql = self.query_edit.toPlainText().strip()
        if not sql:
            return
        readonly = self.chk_readonly.isChecked()
        if not readonly and re.search(r"\b(delete|update|drop|truncate|alter|insert|create)\b", sql, re.I):
            if not self.confirm("This query can change or delete data.\n\nRun it anyway?"):
                return

        conn = None
        start = time.perf_counter()
        try:
            conn = psycopg2.connect(connect_timeout=5, **self.cfg)
            conn.set_session(readonly=readonly)
            with conn.cursor() as cur:
                cur.execute(sql)
                if cur.description:
                    cols = [d[0] for d in cur.description]
                    rows = cur.fetchmany(MAX_RESULT_ROWS)
                    truncated = cur.fetchone() is not None
                    affected = None
                else:
                    cols, rows, truncated, affected = [], [], False, cur.rowcount
            conn.commit()
        except Error as e:
            if conn:
                conn.rollback()
            self.set_query_status(f"❌ {str(e).strip()}", ok=False)
            return
        finally:
            if conn:
                conn.close()

        elapsed = (time.perf_counter() - start) * 1000
        self.add_to_history(sql)

        if cols:
            display = [["NULL" if v is None else v for v in row] for row in rows]
            self.result_pager.set_columns(cols)
            self.result_pager.set_rows(display)
            self.last_result = (cols, rows)
            note = f" (showing first {MAX_RESULT_ROWS})" if truncated else ""
            self.set_query_status(f"✅ {len(rows)} row(s) in {elapsed:.0f} ms{note}")
        else:
            self.result_pager.clear()
            self.last_result = ([], [])
            self.set_query_status(f"✅ Command completed — {affected} row(s) affected ({elapsed:.0f} ms)")
            if not readonly:
                self.refresh_all()

    def export_csv(self):
        cols, rows = self.last_result
        if not cols:
            QMessageBox.information(self, "Nothing to export", "Run a query that returns rows first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", "query_result.csv", "CSV files (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(cols)
                writer.writerows(rows)
            self.notify(f"📤 Exported {len(rows)} rows to {path}")
        except OSError as e:
            self.error(f"Could not write the file:\n{e}")

    # ------------------------------------------------------------------ startup / refresh
    def ensure_schema(self):
        ok, res = self.db(
            "CREATE TABLE IF NOT EXISTS department_types ("
            "dept_id INTEGER PRIMARY KEY, dept_name VARCHAR(100) UNIQUE NOT NULL)"
        )
        if not ok:
            self.error(f"Could not create department_types table:\n{res}")
            return
        ok, rows = self.db("SELECT COUNT(*) FROM department_types", fetch=True)
        if ok and rows[0][0] == 0:
            self.db([
                ("INSERT INTO department_types (dept_id, dept_name) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                 (dept_id, name))
                for name, dept_id in SEED_DEPARTMENTS
            ])

    def startup(self):
        self.ensure_schema()
        self.refresh_all()
        if not self.emp_id.text():
            self.suggest_emp_id()

    def refresh_all(self):
        self.load_employees()
        self.load_job_titles()
        self.load_types()
        self.refresh_emp_combo()
        self.load_departments()
        self.refresh_stats()

    # ------------------------------------------------------------------ style
    @staticmethod
    def get_stylesheet():
        return """
        QMainWindow, QDialog { background-color: #0f1117; }
        QWidget { color: #e6e8ef; font-family: 'Segoe UI', 'Inter', 'Helvetica Neue', sans-serif; font-size: 13px; }

        QLabel#Header { font-size: 24px; font-weight: 700; color: #ffffff; }
        QLabel#SubHeader { color: #8b93a7; font-size: 12px; }
        QLabel#DialogTitle { font-size: 18px; font-weight: 700; color: #ffffff; }
        QLabel#FieldLabel { color: #8b93a7; font-size: 12px; font-weight: 600; }
        QLabel#ModeLabel { color: #a5b4fc; font-weight: 600; }
        QLabel#InfoLabel { background-color: #232838; border: 1px solid #2f3547; border-radius: 8px;
                           padding: 9px 12px; color: #e6e8ef; }

        QFrame#StatCard { background-color: #171a23; border: 1px solid #262b3a; border-radius: 12px; }
        QLabel#StatValue { font-size: 26px; font-weight: 700; color: #ffffff; }
        QLabel#StatTitle { color: #8b93a7; font-size: 12px; }

        QTabWidget::pane { border: 1px solid #262b3a; border-radius: 12px; background-color: #171a23; top: -1px; }
        QTabBar::tab { background: transparent; color: #8b93a7; padding: 11px 22px; margin-right: 4px;
                       border-top-left-radius: 10px; border-top-right-radius: 10px; font-size: 14px; }
        QTabBar::tab:hover { color: #ffffff; }
        QTabBar::tab:selected { background: #171a23; color: #a5b4fc; font-weight: 700; border: 1px solid #262b3a; border-bottom: none; }

        QFrame#FormFrame { background-color: #1e2230; border: 1px solid #2a2f3f; border-radius: 12px; }

        QLineEdit, QComboBox, QDateEdit, QDoubleSpinBox, QSpinBox {
            background-color: #232838; color: #ffffff; border: 1px solid #2f3547;
            border-radius: 8px; padding: 9px 12px; min-height: 18px; selection-background-color: #6366f1;
        }
        QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus { border: 1px solid #6366f1; }
        QLineEdit:read-only { color: #9aa3b8; }
        QComboBox QAbstractItemView { background-color: #1e2230; color: #ffffff; border: 1px solid #2f3547;
                                      selection-background-color: #6366f1; outline: none; }

        QPushButton { background-color: #6366f1; color: white; border: none; border-radius: 8px;
                      padding: 10px 20px; font-size: 13px; font-weight: 600; }
        QPushButton:hover { background-color: #7c7ff5; }
        QPushButton:pressed { background-color: #4f52d9; }
        QPushButton:disabled { background-color: #2a2f3f; color: #5d667c; }
        QPushButton#SecondaryButton { background-color: #2a2f3f; color: #e6e8ef; }
        QPushButton#SecondaryButton:hover { background-color: #353b4f; }
        QPushButton#WarnButton { background-color: #f59e0b; color: #1a1300; }
        QPushButton#WarnButton:hover { background-color: #fbb024; }
        QPushButton#WarnButton:disabled { background-color: #2a2f3f; color: #5d667c; }
        QPushButton#DeleteButton { background-color: #ef4444; }
        QPushButton#DeleteButton:hover { background-color: #f25c5c; }

        QTableWidget { background-color: #171a23; alternate-background-color: #1b1f2b; color: #e6e8ef;
                       border: 1px solid #262b3a; border-radius: 10px; outline: none; }
        QTableWidget::item { padding: 8px; border: none; }
        QTableWidget::item:selected { background-color: #6366f1; color: #ffffff; }
        QHeaderView::section { background-color: #1e2230; color: #a5b4fc; font-weight: 700; border: none;
                               border-bottom: 1px solid #2a2f3f; padding: 10px 8px; }

        QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
        QScrollBar::handle:vertical { background: #353b4f; border-radius: 4px; min-height: 30px; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
        QScrollBar::handle:horizontal { background: #353b4f; border-radius: 4px; min-width: 30px; }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

        QScrollArea { background-color: #0f1117; border: none; }
        QWidget#Central { background-color: #0f1117; }
        QPlainTextEdit#QueryEditor { background-color: #12151d; color: #e6e8ef; border: 1px solid #2f3547;
                                     border-radius: 8px; padding: 10px; selection-background-color: #6366f1; }
        QPlainTextEdit#QueryEditor:focus { border: 1px solid #6366f1; }
        QCheckBox { spacing: 8px; color: #e6e8ef; }
        QCheckBox::indicator { width: 18px; height: 18px; border-radius: 5px; border: 1px solid #2f3547; background: #232838; }
        QCheckBox::indicator:checked { background: #6366f1; border: 1px solid #6366f1; }
        QFrame#PagerBar { background-color: #1e2230; border: 1px solid #2a2f3f; border-radius: 10px; }
        QLabel#PagerInfo { color: #8b93a7; font-size: 12px; background: transparent; }
        QPushButton#PagerButton { background-color: #2a2f3f; color: #e6e8ef; padding: 0; min-width: 32px; max-width: 32px;
                                  min-height: 32px; max-height: 32px; border-radius: 8px; font-size: 16px; font-weight: 700; }
        QPushButton#PagerButton:hover { background-color: #353b4f; }
        QPushButton#PagerButton:disabled { background-color: #232838; color: #4a5266; }
        QPushButton#PagerNum { background-color: transparent; color: #aab1c5; padding: 0 8px; min-width: 32px;
                               min-height: 32px; max-height: 32px; border-radius: 8px; font-weight: 600; }
        QPushButton#PagerNum:hover { background-color: #2a2f3f; color: #ffffff; }
        QPushButton#PagerNum[active="true"] { background-color: #6366f1; color: #ffffff; }
        QStatusBar { color: #8b93a7; }
        QMessageBox { background-color: #171a23; }
        """


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(CRUDApp.get_stylesheet())

    # 1) connection window
    login = SettingsDialog(load_config())
    if login.exec() != QDialog.DialogCode.Accepted:
        sys.exit(0)
    try:
        save_config(login.saved_values())
    except OSError:
        pass

    # 2) main window
    window = CRUDApp(login.values())
    window.show()
    sys.exit(app.exec())