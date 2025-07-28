from enum import Enum
import inspect
import logging
from PySide6.QtWidgets import QPushButton
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QToolButton,
    QLineEdit, QDoubleSpinBox, QCheckBox, QFrame, QApplication
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve

from PySide6.QtCore import Qt
from typing import Dict, cast

from common import camel2Human
from plugins.baseParameters import BaseParameter, BaseParameters, EmptyParameter, EnumParameter, NumericParameter, OptionParameter, StringParameter


class CollapsibleGroupBox(QWidget):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)

        # === Toggle button ===
        self.toggle_button = QToolButton()
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.toggle_button.setArrowType(Qt.DownArrow)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(True)
        self.toggle_button.setFixedSize(16, 16)
        self.toggle_button.setStyleSheet("QToolButton { border: none; }")

        # === Header label ===
        self.header_label = QLabel(title)
        self.header_label.setStyleSheet("""
            QLabel {
                color: white;
                font-weight: bold;
                padding: 2px 6px;
            }
        """)

        # === Header layout ===
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(6, 2, 6, 2)
        header_layout.addWidget(self.header_label)
        header_layout.addStretch()
        header_layout.addWidget(self.toggle_button)

        self.header_frame = QFrame()
        self.header_frame.setLayout(header_layout)
        self.header_frame.setStyleSheet("""
            QFrame {
                background-color: #2A6099;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
        """)

        # === Content Area ===
        self.content_area = QFrame()
        self.content_area.setFrameShape(QFrame.StyledPanel)
        self.content_area.setStyleSheet("""
            QFrame {
                background-color: #D6EAF8;
                border-bottom-left-radius: 6px;
                border-bottom-right-radius: 6px;
            }
        """)
        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(10, 8, 10, 10)
        self.content_layout.setSpacing(6)
        self.content_area.setLayout(self.content_layout)

        # === Animation ===
        self.animation = QPropertyAnimation(self.content_area, b"maximumHeight")
        self.animation.setDuration(250)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)

        # === Main layout ===
        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.header_frame)
        main_layout.addWidget(self.content_area)
        self.setLayout(main_layout)

        # === Connections ===
        self.toggle_button.clicked.connect(self.toggle_content)

        # === Initialize state ===
        if self.toggle_button.isChecked():
            self.content_area.setVisible(True)
            self.content_area.setMaximumHeight(self.content_area.sizeHint().height())
        else:
            self.content_area.setVisible(False)
            self.content_area.setMaximumHeight(0)

    def toggle_content(self):
        expanding = self.toggle_button.isChecked()
        self.toggle_button.setArrowType(Qt.DownArrow if expanding else Qt.RightArrow)

        if expanding:
            self.content_area.setVisible(True)
            self.content_area.setMaximumHeight(0)
            self.animation.setStartValue(0)
            self.animation.setEndValue(self.content_area.sizeHint().height())
        else:
            self.animation.setStartValue(self.content_area.height())
            self.animation.setEndValue(0)

        self.animation.finished.connect(self._on_animation_done)
        self.animation.start()

    def _on_animation_done(self):
        if not self.toggle_button.isChecked():
            self.content_area.setVisible(False)

    def addWidget(self, widget):
        self.content_layout.addWidget(widget)
        self.content_area.setMaximumHeight(self.content_area.sizeHint().height())


def create_parameter_widget(param: BaseParameter) -> QWidget:
    """Return a QWidget (e.g., QLineEdit or QDoubleSpinBox) for a given parameter."""
    widget = None
    if isinstance(param, NumericParameter):
        spin = QDoubleSpinBox()
        if param.minValue is not None:
            spin.setMinimum(param.minValue)
        if param.maxValue is not None:
            spin.setMaximum(param.maxValue)
        spin.setValue(param.value)
        spin.setSuffix(f" {param.units}" if param.units else "")
        spin.setDecimals(4)
        spin.setSingleStep(0.1)
        widget = spin

    elif isinstance(param, OptionParameter):
        checkbox = QCheckBox()
        checkbox.setChecked(bool(param.value))
        widget = checkbox

    elif isinstance(param, EnumParameter):
        combobox = QComboBox()
        enum_members = list(param.enumType)

        for member in enum_members:
            combobox.addItem(member.name, member)

        combobox.setCurrentIndex(enum_members.index(param.value))
        widget = combobox

    elif isinstance(param, StringParameter):
        text = QLineEdit()
        text.setText(param.value)
        widget = text

    if widget == None:
        logging.error(f"Failed to create widget for {param} parameter")
        emptyLabel = QLabel()
        emptyLabel.setText(f"Unknown Parameter Type: {param.name}")
        return emptyLabel

    if param.description:
        widget.setToolTip(param.description)

    return widget


