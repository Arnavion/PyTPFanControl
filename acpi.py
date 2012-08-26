#!/usr/bin/python3

import sys
from settings import Settings

class ACPI:
	def __init__(self, path):
		self._path = path
	
	def read(self):
		f = open(self._path)
		result = {pair[0][:pair[1]]: pair[0][pair[1] + 1:].strip() for pair in ((line, line.index(':')) for line in f)}
		f.close()
		return result

class Temperatures(ACPI):
	def __init__(self):
		super().__init__('/proc/acpi/ibm/thermal')
	
	def read(self):
		return {name: int(temp) for (name, temp) in zip(Settings.sensorNames, super().read()['temperatures'].split())}

class Fan(ACPI):
	def __init__(self):
		super().__init__('/proc/acpi/ibm/fan')
	
	def isWritable(self):
		try:
			f = open(self._path, 'w')
			f.close()
			return True
		except IOError:
			return False
	
	def setLevel(self, level):
		f = open(self._path, 'w')
		f.write('level ' + level)
		f.close()

class Battery(ACPI):
	def __init__(self):
		super().__init__('/proc/acpi/battery/BAT0/state')
