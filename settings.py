#!/usr/bin/python3

from PySide.QtCore import Qt

class Settings:
	sensorNames = ('cpu', 'aps', 'crd', 'gpu', 'no5', 'x7d', 'bat', 'x7f', 'bus', 'pci', 'pwr', 'xc3')
	hiddenTemps = set(('no5', 'x7d', 'x7f', 'xc3'))
	colors = {0: Qt.GlobalColor.cyan, 55: Qt.GlobalColor.yellow, 65: Qt.GlobalColor.magenta, 90: Qt.GlobalColor.red}
	levels = {45: '0', 55: '1', 65: '3', 80: '7', 90: 'disengaged'}
	updateInterval = 5
