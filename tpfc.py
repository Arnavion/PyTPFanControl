#!/usr/bin/python3

import bisect
import operator
import sys
from PySide.QtCore import *
from PySide.QtGui import *

class TPFCWindow(QWidget):
	def __init__(self):
		super().__init__()
		
		self.show()
		
		self.setWindowTitle('TPFanControl')
		
		mainLayout = QHBoxLayout()
		self.setLayout(mainLayout)
		
		tempsGB = QGroupBox('Temperatures')
		mainLayout.addWidget(tempsGB)
		
		tempsLayout = QVBoxLayout()
		tempsGB.setLayout(tempsLayout)
		
		tempsTable = QTableWidget(len(self._sensorNames), 3)
		tempsLayout.addWidget(tempsTable)
		tempsTable.horizontalHeader().hide()
		tempsTable.verticalHeader().setResizeMode(QHeaderView.ResizeToContents)
		tempsTable.setFocusPolicy(Qt.NoFocus)
		tempsTable.setSelectionMode(QTableWidget.NoSelection)
		tempsTable.setShowGrid(False)
		
		for (i, name) in enumerate(self._sensorNames):
			tempsTable.setItem(i, 0, QTableWidgetItem(name))
			
			tempLabel = QTableWidgetItem()
			tempsTable.setItem(i, 1, tempLabel)
			self._valueLabels[name] = tempLabel
			
			tempsTable.setItem(i, 2, QTableWidgetItem('\xB0C'))
		
		visibleTempsLayout = QHBoxLayout()
		tempsLayout.addLayout(visibleTempsLayout)
		
		allButton = QRadioButton('all')
		visibleTempsLayout.addWidget(allButton)
		
		activeButton = QRadioButton('active')
		visibleTempsLayout.addWidget(activeButton)
		activeButton.toggled.connect(lambda: [tempsTable.setRowHidden(self._sensorNames.index(name), activeButton.isChecked()) for name in self._hiddenTemps])
		activeButton.setChecked(True)
		
		tpfcGB = QGroupBox('TPFanControl')
		mainLayout.addWidget(tpfcGB)
		
		tpfcLayout = QVBoxLayout()
		tpfcGB.setLayout(tpfcLayout)
		
		stateLayout = QHBoxLayout()
		tpfcLayout.addLayout(stateLayout)
		
		stateLayout.addWidget(QLabel('State'))
		self._fanStateLabel = QLabel()
		stateLayout.addWidget(self._fanStateLabel)
		
		speedLayout = QHBoxLayout()
		tpfcLayout.addLayout(speedLayout)
		
		speedLayout.addWidget(QLabel('Speed'))
		self._fanSpeedLabel = QLabel()
		speedLayout.addWidget(self._fanSpeedLabel)
		speedLayout.addWidget(QLabel('RPM'))
		
		modeLayout = QHBoxLayout()
		tpfcLayout.addLayout(modeLayout)
		
		modeLayout.addWidget(QLabel('Mode'))
		
		modeOptionsLayout = QVBoxLayout()
		modeLayout.addLayout(modeOptionsLayout)
		
		fanButtonsGroup = QButtonGroup()
		biosModeButton = QRadioButton('BIOS')
		modeOptionsLayout.addWidget(biosModeButton)
		fanButtonsGroup.addButton(biosModeButton)
		biosModeButton.clicked.connect(lambda: self.changeFanMode('auto'))
		
		smartModeButton = QRadioButton('Smart')
		modeOptionsLayout.addWidget(smartModeButton)
		fanButtonsGroup.addButton(smartModeButton)
		smartModeButton.clicked.connect(lambda: self.changeFanMode('auto'))

		manualModeLayout = QHBoxLayout()
		modeOptionsLayout.addLayout(manualModeLayout)
		
		manualModeButton = QRadioButton('Manual')
		manualModeLayout.addWidget(manualModeButton)
		fanButtonsGroup.addButton(manualModeButton)
		manualModeButton.clicked.connect(lambda: self.changeFanMode(manualModeCombo.currentText()))
		
		manualModeCombo = QComboBox()
		manualModeLayout.addWidget(manualModeCombo)
		for speed in [str(speed) for speed in range(8)] + ['disengaged']:
			manualModeCombo.addItem(speed)
		manualModeCombo.setCurrentIndex(8)
		manualModeCombo.currentIndexChanged.connect(lambda: self.changeFanMode(manualModeCombo.currentText()) if manualModeButton.isChecked() else None)
		
		fan = self._readFan()
		if fan['level'] == 'auto':
			biosModeButton.setChecked(True)
		else:
			smartModeButton.setChecked(True)
		
		self._systemTrayIcon = TPFCTrayIcon(self)
		self._systemTrayIcon.activated.connect(lambda reason: self.toggleVisibility() if reason == QSystemTrayIcon.ActivationReason.Trigger else None)
		self._systemTrayIcon.show()
		
		trayIconMenu = QMenu(self)
		self._systemTrayIcon.setContextMenu(trayIconMenu)
		self._restoreHideAction = QAction('Hide', self, triggered = self.toggleVisibility)
		trayIconMenu.addAction(self._restoreHideAction)
		trayIconMenu.addAction(QAction('Quit', self, triggered = QCoreApplication.instance().quit))
		
		try:
			f = open('/proc/acpi/ibm/fan', 'w')
			f.close()
		except IOError:
			QMessageBox.warning(self, 'Warning', 'TPFanControl does not have write access to the ACPI interface. Fan speed will be read-only.')
			biosModeButton.setEnabled(False)
			smartModeButton.setEnabled(False)
			manualModeButton.setEnabled(False)
			manualModeCombo.setEnabled(False)
		
		timer = QTimer(self)
		timer.timeout.connect(self.update)
		timer.start(5000)
		
		self.update()
	
	def setVisible(self, visible):
		super().setVisible(visible)
		try:
			self._restoreHideAction.setText('Hide' if visible else 'Restore')
		except AttributeError:
			pass
	
	def toggleVisibility(self):
		self.setVisible(not self.isVisible())
	
	def closeEvent(self, event):
		self.hide()
		event.ignore()
	
	def update(self):
		self.updateTemps()
		self.updateFanMode()
	
	def changeFanMode(self, mode):
		f = open('/proc/acpi/ibm/fan', 'w')
		f.write('level ' + mode)
		f.close()
		
		self.updateFanMode()
	
	def updateTemps(self):
		temps = self._readTemp()
		for name in self._sensorNames:
			self._valueLabels[name].setText(str(temps[name]))
		maxTemp = max([item for item in temps.items() if item[0] not in self._hiddenTemps], key = operator.itemgetter(1))
		self._systemTrayIcon.update(maxTemp[0], maxTemp[1], self._colors[self._colorTemps[bisect.bisect_left(self._colorTemps, maxTemp[1]) - 1]])
		self.setWindowIcon(self._systemTrayIcon.icon())
	
	def updateFanMode(self):
		fan = self._readFan()
		self._fanStateLabel.setText(fan['level'])
		self._fanSpeedLabel.setText(fan['speed'])
	
	def _readTemp(self):
		f = open('/proc/acpi/ibm/thermal')
		line = f.read()
		f.close()
		return {name: int(temp) for (name, temp) in zip(self._sensorNames, line[(line.find('\t') + 1):-1].split())}
	
	def _readFan(self):
		f = open('/proc/acpi/ibm/fan')
		fan = {part[0][:-1]:part[-1] for part in [line[:-1].split('\t') for line in f]}
		f.close()
		return fan
	
	_sensorNames = ['cpu', 'aps', 'crd', 'gpu', 'no5', 'x7d', 'bat', 'x7f', 'bus', 'pci', 'pwr']
	_hiddenTemps = frozenset(['no5', 'x7d', 'x7f'])
	_levels = {45: '0', 55: '1', 65: '3', 80: '7', 90: 'disengaged'}
	_colors = {0: Qt.GlobalColor.cyan, 55: Qt.GlobalColor.yellow, 65: Qt.GlobalColor.magenta, 90: Qt.GlobalColor.red}
	_colorTemps = sorted(_colors.keys())
	_valueLabels = {}
	
	_fanStateLabel = None
	_fanSpeedLabel = None
	_systemTrayIcon = None
	_restoreHideAction = None

