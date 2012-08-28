#!/usr/bin/python3

import collections
import errno
import sys

from settings import Settings

class ACPI:
	HWMON_PATH = '/sys/devices/platform/thinkpad_hwmon/'

class Temperatures:
	def read():
		result = {}
		for (i, name) in enumerate(Settings.SENSOR_NAMES):
			try:
				with open(ACPI.HWMON_PATH + '/temp%s_input' % (i + 1)) as f:
					result[name] = int(f.read().rstrip()) // 1000
			except IOError as e:
				if e.errno != errno.ENXIO:
					raise
		
		return result

class Fan:
	def read():
		with open(Fan.FAN_INPUT_PATH) as f:
			speed = f.read().rstrip()
		
		with open(Fan.PWM_ENABLE_PATH) as f:
			pwmMode = f.read().rstrip()
			if pwmMode == '0':
				level = 'full-speed'
			
			elif pwmMode == '1':
				with open(Fan.PWM_PATH) as f2:
					level = Fan.HWMON_TO_FIRMWARE[f2.read().rstrip()]
			
			elif pwmMode == '2':
				level = 'auto'
		
		return Fan.FanResult(speed, level)
	
	def isWritable():
		return Fan._isWritable
	
	def setLevel(level):
		if Fan._isWritable:
			if level == 'auto':
				with open(Fan.PWM_ENABLE_PATH, 'w') as f:
					f.write('2')
			
			elif level == 'full-speed':
				with open(Fan.PWM_ENABLE_PATH, 'w') as f:
					f.write('0')
			
			else:
				with open(Fan.PWM_ENABLE_PATH, 'w') as f:
					f.write('1')
				with open(Fan.PWM_PATH, 'w') as f:
					f.write(Fan.FIRMWARE_TO_HWMON[level])
	
	FAN_INPUT_PATH = ACPI.HWMON_PATH + 'fan1_input'
	PWM_ENABLE_PATH = ACPI.HWMON_PATH + 'pwm1_enable'
	PWM_PATH = ACPI.HWMON_PATH + 'pwm1'
	WATCHDOG_PATH = ACPI.HWMON_PATH + 'driver/fan_watchdog'
	FIRMWARE_TO_HWMON = {str(i): str(level) for (i, level) in enumerate((0, 36, 72, 109, 145, 182, 218, 255))}
	HWMON_TO_FIRMWARE = {v: k for (k, v) in FIRMWARE_TO_HWMON.items()}
	
	try:
		with open(PWM_ENABLE_PATH, 'w'):
			_isWritable = True
			with open(WATCHDOG_PATH, 'w') as f:
				f.write(str(Settings.UPDATE_INTERVAL * 2))
	except IOError as e:
		if e.errno == errno.EACCES:
			_isWritable = False
		else:
			raise
	
	FanResult = collections.namedtuple('FanResult', ['speed', 'level'])
