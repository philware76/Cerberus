import logging
from typing import Any, Callable, Dict, Optional, cast

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QFrame,
                               QHBoxLayout, QLabel, QLineEdit, QSpinBox,
                               QToolButton, QVBoxLayout, QWidget)

from Cerberus.plugins.baseParameters import (BaseParameter, BaseParameters,
                                             EnumParameter, NumericParameter,
                                             OptionParameter, StringParameter)


class CollapsibleGroupBox(QWidget):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)

        # === Toggle button ===
        self.toggle_button = QToolButton()
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.toggle_button.setArrowType(Qt.ArrowType.DownArrow)
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
        self.content_area.setFrameShape(QFrame.Shape.StyledPanel)
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
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

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
        self.toggle_button.setArrowType(Qt.ArrowType.DownArrow if expanding else Qt.ArrowType.RightArrow)

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
        if isinstance(param.value, float) or isinstance(param.minValue, float) or isinstance(param.maxValue, float):
            spin = QDoubleSpinBox()
            spin.setDecimals(6)
            spin.setSingleStep(0.1)
            # Apply min/max as float
            if param.minValue is not None:
                spin.setMinimum(float(param.minValue))
            if param.maxValue is not None:
                spin.setMaximum(float(param.maxValue))
            try:
                spin.setValue(float(param.value))  # type: ignore[arg-type]
            except Exception:
                logging.error(f"Invalid float value for parameter {param.name}: {param.value}")
        else:
            spin = QSpinBox()
            if param.minValue is not None:
                spin.setMinimum(int(param.minValue))
            if param.maxValue is not None:
                spin.setMaximum(int(param.maxValue))
            try:
                spin.setValue(int(param.value))  # type: ignore[arg-type]
            except Exception:
                logging.error(f"Invalid int value for parameter {param.name}: {param.value}")

        spin.setSuffix(f" {param.units}" if param.units else "")
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
        if param.value in enum_members:
            combobox.setCurrentIndex(enum_members.index(param.value))
        widget = combobox

    elif isinstance(param, StringParameter):
        text = QLineEdit()
        text.setText(str(param.value))
        widget = text

    if widget is None:
        logging.error(f"Failed to create widget for {param} parameter")
        emptyLabel = QLabel()
        emptyLabel.setText(f"Unknown Parameter Type: {param.name}")
        return emptyLabel

    if param.description:
        widget.setToolTip(param.description)

    return widget


