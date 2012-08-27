#!/usr/bin/python3

import errno
import sys

from settings import Settings

class ACPI:
	def __init__(self, path):
		self._path = path
	
	def read(self):
		with open(self._path) as f:
			return {parts[0]: parts[2].strip() for parts in (line.partition(':') for line in f)}
	
	hwmonPath = '/sys/devices/platform/thinkpad_hwmon/'

class Temperatures:
	def read(self):
		result = {}
		for (i, name) in enumerate(Settings.sensorNames):
			try:
				with open(ACPI.hwmonPath + '/temp%s_input' % (i + 1)) as f:
					result[name] = int(f.read().rstrip()) // 1000
			except IOError as e:
				if e.errno != errno.ENXIO:
					raise
		
		return result

class Fan:
	def __init__(self):
		try:
			with open(Fan._pwmEnablePath, 'w'):
				self._isWritable = True
				with open(Fan._watchdogPath, 'w') as f:
					f.write(str(Settings.updateInterval * 2))
		except IOError as e:
			if e.errno == errno.EACCES:
				self._isWritable = False
			else:
				raise
	
	def read(self):
		result = {}
		
		with open(Fan._fanInputPath) as f:
			result['speed'] = f.read().rstrip()
		
		with open(Fan._pwmEnablePath) as f:
			pwmMode = f.read().rstrip()
			if pwmMode == '0':
				result['level'] = 'full-speed'
			
			elif pwmMode == '1':
				with open(Fan._pwmPath) as f2:
					result['level'] = Fan._hwmonToFirmware[f2.read().rstrip()]
			
			elif pwmMode == '2':
				result['level'] = 'auto'
		
		return result
	
	def isWritable(self):
		return self._isWritable
	
	def setLevel(self, level):
		if self._isWritable:
			if level == 'auto':
				with open(Fan._pwmEnablePath, 'w') as f:
					f.write('2')
			
			elif level == 'full-speed':
				with open(Fan._pwmEnablePath, 'w') as f:
					f.write('0')
			
			else:
				with open(Fan._pwmEnablePath, 'w') as f:
					f.write('1')
				with open(Fan._pwmPath, 'w') as f:
					f.write(Fan._firmwareToHwmon[level])
	
	_fanInputPath = ACPI.hwmonPath + 'fan1_input'
	_pwmEnablePath = ACPI.hwmonPath + 'pwm1_enable'
	_pwmPath = ACPI.hwmonPath + 'pwm1'
	_watchdogPath = ACPI.hwmonPath + 'driver/fan_watchdog'
	_firmwareToHwmon = {str(i): str(level) for (i, level) in enumerate((0, 36, 72, 109, 145, 182, 218, 255))}
	_hwmonToFirmware = {v: k for (k, v) in _firmwareToHwmon.items()}

class Battery(ACPI):
	def __init__(self):
		super().__init__('/proc/acpi/battery/BAT0/state')
