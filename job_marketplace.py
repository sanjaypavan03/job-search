import sys
import sqlite3
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QComboBox, QTabWidget,
                             QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
                             QFormLayout, QTextEdit, QGroupBox, QSpinBox, QDialog,
                             QDialogButtonBox, QStackedWidget, QSplitter)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QIcon, QPixmap


class DatabaseManager:
    def __init__(self):
        self.conn = sqlite3.connect('job_marketplace.db')
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        # Create users table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            user_type TEXT NOT NULL,
            name TEXT,
            email TEXT,
            registration_date TEXT
        )
        ''')

        # Create jobs table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            salary REAL,
            job_type TEXT NOT NULL,
            description TEXT,
            posted_date TEXT,
            FOREIGN KEY (provider_id) REFERENCES users(id)
        )
        ''')

        # Create applications table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            seeker_id INTEGER NOT NULL,
            application_date TEXT,
            status TEXT DEFAULT 'Pending',
            cover_letter TEXT,
            FOREIGN KEY (job_id) REFERENCES jobs(id),
            FOREIGN KEY (seeker_id) REFERENCES users(id)
        )
        ''')

        self.conn.commit()

    def register_user(self, username, password, user_type, name, email):
        try:
            registration_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute(
                "INSERT INTO users (username, password, user_type, name, email, registration_date) VALUES (?, ?, ?, ?, ?, ?)",
                (username, password, user_type, name, email, registration_date)
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def authenticate_user(self, username, password):
        self.cursor.execute(
            "SELECT id, user_type, name, email FROM users WHERE username = ? AND password = ?",
            (username, password)
        )
        user_data = self.cursor.fetchone()
        if user_data:
            return {
                'id': user_data[0],
                'user_type': user_data[1],
                'name': user_data[2],
                'email': user_data[3]
            }
        return None

    def post_job(self, provider_id, title, company, salary, job_type, description):
        posted_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute(
            "INSERT INTO jobs (provider_id, title, company, salary, job_type, description, posted_date) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (provider_id, title, company, salary, job_type, description, posted_date)
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def get_jobs(self, filters=None):
        query = """
        SELECT j.id, j.title, j.company, j.salary, j.job_type, j.description, 
               j.posted_date, u.name as provider_name, u.email as provider_email,
               (SELECT COUNT(*) FROM applications WHERE job_id = j.id) as application_count
        FROM jobs j
        JOIN users u ON j.provider_id = u.id
        """

        where_clauses = []
        params = []

        if filters:
            if filters.get('title'):
                where_clauses.append("j.title LIKE ?")
                params.append(f"%{filters['title']}%")

            if filters.get('company'):
                where_clauses.append("j.company LIKE ?")
                params.append(f"%{filters['company']}%")

            if filters.get('job_type') and filters['job_type'] != "All":
                where_clauses.append("j.job_type = ?")
                params.append(filters['job_type'])

            if filters.get('min_salary'):
                where_clauses.append("j.salary >= ?")
                params.append(filters['min_salary'])

            if filters.get('max_salary'):
                where_clauses.append("j.salary <= ?")
                params.append(filters['max_salary'])

            if filters.get('provider_id'):
                where_clauses.append("j.provider_id = ?")
                params.append(filters['provider_id'])

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)

        query += " ORDER BY j.posted_date DESC"

        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def get_job_by_id(self, job_id):
        self.cursor.execute("""
        SELECT j.id, j.title, j.company, j.salary, j.job_type, j.description, 
               j.posted_date, u.name as provider_name, u.email as provider_email
        FROM jobs j
        JOIN users u ON j.provider_id = u.id
        WHERE j.id = ?
        """, (job_id,))
        return self.cursor.fetchone()

    def delete_job(self, job_id, provider_id):
        # First check if the job belongs to the provider
        self.cursor.execute("SELECT id FROM jobs WHERE id = ? AND provider_id = ?", (job_id, provider_id))
        if not self.cursor.fetchone():
            return False

        # Delete all applications for this job
        self.cursor.execute("DELETE FROM applications WHERE job_id = ?", (job_id,))

        # Delete the job
        self.cursor.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        self.conn.commit()
        return True

    def apply_for_job(self, job_id, seeker_id, cover_letter):
        # Check if user already applied for this job
        self.cursor.execute("SELECT id FROM applications WHERE job_id = ? AND seeker_id = ?", (job_id, seeker_id))
        if self.cursor.fetchone():
            return False, "You have already applied for this job"

        application_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute(
            "INSERT INTO applications (job_id, seeker_id, application_date, cover_letter) VALUES (?, ?, ?, ?)",
            (job_id, seeker_id, application_date, cover_letter)
        )
        self.conn.commit()
        return True, "Application submitted successfully"

    def get_applications(self, filters=None):
        query = """
        SELECT a.id, a.job_id, j.title, j.company, u.name as applicant_name, 
               u.email as applicant_email, a.application_date, a.status, a.cover_letter
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        JOIN users u ON a.seeker_id = u.id
        """

        where_clauses = []
        params = []

        if filters:
            if filters.get('job_id'):
                where_clauses.append("a.job_id = ?")
                params.append(filters['job_id'])

            if filters.get('seeker_id'):
                where_clauses.append("a.seeker_id = ?")
                params.append(filters['seeker_id'])

            if filters.get('provider_id'):
                where_clauses.append("j.provider_id = ?")
                params.append(filters['provider_id'])

            if filters.get('status'):
                where_clauses.append("a.status = ?")
                params.append(filters['status'])

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)

        query += " ORDER BY a.application_date DESC"

        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def update_application_status(self, application_id, new_status):
        self.cursor.execute(
            "UPDATE applications SET status = ? WHERE id = ?",
            (new_status, application_id)
        )
        self.conn.commit()
        return True

    def get_user_applications(self, user_id):
        self.cursor.execute("""
        SELECT a.id, j.title, j.company, a.application_date, a.status
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        WHERE a.seeker_id = ?
        ORDER BY a.application_date DESC
        """, (user_id,))
        return self.cursor.fetchall()

    def get_dashboard_stats(self, user_id, user_type):
        stats = {}

        if user_type == 'provider':
            # Total jobs posted
            self.cursor.execute("SELECT COUNT(*) FROM jobs WHERE provider_id = ?", (user_id,))
            stats['total_jobs'] = self.cursor.fetchone()[0]

            # Total applications received
            self.cursor.execute("""
            SELECT COUNT(*) FROM applications a
            JOIN jobs j ON a.job_id = j.id
            WHERE j.provider_id = ?
            """, (user_id,))
            stats['total_applications'] = self.cursor.fetchone()[0]

            # Applications by status
            self.cursor.execute("""
            SELECT a.status, COUNT(*) FROM applications a
            JOIN jobs j ON a.job_id = j.id
            WHERE j.provider_id = ?
            GROUP BY a.status
            """, (user_id,))
            status_counts = self.cursor.fetchall()
            stats['status_counts'] = {status: count for status, count in status_counts}

        elif user_type == 'seeker':
            # Total applications sent
            self.cursor.execute("SELECT COUNT(*) FROM applications WHERE seeker_id = ?", (user_id,))
            stats['total_applications'] = self.cursor.fetchone()[0]

            # Applications by status
            self.cursor.execute("""
            SELECT status, COUNT(*) FROM applications
            WHERE seeker_id = ?
            GROUP BY status
            """, (user_id,))
            status_counts = self.cursor.fetchall()
            stats['status_counts'] = {status: count for status, count in status_counts}

        return stats

    def close(self):
        self.conn.close()


class LoginDialog(QDialog):
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.user_data = None
        self.setWindowTitle("Job Marketplace - Login")
        self.setMinimumSize(400, 300)

        self.layout = QVBoxLayout()

        # Title
        title_label = QLabel("Job Marketplace")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        self.layout.addWidget(title_label)

        # Tabs for Login and Register
        self.tabs = QTabWidget()

        # Login tab
        login_widget = QWidget()
        login_layout = QFormLayout()

        self.login_username = QLineEdit()
        self.login_password = QLineEdit()
        self.login_password.setEchoMode(QLineEdit.Password)

        login_layout.addRow("Username:", self.login_username)
        login_layout.addRow("Password:", self.login_password)

        login_button = QPushButton("Login")
        login_button.clicked.connect(self.handle_login)
        login_layout.addRow("", login_button)

        login_widget.setLayout(login_layout)
        self.tabs.addTab(login_widget, "Login")

        # Register tab
        register_widget = QWidget()
        register_layout = QFormLayout()

        self.register_username = QLineEdit()
        self.register_password = QLineEdit()
        self.register_password.setEchoMode(QLineEdit.Password)
        self.register_name = QLineEdit()
        self.register_email = QLineEdit()
        self.register_type = QComboBox()
        self.register_type.addItems(["Job Seeker", "Job Provider"])

        register_layout.addRow("Username:", self.register_username)
        register_layout.addRow("Password:", self.register_password)
        register_layout.addRow("Full Name:", self.register_name)
        register_layout.addRow("Email:", self.register_email)
        register_layout.addRow("Account Type:", self.register_type)

        register_button = QPushButton("Register")
        register_button.clicked.connect(self.handle_register)
        register_layout.addRow("", register_button)

        register_widget.setLayout(register_layout)
        self.tabs.addTab(register_widget, "Register")

        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)

    def handle_login(self):
        username = self.login_username.text()
        password = self.login_password.text()

        if not username or not password:
            QMessageBox.warning(self, "Error", "Please fill in all fields")
            return

        user_data = self.db_manager.authenticate_user(username, password)
        if user_data:
            self.user_data = user_data
            self.accept()
        else:
            QMessageBox.warning(self, "Login Failed", "Invalid username or password")

    def handle_register(self):
        username = self.register_username.text()
        password = self.register_password.text()
        name = self.register_name.text()
        email = self.register_email.text()
        user_type = "seeker" if self.register_type.currentText() == "Job Seeker" else "provider"

        if not all([username, password, name, email]):
            QMessageBox.warning(self, "Error", "Please fill in all fields")
            return

        success = self.db_manager.register_user(username, password, user_type, name, email)
        if success:
            QMessageBox.information(self, "Success", "Registration successful. Please log in.")
            self.tabs.setCurrentIndex(0)  # Switch to login tab
            self.login_username.setText(username)
            self.login_password.setText(password)
        else:
            QMessageBox.warning(self, "Registration Failed", "Username already exists")


class JobDetailDialog(QDialog):
    def __init__(self, job_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Job Details: {job_data[1]}")
        self.setMinimumSize(500, 400)

        layout = QVBoxLayout()

        # Job title
        title_label = QLabel(job_data[1])
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        # Company
        company_label = QLabel(f"Company: {job_data[2]}")
        company_font = QFont()
        company_font.setPointSize(12)
        company_label.setFont(company_font)
        layout.addWidget(company_label)

        # Job details
        details_group = QGroupBox("Job Details")
        details_layout = QFormLayout()

        salary_label = QLabel(f"${job_data[3]:,.2f}")
        job_type_label = QLabel(job_data[4])
        posted_date_label = QLabel(job_data[6])

        details_layout.addRow("Salary:", salary_label)
        details_layout.addRow("Job Type:", job_type_label)
        details_layout.addRow("Posted Date:", posted_date_label)

        details_group.setLayout(details_layout)
        layout.addWidget(details_group)

        # Contact info
        contact_group = QGroupBox("Contact Information")
        contact_layout = QFormLayout()

        provider_name_label = QLabel(job_data[7])
        provider_email_label = QLabel(job_data[8])

        contact_layout.addRow("Contact Person:", provider_name_label)
        contact_layout.addRow("Email:", provider_email_label)

        contact_group.setLayout(contact_layout)
        layout.addWidget(contact_group)

        # Description
        desc_group = QGroupBox("Job Description")
        desc_layout = QVBoxLayout()

        description_text = QTextEdit()
        description_text.setPlainText(job_data[5])
        description_text.setReadOnly(True)

        desc_layout.addWidget(description_text)
        desc_group.setLayout(desc_layout)
        layout.addWidget(desc_group)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)


class ApplicationDialog(QDialog):
    def __init__(self, job_data, user_data, db_manager, parent=None):
        super().__init__(parent)
        self.job_data = job_data
        self.user_data = user_data
        self.db_manager = db_manager

        self.setWindowTitle(f"Apply for: {job_data[1]}")
        self.setMinimumSize(500, 400)

        layout = QVBoxLayout()

        # Job title
        title_label = QLabel(f"Job: {job_data[1]} at {job_data[2]}")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        # Application form
        form_group = QGroupBox("Application Form")
        form_layout = QFormLayout()

        # Display user's name and email
        name_label = QLabel(self.user_data['name'])
        email_label = QLabel(self.user_data['email'])

        form_layout.addRow("Your Name:", name_label)
        form_layout.addRow("Your Email:", email_label)

        # Cover letter
        cover_letter_label = QLabel("Cover Letter / Message:")
        self.cover_letter = QTextEdit()
        self.cover_letter.setPlaceholderText(
            "Write a brief message explaining why you're a good fit for this position...")

        form_layout.addRow(cover_letter_label)
        form_layout.addWidget(self.cover_letter)

        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Apply | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.submit_application)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def submit_application(self):
        cover_letter = self.cover_letter.toPlainText().strip()

        if not cover_letter:
            QMessageBox.warning(self, "Error", "Please include a cover letter or message")
            return

        success, message = self.db_manager.apply_for_job(
            self.job_data[0],  # job_id
            self.user_data['id'],  # seeker_id
            cover_letter
        )

        if success:
            QMessageBox.information(self, "Success", message)
            self.accept()
        else:
            QMessageBox.warning(self, "Error", message)


class JobPostingDialog(QDialog):
    def __init__(self, user_data, db_manager, parent=None):
        super().__init__(parent)
        self.user_data = user_data
        self.db_manager = db_manager

        self.setWindowTitle("Post a New Job")
        self.setMinimumSize(600, 500)

        layout = QVBoxLayout()

        # Title
        title_label = QLabel("Create Job Posting")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # Form
        form_layout = QFormLayout()

        self.job_title = QLineEdit()
        self.job_title.setPlaceholderText("e.g. Senior Software Engineer")

        self.company = QLineEdit()
        self.company.setPlaceholderText("e.g. Tech Innovations Inc.")

        self.salary = QSpinBox()
        self.salary.setRange(0, 1000000)
        self.salary.setSingleStep(1000)
        self.salary.setValue(50000)
        self.salary.setPrefix("$ ")

        self.job_type = QComboBox()
        self.job_type.addItems(["Full-time", "Part-time", "Contract", "Internship", "Remote"])

        self.description = QTextEdit()
        self.description.setPlaceholderText("Provide a detailed job description, requirements, and benefits...")

        form_layout.addRow("Job Title:", self.job_title)
        form_layout.addRow("Company:", self.company)
        form_layout.addRow("Salary:", self.salary)
        form_layout.addRow("Job Type:", self.job_type)
        form_layout.addRow("Description:", self.description)

        form_widget = QWidget()
        form_widget.setLayout(form_layout)
        layout.addWidget(form_widget)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.save_job)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def save_job(self):
        title = self.job_title.text().strip()
        company = self.company.text().strip()
        salary = self.salary.value()
        job_type = self.job_type.currentText()
        description = self.description.toPlainText().strip()

        if not all([title, company, description]):
            QMessageBox.warning(self, "Error", "Please fill in all required fields")
            return

        job_id = self.db_manager.post_job(
            self.user_data['id'],
            title,
            company,
            salary,
            job_type,
            description
        )

        if job_id:
            QMessageBox.information(self, "Success", "Job posted successfully")
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "Failed to post job")


class ApplicationStatusDialog(QDialog):
    def __init__(self, application_data, db_manager, parent=None):
        super().__init__(parent)
        self.application_data = application_data
        self.db_manager = db_manager

        self.setWindowTitle(f"Application Details: {application_data[2]}")
        self.setMinimumSize(500, 400)

        layout = QVBoxLayout()

        # Title
        title_label = QLabel(f"Application for: {application_data[2]}")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        # Application details
        details_group = QGroupBox("Application Details")
        details_layout = QFormLayout()

        applicant_label = QLabel(application_data[4])
        email_label = QLabel(application_data[5])
        date_label = QLabel(application_data[6])
        status_label = QLabel(application_data[7])

        details_layout.addRow("Applicant:", applicant_label)
        details_layout.addRow("Email:", email_label)
        details_layout.addRow("Applied on:", date_label)
        details_layout.addRow("Status:", status_label)

        details_group.setLayout(details_layout)
        layout.addWidget(details_group)

        # Cover letter
        cover_group = QGroupBox("Cover Letter")
        cover_layout = QVBoxLayout()

        cover_text = QTextEdit()
        cover_text.setPlainText(application_data[8])
        cover_text.setReadOnly(True)

        cover_layout.addWidget(cover_text)
        cover_group.setLayout(cover_layout)
        layout.addWidget(cover_group)

        # Status update (for provider only)
        if hasattr(parent, 'user_data') and parent.user_data['user_type'] == 'provider':
            status_group = QGroupBox("Update Application Status")
            status_layout = QHBoxLayout()

            self.status_combo = QComboBox()
            self.status_combo.addItems(["Pending", "Reviewing", "Interview", "Accepted", "Rejected"])
            self.status_combo.setCurrentText(application_data[7])

            update_button = QPushButton("Update Status")
            update_button.clicked.connect(self.update_status)

            status_layout.addWidget(self.status_combo)
            status_layout.addWidget(update_button)

            status_group.setLayout(status_layout)
            layout.addWidget(status_group)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def update_status(self):
        new_status = self.status_combo.currentText()
        success = self.db_manager.update_application_status(self.application_data[0], new_status)

        if success:
            QMessageBox.information(self, "Success", "Application status updated")
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "Failed to update status")


class JobMarketplaceApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.user_data = None

        # Perform login
        login_dialog = LoginDialog(self.db_manager)
        if login_dialog.exec_() == QDialog.Accepted:
            self.user_data = login_dialog.user_data
            self.init_ui()
        else:
            sys.exit()

    def init_ui(self):
        self.setWindowTitle("Job Marketplace")
        self.setMinimumSize(900, 600)

        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()

        # Header
        header_layout = QHBoxLayout()

        app_title = QLabel("Job Marketplace")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        app_title.setFont(title_font)

        user_info = QLabel(f"Welcome, {self.user_data['name']} ({self.user_data['user_type'].capitalize()})")

        logout_button = QPushButton("Logout")
        logout_button.clicked.connect(self.logout)

        header_layout.addWidget(app_title)
        header_layout.addStretch()
        header_layout.addWidget(user_info)
        header_layout.addWidget(logout_button)

        main_layout.addLayout(header_layout)

        # Tabs
        self.tabs = QTabWidget()

        # Dashboard tab
        dashboard_tab = QWidget()
        dashboard_layout = QVBoxLayout()

        dashboard_title = QLabel("Dashboard")
        dashboard_title_font = QFont()
        dashboard_title_font.setPointSize(14)
        dashboard_title_font.setBold(True)
        dashboard_title.setFont(dashboard_title_font)
        dashboard_layout.addWidget(dashboard_title)

        self.stats_layout = QHBoxLayout()
        self.load_dashboard()
        dashboard_layout.addLayout(self.stats_layout)

        # Recent activity
        recent_group = QGroupBox("Recent Activity")
        recent_layout = QVBoxLayout()

        if self.user_data['user_type'] == 'provider':
            self.recent_applications = QTableWidget()
            self.recent_applications.setColumnCount(5)
            self.recent_applications.setHorizontalHeaderLabels(["ID", "Job Title", "Applicant", "Date", "Status"])
            self.recent_applications.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            recent_layout.addWidget(self.recent_applications)
            self.load_recent_applications()
        else:  # seeker
            self.recent_jobs = QTableWidget()
            self.recent_jobs.setColumnCount(5)
            self.recent_jobs.setHorizontalHeaderLabels(["ID", "Job Title", "Company", "Salary", "Type"])
            self.recent_jobs.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            recent_layout.addWidget(self.recent_jobs)
            self.load_recent_jobs()

        recent_group.setLayout(recent_layout)
        dashboard_layout.addWidget(recent_group)

        dashboard_tab.setLayout(dashboard_layout)
        self.tabs.addTab(dashboard_tab, "Dashboard")

        # Jobs tab
        jobs_tab = QWidget()
        jobs_layout = QVBoxLayout()

        # Search and filter area
        filter_group = QGroupBox("Search & Filter Jobs")
        filter_layout = QHBoxLayout()

        self.search_title = QLineEdit()
        self.search_title.setPlaceholderText("Job Title")

        self.search_company = QLineEdit()
        self.search_company.setPlaceholderText("Company")

        self.search_type = QComboBox()
        self.search_type.addItems(["All", "Full-time", "Part-time", "Contract", "Internship", "Remote"])

        self.min_salary = QSpinBox()
        self.min_salary.setRange(0, 1000000)
        self.min_salary.setSingleStep(5000)
        self.min_salary.setPrefix("Min $ ")

        self.max_salary = QSpinBox()
        self.max_salary.setRange(0, 1000000)
        self.max_salary.setSingleStep(5000)
        self.max_salary.setValue(200000)
        self.max_salary.setPrefix("Max $ ")

        search_button = QPushButton("Search")
        search_button.clicked.connect(self.search_jobs)

        reset_button = QPushButton("Reset")
        reset_button.clicked.connect(self.reset_job_search)

        filter_layout.addWidget(self.search_title)
        filter_layout.addWidget(self.search_company)
        filter_layout.addWidget(self.search_type)
        filter_layout.addWidget(self.min_salary)
        filter_layout.addWidget(self.max_salary)
        filter_layout.addWidget(search_button)
        filter_layout.addWidget(reset_button)

        filter_group.setLayout(filter_layout)
        jobs_layout.addWidget(filter_group)

        # Jobs table
        jobs_controls_layout = QHBoxLayout()

        if self.user_data['user_type'] == 'provider':
            post_job_button = QPushButton("Post New Job")
            post_job_button.clicked.connect(self.show_post_job_dialog)
            jobs_controls_layout.addWidget(post_job_button)

        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.load_jobs)
        jobs_controls_layout.addWidget(refresh_button)

        jobs_controls_layout.addStretch()

        jobs_layout.addLayout(jobs_controls_layout)

        self.jobs_table = QTableWidget()
        if self.user_data['user_type'] == 'provider':
            self.jobs_table.setColumnCount(7)
            self.jobs_table.setHorizontalHeaderLabels(
                ["ID", "Title", "Company", "Salary", "Type", "Posted", "Applications"])
        else:
            self.jobs_table.setColumnCount(6)
            self.jobs_table.setHorizontalHeaderLabels(["ID", "Title", "Company", "Salary", "Type", "Posted"])

        self.jobs_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.jobs_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.jobs_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.jobs_table.doubleClicked.connect(self.show_job_detail)

        jobs_layout.addWidget(self.jobs_table)

        # Action buttons for jobs
        job_actions_layout = QHBoxLayout()

        view_job_button = QPushButton("View Details")
        view_job_button.clicked.connect(self.show_job_detail)
        job_actions_layout.addWidget(view_job_button)

        if self.user_data['user_type'] == 'seeker':
            apply_job_button = QPushButton("Apply for Job")
            apply_job_button.clicked.connect(self.apply_for_job)
            job_actions_layout.addWidget(apply_job_button)
        else:  # provider
            view_applications_button = QPushButton("View Applications")
            view_applications_button.clicked.connect(self.view_job_applications)
            job_actions_layout.addWidget(view_applications_button)

            delete_job_button = QPushButton("Delete Job")
            delete_job_button.clicked.connect(self.delete_job)
            job_actions_layout.addWidget(delete_job_button)

        jobs_layout.addLayout(job_actions_layout)

        jobs_tab.setLayout(jobs_layout)
        self.tabs.addTab(jobs_tab, "Jobs")

        # Applications tab
        applications_tab = QWidget()
        applications_layout = QVBoxLayout()

        applications_title = QLabel("Applications")
        applications_title_font = QFont()
        applications_title_font.setPointSize(14)
        applications_title_font.setBold(True)
        applications_title.setFont(applications_title_font)
        applications_layout.addWidget(applications_title)

        # Applications table
        applications_controls_layout = QHBoxLayout()

        refresh_apps_button = QPushButton("Refresh")
        refresh_apps_button.clicked.connect(self.load_applications)
        applications_controls_layout.addWidget(refresh_apps_button)

        applications_controls_layout.addStretch()

        applications_layout.addLayout(applications_controls_layout)

        self.applications_table = QTableWidget()
        if self.user_data['user_type'] == 'provider':
            self.applications_table.setColumnCount(5)
            self.applications_table.setHorizontalHeaderLabels(["ID", "Job Title", "Applicant", "Date", "Status"])
        else:  # seeker
            self.applications_table.setColumnCount(5)
            self.applications_table.setHorizontalHeaderLabels(["ID", "Job Title", "Company", "Date", "Status"])

        self.applications_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.applications_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.applications_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.applications_table.doubleClicked.connect(self.show_application_detail)

        applications_layout.addWidget(self.applications_table)

        # Action buttons for applications
        app_actions_layout = QHBoxLayout()

        view_app_button = QPushButton("View Details")
        view_app_button.clicked.connect(self.show_application_detail)
        app_actions_layout.addWidget(view_app_button)

        applications_layout.addLayout(app_actions_layout)

        applications_tab.setLayout(applications_layout)
        self.tabs.addTab(applications_tab, "Applications")

        main_layout.addWidget(self.tabs)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        # Load data
        self.load_jobs()
        self.load_applications()

    def load_dashboard(self):
        # Clear existing stats
        for i in reversed(range(self.stats_layout.count())):
            self.stats_layout.itemAt(i).widget().setParent(None)

        # Get stats from database
        stats = self.db_manager.get_dashboard_stats(self.user_data['id'], self.user_data['user_type'])

        # Create stat cards
        if self.user_data['user_type'] == 'provider':
            # Jobs card
            jobs_group = QGroupBox("Jobs Posted")
            jobs_layout = QVBoxLayout()
            jobs_label = QLabel(str(stats.get('total_jobs', 0)))
            jobs_label.setAlignment(Qt.AlignCenter)
            jobs_font = QFont()
            jobs_font.setPointSize(24)
            jobs_font.setBold(True)
            jobs_label.setFont(jobs_font)
            jobs_layout.addWidget(jobs_label)
            jobs_group.setLayout(jobs_layout)
            self.stats_layout.addWidget(jobs_group)

        # Applications card
        apps_group = QGroupBox("Applications")
        apps_layout = QVBoxLayout()
        apps_label = QLabel(str(stats.get('total_applications', 0)))
        apps_label.setAlignment(Qt.AlignCenter)
        apps_font = QFont()
        apps_font.setPointSize(24)
        apps_font.setBold(True)
        apps_label.setFont(apps_font)
        apps_layout.addWidget(apps_label)
        apps_group.setLayout(apps_layout)
        self.stats_layout.addWidget(apps_group)

        # Status breakdown
        status_group = QGroupBox("Status Breakdown")
        status_layout = QFormLayout()

        status_counts = stats.get('status_counts', {})
        for status, count in status_counts.items():
            status_label = QLabel(str(count))
            status_layout.addRow(f"{status}:", status_label)

        status_group.setLayout(status_layout)
        self.stats_layout.addWidget(status_group)

    def load_recent_applications(self):
        # Clear table
        self.recent_applications.setRowCount(0)

        # Get recent applications for provider's jobs
        applications = self.db_manager.get_applications({'provider_id': self.user_data['id']})

        # Only display the 5 most recent
        applications = applications[:5]

        # Populate table
        for row, app in enumerate(applications):
            self.recent_applications.insertRow(row)
            self.recent_applications.setItem(row, 0, QTableWidgetItem(str(app[0])))
            self.recent_applications.setItem(row, 1, QTableWidgetItem(app[2]))
            self.recent_applications.setItem(row, 2, QTableWidgetItem(app[4]))
            self.recent_applications.setItem(row, 3, QTableWidgetItem(app[6]))
            self.recent_applications.setItem(row, 4, QTableWidgetItem(app[7]))

    def load_recent_jobs(self):
        # Clear table
        self.recent_jobs.setRowCount(0)

        # Get recent jobs
        jobs = self.db_manager.get_jobs()

        # Only display the 5 most recent
        jobs = jobs[:5]

        # Populate table
        for row, job in enumerate(jobs):
            self.recent_jobs.insertRow(row)
            self.recent_jobs.setItem(row, 0, QTableWidgetItem(str(job[0])))
            self.recent_jobs.setItem(row, 1, QTableWidgetItem(job[1]))
            self.recent_jobs.setItem(row, 2, QTableWidgetItem(job[2]))
            salary_item = QTableWidgetItem(f"${job[3]:,.2f}")
            salary_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.recent_jobs.setItem(row, 3, salary_item)
            self.recent_jobs.setItem(row, 4, QTableWidgetItem(job[4]))

    def load_jobs(self):
        # Clear table
        self.jobs_table.setRowCount(0)

        # Get filtered jobs
        filters = {}
        if self.user_data['user_type'] == 'provider':
            filters['provider_id'] = self.user_data['id']

        jobs = self.db_manager.get_jobs(filters)

        # Populate table
        for row, job in enumerate(jobs):
            self.jobs_table.insertRow(row)
            self.jobs_table.setItem(row, 0, QTableWidgetItem(str(job[0])))
            self.jobs_table.setItem(row, 1, QTableWidgetItem(job[1]))
            self.jobs_table.setItem(row, 2, QTableWidgetItem(job[2]))
            salary_item = QTableWidgetItem(f"${job[3]:,.2f}")
            salary_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.jobs_table.setItem(row, 3, salary_item)
            self.jobs_table.setItem(row, 4, QTableWidgetItem(job[4]))
            self.jobs_table.setItem(row, 5, QTableWidgetItem(job[6]))

            if self.user_data['user_type'] == 'provider':
                self.jobs_table.setItem(row, 6, QTableWidgetItem(str(job[9])))

    def load_applications(self):
        # Clear table
        self.applications_table.setRowCount(0)

        # Get applications
        filters = {}
        if self.user_data['user_type'] == 'provider':
            filters['provider_id'] = self.user_data['id']
        else:  # seeker
            filters['seeker_id'] = self.user_data['id']

        applications = self.db_manager.get_applications(filters)

        # Populate table
        for row, app in enumerate(applications):
            self.applications_table.insertRow(row)
            self.applications_table.setItem(row, 0, QTableWidgetItem(str(app[0])))
            self.applications_table.setItem(row, 1, QTableWidgetItem(app[2]))

            if self.user_data['user_type'] == 'provider':
                self.applications_table.setItem(row, 2, QTableWidgetItem(app[4]))  # applicant name
            else:  # seeker
                self.applications_table.setItem(row, 2, QTableWidgetItem(app[3]))  # company

            self.applications_table.setItem(row, 3, QTableWidgetItem(app[6]))
            self.applications_table.setItem(row, 4, QTableWidgetItem(app[7]))

    def search_jobs(self):
        # Get search parameters
        filters = {}

        title = self.search_title.text().strip()
        if title:
            filters['title'] = title

        company = self.search_company.text().strip()
        if company:
            filters['company'] = company

        job_type = self.search_type.currentText()
        if job_type != "All":
            filters['job_type'] = job_type

        min_salary = self.min_salary.value()
        if min_salary > 0:
            filters['min_salary'] = min_salary

        max_salary = self.max_salary.value()
        if max_salary < 1000000:
            filters['max_salary'] = max_salary

        if self.user_data['user_type'] == 'provider':
            filters['provider_id'] = self.user_data['id']

        # Clear table
        self.jobs_table .setRowCount(0)

        # Get filtered jobs
        jobs = self.db_manager.get_jobs(filters)

        # Populate table with search results
        for row, job in enumerate(jobs):
            self.jobs_table.insertRow(row)
            self.jobs_table.setItem(row, 0, QTableWidgetItem(str(job[0])))
            self.jobs_table.setItem(row, 1, QTableWidgetItem(job[1]))
            self.jobs_table.setItem(row, 2, QTableWidgetItem(job[2]))
            salary_item = QTableWidgetItem(f"${job[3]:,.2f}")
            salary_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.jobs_table.setItem(row, 3, salary_item)
            self.jobs_table.setItem(row, 4, QTableWidgetItem(job[4]))
            self.jobs_table.setItem(row, 5, QTableWidgetItem(job[6]))

            if self.user_data['user_type'] == 'provider':
                self.jobs_table.setItem(row, 6, QTableWidgetItem(str(job[9])))

    def reset_job_search(self):
        # Clear search fields
        self.search_title.clear()
        self.search_company.clear()
        self.search_type.setCurrentIndex(0)
        self.min_salary.setValue(0)
        self.max_salary.setValue(200000)

        # Reload all jobs
        self.load_jobs()

    def show_job_detail(self):
        selected_rows = self.jobs_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a job to view")
            return

        job_id = int(self.jobs_table.item(selected_rows[0].row(), 0).text())
        job_data = self.db_manager.get_job_by_id(job_id)

        if job_data:
            dialog = JobDetailDialog(job_data, self)
            dialog.exec_()

    def apply_for_job(self):
        if self.user_data['user_type'] != 'seeker':
            return

        selected_rows = self.jobs_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a job to apply for")
            return

        job_id = int(self.jobs_table.item(selected_rows[0].row(), 0).text())
        job_data = self.db_manager.get_job_by_id(job_id)

        if job_data:
            dialog = ApplicationDialog(job_data, self.user_data, self.db_manager, self)
            if dialog.exec_() == QDialog.Accepted:
                self.load_applications()
                self.load_jobs()  # Refresh job list to update application counts

    def show_post_job_dialog(self):
        if self.user_data['user_type'] != 'provider':
            return

        dialog = JobPostingDialog(self.user_data, self.db_manager, self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_jobs()
            self.load_dashboard()

    def delete_job(self):
        if self.user_data['user_type'] != 'provider':
            return

        selected_rows = self.jobs_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a job to delete")
            return

        job_id = int(self.jobs_table.item(selected_rows[0].row(), 0).text())

        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            "Are you sure you want to delete this job listing? This will also delete all applications for this job.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            success = self.db_manager.delete_job(job_id, self.user_data['id'])
            if success:
                QMessageBox.information(self, "Success", "Job deleted successfully")
                self.load_jobs()
                self.load_applications()
                self.load_dashboard()
            else:
                QMessageBox.warning(self, "Error", "Failed to delete job")

    def view_job_applications(self):
        if self.user_data['user_type'] != 'provider':
            return

        selected_rows = self.jobs_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a job to view applications")
            return

        job_id = int(self.jobs_table.item(selected_rows[0].row(), 0).text())

        # Switch to applications tab and filter by job_id
        self.tabs.setCurrentIndex(2)  # Applications tab

        # Clear table
        self.applications_table.setRowCount(0)

        # Get applications for this job
        applications = self.db_manager.get_applications({'job_id': job_id})

        # Populate table
        for row, app in enumerate(applications):
            self.applications_table.insertRow(row)
            self.applications_table.setItem(row, 0, QTableWidgetItem(str(app[0])))
            self.applications_table.setItem(row, 1, QTableWidgetItem(app[2]))
            self.applications_table.setItem(row, 2, QTableWidgetItem(app[4]))  # applicant name
            self.applications_table.setItem(row, 3, QTableWidgetItem(app[6]))
            self.applications_table.setItem(row, 4, QTableWidgetItem(app[7]))

    def show_application_detail(self):
        selected_rows = self.applications_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select an application to view")
            return

        app_id = int(self.applications_table.item(selected_rows[0].row(), 0).text())

        # Get application data
        applications = self.db_manager.get_applications({'id': app_id})
        if applications:
            dialog = ApplicationStatusDialog(applications[0], self.db_manager, self)
            if dialog.exec_() == QDialog.Accepted:
                self.load_applications()
                self.load_dashboard()

    def logout(self):
        reply = QMessageBox.question(
            self,
            "Confirm Logout",
            "Are you sure you want to logout?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.db_manager.close()
            self.close()
            # Restart application
            QApplication.exit(0)

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Modern look across platforms
    window = JobMarketplaceApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()