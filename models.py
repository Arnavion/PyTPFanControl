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
			if hasattr(self, '_temps'):
				return str(self._temps.get(Settings.SENSOR_NAMES[index.row()], 'n/a'))
			else:
				return 'n/a'
		
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
	
	def tick(self):
		self.beginResetModel()
		
		self._temps = Temperatures.read()
		
		# Find the item in the dictionary for the highest temperature
		self._maxTemp = max((item for item in self._temps.items() if item[0] not in Settings.HIDDEN_TEMPS), key=operator.itemgetter(1))
		
		self.endResetModel()
	
	def maxTemp(self):
		return self._maxTemp


class FanModel(QAbstractItemModel):
	def rowCount(self, parent=QModelIndex()):
		return 0
	
	def data(self, index, role=Qt.DisplayRole):
		return None
	
	def tick(self):
		self.beginResetModel()
		
		self._fan = Fan.read()
		
		self.endResetModel()
		
		if self._fan.level != 'auto':
			Fan.setLevel(self._fan.level)
	
	def level(self):
		return self._fan.level
	
	def setLevel(self, level):
		"""
		Set the fan level to the new level.
		
		"""
		
		Fan.setLevel(level)
		self.tick()
	
	def speed(self):
		return self._fan.speed
	
	LEVEL_DISPLAY_STRINGS = {speed: speed for speed in Fan.FIRMWARE_TO_HWMON.keys()}
	LEVEL_DISPLAY_STRINGS['auto'] = 'Auto'
	LEVEL_DISPLAY_STRINGS['full-speed'] = 'Full speed'
