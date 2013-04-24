#!/usr/bin/python3

import bisect
import operator
from os import path
import sys

from PySide.QtCore import *
from PySide.QtGui import *
from PySide.QtUiTools import QUiLoader

from acpi import Temperatures, Fan
from settings import Settings


class TPFCUiLoader(QUiLoader):
	"""
	Specialized QUiLoader to load TPFCWindow from tpfc.ui
	
	"""
	
	def createWidget(self, className, parent=None, name=''):
		if className == 'TPFCWindow':
			result = TPFCWindow(parent, objectName=name)
			self._loadResult = result
		else:
			result = super().createWidget(className, parent, name)
			setattr(self._loadResult, '_' + name, result)
		
		return result


class TPFCWindow(QWidget):
	"""
	Main window of application.
	
	"""
	
	def loaded(self):
		# Holds the fan levels' temperatures in sorted order
		self._levelTemps = sorted(Settings.LEVELS.keys())
		# Holds the icon colors' temperatures in sorted order
		self._colorTemps = sorted(Settings.COLORS.keys())
		
		self._tempsTable.setRowCount(len(Settings.SENSOR_NAMES))
		self._tempsTable.verticalHeader().setResizeMode(QHeaderView.ResizeToContents)
		
		# Map of sensor name to the corresponding GUI label which displays the temperature of that sensor
		self._valueLabels = {}
		for (i, name) in enumerate(Settings.SENSOR_NAMES):
			self._tempsTable.setItem(i, 0, QTableWidgetItem(name))
			
			tempLabel = QTableWidgetItem()
			self._tempsTable.setItem(i, 1, tempLabel)
			self._valueLabels[name] = tempLabel
			
			self._tempsTable.setItem(i, 2, QTableWidgetItem('\xB0C'))
		
		self._activeButton.toggled.connect(self.toggleTempSensorsVisibility)
		self.toggleTempSensorsVisibility()
		
		self._biosModeButton.toggled.connect(self.enableBIOSMode)
		self._smartModeButton.toggled.connect(self.enableSmartMode)
		self._manualModeButton.toggled.connect(self.enableManualMode)
		
		for speed in sorted(Fan.FIRMWARE_TO_HWMON):
			self._manualModeCombo.addItem(TPFCWindow.LEVEL_DISPLAY_STRINGS[speed], speed)
		self._manualModeCombo.addItem(TPFCWindow.LEVEL_DISPLAY_STRINGS['full-speed'], 'full-speed')
		self._manualModeCombo.setCurrentIndex(len(Fan.FIRMWARE_TO_HWMON))
		# Changing the selected level changes the fan level immediately if manual mode is enabled
		self._manualModeCombo.currentIndexChanged.connect(self.enableManualMode)
		
		# Start off the application in smart mode
		if Fan.isWritable():
			self._smartModeButton.setChecked(True)
		else:
			self._biosModeButton.setChecked(True)
		
		self.show()
		
		# The icon engine and icon object
		self._iconEngine = TPFCIconEngine()
		self._icon = QIcon(self._iconEngine)
		
		# The system tray icon
		self._systemTrayIcon = QSystemTrayIcon(self)
		self._systemTrayIcon.activated.connect(self.systemTrayIconActivated)
		self._systemTrayIcon.setIcon(self._icon)
		self._systemTrayIcon.show()
		
		# The window icon
		self.setWindowIcon(self._icon)
		
		# The context menu for the system tray icon
		trayIconMenu = QMenu(self)
		self._systemTrayIcon.setContextMenu(trayIconMenu)
		# The first entry in the context menu hides or shows the main window
		self._restoreHideAction = QAction('Hide', self, triggered=self.toggleVisibility)
		trayIconMenu.addAction(self._restoreHideAction)
		# The second entry in the context menu quits the program
		trayIconMenu.addAction(QAction('Quit', self, triggered=self.quit))
		
		# Set up updating the fan and temperature regularly, using the update interval specified in the settings
		QTimer(self, timeout=self.update).start(Settings.UPDATE_INTERVAL * 1000)
		
		self.update()
		
		# If the fan level is not modificable, show a warning notification balloon from the system tray icon and disable the fan level controls
		if not Fan.isWritable():
			title = 'Warning'
			message = 'PyTPFanControl does not have write access to the ACPI interface. Fan speed will be read-only.'
			
			try:
				import dbus
				notifications = dbus.SessionBus().get_object("org.freedesktop.Notifications", '/org/freedesktop/Notifications')
				notifications.Notify('PyTPFanControl', dbus.UInt32(0), 'dialog-warning', title, message, dbus.Array(signature='s'), dbus.Dictionary(signature='sv'), 0)
			except (ImportError, dbus.exceptions.DBusException):
				QTimer.singleShot(1000, lambda: self._systemTrayIcon.showMessage(title, message, QSystemTrayIcon.MessageIcon.Warning))
			
			for control in (self._biosModeButton, self._smartModeButton, self._manualModeButton, self._manualModeCombo):
				control.setEnabled(False)
	
	def update(self):
		"""
		Update the temperature and fan sensor displays, and the system tray and window icons. If smart mode is enabled, also calculate the new fan level.
		
		"""
		
		# Update the temperature labels and icons
		maxTemp = self.updateTemps()
		# If smart mode is enabled
		if self._smartMode:
			# Calculate and set the new fan level
			newFanLevel = Settings.LEVELS[self._levelTemps[bisect.bisect_left(self._levelTemps, maxTemp) - 1]]
			self.setFanLevel(newFanLevel)
		
		# Update the fan labels
		self.updateFan()
	
	def updateTemps(self):
		"""
		Update the temperature sensor labels, the system tray icon, and the window icon, and return the highest temperature value.
		
		"""
		
		# Read the temperatures
		temps = Temperatures.read()
		# ... and update the labels
		for name in Settings.SENSOR_NAMES:
			self._valueLabels[name].setText(str(temps.get(name, 'n/a')))
		# Find the item in the dictionary for the highest temperature
		maxTemp = max((item for item in temps.items() if item[0] not in Settings.HIDDEN_TEMPS), key=operator.itemgetter(1))
		# ... and update the system tray icon and the window icon with the new temperature, sensor and background color
		self.updateIcons(maxTemp[0], maxTemp[1], Settings.COLORS[self._colorTemps[bisect.bisect_left(self._colorTemps, maxTemp[1]) - 1]])
		
		# Return the highest temperature value
		return maxTemp[1]
	
	def updateFan(self):
		"""
		Update the fan speed and level labels.
		
		"""
		
		fan = Fan.read()
		self._fanLevelLabel.setText(TPFCWindow.LEVEL_DISPLAY_STRINGS[fan.level])
		self._fanSpeedLabel.setText(fan.speed)
		
		# If the fan is on manual or smart mode, reset the watchdog timer by setting the same level as the current one
		if fan.level != 'auto':
			Fan.setLevel(fan.level)
	
	def toggleTempSensorsVisibility(self):
		for name in Settings.HIDDEN_TEMPS:
			self._tempsTable.setRowHidden(Settings.SENSOR_NAMES.index(name), self._activeButton.isChecked())
	
	def enableBIOSMode(self):
		"""
		Enable BIOS mode if the BIOS mode button is checked.
		
		"""
		
		if self._biosModeButton.isChecked():
			self._smartMode = False
			self.setFanLevel('auto')
	
	def enableSmartMode(self):
		"""
		Enable smart mode if the smart mode button is checked.
		
		"""
		
		if self._smartModeButton.isChecked():
			self._smartMode = True
			# Fan level will be set in the next update()
	
	def enableManualMode(self):
		"""
		Enable manual mode if the manual mode button is checked.
		
		"""
		
		if self._manualModeButton.isChecked():
			self._smartMode = False
			self.setFanLevel(self._manualModeCombo.itemData(self._manualModeCombo.currentIndex()))
	
	def updateIcons(self, name, temp, color):
		"""
		Update the system tray icon and the window icon to display the given sensor name and temperature with the given background color.
		
		"""
		
		if self._iconEngine.update(name, temp, color):
			# Only re-compute the icons if the icon has changed
			self._systemTrayIcon.setIcon(self._icon)
			self.setWindowIcon(self._icon)
	
	def systemTrayIconActivated(self, reason):
		if reason == QSystemTrayIcon.ActivationReason.Trigger:
			self.toggleVisibility()
		
		# Set the text of the 'Restore'/'Hide' system tray context menu entry
		self._restoreHideAction.setText('Hide' if self.isVisible() else 'Restore')
	
	def toggleVisibility(self):
		"""
		Toggle the visibility of the main window.
		
		"""
		
		self.setVisible(not self.isVisible())
	
	def setFanLevel(self, level):
		"""
		Set the fan level to the new level and update the fan labels.
		
		"""
		
		Fan.setLevel(level)
		self.updateFan()
	
	def quit(self):
		"""
		Set the fan back into BIOS mode and quit the application.
		
		"""
		
		self.setFanLevel('auto')
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
	
	LEVEL_DISPLAY_STRINGS = {speed: speed for speed in Fan.FIRMWARE_TO_HWMON.keys()}
	LEVEL_DISPLAY_STRINGS['auto'] = 'Auto'
	LEVEL_DISPLAY_STRINGS['full-speed'] = 'Full speed'


