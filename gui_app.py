import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QCheckBox, QTextEdit, QFileDialog,
    QProgressBar, QGroupBox, QMessageBox, QLineEdit, QSpinBox
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QMutex, QWaitCondition
from PyQt6.QtGui import QFont
import os
import queue
import threading
from csv_handler import CSVHandler
from account_manager import AccountManager
from timer_manager import TimerManager

#e955120e5c61b9eb64e9__cr.ca:27e87286655e11fe@gw.dataimpulse.com:823
class WorkerThread(threading.Thread):
    """Individual worker thread for processing accounts"""
    
    def __init__(self, thread_id, account_queue, room_number, register_first, proxy_url, 
                 callback_progress, callback_status, callback_processed):
        super().__init__()
        self.thread_id = thread_id
        self.account_queue = account_queue
        self.room_number = room_number
        self.register_first = register_first
        self.proxy_url = proxy_url
        self.callback_progress = callback_progress
        self.callback_status = callback_status
        self.callback_processed = callback_processed
        self.is_running = True
        self.daemon = True
    
    def run(self):
        """Process accounts from queue"""
        manager = AccountManager(proxy_url=self.proxy_url if self.proxy_url else None)
        
        while self.is_running:
            try:
                # Get account from queue with timeout
                account, idx, total = self.account_queue.get(timeout=1)
                
                if account is None:  # Poison pill
                    break
                
                self.callback_status(f"[Thread {self.thread_id}] Processing {account['email']} ({idx + 1}/{total})...")
                
                # Process account
                success = manager.process_account_for_room(
                    account, 
                    self.room_number,
                    self.register_first
                )
                
                # Update account status
                if success:
                    CSVHandler.update_room_status(account, self.room_number, True)
                    self.callback_status(f"[Thread {self.thread_id}] ✅ Success: {account['email']}")
                else:
                    self.callback_status(f"[Thread {self.thread_id}] ❌ Failed: {account['email']}")
                
                # Report progress and processed account
                self.callback_progress(idx + 1, total)
                self.callback_processed(account.copy())
                
                self.account_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                self.callback_status(f"[Thread {self.thread_id}] ❌ Error: {str(e)}")
                try:
                    self.account_queue.task_done()
                except:
                    pass
    
    def stop(self):
        """Stop the worker thread"""
        self.is_running = False


class ProcessThread(QThread):
    """Main thread coordinator for multi-threaded processing"""
    
    progress = pyqtSignal(int, int)  # current, total
    status = pyqtSignal(str)  # status message
    account_processed = pyqtSignal(dict)  # processed account data
    finished = pyqtSignal(bool)  # success status
    
    def __init__(self, accounts, room_number, register_first=False, proxy_url="", num_threads=1):
        super().__init__()
        self.accounts = accounts
        self.room_number = room_number
        self.register_first = register_first
        self.proxy_url = proxy_url
        self.num_threads = num_threads
        self.is_running = True
        self.account_queue = queue.Queue()
        self.workers = []
        self.progress_lock = threading.Lock()
        self.processed_count = 0
    
    def emit_progress(self, current, total):
        """Thread-safe progress emission"""
        with self.progress_lock:
            self.progress.emit(current, total)
    
    def emit_status(self, message):
        """Thread-safe status emission"""
        self.status.emit(message)
    
    def emit_processed(self, account):
        """Thread-safe account processed emission"""
        self.account_processed.emit(account)
    
    def run(self):
        """Coordinate multi-threaded account processing"""
        total = len(self.accounts)
        
        self.status.emit(f"🚀 Starting {self.num_threads} worker thread(s)...\n")
        
        # Create worker threads
        for i in range(self.num_threads):
            worker = WorkerThread(
                thread_id=i + 1,
                account_queue=self.account_queue,
                room_number=self.room_number,
                register_first=self.register_first,
                proxy_url=self.proxy_url,
                callback_progress=self.emit_progress,
                callback_status=self.emit_status,
                callback_processed=self.emit_processed
            )
            worker.start()
            self.workers.append(worker)
        
        # Add accounts to queue
        for idx, account in enumerate(self.accounts):
            if not self.is_running:
                break
            self.account_queue.put((account, idx, total))
        
        # Add poison pills to stop workers
        for _ in range(self.num_threads):
            self.account_queue.put((None, 0, 0))
        
        # Wait for all tasks to complete
        self.account_queue.join()
        
        # Wait for all workers to finish
        for worker in self.workers:
            worker.join(timeout=2)
        
        if self.is_running:
            self.status.emit(f"\n🎉 Completed processing {total} accounts for Room {self.room_number}")
            self.finished.emit(True)
        else:
            self.status.emit(f"\n⏹️ Processing stopped")
            self.finished.emit(False)
    
    def stop(self):
        """Stop all worker threads"""
        self.is_running = False
        
        # Stop all workers
        for worker in self.workers:
            worker.stop()
        
        # Clear queue
        while not self.account_queue.empty():
            try:
                self.account_queue.get_nowait()
                self.account_queue.task_done()
            except queue.Empty:
                break