def create_parameters_groupbox(title: str, parameters: dict[str, BaseParameter]):
    groupbox = CollapsibleGroupBox(title)
    widget_map = {}

    for param in parameters.values():
        row = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Name label
        name_label = QLabel(param.name)
        name_label.setStyleSheet("QLabel { color: black; }")

        # Create parameter widget via polymorphic call
        value_widget = create_parameter_widget(param)
        value_widget.setFixedWidth(120)  # optional fixed width for alignment

        layout.addWidget(name_label)
        layout.addStretch()
        layout.addWidget(value_widget)
        layout.setStretch(1, 1)

        row.setLayout(layout)
        groupbox.addWidget(row)

        widget_map[param.name] = value_widget

    return groupbox, widget_map


def create_all_parameters_ui(groups: Dict[str, BaseParameters]) -> tuple[QWidget, dict[str, dict[str, QWidget]]]:
    container = QWidget()
    main_layout = QVBoxLayout()
    all_widget_map = {}

    for group_name, base_params in groups.items():
        groupbox, widget_map = create_parameters_groupbox(group_name, base_params)
        all_widget_map[group_name] = widget_map
        main_layout.addWidget(groupbox)

    main_layout.addStretch()
    container.setLayout(main_layout)
    return container, all_widget_map


def apply_parameters(groups: Dict[str, BaseParameters], widget_map: dict[str, dict[str, QWidget]]):
    """
    Update BaseParameters with the current values from the widgets.
    """
    for group_name, param_widgets in widget_map.items():
        base_params = groups[group_name]
        for param_name, widget in param_widgets.items():
            param = base_params[param_name]
            if isinstance(widget, QDoubleSpinBox):
                param.value = widget.value()
            elif isinstance(widget, QLineEdit):
                param.value = widget.text()
            elif isinstance(widget, QCheckBox):
                param.value = widget.isChecked()
            elif isinstance(widget, QComboBox):
                param.value = cast(QComboBox, widget).currentData()


def create_method_param_widget(name, param_type, default_value=None):
    if param_type == bool:  # or (default_value is not None and isinstance(default_value, bool)):
        widget = QCheckBox()
        if default_value is not None:
            widget.setChecked(default_value)
        return widget

    elif param_type == int:  # or (default_value is not None and isinstance(default_value, int)):
        widget = QSpinBox()
        widget.setRange(-2147483648, 2147483647)
        widget.setMinimumWidth(30)
        if default_value is not None:
            widget.setValue(default_value)
        return widget

    elif param_type == float:  # or (default_value is not None and isinstance(default_value, float)):
        widget = QDoubleSpinBox()
        widget.setRange(-999999.99, 999999.99)
        widget.setDecimals(2)
        widget.setMinimumWidth(30)
        if default_value is not None:
            widget.setValue(default_value)
        return widget

    elif param_type == str:  # or (default_value is not None and isinstance(default_value, str)):
        widget = QLineEdit()
        if default_value is not None:
            widget.setText(str(default_value))
        widget.setMinimumWidth(100)
        return widget

    else:
        # Default to string input for unknown types
        widget = QLineEdit()
        if default_value is not None:
            widget.setText(str(default_value))
        return widget


