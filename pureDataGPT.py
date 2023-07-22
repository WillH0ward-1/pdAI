import sys
import os
import requests
import subprocess
import shlex
import json
import random
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QLineEdit, QPlainTextEdit, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QSlider, QFileDialog, QCheckBox, QStyle, QMessageBox, QDialog
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.fernet import Fernet
from getpass import getpass
import base64
from PyQt5.QtWidgets import QInputDialog
from PyQt5.QtWidgets import QProgressBar
from PyQt5.QtCore import QTimer
from PyQt5.QtCore import QThread

def get_pd_path():
    try:
        result = subprocess.run(shlex.split("which pd"), stdout=subprocess.PIPE)
        return result.stdout.decode().strip()
    except:
        return None

pd_path = get_pd_path()
if pd_path:
    print(f"PureData executable found at: {pd_path}")
else:
    print("PureData executable not found")

def generate_pd_code(prompt, api_key, temperature):
    model_engine = "gpt-3.5-turbo"
    api_endpoint = f"https://api.openai.com/v1/chat/completions"  # Change the endpoint here
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "You are a knowledgeable professor of audio technology that can generate complete PureData code."},
            {"role": "user", "content": f"Represent the following as PureData code: {prompt}"},
            {"role": "user", "content": f"Follow conventions outlined here:\n\nhttps://puredata.info/docs/manuals/pd/\nhttps://puredata.info/docs/ListOfPdExternals/"},
            {"role": "user", "content": "Return only .pd code, no other text or information unrelated to the patch"},
        ],
        "max_tokens": 1024,
        "temperature": temperature,
        "n": 1,
    }


    response = requests.post(api_endpoint, headers=headers, json=data)

    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"], None
    else:
        return None, f"Error generating Pure Data code: {response.status_code} - {response.text}"

def generate_start(prompt, api_key, temperature, random_word, save_path=os.path.join(os.path.expanduser("~"), "Documents", "PureDataGPTpatches")):
    if api_key == "":
        QMessageBox.critical(None, "Error", "API key is required")
        return
    if random_word:
        prompt += f" {get_random_term()}"
    generated_text, error_message = generate_pd_code(prompt, api_key, temperature)
    if error_message:
        QMessageBox.warning(None, "Error", error_message)
        return

    # Remove any trailing whitespace
    generated_text = generated_text.rstrip()

    # Create a folder for the .pd files if it doesn't exist
    os.makedirs(save_path, exist_ok=True)

    # Create the .pd file in the chosen path
    pd_file_path = os.path.join(save_path, "GeneratedPureData.pd")

    # Write the generated code to the .pd file
    with open(pd_file_path, "w") as pd_file:
        pd_file.write(generated_text)

    # Open the .pd file with the Pure Data application
    if pd_path is not None:
        subprocess.Popen([pd_path, pd_file_path])
    else:
        QMessageBox.critical(None, "Error", "Pure Data executable not found")

class GeneratePDThread(QThread):
    def __init__(self, prompt, api_key, temperature, save_path):
        super().__init__()
        self.prompt = prompt
        self.api_key = api_key
        self.temperature = temperature
        self.save_path = save_path

    def run(self):
        generate_start(self.prompt, self.api_key, self.temperature, self.save_path)


