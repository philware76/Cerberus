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
            item = QListWidgetItem()
            item_widget = self._create_plan_item(plan_id, plan)
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, item_widget)

        layout.addWidget(QLabel("Test Plans:"))
        layout.addWidget(self.list_widget)
        self.setLayout(layout)

    def _create_plan_item(self, plan_id: int, plan: Plan) -> QWidget:
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        vbox = QVBoxLayout()
        vbox.setContentsMargins(8, 8, 8, 8)
        vbox.setSpacing(4)

        title = QLabel(f"ID: {plan_id} | Name: {plan.name}")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        vbox.addWidget(title)

        user_label = QLabel(f"User: {getattr(plan, 'user', 'N/A')}")
        vbox.addWidget(user_label)

        date_label = QLabel(f"Date/Time: {getattr(plan, 'datetime', 'N/A')}")
        vbox.addWidget(date_label)

        tests = getattr(plan, 'tests', [])
        tests_label = QLabel(f"Tests: {', '.join(tests) if tests else 'None'}")
        vbox.addWidget(tests_label)

        frame.setLayout(vbox)
        return frame

# Example usage:
# plans = plan_service.listTestPlans()
# plan_list_widget = PlanListWidget(plans)
# parent_layout.addWidget(plan_list_widget)
