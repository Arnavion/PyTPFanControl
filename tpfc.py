#!/usr/bin/python3

import bisect
import operator
import sys

from PySide.QtCore import *
from PySide.QtGui import *

from acpi import Temperatures, Fan, Battery

class TPFCWindow(QWidget):
	def __init__(self):
		super().__init__(windowTitle = 'TPFanControl')
		
		self._hiddenTemps = set(('no5', 'x7d', 'x7f', 'xc3'))
		self._levels = {45: '0', 55: '1', 65: '3', 80: '7', 90: 'disengaged'}
		self._colors = {0: Qt.GlobalColor.cyan, 55: Qt.GlobalColor.yellow, 65: Qt.GlobalColor.magenta, 90: Qt.GlobalColor.red}
		self._colorTemps = sorted(self._colors.keys())
		
		self._temperatures = Temperatures()
		self._fan = Fan()
		
		if Battery().read()['present'] == 'no':
			self._hiddenTemps.add('bat')
		
		mainLayout = QHBoxLayout()
		self.setLayout(mainLayout)
		
		tempsGB = QGroupBox('Temperatures')
		mainLayout.addWidget(tempsGB)
		
		tempsLayout = QVBoxLayout()
		tempsGB.setLayout(tempsLayout)
		
		tempsTable = QTableWidget(len(Temperatures.sensorNames), 3, focusPolicy = Qt.NoFocus, selectionMode = QTableWidget.NoSelection, showGrid = False)
		tempsLayout.addWidget(tempsTable)
		tempsTable.horizontalHeader().hide()
		tempsTable.verticalHeader().setResizeMode(QHeaderView.ResizeToContents)
		
		self._valueLabels = {}
		for (i, name) in enumerate(Temperatures.sensorNames):
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
		activeButton.toggled.connect(lambda: [tempsTable.setRowHidden(Temperatures.sensorNames.index(name), activeButton.isChecked()) for name in self._hiddenTemps])
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
		biosModeButton = QRadioButton('BIOS', clicked = lambda: self.setFanMode('auto'))
		modeOptionsLayout.addWidget(biosModeButton)
		fanButtonsGroup.addButton(biosModeButton)
		
		smartModeButton = QRadioButton('Smart', clicked = lambda: self.setFanMode('auto'))
		modeOptionsLayout.addWidget(smartModeButton)
		fanButtonsGroup.addButton(smartModeButton)

		manualModeLayout = QHBoxLayout()
		modeOptionsLayout.addLayout(manualModeLayout)
		
		manualModeButton = QRadioButton('Manual', clicked = lambda: self.setFanMode(manualModeCombo.currentText()))
		manualModeLayout.addWidget(manualModeButton)
		fanButtonsGroup.addButton(manualModeButton)
		
		manualModeCombo = QComboBox()
		manualModeLayout.addWidget(manualModeCombo)
		for speed in [str(speed) for speed in range(8)] + ['disengaged']:
			manualModeCombo.addItem(speed)
		manualModeCombo.setCurrentIndex(8)
		manualModeCombo.currentIndexChanged.connect(lambda: self.setFanMode(manualModeCombo.currentText()) if manualModeButton.isChecked() else None)
		
		if self._fan.read()['level'] == 'auto':
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
		timer.start(5000)
		
		self.update()
		
		if not self._fan.isWritable():
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
		self.updateTemps()
		self.updateFanMode()
	
	def setFanMode(self, mode):
		self._fan.setMode(mode)
		self.updateFanMode()
	
	def updateTemps(self):
		temps = self._temperatures.read()
		for name in Temperatures.sensorNames:
			self._valueLabels[name].setText(str(temps[name]))
		maxTemp = max((item for item in temps.items() if item[0] not in self._hiddenTemps), key = operator.itemgetter(1))
		self._systemTrayIcon.update(maxTemp[0], maxTemp[1], self._colors[self._colorTemps[bisect.bisect_left(self._colorTemps, maxTemp[1]) - 1]])
	
	def updateFanMode(self):
		fan = self._fan.read()
		self._fanStateLabel.setText(fan['level'])
		self._fanSpeedLabel.setText(fan['speed'])

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

def main():
	app = QApplication(sys.argv, quitOnLastWindowClosed = False)
	TPFCWindow()
	sys.exit(app.exec_())

if __name__ == '__main__':
	main()