class PureDataCodeGenerator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.save_path = os.path.join(os.path.expanduser("~"), "Documents", "PureDataGPTpatches")
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("pureDataGPT")

        font = QFont()
        font.setPointSize(14)

        self.prompt_label = QLabel("PureData Prompt:")
        self.prompt_label.setFont(font)
        self.prompt_entry = QPlainTextEdit("120bpm metronome, 440hz sine")
        self.prompt_entry.setFont(font)
        self.prompt_entry.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        
        self.settings_button = QPushButton("Settings")
        self.settings_button.setFont(font)
        self.settings_button.clicked.connect(self.open_settings)
        self.settings_button.setToolTip("Click to access settings, including API key configuration")

        self.temperature_label = QLabel(f"Temperature: {0.5:.2f}")
        self.temperature_label.setFont(font)
        self.temperature_slider = QSlider(Qt.Horizontal)
        self.temperature_slider.setRange(0, 100)
        self.temperature_slider.setValue(50)
        self.temperature_slider.setTickInterval(1)
        self.temperature_slider.valueChanged.connect(self.update_temperature)
        self.temperature_slider.setToolTip("Temperature controls the determinism of the GPT. Higher value = creative results. Lower value produces more focused output. There is a tradeoff between creativity and focus.")

        self.generate_button = QPushButton("Generate")
        self.generate_button.setFont(font)
        self.generate_button.clicked.connect(self.generate_pd)
        self.generate_button.setToolTip("Click to generate a Pure Data patch based on the entered prompt")

        self.random_term_button = QPushButton("Generate Random Word")
        self.random_term_button.setFont(font)
        self.random_term_button.clicked.connect(self.add_random_term)
        self.random_term_button.setToolTip("Add a random word to the current prompt")

        self.api_key_entry = QLineEdit()
        self.save_path_entry = QLineEdit()

        vbox = QVBoxLayout()

        vbox.addWidget(self.prompt_label)
        vbox.addWidget(self.prompt_entry)
        vbox.addWidget(self.temperature_label)
        vbox.addWidget(self.temperature_slider)

        hbox = QHBoxLayout()  # Create a new horizontal layout for Generate and Settings buttons
        hbox.addWidget(self.generate_button)
        hbox.addWidget(self.random_term_button)
        hbox.addWidget(self.settings_button)
        vbox.addLayout(hbox)

        widget = QWidget()
        widget.setLayout(vbox)
        self.setCentralWidget(widget)
        
        self.setFixedSize(600, 250)

        self.load_api_key()


    def reveal_api_key(self, api_key_entry):
        current_echo_mode = api_key_entry.echoMode()
        if current_echo_mode == QLineEdit.Password:
            api_key_entry.setEchoMode(QLineEdit.Normal)
            self.sender().setText("Hide Key")
        else:
            api_key_entry.setEchoMode(QLineEdit.Password)
            self.sender().setText("Reveal Key")

    def open_settings(self):
        settings_dialog = QDialog(self)
        settings_dialog.setWindowTitle("Settings")
        vbox = QVBoxLayout()

        font = QFont()
        font.setPointSize(14)

        api_key_label = QLabel("API Key:")
        api_key_label.setFont(font)
        api_key_entry = QLineEdit(self.api_key_entry.text())
        api_key_entry.setEchoMode(QLineEdit.Password)
        api_key_entry.setFont(font)

        save_api_key_button = QPushButton("Save API Key")
        save_api_key_button.setFont(font)
        save_api_key_button.clicked.connect(lambda: self.save_api_key(api_key_entry.text()))

        # Add the Reveal Key button
        reveal_key_button = QPushButton("Reveal Key")
        reveal_key_button.setFont(font)
        reveal_key_button.clicked.connect(lambda: self.reveal_api_key(api_key_entry))

        save_path_label = QLabel("Save Path:")
        save_path_label.setFont(font)
        save_path_entry = QLineEdit(self.save_path_entry.text() or self.save_path)
        save_path_entry.setFont(font)

        browse_button = QPushButton("Browse")
        browse_button.setFont(font)
        browse_button.clicked.connect(lambda: self.browse_folder(save_path_entry))

        vbox.addWidget(api_key_label)
        vbox.addWidget(api_key_entry)
        vbox.addWidget(save_api_key_button)
        vbox.addWidget(reveal_key_button)
        vbox.addWidget(save_path_label)
        vbox.addWidget(save_path_entry)
        vbox.addWidget(browse_button)

        settings_dialog.setLayout(vbox)
        settings_dialog.exec_()


    
    def update_temperature(self, value):
        temperature = value / 100
        self.temperature_label.setText(f"Temperature: {temperature:.2f}")

    def browse_folder(self, save_path_entry):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Save Path")
        if folder_path:
            save_path_entry.setText(folder_path)

    def add_random_term(self):
        random_terms = [get_random_term() for _ in range(5)]
        formatted_terms = ", ".join(random_terms)
        self.prompt_entry.setText(f"{self.prompt_entry.text()} {formatted_terms}")


    def generate_pd(self):
        self.loading_dialog = QDialog(self)
        self.loading_dialog.setWindowTitle("Generating Patch...")

        vbox = QVBoxLayout()

        self.loading_message = QLabel()
        vbox.addWidget(self.loading_message)

        self.loading_progress = QProgressBar()
        self.loading_progress.setRange(0, 0)
        vbox.addWidget(self.loading_progress)

        self.loading_dialog.setLayout(vbox)

        self.update_witty_message()
        self.loading_dialog.show()

        prompt = self.prompt_entry.text()
        api_key = self.api_key_entry.text()
        temperature = self.temperature_slider.value() / 100
        save_path = self.save_path_entry.text() or self.save_path

        self.generate_pd_thread = GeneratePDThread(prompt, api_key, temperature, save_path)
        self.generate_pd_thread.finished.connect(self.loading_dialog.close)
        self.generate_pd_thread.start()

    def update_witty_message(self):
        self.loading_message.setText(generate_witty_message())
        QTimer.singleShot(random.randint(3000, 5000), self.update_witty_message)

    def generate_pd_worker(self):
        prompt = self.prompt_entry.text()
        api_key = self.api_key_entry.text()
        temperature = self.temperature_slider.value() / 100
        save_path = self.save_path_entry.text() or self.save_path

        generate_start(prompt, api_key, temperature, save_path)
        self.loading_dialog.close()

    def save_api_key(self, api_key):
        self.api_key_entry.setText(api_key)

        password, ok = QInputDialog.getText(self, "Password", "Enter a password to protect your API key:", QLineEdit.Password)
        if not ok:
            return
        password = password.encode()

        salt = os.urandom(16)
        key = self.generate_key_from_password(password, salt)
        encrypted_api_key = self.encrypt_data(api_key.encode(), key)

        with open("api_key.txt", "wb") as api_key_file:
            api_key_file.write(salt + encrypted_api_key)

        QMessageBox.information(self, "Success", "API key saved and encrypted!")

    def load_api_key(self):
        try:
            with open("api_key.txt", "rb") as api_key_file:
                data = api_key_file.read()
                salt = data[:16]
                encrypted_api_key = data[16:]

            password, ok = QInputDialog.getText(self, "Password", "Enter your password to decrypt the API key:", QLineEdit.Password)
            if not ok:
                return
            password = password.encode()

            key = self.generate_key_from_password(password, salt)
            api_key = self.decrypt_data(encrypted_api_key, key).decode()
            self.api_key_entry.setText(api_key)
        except FileNotFoundError:
            print("API key file not found.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to decrypt the API key: {str(e)}")
    
    def generate_key_from_password(self, password, salt):
        kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1)
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return key

    def encrypt_data(self, data, key):
        fernet = Fernet(key)
        return fernet.encrypt(data)

    def decrypt_data(self, encrypted_data, key):
        fernet = Fernet(key)
        return fernet.decrypt(encrypted_data)


with open("randomPrompts.json", "r") as f:
    terms_json = json.load(f)

terms = terms_json["randomPrompts"]

def get_random_term():
    return random.choice(terms)

def load_witty_messages_from_json():
    with open("witty_loading_phases.json", "r") as file:
        data = json.load(file)
        return data["witty_messages"]

def generate_witty_message():
    witty_messages = load_witty_messages_from_json()
    return random.choice(witty_messages)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PureDataCodeGenerator()
    window.show()
    sys.exit(app.exec_())