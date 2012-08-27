#!/usr/bin/python3

import errno
import os
import sys

from settings import Settings

class ACPI:
	hwmonPath = '/sys/devices/platform/thinkpad_hwmon/'

class Temperatures:
	def read():
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
	def read():
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
	
	def isWritable():
		return Fan._isWritable
	
	def setLevel(level):
		if Fan._isWritable:
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
	
	try:
		with open(_pwmEnablePath, 'w'):
			_isWritable = True
			with open(_watchdogPath, 'w') as f:
				f.write(str(Settings.updateInterval * 2))
	except IOError as e:
		if e.errno == errno.EACCES:
			_isWritable = False
		else:
			raise

class Battery:
	def isPluggedIn():
		return os.path.isdir('/sys/class/power_supply/BAT0')