class TPFCTrayIcon(QSystemTrayIcon):
	def __init__(self, parent):
		super().__init__(parent)

		self._trayIconEngine = TPFCTrayIconEngine()
		self.setIcon(QIcon(self._trayIconEngine))
	
	def update(self, name, temp, color):
		if self._trayIconEngine.update(name, temp, color):
			self.setIcon(self.icon())
	
	_trayIconEngine = None

class TPFCTrayIconEngine(QIconEngineV2):
	def __init__(self):
		super().__init__()
		self._backgroundBrush = QBrush()
		self._backgroundBrush.setStyle(Qt.SolidPattern)
	
	def paint(self, painter, rect, mode, state):
		painter.fillRect(rect, Qt.transparent)
		if self._name != None and self._temp != None:
			painter.setBackground(self._backgroundBrush)
			painter.eraseRect(rect)
			font = painter.font()
			fontSize = None
			text = self._name + '\n' + str(self._temp)
			try:
				fontSize = self._fontSizes[rect]
			except KeyError:
				fontSize = rect.height()
			while True:
				font.setPointSize(fontSize)
				painter.setFont(font)
				boundingRect = painter.boundingRect(rect, Qt.AlignCenter, text)
				if boundingRect.width() <= rect.width() and boundingRect.height() <= rect.height():
					self._fontSizes[rect] = fontSize
					break
				else:
					fontSize = fontSize - 1
			painter.drawText(rect, Qt.AlignCenter, text)
	
	def update(self, name, temp, color):
		if self._name != name or self._temp != temp or self._backgroundBrush.color() != color:
			self._name = name
			self._temp = temp
			self._backgroundBrush.setColor(color)
			
			return True
		
		else:
			return False
	
	_name = None
	_temp = None
	_backgroundBrush = None
	_fontSizes = {}

def main():
	app = QApplication(sys.argv)
	QApplication.setQuitOnLastWindowClosed(False)
	w = TPFCWindow()
	sys.exit(app.exec_())

if __name__ == '__main__':
	main()