def create_parameters_groupbox(title: str, parameters: dict[str, BaseParameter], dependencies: Optional[Dict[str, Dict[str, Callable[[Any], bool]]]] = None):
    """
    Create a collapsible group box for parameters with optional dependency management.

    Args:
        title: Group box title
        parameters: Dictionary of parameters to create widgets for
        dependencies: Optional dictionary defining parameter dependencies (legacy support).
                     The new preferred method is to use parameter.setWidgetDependency().
    """
    groupbox = CollapsibleGroupBox(title)
    widget_map = {}
    dependency_connections = []

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

    # Set up parameter-based dependencies (NEW preferred method)
    for param in parameters.values():
        if param.hasWidgetDependencies():
            dependent_widget = widget_map[param.name]

            for widget_property, controlling_param in param.getWidgetDependencies().items():
                # Find the controlling widget by parameter name
                controlling_widget = None
                for other_param in parameters.values():
                    if other_param is controlling_param:
                        controlling_widget = widget_map[other_param.name]
                        break

                if controlling_widget is not None:
                    # Create dependency handler based on widget property
                    def create_parameter_dependency_handler(dep_widget, prop_name, ctrl_param):
                        def handle_change(*args):
                            if isinstance(controlling_widget, QCheckBox):
                                param_value = controlling_widget.isChecked()
                            elif isinstance(controlling_widget, QComboBox):
                                param_value = controlling_widget.currentData()
                            elif isinstance(controlling_widget, (QSpinBox, QDoubleSpinBox)):
                                param_value = controlling_widget.value()
                            elif isinstance(controlling_widget, QLineEdit):
                                param_value = controlling_widget.text()
                            else:
                                param_value = True

                            # Update the controlling parameter's value to match widget
                            ctrl_param.value = param_value

                            # Apply the widget property based on parameter value
                            if prop_name == "enabled":
                                dep_widget.setEnabled(bool(param_value))
                            elif prop_name == "visible":
                                dep_widget.setVisible(bool(param_value))
                            # Add more widget properties as needed

                        return handle_change

                    handler = create_parameter_dependency_handler(dependent_widget, widget_property, controlling_param)
                    dependency_connections.append((controlling_widget, handler))

                    # Connect the appropriate signal based on widget type
                    if isinstance(controlling_widget, QCheckBox):
                        controlling_widget.toggled.connect(handler)
                    elif isinstance(controlling_widget, QComboBox):
                        controlling_widget.currentIndexChanged.connect(handler)
                    elif isinstance(controlling_widget, (QSpinBox, QDoubleSpinBox)):
                        controlling_widget.valueChanged.connect(handler)
                    elif isinstance(controlling_widget, QLineEdit):
                        controlling_widget.textChanged.connect(handler)

                    # Set initial state
                    handler()

    # Set up legacy dependencies (for backward compatibility)
    if dependencies:
        for dependent_param, controllers in dependencies.items():
            if dependent_param in widget_map:
                dependent_widget = widget_map[dependent_param]

                for controlling_param, validation_func in controllers.items():
                    if controlling_param in widget_map:
                        controlling_widget = widget_map[controlling_param]

                        # Create and store the connection function
                        def create_dependency_handler(dep_widget, val_func):
                            def handle_change(*args):
                                if isinstance(controlling_widget, QCheckBox):
                                    enable = val_func(controlling_widget.isChecked())
                                elif isinstance(controlling_widget, QComboBox):
                                    enable = val_func(controlling_widget.currentData())
                                elif isinstance(controlling_widget, (QSpinBox, QDoubleSpinBox)):
                                    enable = val_func(controlling_widget.value())
                                elif isinstance(controlling_widget, QLineEdit):
                                    enable = val_func(controlling_widget.text())
                                else:
                                    enable = True

                                dep_widget.setEnabled(enable)
                            return handle_change

                        handler = create_dependency_handler(dependent_widget, validation_func)
                        dependency_connections.append((controlling_widget, handler))

                        # Connect the appropriate signal based on widget type
                        if isinstance(controlling_widget, QCheckBox):
                            controlling_widget.toggled.connect(handler)
                        elif isinstance(controlling_widget, QComboBox):
                            controlling_widget.currentIndexChanged.connect(handler)
                        elif isinstance(controlling_widget, (QSpinBox, QDoubleSpinBox)):
                            controlling_widget.valueChanged.connect(handler)
                        elif isinstance(controlling_widget, QLineEdit):
                            controlling_widget.textChanged.connect(handler)

                        # Set initial state
                        handler()

    return groupbox, widget_map


def create_all_parameters_ui(groups: Dict[str, BaseParameters], dependencies: Optional[Dict[str, Dict[str, Dict[str, Callable[[Any], bool]]]]] = None) -> tuple[QWidget, dict[str, dict[str, QWidget]]]:
    """
    Create UI for all parameter groups with optional dependencies.

    Args:
        groups: Dictionary of parameter groups
        dependencies: Optional nested dictionary defining dependencies.
                     Format: {group_name: {dependent_param: {controlling_param: validation_function}}}
    """
    container = QWidget()
    main_layout = QVBoxLayout()
    all_widget_map = {}

    for group_name, base_params in groups.items():
        group_dependencies = dependencies.get(group_name) if dependencies else None
        groupbox, widget_map = create_parameters_groupbox(group_name, base_params, group_dependencies)
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
            if isinstance(widget, QSpinBox):
                param.value = widget.value()
            elif isinstance(widget, QLineEdit):
                param.value = widget.text()
            elif isinstance(widget, QCheckBox):
                param.value = widget.isChecked()
            elif isinstance(widget, QComboBox):
                param.value = cast(QComboBox, widget).currentData()


def create_checkbox_dependency(checkbox_value: bool = True) -> Callable[[Any], bool]:
    """
    Convenience function to create a dependency that enables a widget when a checkbox is checked.

    Args:
        checkbox_value: The checkbox value that should enable the dependent widget (default: True)

    Returns:
        A validation function for use in dependencies
    """
    return lambda value: bool(value) == checkbox_value


def create_txlevel_test_dependencies() -> Dict[str, Dict[str, Dict[str, Callable[[Any], bool]]]]:
    """
    Create the specific dependencies for TxLevelTest parameters.

    Returns:
        Dependencies dictionary for use with create_all_parameters_ui
    """
    return {
        "Test Specs": {
            "MHz step": {
                "Full band sweep": create_checkbox_dependency(True)
            }
        }
    }
