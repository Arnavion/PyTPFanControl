#!/usr/bin/python3

import bisect
import operator
import sys

from PySide.QtCore import *
from PySide.QtGui import *

from acpi import Temperatures, Fan
from settings import Settings

class TPFCWindow(QWidget):
	def __init__(self):
		super().__init__(windowTitle = 'TPFanControl')
		
		self._levelTemps = sorted(Settings.LEVELS.keys())
		self._colorTemps = sorted(Settings.COLORS.keys())
		
		self._smartMode = False
		
		mainLayout = QHBoxLayout()
		self.setLayout(mainLayout)
		
		tempsGB = QGroupBox('Temperatures')
		mainLayout.addWidget(tempsGB)
		
		tempsLayout = QVBoxLayout()
		tempsGB.setLayout(tempsLayout)
		
		tempsTable = QTableWidget(len(Settings.SENSOR_NAMES), 3, focusPolicy = Qt.NoFocus, selectionMode = QTableWidget.NoSelection, showGrid = False)
		tempsLayout.addWidget(tempsTable)
		tempsTable.horizontalHeader().hide()
		tempsTable.verticalHeader().setResizeMode(QHeaderView.ResizeToContents)
		
		self._valueLabels = {}
		for (i, name) in enumerate(Settings.SENSOR_NAMES):
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
		activeButton.toggled.connect(lambda: [tempsTable.setRowHidden(Settings.SENSOR_NAMES.index(name), activeButton.isChecked()) for name in Settings.HIDDEN_TEMPS])
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
		biosModeButton = QRadioButton('BIOS', clicked = self.enableBIOSMode)
		modeOptionsLayout.addWidget(biosModeButton)
		fanButtonsGroup.addButton(biosModeButton)
		
		smartModeButton = QRadioButton('Smart', clicked = self.enableSmartMode)
		modeOptionsLayout.addWidget(smartModeButton)
		fanButtonsGroup.addButton(smartModeButton)

		manualModeLayout = QHBoxLayout()
		modeOptionsLayout.addLayout(manualModeLayout)
		
		manualModeButton = QRadioButton('Manual', clicked = lambda: self.enableManualMode(manualModeCombo.currentText()))
		manualModeLayout.addWidget(manualModeButton)
		fanButtonsGroup.addButton(manualModeButton)
		
		manualModeCombo = QComboBox()
		manualModeLayout.addWidget(manualModeCombo)
		for speed in sorted(Fan.FIRMWARE_TO_HWMON):
			manualModeCombo.addItem(speed)
		manualModeCombo.addItem('full-speed')
		manualModeCombo.setCurrentIndex(len(Fan.FIRMWARE_TO_HWMON))
		manualModeCombo.currentIndexChanged.connect(lambda: self.enableManualMode(manualModeCombo.currentText()) if manualModeButton.isChecked() else None)
		
		if Fan.read()['level'] == 'auto':
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
		
		self.show()
		
		timer = QTimer(self)
		timer.timeout.connect(self.update)
		timer.start(Settings.UPDATE_INTERVAL * 1000)
		
		self.update()
		
		if not Fan.isWritable():
			self._systemTrayIcon.showMessage('Warning', 'TPFanControl does not have write access to the ACPI interface. Fan speed will be read-only.', QSystemTrayIcon.MessageIcon.Warning)
			for control in (biosModeButton, smartModeButton, manualModeButton, manualModeCombo):
				control.setEnabled(False)
	
	def setVisible(self, visible):
		super().setVisible(visible)
		self._restoreHideAction.setText('Hide' if visible else 'Restore')
		if visible and self.windowState() == Qt.WindowMinimized:
			self.setWindowState(Qt.WindowNoState)
	
	def toggleVisibility(self):
		self.setVisible(not self.isVisible())
	
	def closeEvent(self, event):
		self.hide()
		event.ignore()
	
	def update(self):
		maxTemp = self.updateTemps()
		if self._smartMode:
			newFanLevel = Settings.LEVELS[self._levelTemps[bisect.bisect_left(self._levelTemps, maxTemp) - 1]]
			self.setFanLevel(newFanLevel)
		
		self.updateFan()
	
	def enableBIOSMode(self):
		self._smartMode = False
		self.setFanLevel('auto')
	
	def enableSmartMode(self):
		self._smartMode = True
	
	def enableManualMode(self, newLevel):
		self._smartMode = False
		self.setFanLevel(newLevel)
	
	def setFanLevel(self, level):
		Fan.setLevel(level)
		self.updateFan()
	
	def updateTemps(self):
		temps = Temperatures.read()
		for name in Settings.SENSOR_NAMES:
			self._valueLabels[name].setText(str(temps.get(name, 'n/a')))
		maxTemp = max((item for item in temps.items() if item[0] not in Settings.HIDDEN_TEMPS), key = operator.itemgetter(1))
		self._systemTrayIcon.update(maxTemp[0], maxTemp[1], Settings.COLORS[self._colorTemps[bisect.bisect_left(self._colorTemps, maxTemp[1]) - 1]])
		return maxTemp[1]
	
	def updateFan(self):
		fan = Fan.read()
		self._fanStateLabel.setText(fan['level'])
		self._fanSpeedLabel.setText(fan['speed'])
		if fan['level'] != 'auto':
			Fan.setLevel(fan['level'])

class TPFCTrayIcon(QSystemTrayIcon):
	def __init__(self, parent):
		super().__init__(parent)

		self._iconEngine = TPFCIconEngine()
		self.setIcon(QIcon(self._iconEngine))
	
	def update(self, name, temp, color):
		if self._iconEngine.update(name, temp, color):
			self.setIcon(self.icon())
			self.parent().setWindowIcon(self.icon())

class TPFCIconEngine(QIconEngineV2):
	def __init__(self):
		super().__init__()
		
		self._name = None
		self._temp = None
		self._fontSizes = {}
		
		self._backgroundBrush = QBrush()
		self._backgroundBrush.setStyle(Qt.SolidPattern)
	
	def paint(self, painter, rect, mode, state):
		painter.fillRect(rect, Qt.transparent)
		if self._name != None and self._temp != None:
			if isinstance(painter.device(), QWidget): # systray icon; only drawText works; fillRect, drawLine, etc. don't
				pen = painter.pen()
				penColor = pen.color()
				pen.setColor(self._backgroundBrush.color())
				painter.setPen(pen)
				font = painter.font()
				font.setPointSize(rect.height())
				painter.setFont(font)
				painter.drawText(rect, '\u2588') # █
				pen.setColor(penColor)
				painter.setPen(pen)
			else: # task manager / task switcher icons; fillRect works
				painter.setBackground(self._backgroundBrush)
				painter.eraseRect(rect)
			font = painter.font()
			fontSize = None
			text = self._name + '\n' + str(self._temp)
			fontSize = self._fontSizes.get(rect, rect.height())
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

def main():
	app = QApplication(sys.argv, quitOnLastWindowClosed = False)
	TPFCWindow()
	sys.exit(app.exec_())

if __name__ == '__main__':
	main()