class MainWindow(QMainWindow):
    """Main GUI window"""
    
    def __init__(self):
        super().__init__()
        self.accounts = []
        self.current_file = None
        self.process_thread = None
        self.processed_accounts = []
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Glade Contest Bot - Room Manager")
        self.setGeometry(100, 100, 1400, 800)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout - horizontal split
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Left panel - Controls
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_panel.setLayout(left_layout)
        left_panel.setMaximumWidth(550)
        left_panel.setMinimumWidth(500)
        
        # Title
        title = QLabel("🎮 Glade Contest Bot")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(title)
        
        # File selection group
        file_group = QGroupBox("📁 File Selection")
        file_layout = QVBoxLayout()
        
        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("padding: 10px; background-color: #f0f0f0; border-radius: 5px;")
        file_layout.addWidget(self.file_label)
        
        btn_layout = QHBoxLayout()
        self.select_file_btn = QPushButton("Select CSV File")
        self.select_file_btn.clicked.connect(self.select_file)
        btn_layout.addWidget(self.select_file_btn)
        
        self.reload_btn = QPushButton("Reload File")
        self.reload_btn.clicked.connect(self.reload_file)
        self.reload_btn.setEnabled(False)
        btn_layout.addWidget(self.reload_btn)
        
        file_layout.addLayout(btn_layout)
        file_group.setLayout(file_layout)
        left_layout.addWidget(file_group)
        
        # Proxy configuration group
        proxy_group = QGroupBox("🔄 Proxy Configuration")
        proxy_layout = QVBoxLayout()
        
        proxy_desc = QLabel("Auto-rotating proxy URL:")
        proxy_desc.setStyleSheet("color: #666; font-size: 10px;")
        proxy_layout.addWidget(proxy_desc)
        
        self.proxy_input = QLineEdit()
        self.proxy_input.setPlaceholderText("proxy-url:port")
        proxy_layout.addWidget(self.proxy_input)
        
        proxy_btn_layout = QHBoxLayout()
        self.proxy_test_btn = QPushButton("Test Proxy")
        self.proxy_test_btn.clicked.connect(self.test_proxy)
        proxy_btn_layout.addWidget(self.proxy_test_btn)
        proxy_layout.addLayout(proxy_btn_layout)
        
        self.proxy_status_label = QLabel("Proxy: Not configured")
        self.proxy_status_label.setStyleSheet("padding: 5px; color: #666; font-size: 10px;")
        proxy_layout.addWidget(self.proxy_status_label)
        
        proxy_group.setLayout(proxy_layout)
        left_layout.addWidget(proxy_group)
        
        # Threading configuration group
        thread_group = QGroupBox("⚡ Threading Configuration")
        thread_layout = QVBoxLayout()
        
        thread_input_layout = QHBoxLayout()
        thread_label = QLabel("Threads:")
        thread_input_layout.addWidget(thread_label)
        
        self.thread_spinner = QSpinBox()
        self.thread_spinner.setMinimum(1)
        self.thread_spinner.setMaximum(50)
        self.thread_spinner.setValue(5)
        self.thread_spinner.setToolTip("Number of concurrent threads (1-50)")
        thread_input_layout.addWidget(self.thread_spinner)
        thread_input_layout.addStretch()
        
        thread_layout.addLayout(thread_input_layout)
        
        thread_info = QLabel("💡 Recommended: 5-20 threads")
        thread_info.setStyleSheet("color: #666; font-size: 10px; font-style: italic;")
        thread_layout.addWidget(thread_info)
        
        thread_group.setLayout(thread_layout)
        left_layout.addWidget(thread_group)
        
        # Room selection group
        room_group = QGroupBox("🎯 Room Selection")
        room_layout = QVBoxLayout()
        
        self.room1_checkbox = QCheckBox("Room 1 (Register + Play)")
        self.room2_checkbox = QCheckBox("Room 2 (Play - requires 24h)")
        self.room3_checkbox = QCheckBox("Room 3 (Play - requires 24h)")
        
        room_layout.addWidget(self.room1_checkbox)
        room_layout.addWidget(self.room2_checkbox)
        room_layout.addWidget(self.room3_checkbox)
        
        room_group.setLayout(room_layout)
        left_layout.addWidget(room_group)
        
        # Status group
        status_group = QGroupBox("📊 Status")
        status_layout = QVBoxLayout()
        
        self.account_status_label = QLabel("Total: 0 | Ready: 0")
        self.account_status_label.setStyleSheet("padding: 5px; font-size: 11px;")
        status_layout.addWidget(self.account_status_label)
        
        self.timer_label = QLabel("Select a room to see timer")
        self.timer_label.setStyleSheet("padding: 5px; color: #666; font-size: 10px;")
        status_layout.addWidget(self.timer_label)
        
        status_group.setLayout(status_layout)
        left_layout.addWidget(status_group)
        
        # Progress bar
        progress_group = QGroupBox("📈 Progress")
        progress_layout = QVBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        progress_group.setLayout(progress_layout)
        left_layout.addWidget(progress_group)
        
        # Action buttons
        action_layout = QVBoxLayout()
        
        self.start_btn = QPushButton("▶️ Start Processing")
        self.start_btn.clicked.connect(self.start_processing)
        self.start_btn.setEnabled(False)
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 12px; font-size: 14px; font-weight: bold;")
        action_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹️ Stop Processing")
        self.stop_btn.clicked.connect(self.stop_processing)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("background-color: #f44336; color: white; padding: 12px; font-size: 14px; font-weight: bold;")
        action_layout.addWidget(self.stop_btn)
        
        left_layout.addLayout(action_layout)
        
        # Footer
        footer = QLabel("💡 Upload CSV with: email, password, first_name, last_name, phone_number")
        footer.setStyleSheet("padding: 10px; color: #666; font-style: italic; font-size: 9px;")
        footer.setWordWrap(True)
        left_layout.addWidget(footer)
        
        left_layout.addStretch()
        
        # Right panel - Logs
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_panel.setLayout(right_layout)
        
        # Log output
        log_header = QLabel("📝 Process Log")
        log_header_font = QFont()
        log_header_font.setPointSize(14)
        log_header_font.setBold(True)
        log_header.setFont(log_header_font)
        right_layout.addWidget(log_header)
        
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("font-family: 'Courier New', monospace; font-size: 11px; background-color: #1e1e1e; color: #d4d4d4; padding: 10px;")
        right_layout.addWidget(self.log_output)
        
        # Add panels to main layout
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel, stretch=1)
    
    def test_proxy(self):
        """Test proxy configuration"""
        proxy_url = self.proxy_input.text().strip()
        
        if not proxy_url:
            QMessageBox.warning(self, "Warning", "Please enter a proxy URL first!")
            return
        
        self.proxy_status_label.setText("Testing proxy...")
        self.proxy_status_label.setStyleSheet("padding: 5px; color: orange; font-size: 10px;")
        
        try:
            import requests
            proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
            response = requests.get('http://httpbin.org/ip', proxies=proxies, timeout=10)
            
            if response.status_code == 200:
                self.proxy_status_label.setText(f"✅ Proxy working! IP: {response.json().get('origin', 'Unknown')}")
                self.proxy_status_label.setStyleSheet("padding: 5px; color: green; font-size: 10px;")
                QMessageBox.information(self, "Success", "Proxy is working correctly!")
            else:
                self.proxy_status_label.setText("❌ Proxy test failed")
                self.proxy_status_label.setStyleSheet("padding: 5px; color: red; font-size: 10px;")
                QMessageBox.warning(self, "Error", f"Proxy returned status code: {response.status_code}")
        
        except Exception as e:
            self.proxy_status_label.setText(f"❌ Proxy error: {str(e)[:30]}...")
            self.proxy_status_label.setStyleSheet("padding: 5px; color: red; font-size: 10px;")
            QMessageBox.critical(self, "Error", f"Proxy test failed:\n{str(e)}")
    
    def select_file(self):
        """Open file dialog to select CSV file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select CSV File",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            self.load_file(file_path)
    
    def load_file(self, file_path):
        """Load CSV file and display info"""
        try:
            self.accounts = CSVHandler.read_csv(file_path)
            self.current_file = file_path
            
            filename = os.path.basename(file_path)
            self.file_label.setText(f"✅ Loaded: {filename} ({len(self.accounts)} accounts)")
            self.file_label.setStyleSheet("padding: 10px; background-color: #d4edda; border-radius: 5px;")
            
            self.log_output.append(f"📂 Loaded file: {filename}")
            self.log_output.append(f"📊 Total accounts: {len(self.accounts)}\n")
            
            self.start_btn.setEnabled(True)
            self.reload_btn.setEnabled(True)
            
            self.update_account_status()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load CSV file:\n{str(e)}")
            self.log_output.append(f"❌ Error loading file: {str(e)}\n")
    
    def reload_file(self):
        """Reload the current file"""
        if self.current_file:
            self.load_file(self.current_file)
    
    def test_proxy(self):
        """Test if the proxy is working"""
        proxy_url = self.proxy_input.text().strip()
        
        if not proxy_url:
            QMessageBox.warning(self, "Warning", "Please enter a proxy URL first!")
            return
        
        self.proxy_test_btn.setEnabled(False)
        self.proxy_test_btn.setText("Testing...")
        self.proxy_status_label.setText("Testing proxy connection...")
        self.proxy_status_label.setStyleSheet("padding: 5px; color: #ff9800;")
        
        # Test proxy in a separate thread to avoid blocking UI
        import threading
        
        def test_connection():
            try:
                import requests
                proxies = {
                    'http': proxy_url,
                    'https': proxy_url
                }
                
                # Test with a simple request
                response = requests.get('https://httpbin.org/ip', proxies=proxies, timeout=10)
                
                if response.status_code == 200:
                    self.proxy_status_label.setText(f"✅ Proxy working! IP: {response.json().get('origin', 'N/A')}")
                    self.proxy_status_label.setStyleSheet("padding: 5px; color: #4CAF50;")
                    self.log_output.append(f"✅ Proxy test successful: {proxy_url}\n")
                else:
                    self.proxy_status_label.setText(f"❌ Proxy test failed (Status: {response.status_code})")
                    self.proxy_status_label.setStyleSheet("padding: 5px; color: #f44336;")
                    self.log_output.append(f"❌ Proxy test failed\n")
                    
            except Exception as e:
                self.proxy_status_label.setText(f"❌ Proxy error: {str(e)[:50]}")
                self.proxy_status_label.setStyleSheet("padding: 5px; color: #f44336;")
                self.log_output.append(f"❌ Proxy test error: {str(e)}\n")
            
            finally:
                self.proxy_test_btn.setEnabled(True)
                self.proxy_test_btn.setText("Test Proxy")
        
        thread = threading.Thread(target=test_connection)
        thread.daemon = True
        thread.start()
    
    def update_account_status(self):
        """Update account status display"""
        if not self.accounts:
            return
        
        total = len(self.accounts)
        
        # Get selected room
        selected_room = self.get_selected_room()
        if not selected_room:
            self.account_status_label.setText(f"Total accounts: {total} | Select a room to see status")
            self.timer_label.setText("")
            return
        
        # Filter ready accounts
        ready_accounts = TimerManager.filter_ready_accounts(self.accounts, selected_room)
        ready_count = len(ready_accounts)
        
        self.account_status_label.setText(
            f"Total accounts: {total} | Ready for Room {selected_room}: {ready_count}"
        )
        
        # Show timer info for accounts not ready
        not_ready = total - ready_count
        if not_ready > 0:
            # Get time until ready for first not-ready account
            for account in self.accounts:
                if account not in ready_accounts:
                    time_remaining = TimerManager.get_time_until_ready(account, selected_room)
                    time_str = TimerManager.format_time_remaining(time_remaining)
                    self.timer_label.setText(f"⏰ {not_ready} account(s) not ready | Next available: {time_str}")
                    break
        else:
            self.timer_label.setText("✅ All accounts are ready!")
    
    def get_selected_room(self):
        """Get selected room number"""
        if self.room1_checkbox.isChecked():
            return 1
        elif self.room2_checkbox.isChecked():
            return 2
        elif self.room3_checkbox.isChecked():
            return 3
        return None
    
    def start_processing(self):
        """Start processing accounts"""
        if not self.accounts:
            QMessageBox.warning(self, "Warning", "Please select a CSV file first!")
            return
        
        selected_room = self.get_selected_room()
        if not selected_room:
            QMessageBox.warning(self, "Warning", "Please select a room to process!")
            return
        
        # Filter ready accounts
        ready_accounts = TimerManager.filter_ready_accounts(self.accounts, selected_room)
        
        if not ready_accounts:
            QMessageBox.warning(
                self, 
                "Warning", 
                f"No accounts are ready for Room {selected_room}!\n\n"
                "Please wait for the 24-hour cooldown to expire."
            )
            return
        
        # Confirm
        register_first = (selected_room == 1)
        action = "Register and play" if register_first else "Play"
        
        result = QMessageBox.question(
            self,
            "Confirm",
            f"{action} Room {selected_room} for {len(ready_accounts)} account(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if result != QMessageBox.StandardButton.Yes:
            return
        
        # Disable controls
        self.start_btn.setEnabled(False)
        self.select_file_btn.setEnabled(False)
        self.reload_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.room1_checkbox.setEnabled(False)
        self.room2_checkbox.setEnabled(False)
        self.room3_checkbox.setEnabled(False)
        self.proxy_input.setEnabled(False)
        self.proxy_test_btn.setEnabled(False)
        self.thread_spinner.setEnabled(False)
        
        # Clear log
        self.log_output.clear()
        self.log_output.append(f"🚀 Starting processing for Room {selected_room}...\n")
        
        # Get configuration
        proxy_url = self.proxy_input.text().strip()
        num_threads = self.thread_spinner.value()
        
        if proxy_url:
            self.log_output.append(f"🔄 Using proxy: {proxy_url}\n")
        else:
            self.log_output.append(f"ℹ️ No proxy configured (direct connection)\n")
        
        self.log_output.append(f"⚡ Using {num_threads} thread(s) for processing\n")
        
        # Reset processed accounts list
        self.processed_accounts = []
        
        # Start processing thread
        self.process_thread = ProcessThread(
            ready_accounts, 
            selected_room, 
            register_first, 
            proxy_url,
            num_threads
        )
        self.process_thread.progress.connect(self.update_progress)
        self.process_thread.status.connect(self.update_status)
        self.process_thread.account_processed.connect(self.save_account_incrementally)
        self.process_thread.finished.connect(self.processing_finished)
        self.process_thread.start()
    
    def stop_processing(self):
        """Stop processing"""
        if self.process_thread:
            self.process_thread.stop()
            self.log_output.append("\n⏹️ Stopping process...\n")
    
    def update_progress(self, current, total):
        """Update progress bar"""
        progress = int((current / total) * 100)
        self.progress_bar.setValue(progress)
    
    def update_status(self, message):
        """Update status log"""
        self.log_output.append(message)
        self.log_output.verticalScrollBar().setValue(
            self.log_output.verticalScrollBar().maximum()
        )
    
    def save_account_incrementally(self, account):
        """Save account data incrementally"""
        self.processed_accounts.append(account)
        
        # Determine room number from account status
        room_number = None
        if account.get('room3_status') == 'true':
            room_number = 3
        elif account.get('room2_status') == 'true':
            room_number = 2
        elif account.get('room1_status') == 'true':
            room_number = 1
        
        if room_number:
            output_file = CSVHandler.get_output_filename(room_number)
            try:
                CSVHandler.write_csv(output_file, self.processed_accounts)
                self.log_output.append(f"💾 Saved progress to {output_file}")
            except Exception as e:
                self.log_output.append(f"❌ Error saving: {str(e)}")
    
    def processing_finished(self, success):
        """Handle processing completion"""
        # Re-enable controls
        self.start_btn.setEnabled(True)
        self.select_file_btn.setEnabled(True)
        self.reload_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.room1_checkbox.setEnabled(True)
        self.room2_checkbox.setEnabled(True)
        self.room3_checkbox.setEnabled(True)
        self.proxy_input.setEnabled(True)
        self.proxy_test_btn.setEnabled(True)
        self.thread_spinner.setEnabled(True)
        
        if success and self.processed_accounts:
            selected_room = self.get_selected_room()
            output_file = CSVHandler.get_output_filename(selected_room)
            
            self.log_output.append(f"\n✅ Processing completed!")
            self.log_output.append(f"💾 Final output saved to: {output_file}\n")
            
            QMessageBox.information(
                self,
                "Success",
                f"Processing completed!\n\n"
                f"Processed: {len(self.processed_accounts)} accounts\n"
                f"Output saved to: {output_file}"
            )
        
        # Reload file to get updated status
        if self.current_file:
            self.reload_file()
        
        self.progress_bar.setValue(0)


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
