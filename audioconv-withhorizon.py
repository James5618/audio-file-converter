import os
import sys
import traceback
import shutil

# Set ffmpeg path - cross-platform support
if sys.platform == 'win32':
    # Windows: Use local ffmpeg if available
    ffmpeg_dir = os.path.join(os.path.dirname(__file__), 'ffmpeg', 'ffmpeg-8.0.1-essentials_build', 'bin')
    if os.path.exists(ffmpeg_dir):
        os.environ['PATH'] = ffmpeg_dir + os.pathsep + os.environ.get('PATH', '')
elif sys.platform == 'darwin':
    # macOS: Check for Homebrew installation
    homebrew_paths = ['/opt/homebrew/bin', '/usr/local/bin']
    for path in homebrew_paths:
        if os.path.exists(os.path.join(path, 'ffmpeg')):
            os.environ['PATH'] = path + os.pathsep + os.environ.get('PATH', '')
            break
    else:
        # If ffmpeg not found, check if it's already in PATH
        if not shutil.which('ffmpeg'):
            print("Warning: ffmpeg not found. Install with: brew install ffmpeg")
else:
    # Linux: Check common installation paths
    if not shutil.which('ffmpeg'):
        print("Warning: ffmpeg not found. Install with:")
        print("  Ubuntu/Debian: sudo apt install ffmpeg")
        print("  Fedora: sudo dnf install ffmpeg")
        print("  Arch Linux: sudo pacman -S ffmpeg")

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

class CueSplitterThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(list)

    def __init__(self, cue_file, audio_file, output_folder):
        super().__init__()
        self.cue_file = cue_file
        self.audio_file = audio_file
        self.output_folder = output_folder
        self.failed_files = []

    def parse_cue(self):
        tracks = []
        current_track = {}
        
        try:
            with open(self.cue_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            with open(self.cue_file, 'r', encoding='latin-1') as f:
                lines = f.readlines()
        
        for line in lines:
            line = line.strip()
            if line.startswith('TRACK'):
                if current_track:
                    tracks.append(current_track)
                parts = line.split()
                current_track = {'number': int(parts[1])}
            elif line.startswith('TITLE'):
                title = line.split('TITLE', 1)[1].strip().strip('"')
                if 'number' in current_track:
                    current_track['title'] = title
            elif line.startswith('PERFORMER'):
                performer = line.split('PERFORMER', 1)[1].strip().strip('"')
                if 'number' in current_track:
                    current_track['performer'] = performer
            elif line.startswith('INDEX 01'):
                time_str = line.split('INDEX 01', 1)[1].strip()
                parts = time_str.split(':')
                minutes = int(parts[0])
                seconds = int(parts[1])
                frames = int(parts[2])
                total_ms = (minutes * 60 + seconds) * 1000 + (frames * 1000 // 75)
                current_track['start'] = total_ms
        
        if current_track:
            tracks.append(current_track)
        
        return tracks

    def run(self):
        try:
            # Normalize paths for OneDrive/SharePoint
            self.cue_file = os.path.normpath(self.cue_file)
            self.audio_file = os.path.normpath(self.audio_file)
            self.output_folder = os.path.normpath(self.output_folder)
            
            # Verify files exist
            if not os.path.exists(self.cue_file):
                raise FileNotFoundError(f"Cue file not found: {self.cue_file}")
            if not os.path.exists(self.audio_file):
                raise FileNotFoundError(f"Audio file not found: {self.audio_file}")
            if not os.path.exists(self.output_folder):
                os.makedirs(self.output_folder, exist_ok=True)
            
            tracks = self.parse_cue()
            audio = AudioSegment.from_file(self.audio_file)
            total_tracks = len(tracks)

            for i, track in enumerate(tracks):
                try:
                    start_time = track['start']
                    end_time = tracks[i + 1]['start'] if i + 1 < len(tracks) else len(audio)
                    
                    track_audio = audio[start_time:end_time]
                    
                    track_num = str(track['number']).zfill(2)
                    title = track.get('title', f'Track {track_num}')
                    # Sanitize filename
                    title = ''.join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
                    filename = f"{track_num} - {title}.flac"
                    output_path = os.path.join(self.output_folder, filename)
                    
                    track_audio.export(output_path, format='flac')
                    
                except Exception as e:
                    self.failed_files.append(f"Track {track.get('number', 'unknown')}: {str(e)}")
                    with open('cue_split_errors.log', 'a') as log_file:
                        log_file.write(f"Track {track.get('number', 'unknown')} - {str(e)}\n")
                        log_file.write(traceback.format_exc() + "\n")
                
                self.progress.emit(int((i + 1) / total_tracks * 100))
        
        except Exception as e:
            self.failed_files.append(f"General error: {str(e)}")
            with open('cue_split_errors.log', 'a') as log_file:
                log_file.write(f"General error - {str(e)}\n")
                log_file.write(traceback.format_exc() + "\n")
        
        self.finished.emit(self.failed_files)

class ConverterApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Music Converter')
        self.setGeometry(100, 100, 400, 450)

        layout = QVBoxLayout()

        self.label = QLabel('Select a folder containing .m4a, .flac, and .wv files to convert:')
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
        self.wv_checkbox = QCheckBox('.wv')
        self.wv_checkbox.setChecked(True)
        self.file_type_layout.addWidget(self.wv_checkbox)
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

        self.cue_split_button = QPushButton('Split Audio with Cue Sheet')
        self.cue_split_button.clicked.connect(self.split_with_cue)
        layout.addWidget(self.cue_split_button)

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

    def split_with_cue(self):
        cue_file, _ = QFileDialog.getOpenFileName(self, 'Select Cue File', '', 'Cue Files (*.cue)')
        if cue_file:
            audio_file, _ = QFileDialog.getOpenFileName(
                self, 'Select Audio File', 
                os.path.dirname(cue_file),
                'Audio Files (*.flac *.wv)'
            )
            if audio_file:
                output_folder = QFileDialog.getExistingDirectory(self, 'Select Output Folder')
                if output_folder:
                    self.thread = CueSplitterThread(cue_file, audio_file, output_folder)
                    self.thread.progress.connect(self.update_progress)
                    self.thread.finished.connect(self.cue_split_finished)
                    self.thread.start()

    def convert_files(self):
        if hasattr(self, 'folder'):
            overwrite = self.overwrite_checkbox.isChecked()
            file_types = []
            if self.m4a_checkbox.isChecked():
                file_types.append('.m4a')
            if self.flac_checkbox.isChecked():
                file_types.append('.flac')
            if self.wv_checkbox.isChecked():
                file_types.append('.wv')
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

    def cue_split_finished(self, failed_files):
        self.label.setText('Cue Split Finished!')
        self.progress.setValue(100)
        if failed_files:
            self.failed_files_text.setPlainText('\n'.join(failed_files))
        else:
            self.failed_files_text.setPlainText('All tracks split successfully.')

if __name__ == '__main__':
    app = QApplication([])
    converter = ConverterApp()
    converter.show()
    app.exec()

