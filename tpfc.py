#!/usr/bin/python3

import bisect
import operator
from os import path
import sys

from PyQt4 import uic
from PyQt4.QtCore import *
from PyQt4.QtGui import *

from acpi import Fan
from models import TemperaturesModel, FanModel
from settings import Settings


CustomClass, WidgetClass = uic.loadUiType(path.dirname(path.realpath(__file__)) + '/tpfc.ui')
class TPFCWindow(CustomClass, WidgetClass):
	"""
	Main window of application.
	
	"""
	
	def __init__(self, parent=None):
		super().__init__(parent)
		self.setupUi(self)
		
		self._tempsModel = TemperaturesModel(self)
		
		self._fanModel = FanModel(self._tempsModel, self)
		
		# Connect the temperatures table to the temperatures model
		self.tempsTable.setModel(self._tempsModel)
		self.tempsTable.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
		
		# Update the icons when the temperatures change
		self._tempsModel.modelReset.connect(self.updateTemperatureIcons)
		
		# Connect the fan speed and level labels to the fan model.
		self._fanModel.modelReset.connect(self.updateFanLabels)
		
		self.activeButton.toggled.connect(self.toggleTempSensorsVisibility)
		self.toggleTempSensorsVisibility()
		
		self.biosModeButton.toggled.connect(self.enableBIOSMode)
		self.smartModeButton.toggled.connect(self.enableSmartMode)
		self.manualModeButton.toggled.connect(self.enableManualMode)
		
		for speed in sorted(Fan.FIRMWARE_TO_HWMON):
			self.manualModeCombo.addItem(FanModel.LEVEL_DISPLAY_STRINGS[speed], speed)
		self.manualModeCombo.addItem(FanModel.LEVEL_DISPLAY_STRINGS['full-speed'], 'full-speed')
		self.manualModeCombo.setCurrentIndex(len(Fan.FIRMWARE_TO_HWMON))
		# Changing the selected level changes the fan level immediately if manual mode is enabled
		self.manualModeCombo.currentIndexChanged.connect(self.enableManualMode)
		
		# Start off the application in smart mode
		if Fan.isWritable():
			self.smartModeButton.setChecked(True)
		else:
			self.biosModeButton.setChecked(True)
		
		self.show()
		
		# The icon engine and icon object
		self._iconEngine = TPFCIconEngine(self._tempsModel)
		icon = QIcon(self._iconEngine)
		
		# The system tray icon
		self._systemTrayIcon = QSystemTrayIcon(icon, self)
		self._systemTrayIcon.activated.connect(self.systemTrayIconActivated)
		self._systemTrayIcon.setVisible(True)
		
		# The window icon
		self.setWindowIcon(icon)
		
		# The context menu for the system tray icon
		trayIconMenu = QMenu(self)
		self._systemTrayIcon.setContextMenu(trayIconMenu)
		# The first entry in the context menu hides or shows the main window
		self._restoreHideAction = QAction('Hide', self, triggered=self.toggleVisibility)
		trayIconMenu.addAction(self._restoreHideAction)
		# The second entry in the context menu quits the program
		trayIconMenu.addAction(QAction('Quit', self, triggered=self.quit))
		
		# If the fan level is not modificable, show a warning notification balloon from the system tray icon and disable the fan level controls
		if not Fan.isWritable():
			title = 'Warning'
			message = 'PyTPFanControl does not have write access to the ACPI interface. Fan speed will be read-only.'
			
			dbusAvailable = True
			try:
				import dbus
				try:
					notifications = dbus.SessionBus().get_object("org.freedesktop.Notifications", '/org/freedesktop/Notifications')
					notifications.Notify('PyTPFanControl', dbus.UInt32(0), 'dialog-warning', title, message, dbus.Array(signature='s'), dbus.Dictionary(signature='sv'), 0)
				except dbus.exceptions.DBusException:
					dbusAvailable = False
			except ImportError:
				dbusAvailable = False
			
			if not dbusAvailable:
				QTimer.singleShot(1000, lambda: self._systemTrayIcon.showMessage(title, message, QSystemTrayIcon.Warning))
			
			for control in (self.biosModeButton, self.smartModeButton, self.manualModeButton, self.manualModeCombo):
				control.setEnabled(False)
	
	def toggleTempSensorsVisibility(self):
		for name in Settings.HIDDEN_TEMPS:
			self.tempsTable.setRowHidden(Settings.SENSOR_NAMES.index(name), self.activeButton.isChecked())
	
	def enableBIOSMode(self):
		"""
		Enable BIOS mode if the BIOS mode button is checked.
		
		"""
		
		if self.biosModeButton.isChecked():
			self._fanModel.setBIOSMode()
	
	def enableSmartMode(self):
		"""
		Enable smart mode if the smart mode button is checked.
		
		"""
		
		if self.smartModeButton.isChecked():
			self._fanModel.setSmartMode()
	
	def enableManualMode(self):
		"""
		Enable manual mode if the manual mode button is checked.
		
		"""
		
		if self.manualModeButton.isChecked():
			self._fanModel.setManualMode(self.manualModeCombo.itemData(self.manualModeCombo.currentIndex()))
	
	def updateTemperatureIcons(self):
		"""
		Update the system tray icon and the window icon to display the name and temperature of the hottest sensor.
		
		"""
		
		# Only re-compute the icons if the icon has changed
		if self._iconEngine.update():
			self._systemTrayIcon.setIcon(self._systemTrayIcon.icon())
			self.setWindowIcon(self.windowIcon())
	
	def updateFanLabels(self):
		"""
		Update the fan speed and level labels.
		
		"""
		
		self.fanLevelLabel.setText(FanModel.LEVEL_DISPLAY_STRINGS[self._fanModel.level()])
		self.fanSpeedLabel.setText(self._fanModel.speed())
	
	def systemTrayIconActivated(self, reason):
		if reason == QSystemTrayIcon.Trigger:
			self.toggleVisibility()
		
		elif reason == QSystemTrayIcon.Context:
			# Set the text of the 'Restore'/'Hide' system tray context menu entry
			self._restoreHideAction.setText('Hide' if self.isVisible() else 'Restore')
	
	def toggleVisibility(self):
		"""
		Toggle the visibility of the main window.
		
		"""
		
		self.setVisible(not self.isVisible())
	
	def quit(self):
		"""
		Set the fan back into BIOS mode and quit the application.
		
		"""
		
		self._fanModel.setBIOSMode()
		QCoreApplication.instance().quit()

	def showEvent(self, event):
		# If the window is being restored, force it to not be minimized
		if self.windowState() == Qt.WindowMinimized:
			self.setWindowState(Qt.WindowNoState)
	
	def closeEvent(self, event):
		"""
		Suppress the window's close event and hide it instead. The application only quits when the 'Quit' system tray context menu entry is selected.
		
		"""
		
		self.hide()
		event.ignore()


