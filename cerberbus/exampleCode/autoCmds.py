import inspect
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QApplication, QCheckBox, QDoubleSpinBox,
                               QHBoxLayout, QLabel, QLineEdit, QPushButton,
                               QScrollArea, QSpinBox, QVBoxLayout, QWidget)

from gui.widgetGen import CollapsibleGroupBox


class CommandWidgetGenerator:
    def __init__(self, target_object):
        self.target_object = target_object
        self.command_widgets = []

    def create_parameter_widget(self, param_name, param_type, default_value=None):
        """Create appropriate widget based on parameter type"""
        print(f"    Creating widget for {param_name}: type={param_type}, default={default_value}")  # Debug

        if param_type == bool:  # or (default_value is not None and isinstance(default_value, bool)):
            widget = QCheckBox()
            if default_value is not None:
                widget.setChecked(default_value)
            return widget

        elif param_type == int:  # or (default_value is not None and isinstance(default_value, int)):
            widget = QSpinBox()
            widget.setRange(-2147483648, 2147483647)
            if default_value is not None:
                widget.setValue(default_value)
            return widget

        elif param_type == float:  # or (default_value is not None and isinstance(default_value, float)):
            widget = QDoubleSpinBox()
            widget.setRange(-999999.99, 999999.99)
            widget.setDecimals(2)
            if default_value is not None:
                widget.setValue(default_value)
            return widget

        elif param_type == str:  # or (default_value is not None and isinstance(default_value, str)):
            widget = QLineEdit()
            if default_value is not None:
                widget.setText(str(default_value))
            return widget

        else:
            # Default to string input for unknown types
            widget = QLineEdit()
            if default_value is not None:
                widget.setText(str(default_value))
            widget.setPlaceholderText(f"Enter {param_type.__name__ if hasattr(param_type, '__name__') else 'value'}")
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
            if param_type == str or not text:
                return text
            elif param_type == int:
                try:
                    return int(float(text))  # Handle "1.0" -> 1
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
        cmd_button.setToolTip(method.__doc__.strip())
        layout.addWidget(cmd_button)

        # Get method signature
        try:
            sig = inspect.signature(method)
            # Get ALL parameters except 'self'
            all_params = list(sig.parameters.values())
            params = [p for p in all_params if p.name != 'self']
            print(f"Method {method_name} has {len(params)} parameters: {[p.name for p in params]}")  # Debug print
        except (ValueError, TypeError) as e:
            print(f"Could not get signature for {method_name}: {e}")
            params = []

        paramWidgets = []

        # Create parameter widgets for ALL parameters
        for i, param in enumerate(params):
            param_type = param.annotation if param.annotation != inspect.Parameter.empty else str
            has_default = param.default != inspect.Parameter.empty
            default_val = param.default if has_default else None

            print(f"  Parameter {i}: {param.name}, type: {param_type}, has_default: {has_default}, default: {default_val}")

            # Add parameter label
            label = QLabel(f"{param.name}:")
            label.setMinimumWidth(30)
            label.setAlignment(Qt.AlignmentFlag.AlignRight)
            layout.addWidget(label)

            # Infer type from default value if no annotation and has default
            if param_type == inspect.Parameter.empty and default_val is not None:
                param_type = type(default_val)
            elif param_type == inspect.Parameter.empty:
                param_type = str  # Default to string for unknown types

            # Create widget
            paramWidget = self.create_parameter_widget(param.name, param_type, default_val)
            paramWidget.setMinimumWidth(100)
            layout.addWidget(paramWidget)

            paramWidgets.append((param.name, paramWidget, param_type, param.default, has_default))

        # Connect button click to method call
        def call_method():
            args = []
            kwargs = {}

            for param_name, paramWidget, param_type, default_value, has_default in paramWidgets:
                value = self.get_widget_value(paramWidget, param_type)

                # Required parameters (no default) go as positional args
                if not has_default:
                    args.append(value)
                else:
                    # Optional parameters go as kwargs only if different from default
                    if value != default_value:
                        kwargs[param_name] = value

            try:
                if kwargs:
                    result = method(*args, **kwargs)
                    print(f"Called {method_name}({', '.join(map(str, args))}, {kwargs}) -> {result}")
                else:
                    result = method(*args)
                    print(f"Called {method_name}({', '.join(map(str, args))}) -> {result}")

            except Exception as e:
                print(f"Error calling {method_name}: {e}")
                import traceback
                traceback.print_exc()

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

        # Find all callable methods (excluding private ones and common object methods)
        methods = []
        for attr_name in sorted(dir(self.target_object)):
            if not attr_name.startswith('_') or attr_name.startswith('__'):
                attr = getattr(self.target_object, attr_name)
                if callable(attr) and not attr_name.startswith('_'):
                    methods.append((attr_name, attr))
                    print(f"Found method: {attr_name}")  # Debug print

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


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Create example device
    device = ExampleDevice()

    # Generate command widget
    generator = CommandWidgetGenerator(device)
    widget = generator.generate_widget()

    groupbox = CollapsibleGroupBox("Example Device")
    groupbox.addWidget(widget)

    window = QWidget()
    mainLayout = QVBoxLayout(window)
    mainLayout.addWidget(groupbox)
    mainLayout.addStretch()

    window.setWindowTitle("Device Command Interface")
    window.resize(600, 400)
    window.show()

    sys.exit(app.exec())