def create_all_methods_ui(instance) -> CollapsibleGroupBox:
    groupbox = CollapsibleGroupBox("Device Methods")
    methods = inspect.getmembers(instance, predicate=inspect.ismethod)

    for method_name, method in methods:
        if method_name.startswith("_"):
            continue

        row = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        try:
            sig = inspect.signature(method)
            params = [p for p in sig.parameters.values() if p.name != 'self']
        except Exception as e:
            print(f"Could not inspect {method_name}: {e}")
            continue

        widget_map = {}

        def make_handler(method, widget_map):
            def handler():
                args = []
                for name, (widget, ptype) in widget_map.items():
                    if isinstance(widget, QLineEdit):
                        val = widget.text()
                        try:
                            val = ptype(val)
                        except:
                            pass
                    elif isinstance(widget, QCheckBox):
                        val = widget.isChecked()
                    else:
                        val = None
                    args.append(val)
                result = method(*args)
                print(f"→ {method.__name__}({args}) = {result}")
            return handler

        button = QPushButton(camel2Human(method_name))
        if method.__doc__ is not None:
            button.setToolTip(method.__doc__.strip())
        button.setMinimumWidth(120)
        button.clicked.connect(make_handler(method, widget_map))
        layout.addWidget(button)

        for param in params:
            label = QLabel(param.name + ":")
            label.setStyleSheet("QLabel { color: black; }")
            label.setAlignment(Qt.AlignRight)
            label.setMinimumWidth(50)
            layout.addWidget(label)

            param_type = param.annotation if param.annotation != inspect.Parameter.empty else str
            default_val = param.default if param.default != inspect.Parameter.empty else None
            widget = create_method_param_widget(param.name, param_type, default_val)
            widget.setMinimumWidth(100)
            widget.setToolTip(param.name)
            layout.addWidget(widget)

            widget_map[param.name] = (widget, param_type)

        layout.addStretch()
        row.setLayout(layout)
        groupbox.addWidget(row)

    return groupbox


class TimingMode(Enum):
    Plaid = 0
    Fast = 1
    Slow = 2


class ExampleDevice:
    def __init__(self):
        self.rbw = 1000.0
        self.span = 10000.0
        self.enabled = True
        self.mode = "auto"

    def setRBW(self, freq: float):
        """Set resolution bandwidth"""
        self.rbw = freq
        return f"RBW set to {freq} Hz"

    def setSpan(self, span: float):
        """Set frequency span"""
        self.span = span
        return f"Span set to {span}"

    def setMode(self, mode: str, auto_scale: bool):
        """Set measurement mode"""
        self.mode = mode
        return f"Mode set to {mode}, auto_scale: {auto_scale}"

    def enable(self, state: bool):
        """Enable/disable device"""
        self.enabled = state
        return f"Device {'enabled' if state else 'disabled'}"

    def calibrate(self):
        """Perform calibration"""
        return "Calibration complete"


def demo():
    import sys
    from PySide6.QtWidgets import QVBoxLayout, QMainWindow

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Sample data
    bp1 = BaseParameters("Voltage Parameters")
    bp1.addParameter(NumericParameter(name="VCC", value=3.3, units="V", minValue=3.0, maxValue=3.6))
    bp1.addParameter(NumericParameter(name="VDDIO", value=1.8, units="V", minValue=1.6, maxValue=2.0))
    bp1.addParameter(NumericParameter(name="Dangle berries", value=5000, units="Ber", minValue=1000, maxValue=10000))
    bp1.addParameter(StringParameter(name="Username", value="bert.russell", description="It's a coverup!"))

    bp2 = BaseParameters("Timing Parameters")
    bp2.addParameter(NumericParameter(name="Delay", value=10.0, units="ms"))
    bp2.addParameter(OptionParameter(name="Bert Mode", value=True, description="This is to enable BERT MODE!"))
    bp2.addParameter(EnumParameter("Timing Mode", TimingMode.Fast, enumType=TimingMode))
    groups = {bp1.groupName: bp1, bp2.groupName: bp2}

    # Main window
    window = QWidget()
    layout = QVBoxLayout(window)

    ui, widget_map = create_all_parameters_ui(groups)
    layout.addWidget(ui)

    apply_btn = QPushButton("Apply")
    layout.addWidget(apply_btn)

    def on_apply():
        apply_parameters(groups, widget_map)
        print("Updated parameters:")
        for group in groups.values():
            for param in group.values():
                print(f"{group.groupName} -> {param.name}: {param.value} {param.units}")

    apply_btn.clicked.connect(on_apply)

    device = ExampleDevice()
    group = create_all_methods_ui(device)
    layout.addWidget(group)
    layout.addStretch()

    window.setWindowTitle("Test Parameters")
    window.resize(400, 300)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    demo()
