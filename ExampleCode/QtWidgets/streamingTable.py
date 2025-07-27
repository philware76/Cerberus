import sys
import numpy as np
from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout,
                               QWidget, QTableView, QPushButton, QHBoxLayout,
                               QHeaderView, QAbstractItemView, QLabel, QSpinBox)
from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex, Signal, QTimer
from PySide6.QtGui import QFont
import threading
import time
import random


class StreamingNumpyTableModel(QAbstractTableModel):
    """Table model that automatically updates when numpy array grows"""

    def __init__(self, headers, initial_data=None, dtype=None, timestamp_columns=None, parent=None):
        super().__init__(parent)
        self._headers = headers

        # Use object dtype by default to handle mixed data types (strings, numbers, etc.)
        if dtype is None:
            dtype = object

        self._data = initial_data if initial_data is not None else np.empty((0, len(headers)), dtype=dtype)
        self._original_dtype = self._data.dtype

        # Track which columns should be formatted as timestamps
        self._timestamp_columns = timestamp_columns if timestamp_columns is not None else []

    def rowCount(self, parent=QModelIndex()):
        return self._data.shape[0]

    def columnCount(self, parent=QModelIndex()):
        return len(self._headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        row, col = index.row(), index.column()

        if role == Qt.DisplayRole or role == Qt.EditRole:
            if row < self._data.shape[0] and col < self._data.shape[1]:
                value = self._data[row, col]

                # Check if this column should be formatted as timestamp
                if col in self._timestamp_columns and isinstance(value, (int, float, np.integer, np.floating)):
                    # Format as readable timestamp
                    try:
                        import datetime
                        dt = datetime.datetime.fromtimestamp(float(value))
                        return dt.strftime("%H:%M:%S.%f")[:-3]  # HH:MM:SS.mmm format
                    except (ValueError, OSError):
                        return str(value)

                # Format display based on data type
                elif isinstance(value, (int, np.integer)):
                    return str(int(value))
                elif isinstance(value, (float, np.floating)):
                    return f"{float(value):.6g}"
                else:
                    return str(value)

        elif role == Qt.TextAlignmentRole:
            if row < self._data.shape[0] and col < self._data.shape[1]:
                value = self._data[row, col]
                if isinstance(value, (int, float, np.integer, np.floating)):
                    return Qt.AlignRight | Qt.AlignVCenter
            return Qt.AlignLeft | Qt.AlignVCenter

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                if section < len(self._headers):
                    return self._headers[section]
                return f"Col {section}"
            else:
                return str(section + 1)  # 1-based row numbering
        return None

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def append_row(self, new_row_data):
        """Add a new row to the table - called when numpy array grows"""
        if len(new_row_data) != len(self._headers):
            raise ValueError(f"Row data length {len(new_row_data)} doesn't match headers {len(self._headers)}")

        row_count = self.rowCount()

        # Signal that we're about to insert rows
        self.beginInsertRows(QModelIndex(), row_count, row_count)

        # Add the new row to numpy array
        new_row = np.array([new_row_data], dtype=self._data.dtype)
        if self._data.size == 0:
            self._data = new_row
        else:
            self._data = np.vstack([self._data, new_row])

        # Signal that we've finished inserting
        self.endInsertRows()

    def append_rows(self, new_rows_data):
        """Add multiple rows at once - more efficient for batch updates"""
        if not new_rows_data:
            return

        start_row = self.rowCount()
        end_row = start_row + len(new_rows_data) - 1

        self.beginInsertRows(QModelIndex(), start_row, end_row)

        new_rows = np.array(new_rows_data, dtype=self._data.dtype)
        if self._data.size == 0:
            self._data = new_rows
        else:
            self._data = np.vstack([self._data, new_rows])

        self.endInsertRows()

    def update_from_numpy_array(self, new_array):
        """Update model when external numpy array has grown"""
        if new_array.shape[1] != len(self._headers):
            raise ValueError("Array column count doesn't match headers")

        old_row_count = self.rowCount()
        new_row_count = new_array.shape[0]

        if new_row_count > old_row_count:
            # New rows added
            self.beginInsertRows(QModelIndex(), old_row_count, new_row_count - 1)
            self._data = new_array.copy()
            self.endInsertRows()
        elif new_row_count < old_row_count:
            # Rows removed (less common for streaming)
            self.beginRemoveRows(QModelIndex(), new_row_count, old_row_count - 1)
            self._data = new_array.copy()
            self.endRemoveRows()
        else:
            # Same size, but data might have changed
            self._data = new_array.copy()
            self.dataChanged.emit(self.index(0, 0),
                                  self.index(new_row_count - 1, len(self._headers) - 1))

    def clear_data(self):
        """Clear all data while keeping headers"""
        if self.rowCount() > 0:
            self.beginRemoveRows(QModelIndex(), 0, self.rowCount() - 1)
            self._data = np.empty((0, len(self._headers)), dtype=self._data.dtype)
            self.endRemoveRows()

    def get_numpy_array(self):
        """Get copy of current numpy array"""
        return self._data.copy()


class StreamingTableWidget(QWidget):
    """Widget that displays streaming numpy data"""

    def __init__(self, headers, auto_scroll=True, max_rows=None, dtype=None, timestamp_columns=None, parent=None):
        super().__init__(parent)
        self.headers = headers
        self.auto_scroll = auto_scroll
        self.max_rows = max_rows
        self.dtype = dtype if dtype is not None else object  # Default to object for mixed types
        self.timestamp_columns = timestamp_columns if timestamp_columns is not None else []

        self.setup_ui()
        self.setup_model()
        self.configure_table()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Info bar
        info_layout = QHBoxLayout()
        self.row_count_label = QLabel("Rows: 0")
        self.update_rate_label = QLabel("Updates/sec: 0.0")
        info_layout.addWidget(self.row_count_label)
        info_layout.addWidget(self.update_rate_label)
        info_layout.addStretch()
        layout.addLayout(info_layout)

        # Table view
        self.table_view = QTableView()
        layout.addWidget(self.table_view)

        # Control buttons
        button_layout = QHBoxLayout()

        self.clear_btn = QPushButton("Clear Data")
        self.scroll_btn = QPushButton("Auto Scroll: ON" if self.auto_scroll else "Auto Scroll: OFF")
        self.pause_btn = QPushButton("Pause Updates")

        button_layout.addWidget(self.clear_btn)
        button_layout.addWidget(self.scroll_btn)
        button_layout.addWidget(self.pause_btn)
        button_layout.addStretch()

        layout.addLayout(button_layout)

        # Connect buttons
        self.clear_btn.clicked.connect(self.clear_data)
        self.scroll_btn.clicked.connect(self.toggle_auto_scroll)
        self.pause_btn.clicked.connect(self.toggle_pause)

        # Update tracking
        self.update_count = 0
        self.last_update_time = time.time()
        self.is_paused = False

        # Timer for update rate calculation
        self.rate_timer = QTimer()
        self.rate_timer.timeout.connect(self.update_rate_display)
        self.rate_timer.start(1000)  # Update every second

    def setup_model(self):
        self.model = StreamingNumpyTableModel(self.headers, dtype=self.dtype, timestamp_columns=self.timestamp_columns)
        self.table_view.setModel(self.model)

        # Connect to model changes
        self.model.rowsInserted.connect(self.on_rows_inserted)

    def configure_table(self):
        """Configure table appearance"""
        # Set font
        font = QFont("Consolas", 9)
        self.table_view.setFont(font)

        # Configure headers
        h_header = self.table_view.horizontalHeader()
        h_header.setSectionResizeMode(QHeaderView.Stretch)

        v_header = self.table_view.verticalHeader()
        v_header.setDefaultSectionSize(25)  # Compact rows

        # Appearance
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectRows)

        # Performance optimizations for large datasets
        self.table_view.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table_view.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)

    def add_row(self, row_data):
        """Add a single row of data"""
        if not self.is_paused:
            self.model.append_row(row_data)
            self.update_count += 1

            # Enforce max rows limit
            if self.max_rows and self.model.rowCount() > self.max_rows:
                # Remove oldest rows (this is a simplified approach)
                # For better performance, consider using a circular buffer
                self.trim_to_max_rows()

    def add_rows(self, rows_data):
        """Add multiple rows at once"""
        if not self.is_paused:
            self.model.append_rows(rows_data)
            self.update_count += len(rows_data)

            if self.max_rows and self.model.rowCount() > self.max_rows:
                self.trim_to_max_rows()

    def update_from_numpy_array(self, numpy_array):
        """Update table from external numpy array"""
        if not self.is_paused:
            old_count = self.model.rowCount()
            self.model.update_from_numpy_array(numpy_array)
            new_count = self.model.rowCount()
            self.update_count += max(0, new_count - old_count)

    def trim_to_max_rows(self):
        """Keep only the most recent max_rows"""
        current_array = self.model.get_numpy_array()
        if current_array.shape[0] > self.max_rows:
            trimmed_array = current_array[-self.max_rows:]
            self.model.beginResetModel()
            self.model._data = trimmed_array
            self.model.endResetModel()

    def on_rows_inserted(self, parent, first, last):
        """Called when new rows are added"""
        self.row_count_label.setText(f"Rows: {self.model.rowCount()}")

        # Auto-scroll to bottom
        if self.auto_scroll:
            self.table_view.scrollToBottom()

    def update_rate_display(self):
        """Update the display of updates per second"""
        current_time = time.time()
        time_diff = current_time - self.last_update_time

        if time_diff > 0:
            rate = self.update_count / time_diff
            self.update_rate_label.setText(f"Updates/sec: {rate:.1f}")

        # Reset counters
        self.update_count = 0
        self.last_update_time = current_time

    def clear_data(self):
        """Clear all data"""
        self.model.clear_data()
        self.row_count_label.setText("Rows: 0")

    def toggle_auto_scroll(self):
        """Toggle auto-scroll feature"""
        self.auto_scroll = not self.auto_scroll
        self.scroll_btn.setText(f"Auto Scroll: {'ON' if self.auto_scroll else 'OFF'}")

    def toggle_pause(self):
        """Toggle pause state"""
        self.is_paused = not self.is_paused
        self.pause_btn.setText("Resume Updates" if self.is_paused else "Pause Updates")

    def get_numpy_array(self):
        """Get current numpy array"""
        return self.model.get_numpy_array()


