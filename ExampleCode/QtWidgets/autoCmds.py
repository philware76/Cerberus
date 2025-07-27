import sys
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                               QPushButton, QLineEdit, QSpinBox, QDoubleSpinBox,
                               QCheckBox, QComboBox, QLabel, QScrollArea)
from PySide6.QtCore import Qt
import inspect


class CommandWidgetGenerator:
    def __init__(self, target_object):
        self.target_object = target_object
        self.command_widgets = []

    def create_parameter_widget(self, param_name, param_type, default_value=None):
        """Create appropriate widget based on parameter type"""
        if param_type == bool:
            widget = QCheckBox()
            if default_value is not None:
                widget.setChecked(default_value)
            return widget

        elif param_type == int:
            widget = QSpinBox()
            widget.setRange(-2147483648, 2147483647)
            if default_value is not None:
                widget.setValue(default_value)
            return widget

        elif param_type == float:
            widget = QDoubleSpinBox()
            widget.setRange(-999999.99, 999999.99)
            widget.setDecimals(6)
            if default_value is not None:
                widget.setValue(default_value)
            return widget

        elif param_type == str:
            widget = QLineEdit()
            if default_value is not None:
                widget.setText(str(default_value))
            return widget

        else:
            # Default to string input for unknown types
            widget = QLineEdit()
            if default_value is not None:
                widget.setText(str(default_value))
            return widget

    def get_widget_value(self, widget, param_type):
        """Extract value from widget based on type"""
        if isinstance(widget, QCheckBox):
            return widget.isChecked()
        elif isinstance(widget, QSpinBox):
            return widget.value()
        elif isinstance(widget, QDoubleSpinBox):
            return widget.value()
        elif isinstance(widget, QLineEdit):
            text = widget.text()
            if param_type == str:
                return text
            elif param_type == int:
                try:
                    return int(text)
                except ValueError:
                    return 0
            elif param_type == float:
                try:
                    return float(text)
                except ValueError:
                    return 0.0
            else:
                return text
        return None

    def create_command_widget(self, method_name, method):
        """Create a horizontal layout for a command with its parameters"""
        layout = QHBoxLayout()

        # Create command button
        cmd_button = QPushButton(method_name)
        cmd_button.setMinimumWidth(120)
        layout.addWidget(cmd_button)

        # Get method signature
        try:
            sig = inspect.signature(method)
            params = list(sig.parameters.values())[1:]  # Skip 'self' parameter
        except (ValueError, TypeError):
            params = []

        param_widgets = []

        # Create parameter widgets
        for param in params:
            param_type = param.annotation if param.annotation != inspect.Parameter.empty else str
            default_val = param.default if param.default != inspect.Parameter.empty else None

            # Add parameter label
            label = QLabel(f"{param.name}:")
            label.setMinimumWidth(60)
            layout.addWidget(label)

            # Create appropriate widget
            widget = self.create_parameter_widget(param.name, param_type, default_val)
            widget.setMinimumWidth(100)
            layout.addWidget(widget)

            param_widgets.append((param.name, widget, param_type))

        # Connect button click to method call
        def call_method():
            args = []
            for param_name, widget, param_type in param_widgets:
                value = self.get_widget_value(widget, param_type)
                args.append(value)

            try:
                result = method(*args)
                print(f"Called {method_name}({', '.join(map(str, args))}) -> {result}")
            except Exception as e:
                print(f"Error calling {method_name}: {e}")

        cmd_button.clicked.connect(call_method)

        layout.addStretch()  # Push everything to the left
        return layout

    def generate_widget(self, parent=None):
        """Generate the main widget with all command layouts"""
        main_widget = QWidget(parent)
        main_layout = QVBoxLayout(main_widget)

        # Create scroll area for many commands
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # Find all callable methods (excluding private ones)
        methods = []
        for attr_name in dir(self.target_object):
            if not attr_name.startswith('_'):
                attr = getattr(self.target_object, attr_name)
                if callable(attr):
                    methods.append((attr_name, attr))

        # Create widgets for each method
        for method_name, method in methods:
            cmd_layout = self.create_command_widget(method_name, method)
            scroll_layout.addLayout(cmd_layout)

        scroll_layout.addStretch()
        scroll_widget.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)

        main_layout.addWidget(scroll_area)
        return main_widget


# Example usage with a sample class
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

    def setSpan(self, span: float, units: str = "Hz"):
        """Set frequency span"""
        self.span = span
        return f"Span set to {span} {units}"

    def setMode(self, mode: str, auto_scale: bool = True):
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


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Create example device
    device = ExampleDevice()

    # Generate command widget
    generator = CommandWidgetGenerator(device)
    widget = generator.generate_widget()

    widget.setWindowTitle("Device Command Interface")
    widget.resize(600, 400)
    widget.show()

    sys.exit(app.exec_())