class TPFCIconEngine(QIconEngine):
	"""
	Create an icon engine which knows how to generate icons given a sensor name, temperature and background color.
	
	"""
	
	def __init__(self, tempsModel):
		super().__init__()
		
		# Temperatures model
		self._tempsModel = tempsModel
		
		# Map of icon size rectangle to the maximum font size with which the text can be drawn to fit in the icon
		self._fontSizes = {}
		
		# The currently displayed maximum temperature and sensor
		self._maxTemp = ('', None)
		
		# The background brush
		self._backgroundBrush = QBrush(Qt.SolidPattern)
		
		self.update()
	
	def paint(self, painter, rect, mode, state):
		# Set the background brush
		painter.setBackground(self._backgroundBrush)
		# ... and fill the rectangle with it
		painter.eraseRect(rect)
		
		# The text to be displayed in the icon
		text = '{0}\n{1}'.format(self._maxTemp[1], self._maxTemp[0])
		
		self.setOptimalFontSize(painter, rect, text)
		
		painter.drawText(rect, Qt.AlignCenter, text)
	
	def update(self):
		"""
		Update the icon engine with the new sensor name, temperature and background color for the icons. Return `True` if any of the values are different from the last call to `update` and thus, if re-rendering the icon is needed.
		
		"""
		
		maxTemp = self._tempsModel.maxTemp()
		
		color = Settings.COLORS[TPFCIconEngine.COLOR_TEMPS[bisect.bisect_left(TPFCIconEngine.COLOR_TEMPS, maxTemp[1]) - 1]]
		
		if self._maxTemp != maxTemp or self._backgroundBrush.color() != color:
			self._maxTemp = maxTemp
			self._backgroundBrush.setColor(color)
			
			return True
		
		else:
			return False
	
	def setOptimalFontSize(self, painter, rect, text):
		# The font of the painter
		font = painter.font()
		# The key to find in the _fontSizes dict
		fontSizesKey = (rect.width(), rect.height())
		# The largest font size to draw the text in the icon and still have it fit
		fontSize = self._fontSizes.get(fontSizesKey, rect.height())
		
		# Check that the text will fit in the icon with that fontSize. If it doesn't, decrease it progressively until it does.
		while True:
			font.setPointSize(fontSize)
			painter.setFont(font)
			boundingRect = painter.boundingRect(rect, Qt.AlignCenter, text)
			if boundingRect.width() <= rect.width() and boundingRect.height() <= rect.height():
				# If this font size works, save it as the maximum font size for this rectangle
				self._fontSizes[fontSizesKey] = fontSize
				break
			else:
				# ... else decrease it and try again
				factor = max(boundingRect.width() / rect.width(), boundingRect.height() / rect.height())
				oldFontSize = fontSize
				fontSize = fontSize // factor
				if fontSize == oldFontSize:
					fontSize = fontSize - 1 # Atleast decrease the font size by 1
	
	# Holds the icon colors' temperatures in sorted order
	COLOR_TEMPS = sorted(Settings.COLORS.keys())


def main():
	# Create the application. The application will not close even if its windows are closed.
	app = QApplication(sys.argv)
	
	# Load the UI and create the main window
	window = TPFCWindow()
	
	# Start the event loop
	sys.exit(app.exec_())


if __name__ == '__main__':
	main()
