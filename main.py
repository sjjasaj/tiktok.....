import sys
import asyncio
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QPlainTextEdit, QComboBox, QGroupBox, QMessageBox, QSplitter, QCheckBox
)

APP_NAME = "TikTok Gift Controller"

class Bridge(QObject):
    log = Signal(str)
    gift = Signal(str, str, int)
    status = Signal(str)

class TikTokWorker(threading.Thread):
    def __init__(self, username, bridge):
        super().__init__(daemon=True)
        self.username = username.lstrip("@").strip()
        self.bridge = bridge
        self.stop_event = threading.Event()
        self.client = None

    def stop(self):
        self.stop_event.set()
        try:
            if self.client:
                self.client.stop()
        except Exception:
            pass

    def run(self):
        try:
            from TikTokLive import TikTokLiveClient
            from TikTokLive.events import ConnectEvent, DisconnectEvent, GiftEvent
            self.client = TikTokLiveClient(unique_id=self.username)

            @self.client.on(ConnectEvent)
            async def on_connect(event):
                self.bridge.status.emit("Conectado al LIVE")
                self.bridge.log.emit(f"Conexión establecida con @{self.username}")

            @self.client.on(DisconnectEvent)
            async def on_disconnect(event):
                self.bridge.status.emit("Desconectado")
                self.bridge.log.emit("TikTok LIVE desconectado.")

            @self.client.on(GiftEvent)
            async def on_gift(event):
                try:
                    gift_name = getattr(getattr(event, "gift", None), "name", None) or "Regalo"
                    user = getattr(getattr(event, "user", None), "unique_id", None) or "usuario"
                    count = int(getattr(event, "repeat_count", 1) or 1)
                    # TikTok gift streaks may send interim events; only trigger at streak end.
                    repeat_end = getattr(event, "repeat_end", 1)
                    if repeat_end == 0:
                        return
                    self.bridge.gift.emit(str(gift_name), str(user), count)
                except Exception as exc:
                    self.bridge.log.emit(f"No se pudo interpretar un evento de regalo: {exc}")

            self.bridge.status.emit("Conectando…")
            self.bridge.log.emit(f"Intentando conectar con @{self.username}. La integración no es oficial.")
            asyncio.run(self.client.start())
        except Exception as exc:
            self.bridge.status.emit("Error de conexión")
            self.bridge.log.emit(f"Error: {type(exc).__name__}: {exc}")
            self.bridge.log.emit("Comprueba que el usuario esté en LIVE y que TikTokLive sea compatible con TikTok.")
        finally:
            self.bridge.status.emit("Desconectado")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1040, 720)
        self.bridge = Bridge()
        self.bridge.log.connect(self.add_log)
        self.bridge.gift.connect(self.on_gift)
        self.bridge.status.connect(self.set_status)
        self.worker = None
        self.rules = {}
        self._build_ui()
        self.add_log("Listo. Usa 'Probar regalo' para verificar las reglas sin estar en directo.")

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("TIKTOK GIFT CONTROLLER")
        title.setStyleSheet("font-size: 22px; font-weight: 800; color: #d7c7ff;")
        self.status = QLabel("Desconectado")
        self.status.setStyleSheet("color:#ffcc70; font-weight:700;")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.status)
        layout.addLayout(header)

        connect_box = QGroupBox("Conexión a TikTok LIVE")
        conn = QHBoxLayout(connect_box)
        self.username = QLineEdit()
        self.username.setPlaceholderText("Tu usuario de TikTok (sin contraseña)")
        self.connect_btn = QPushButton("Conectar LIVE")
        self.disconnect_btn = QPushButton("Desconectar")
        self.disconnect_btn.setEnabled(False)
        self.connect_btn.clicked.connect(self.connect_live)
        self.disconnect_btn.clicked.connect(self.disconnect_live)
        conn.addWidget(QLabel("@"))
        conn.addWidget(self.username, 1)
        conn.addWidget(self.connect_btn)
        conn.addWidget(self.disconnect_btn)
        layout.addWidget(connect_box)

        splitter = QSplitter(Qt.Vertical)
        top = QWidget()
        top_layout = QHBoxLayout(top)
        rules_box = QGroupBox("Reglas de regalos")
        rules_layout = QVBoxLayout(rules_box)
        form = QHBoxLayout()
        self.gift_name = QLineEdit()
        self.gift_name.setPlaceholderText("Nombre exacto del regalo")
        self.action = QComboBox()
        self.action.addItems(["Notificación en app", "Sonido WAV"])
        form.addWidget(self.gift_name, 2)
        form.addWidget(self.action, 1)
        rules_layout.addLayout(form)
        rule_buttons = QHBoxLayout()
        add_rule = QPushButton("Guardar regla")
        remove_rule = QPushButton("Eliminar regla seleccionada")
        add_rule.clicked.connect(self.add_rule)
        remove_rule.clicked.connect(self.remove_rule)
        rule_buttons.addWidget(add_rule)
        rule_buttons.addWidget(remove_rule)
        rules_layout.addLayout(rule_buttons)
        self.rule_table = QTableWidget(0, 2)
        self.rule_table.setHorizontalHeaderLabels(["Regalo", "Acción"])
        self.rule_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        rules_layout.addWidget(self.rule_table)
        top_layout.addWidget(rules_box, 3)

        gifts_box = QGroupBox("Regalos detectados")
        gifts_layout = QVBoxLayout(gifts_box)
        self.gift_table = QTableWidget(0, 3)
        self.gift_table.setHorizontalHeaderLabels(["Regalo", "Usuario", "Cantidad"])
        self.gift_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        gifts_layout.addWidget(self.gift_table)
        self.test_btn = QPushButton("Probar regalo")
        self.test_btn.clicked.connect(self.test_gift)
        gifts_layout.addWidget(self.test_btn)
        top_layout.addWidget(gifts_box, 4)
        splitter.addWidget(top)

        logs_box = QGroupBox("Registro")
        logs_layout = QVBoxLayout(logs_box)
        self.logs = QPlainTextEdit()
        self.logs.setReadOnly(True)
        logs_layout.addWidget(self.logs)
        splitter.addWidget(logs_box)
        splitter.setSizes([430, 200])
        layout.addWidget(splitter, 1)

        footer = QLabel("Prototipo comunitario · No pide contraseña · Las acciones externas requieren configuración adicional")
        footer.setStyleSheet("color:#9292a8;")
        layout.addWidget(footer)

        self.setStyleSheet("""
            QMainWindow, QWidget { background:#15141d; color:#f1eff8; font-size:13px; }
            QGroupBox { border:1px solid #454052; border-radius:8px; margin-top:10px; padding:10px; font-weight:700; }
            QGroupBox::title { subcontrol-origin:margin; left:12px; padding:0 5px; color:#c6b2ff; }
            QLineEdit, QComboBox, QPlainTextEdit, QTableWidget { background:#201e2a; border:1px solid #494457; border-radius:5px; padding:6px; selection-background-color:#6744a8; }
            QPushButton { background:#6844a8; border:0; border-radius:6px; padding:8px 12px; font-weight:700; }
            QPushButton:hover { background:#8059c5; }
            QPushButton:disabled { background:#383442; color:#888; }
            QHeaderView::section { background:#292635; padding:6px; border:0; }
        """)

    def add_log(self, message):
        self.logs.appendPlainText(time.strftime("[%H:%M:%S] ") + message)

    def set_status(self, value):
        self.status.setText(value)
        connected = value in ("Conectado al LIVE", "Conectando…")
        self.connect_btn.setEnabled(not connected)
        self.disconnect_btn.setEnabled(connected)

    def connect_live(self):
        username = self.username.text().strip()
        if not username:
            QMessageBox.information(self, "Falta el usuario", "Escribe tu usuario de TikTok.")
            return
        if self.worker and self.worker.is_alive():
            QMessageBox.information(self, "Conexión activa", "Desconecta primero la sesión actual.")
            return
        self.worker = TikTokWorker(username, self.bridge)
        self.worker.start()

    def disconnect_live(self):
        if self.worker:
            self.worker.stop()
        self.set_status("Desconectado")
        self.add_log("Solicitud de desconexión enviada.")

    def add_rule(self):
        name = self.gift_name.text().strip()
        if not name:
            QMessageBox.information(self, "Falta el regalo", "Escribe el nombre del regalo.")
            return
        action = self.action.currentText()
        self.rules[name.casefold()] = (name, action)
        self.refresh_rules()
        self.add_log(f"Regla guardada: {name} → {action}")
        self.gift_name.clear()

    def refresh_rules(self):
        self.rule_table.setRowCount(0)
        for name, action in self.rules.values():
            row = self.rule_table.rowCount()
            self.rule_table.insertRow(row)
            self.rule_table.setItem(row, 0, QTableWidgetItem(name))
            self.rule_table.setItem(row, 1, QTableWidgetItem(action))

    def remove_rule(self):
        row = self.rule_table.currentRow()
        if row < 0:
            return
        item = self.rule_table.item(row, 0)
        if item:
            self.rules.pop(item.text().casefold(), None)
        self.refresh_rules()

    def test_gift(self):
        name = self.gift_name.text().strip()
        if not name and self.rule_table.rowCount():
            name = self.rule_table.item(0, 0).text()
        if not name:
            name = "Rosa"
        self.on_gift(name, "prueba_local", 1)

    def on_gift(self, name, user, count):
        row = self.gift_table.rowCount()
        self.gift_table.insertRow(row)
        for col, value in enumerate((name, user, str(count))):
            self.gift_table.setItem(row, col, QTableWidgetItem(value))
        self.add_log(f"Regalo: {name} ×{count} de @{user}")
        rule = self.rules.get(name.casefold())
        if not rule:
            return
        _, action = rule
        if action == "Notificación en app":
            QMessageBox.information(self, "Regalo recibido", f"@{user} envió {name} ×{count}")
        elif action == "Sonido WAV":
            self.play_sound()

    def play_sound(self):
        # Built-in Windows sound fallback; avoids requiring extra audio libraries.
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
            self.add_log("Acción ejecutada: sonido de Windows.")
        except Exception:
            self.add_log("No se pudo reproducir el sonido en este sistema.")

    def closeEvent(self, event):
        if self.worker:
            self.worker.stop()
        event.accept()

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
