#!/usr/bin/python3

import os

from PySide.QtCore import Qt
from PySide.QtGui import QColor


class Settings:
	"""
	Hold the settings of PyTPFanControl.
	
	"""
	
	"""The names of the thermal sensors."""
	SENSOR_NAMES = ('cpu', 'aps', 'crd', 'gpu', 'no5', 'x7d', 'bat', 'x7f', 'bus', 'pci', 'pwr', 'xc3')
	
	"""The names of the temperatures which don't return any data, or which are otherwise useless."""
	HIDDEN_TEMPS = frozenset(
		('no5', 'x7d', 'x7f', 'xc3') +
		# If the battery is unplugged, add the bat sensor to the hidden sensors
		(('bat',) if not os.path.isdir('/sys/class/power_supply/BAT0') else ())
	)
	
	"""The background color of the icon. The key is the temperature in Celsius, and the value is the color."""
	COLORS = {0: Qt.GlobalColor.cyan, 55: Qt.GlobalColor.yellow, 65: QColor('orange'), 90: Qt.GlobalColor.red}
	
	"""The fan levels for SMART mode. The key is the temperature in Celsius, and the value is the fan level."""
	LEVELS = {0: '0', 55: '1', 65: '3', 80: '7', 90: 'disengaged'}
	
	"""The time in seconds between updates of the thermal sensors and fan sensor."""
	UPDATE_INTERVAL = 5
	
	"""Set to true for temperatures to be displayed in Fahrenheit. The keys in COLORS and LEVELS are still given in Celsius, regardless of this property."""
	FAHRENHEIT_OUTPUT = False