class DataStreamer:
    """Simulates streaming data source"""

    def __init__(self, table_widget, update_rate=10):
        self.table_widget = table_widget
        self.update_rate = update_rate  # Updates per second
        self.running = False
        self.thread = None

    def start_streaming(self):
        """Start the data streaming thread"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._stream_data)
            self.thread.daemon = True
            self.thread.start()

    def stop_streaming(self):
        """Stop the data streaming"""
        self.running = False
        if self.thread:
            self.thread.join()

    def _stream_data(self):
        """Generate and stream data"""
        counter = 0
        while self.running:
            # Generate sample data (timestamp, random values)
            timestamp = time.time()
            value1 = random.uniform(-10, 10)
            value2 = random.uniform(0, 100)
            value3 = random.choice(['A', 'B', 'C'])

            row_data = [timestamp, value1, value2, value3]

            # Add to table (this will be called from background thread)
            # Note: In real applications, you'd use Qt signals for thread safety
            self.table_widget.add_row(row_data)

            counter += 1
            time.sleep(1.0 / self.update_rate)


class MainWindow(QMainWindow):
    """Demo main window with streaming data"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Streaming Numpy Table Demo")
        self.setGeometry(100, 100, 900, 600)

        # Create table with headers and specify timestamp column
        headers = ["Timestamp", "Signal (mV)", "Power (%)", "Status"]
        self.table_widget = StreamingTableWidget(
            headers,
            auto_scroll=True,
            max_rows=1000,
            timestamp_columns=[0]  # Column 0 (Timestamp) should be formatted as time
        )
        self.setCentralWidget(self.table_widget)

        # Create data streamer
        self.streamer = DataStreamer(self.table_widget, update_rate=5)  # 5 updates/sec

        # Add menu or toolbar for start/stop
        self.setup_controls()

        # Start streaming automatically
        self.streamer.start_streaming()

    def setup_controls(self):
        """Add start/stop controls"""
        # This could be added to the table widget or as a separate toolbar
        pass

    def closeEvent(self, event):
        """Clean shutdown"""
        self.streamer.stop_streaming()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
