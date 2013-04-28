#!/usr/bin/python3

import bisect
import operator

from PySide.QtCore import *

from acpi import Temperatures, Fan
from settings import Settings


class TemperaturesModel(QAbstractTableModel):
	def __init__(self, parent=None):
		super().__init__(parent)
		
		self._rowCount = len(Settings.SENSOR_NAMES)
		
		# Set up updating the temperature regularly, using the update interval specified in the settings
		QTimer(self, timeout=self.update).start(Settings.UPDATE_INTERVAL * 1000)
		self.update()
	
	def rowCount(self, parent=QModelIndex()):
		return self._rowCount
	
	def columnCount(self, parent=QModelIndex()):
		return 3
	
	def data(self, index, role=Qt.DisplayRole):
		if not index.isValid():
			return None
		
		if index.row() < 0 or index.row() >= self._rowCount:
			return None
		
		if role != Qt.DisplayRole:
			return None
		
		column = index.column()
		
		if column == 0:
			return Settings.SENSOR_NAMES[index.row()]
		
		elif column == 1:
			return str(self._temps.get(Settings.SENSOR_NAMES[index.row()], 'n/a'))
		
		elif column == 2:
			if Settings.FAHRENHEIT_OUTPUT:
				return '\xB0F'
			else:
				return '\xB0C'
		
		else:
			return None
	
	def headerData(self, section, orientation, role=Qt.DisplayRole):
		if role != Qt.DisplayRole:
			return None
		
		if orientation != Qt.Horizontal:
			return None
		
		if section == 0:
			return 'Name'
		
		elif section == 1:
			return 'Temperature'
		
		elif section == 2:
			return 'Unit'
		
		else:
			return None
	
	def maxTemp(self):
		return self._maxTemp
	
	def update(self):
		self.beginResetModel()
		
		self._temps = Temperatures.read()
		
		# Find the item in the dictionary for the highest temperature
		self._maxTemp = max((item for item in self._temps.items() if item[0] not in Settings.HIDDEN_TEMPS), key=operator.itemgetter(1))
		
		self.endResetModel()


class FanModel(QAbstractItemModel):
	def __init__(self, tempsModel, parent=None):
		super().__init__(parent)
		
		self._tempsModel = tempsModel
		
		self._mode = 'auto'
		
		#Update when the temperatures model updates
		self._tempsModel.modelReset.connect(self.update)
		self.update()
	
	def rowCount(self, parent=QModelIndex()):
		return 0
	
	def data(self, index, role=Qt.DisplayRole):
		return None
	
	def mode(self):
		return self._mode
	
	def setBIOSMode(self):
		self._mode = 'auto'
		Fan.setLevel('auto')
		self.update()
	
	def setSmartMode(self):
		self._mode = 'smart'
		self.update()
	
	def setManualMode(self, level):
		self._mode = 'manual'
		Fan.setLevel(level)
		self.update()
	
	def level(self):
		return self._fanStatus.level
	
	def speed(self):
		return self._fanStatus.speed
	
	def update(self):
		self.beginResetModel()
		
		if self._mode == 'smart':
			newFanLevel = Settings.LEVELS[FanModel.LEVEL_TEMPS[bisect.bisect_left(FanModel.LEVEL_TEMPS, self._tempsModel.maxTemp()[1]) - 1]]
			Fan.setLevel(newFanLevel)
		
		elif self._mode == 'manual':
			self._fanStatus = Fan.read()
			# Reset the watchdog timer
			Fan.setLevel(self._fanStatus.level)
		
		self._fanStatus = Fan.read()
		
		self.endResetModel()
	
	LEVEL_DISPLAY_STRINGS = {speed: speed for speed in Fan.FIRMWARE_TO_HWMON.keys()}
	LEVEL_DISPLAY_STRINGS['auto'] = 'Auto'
	LEVEL_DISPLAY_STRINGS['full-speed'] = 'Full speed'
	
	# Holds the fan levels' temperatures in sorted order
	LEVEL_TEMPS = sorted(Settings.LEVELS.keys())
