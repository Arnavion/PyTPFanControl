#!/usr/bin/python3

import os

from PySide.QtCore import Qt

class Settings:
	SENSOR_NAMES = ('cpu', 'aps', 'crd', 'gpu', 'no5', 'x7d', 'bat', 'x7f', 'bus', 'pci', 'pwr', 'xc3')
	HIDDEN_TEMPS = {'no5', 'x7d', 'x7f', 'xc3'}
	COLORS = {0: Qt.GlobalColor.cyan, 55: Qt.GlobalColor.yellow, 65: Qt.GlobalColor.magenta, 90: Qt.GlobalColor.red}
	LEVELS = {45: '0', 55: '1', 65: '3', 80: '7', 90: 'disengaged'}
	UPDATE_INTERVAL = 5
	
	if not os.path.isdir('/sys/class/power_supply/BAT0'):
		HIDDEN_TEMPS.add('bat')
