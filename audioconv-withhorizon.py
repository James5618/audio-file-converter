import os
import traceback
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog,
    QProgressBar, QLabel, QCheckBox, QHBoxLayout, QComboBox, QTextEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from pydub import AudioSegment

class ConverterThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(list)

    def __init__(self, folder, overwrite, file_types, destination_folder, bitrate, sample_rate, gamma_horizon):
        super().__init__()
        self.folder = folder
        self.overwrite = overwrite
        self.file_types = file_types
        self.destination_folder = destination_folder
        self.bitrate = bitrate
        self.sample_rate = sample_rate
        self.gamma_horizon = gamma_horizon
        self.failed_files = []

    def run(self):
        files = []
        for root, _, filenames in os.walk(self.folder):
            for filename in filenames:
                if any(filename.endswith(ext) for ext in self.file_types):
                    files.append(os.path.join(root, filename))

        total_files = len(files)

        for i, file_path in enumerate(files):
            try:
                if self.overwrite:
                    output_path = file_path
                else:
                    relative_path = os.path.relpath(file_path, self.folder)
                    output_path = os.path.join(self.destination_folder, relative_path)
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    output_path = os.path.splitext(output_path)[0] + ('.wav' if self.gamma_horizon else '.mp3')

                if self.overwrite or not os.path.exists(output_path):
                    audio = AudioSegment.from_file(file_path)
                    if self.gamma_horizon:
                        audio = audio.set_frame_rate(8000).set_channels(1).set_sample_width(1)
                        audio.export(output_path, format='wav', codec='pcm_ulaw')
                    else:
                        audio = audio.set_frame_rate(self.sample_rate).set_channels(2).set_sample_width(2)
                        audio.export(output_path, format='mp3', bitrate=self.bitrate)
            except Exception as e:
                self.failed_files.append(file_path)
                with open('conversion_errors.log', 'a') as log_file:
                    log_file.write(f"{file_path} - {str(e)}\n")
                    log_file.write(traceback.format_exc() + "\n")
            self.progress.emit(int((i + 1) / total_files * 100))

        self.finished.emit(self.failed_files)

class ConverterApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Music Converter')
        self.setGeometry(100, 100, 400, 450)

        layout = QVBoxLayout()

        self.label = QLabel('Select a folder containing .m4a and .flac files to convert:')
        layout.addWidget(self.label)

        self.button = QPushButton('Select Folder')
        self.button.clicked.connect(self.select_folder)
        layout.addWidget(self.button)

        self.file_type_layout = QHBoxLayout()
        self.m4a_checkbox = QCheckBox('.m4a')
        self.m4a_checkbox.setChecked(True)
        self.file_type_layout.addWidget(self.m4a_checkbox)
        self.flac_checkbox = QCheckBox('.flac')
        self.flac_checkbox.setChecked(True)
        self.file_type_layout.addWidget(self.flac_checkbox)
        layout.addLayout(self.file_type_layout)

        self.overwrite_checkbox = QCheckBox('Overwrite original files')
        layout.addWidget(self.overwrite_checkbox)

        self.destination_button = QPushButton('Select Destination Folder')
        self.destination_button.clicked.connect(self.select_destination_folder)
        layout.addWidget(self.destination_button)

        self.bitrate_label = QLabel('Select Bitrate:')
        layout.addWidget(self.bitrate_label)
        self.bitrate_combo = QComboBox()
        self.bitrate_combo.addItems(['128k', '192k', '320k'])
        layout.addWidget(self.bitrate_combo)

        self.sample_rate_label = QLabel('Select Sample Rate:')
        layout.addWidget(self.sample_rate_label)
        self.sample_rate_combo = QComboBox()
        self.sample_rate_combo.addItems(['22050', '44100', '48000'])
        layout.addWidget(self.sample_rate_combo)

        self.gamma_horizon_checkbox = QCheckBox('Convert to Gamma Horizon Specifications')
        layout.addWidget(self.gamma_horizon_checkbox)

        self.convert_button = QPushButton('Convert')
        self.convert_button.clicked.connect(self.convert_files)
        layout.addWidget(self.convert_button)

        self.progress = QProgressBar()
        self.progress.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.progress)

        self.failed_files_label = QLabel('Failed Files:')
        layout.addWidget(self.failed_files_label)
        self.failed_files_text = QTextEdit()
        self.failed_files_text.setReadOnly(True)
        layout.addWidget(self.failed_files_text)

        self.setLayout(layout)

    def select_folder(self):
        self.folder = QFileDialog.getExistingDirectory(self, 'Select Folder')
        if self.folder:
            self.label.setText(f'Selected Folder: {self.folder}')

    def select_destination_folder(self):
        self.destination_folder = QFileDialog.getExistingDirectory(self, 'Select Destination Folder')
        if self.destination_folder:
            self.label.setText(f'Selected Destination Folder: {self.destination_folder}')

    def convert_files(self):
        if hasattr(self, 'folder'):
            overwrite = self.overwrite_checkbox.isChecked()
            file_types = []
            if self.m4a_checkbox.isChecked():
                file_types.append('.m4a')
            if self.flac_checkbox.isChecked():
                file_types.append('.flac')
            bitrate = self.bitrate_combo.currentText()
            sample_rate = int(self.sample_rate_combo.currentText())
            gamma_horizon = self.gamma_horizon_checkbox.isChecked()
            self.thread = ConverterThread(
                self.folder, overwrite, file_types,
                getattr(self, 'destination_folder', None),
                bitrate, sample_rate, gamma_horizon
            )
            self.thread.progress.connect(self.update_progress)
            self.thread.finished.connect(self.conversion_finished)
            self.thread.start()

    def update_progress(self, value):
        self.progress.setValue(value)

    def conversion_finished(self, failed_files):
        self.label.setText('Conversion Finished!')
        self.progress.setValue(100)
        if failed_files:
            self.failed_files_text.setPlainText('\n'.join(failed_files))
        else:
            self.failed_files_text.setPlainText('No files failed.')

if __name__ == '__main__':
    app = QApplication([])
    converter = ConverterApp()
    converter.show()
    app.exec()

