"""
Basic Qt client example
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel
from PyQt6.QtCore import QTimer

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from client.ui.main_window import MainWindow
from client.data.data_manager import DataManager


def main():
    """Run a basic Qt client example"""
    
    app = QApplication(sys.argv)
    
    # Create main window
    window = MainWindow()
    window.show()
    
    # Create data manager
    data_manager = DataManager()
    
    # Connect data manager to window
    data_manager.data_received.connect(window.update_data)
    
    # Start data simulation (for demo purposes)
    timer = QTimer()
    timer.timeout.connect(lambda: data_manager.simulate_data())
    timer.start(1000)  # Update every second
    
    print("Qt client started...")
    print("Close the window to exit.")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
