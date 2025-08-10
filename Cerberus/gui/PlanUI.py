from typing import List, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QListWidget,
                               QListWidgetItem, QPushButton, QVBoxLayout,
                               QWidget)

from Cerberus.plan import Plan


class PlanListWidget(QWidget):
    """
    Widget to display a list of test plans returned by PlanService.listTestPlans().
    Each plan shows ID, name, user, date/time, and list of tests.
    """

    def __init__(self, plans: List[Tuple[int, Plan]], parent=None):
        super().__init__(parent)
        self.plans = plans
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        self.list_widget = QListWidget()

        for plan_id, plan in self.plans:
            item_widget = self._create_plan_item(plan_id, plan)
            item = QListWidgetItem(self.list_widget)
            item.setSizeHint(item_widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, item_widget)

        layout.addWidget(QLabel("Test Plans:"))
        layout.addWidget(self.list_widget)
        self.setLayout(layout)

    def _create_plan_item(self, plan_id: int, plan: Plan) -> QWidget:
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setStyleSheet("""
            QFrame {
                background-color: #D6EAF8;
                border-radius: 6px;
                border: 1px solid #2A6099;
            }
        """)

        # Info row
        hbox = QHBoxLayout()
        hbox.setContentsMargins(10, 8, 10, 8)
        hbox.setSpacing(16)

        id_label = QLabel(str(plan_id))
        id_label.setStyleSheet("font-weight: bold; color: #2A6099; padding: 2px 8px;")
        id_label.setFixedWidth(40)  # 4 chars width
        hbox.addWidget(id_label)

        name_label = QLabel(getattr(plan, 'name', 'N/A'))
        name_label.setStyleSheet("font-weight: bold; color: #154360; padding: 2px 8px;")
        name_label.setFixedWidth(140)  # ~20 chars width
        hbox.addWidget(name_label)

        date_label = QLabel(str(getattr(plan, 'date', getattr(plan, 'datetime', 'N/A'))))
        date_label.setStyleSheet("color: #1B4F72; padding: 2px 8px;")
        date_label.setFixedWidth(120)  # ~16 chars width
        hbox.addWidget(date_label)

        user_label = QLabel(getattr(plan, 'user', 'N/A'))
        user_label.setStyleSheet("color: #2874A6; padding: 2px 8px;")
        user_label.setFixedWidth(90)  # ~12 chars width
        hbox.addWidget(user_label)

        # Add [+] button for adding tests
        add_btn = QPushButton()
        add_btn.setFixedSize(28, 28)
        add_btn.setText("+")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet("""
            QPushButton {
                font-size: 18px; font-weight: bold; color: #2A6099;
                background: #D6EAF8; border-radius: 14px; border: 1px solid #2A6099;
            }
            QPushButton:hover {
                background: #AED6F1; color: #154360; border: 2px solid #154360;
            }
            QPushButton:pressed {
                background: #2A6099; color: white; border: 2px solid #154360;
            }
        """)

        def on_add_clicked():
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(add_btn, "Demo", "You clicked me")
        add_btn.clicked.connect(on_add_clicked)
        hbox.addWidget(add_btn)

        # Add [dustbin] button for deleting plan
        delete_plan_btn = QPushButton()
        delete_plan_btn.setFixedSize(28, 28)
        delete_plan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        try:
            from PySide6.QtGui import QIcon
            delete_plan_btn.setIcon(QIcon.fromTheme("edit-delete"))
        except Exception:
            delete_plan_btn.setText("🗑")
        delete_plan_btn.setStyleSheet("""
            QPushButton {
                background: #D6EAF8; border-radius: 14px; border: 1px solid #2A6099;
            }
            QPushButton:hover {
                background: #F1948A; border: 2px solid #922B21;
            }
            QPushButton:pressed {
                background: #922B21; color: white; border: 2px solid #922B21;
            }
        """)

        def on_delete_plan_clicked():
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(delete_plan_btn, "Demo", "You've deleted this plan")
        delete_plan_btn.clicked.connect(on_delete_plan_clicked)
        hbox.addWidget(delete_plan_btn)

        hbox.addStretch()

        # TestPlans widget (vertical)
        tests = getattr(plan, 'tests', list(plan) if hasattr(plan, '__iter__') else [])
        tests_widget = QWidget()
        tests_layout = QVBoxLayout()
        tests_layout.setContentsMargins(0, 0, 0, 0)
        tests_layout.setSpacing(4)
        if tests:
            for test_name in tests:
                test_row = QWidget()
                test_row_layout = QHBoxLayout()
                test_row_layout.setContentsMargins(0, 0, 0, 0)
                test_row_layout.setSpacing(6)
                # Add left spacer to align with plan info row
                left_spacer = QWidget()
                left_spacer.setFixedWidth(40)  # sum of fixed widths and spacings
                test_row_layout.addWidget(left_spacer)
                test_label = QLabel(str(test_name))
                test_label.setStyleSheet("background: #2A6099; color: white; border-radius: 4px; padding: 2px 10px; font-size: 12px;")
                test_row_layout.addWidget(test_label)
                delete_btn = QPushButton()
                delete_btn.setFixedSize(24, 24)
                # Try to use a dustbin icon, fallback to text if not available
                try:
                    from PySide6.QtGui import QIcon
                    delete_btn.setIcon(QIcon.fromTheme("edit-delete"))
                except Exception:
                    delete_btn.setText("Delete")
                test_row_layout.addWidget(delete_btn)
                test_row.setLayout(test_row_layout)
                tests_layout.addWidget(test_row)

        tests_widget.setLayout(tests_layout)

        # Combine info row and test list vertically
        vbox = QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(2)
        vbox.addLayout(hbox)
        vbox.addWidget(tests_widget)

        frame.setLayout(vbox)
        return frame
