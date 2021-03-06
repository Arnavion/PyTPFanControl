import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor


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
	COLORS = {0: Qt.cyan, 45: Qt.yellow, 65: QColor('orange'), 90: Qt.red}
	
	"""The fan levels for SMART mode. The key is the temperature in Celsius, and the value is the fan level."""
	LEVELS = {0: '0', 45: '1', 65: '3', 80: '7', 90: 'full-speed'}
	
	"""The time in seconds between updates of the thermal sensors and fan sensor."""
	UPDATE_INTERVAL = 5
	
	"""Set to ```True``` for temperatures to be displayed in Fahrenheit. The keys in COLORS and LEVELS are still given in Celsius, regardless of this property."""
	FAHRENHEIT_OUTPUT = False
	
	"""Set to ```True``` if you want temperatures to be rounded to the nearest degree, or to ```False``` to have them be truncated."""
	ROUND_TEMPS = False