class TPFCIconEngine(QIconEngineV2):
	"""
	Create an icon engine which knows how to generate icons given a sensor name, temperature and background color.
	
	"""
	
	def __init__(self):
		super().__init__()
		
		# Name of the sensor
		self._name = ''
		# Temperature of the sensor
		self._temp = ''
		# Map of icon size rectangle to the maximum font size with which the text can be drawn to fit in the icon
		self._fontSizes = {}
		
		# The background brush
		self._backgroundBrush = QBrush(Qt.SolidPattern)
	
	def paint(self, painter, rect, mode, state):
		# This is a workaround for what seems to be a bug in KDE. When drawing system tray icons, none of the drawing methods except drawText work.
		# Because of this, I write out a unicode box symbol in the background color instead of filling the rectangle with the background brush.
		if isinstance(painter.device(), QWidget): # System tray icon; only drawText works; fillRect, drawLine, etc. don't
			# Get the pen of the painter
			pen = painter.pen()
			# ... and set its foreground color to the required background color
			penColor = pen.color()
			pen.setColor(self._backgroundBrush.color())
			painter.setPen(pen)
			
			# Set the font size to be the same as the rectangle height
			font = painter.font()
			font.setPointSize(rect.height() * 2)
			painter.setFont(font)
			
			# Draw the unicode box █
			backgroundRect = rect.adjusted(-rect.width() // 2, -rect.height() // 2, rect.width() // 2, rect.height() // 2);
			painter.drawText(backgroundRect, '\u2588')
			
			# Restore the original foreground color. The font size will be set later.
			pen.setColor(penColor)
			painter.setPen(pen)
		
		else: # Task manager / task switcher icons; eraseRect works
			# Set the background brush
			painter.setBackground(self._backgroundBrush)
			# ... and fill the rectangle with it
			painter.eraseRect(rect)
		
		# The text to be displayed in the icon
		text = '{0}\n{1}'.format(self._temp, self._name)
		# The font of the painter
		font = painter.font()
		# The largest font size to draw the text in the icon and still have it fit
		fontSize = self._fontSizes.get(rect, rect.height() // 2)
		
		# Check that the text will fit in the icon with that fontSize. If it doesn't, decrease it by 1 point progressively until it does.
		while True:
			font.setPointSize(fontSize)
			painter.setFont(font)
			boundingRect = painter.boundingRect(rect, Qt.AlignCenter, text)
			if boundingRect.width() <= rect.width() and boundingRect.height() <= rect.height():
				# If this font size works, save it as the maximum font size for this rectangle
				self._fontSizes[rect] = fontSize
				break
			else:
				# ... else decrease it by one point and try again
				fontSize = fontSize - 1
		
		# The font size has been determined, so draw the text
		painter.drawText(rect, Qt.AlignCenter, text)
	
	def update(self, name, temp, color):
		"""
		Update the icon engine with the new sensor name, temperature and background color for the icons. Return `True` if any of the values are different from the last call to `update` and thus, if re-rendering the icon is needed.
		
		"""
		
		if self._name != name or self._temp != temp or self._backgroundBrush.color() != color:
			self._name = name
			self._temp = temp
			self._backgroundBrush.setColor(color)
			
			return True
		
		else:
			return False


def main():
	# Create the application. The application will not close even if its windows are closed.
	app = QApplication(sys.argv)
	
	# Load the UI and create the main window
	window = TPFCUiLoader().load(path.dirname(path.realpath(__file__)) + '/tpfc.ui')
	
	window.loaded()
	
	# Start the event loop
	sys.exit(app.exec_())


if __name__ == '__main__':
	main()
