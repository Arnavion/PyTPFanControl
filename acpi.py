#!/usr/bin/python3

import collections
import errno
import sys

from settings import Settings

"""Path to the root of the hardware monitoring sysfs interface provided by the thinkpad-acpi kernel module."""
HWMON_PATH = '/sys/devices/platform/thinkpad_hwmon/'


class Temperatures:
	"""
	Functions related to the thermal sensors.
	
	"""
	
	def read():
		"""
		Read the thermal sensors and return a `dict` of sensor name -> sensor temperature in Celsius.
		
		"""
		
		# Prepare the dict
		result = {}
		# Settings.SENSOR_NAMES holds the sensor names in order of the temp*_input files, so match the sensor name to the temperature value from the file in sequence
		for (i, name) in enumerate(Settings.SENSOR_NAMES):
			# Unavailable sensors throw ENXIO, so it's fine to ignore them.
			try:
				with open(HWMON_PATH + '/temp%s_input' % (i + 1)) as f:
					# The value read from the file is in Celsius and multiplied by 1000, so convert it to a normal Celsius value
					result[name] = int(f.read().rstrip()) // 1000
			except IOError as e:
				if e.errno != errno.ENXIO:
					raise
		
		return result
	
	def toDisplayTemp(temp):
		"""
		Convert temp to Fahrenheit if required, and to a `str` suitable for output.
		
		`temp` is either a number obtained from Temperatures.read(), or the string 'n/a'. If it is the latter, it is returned unchanged.
		
		"""
		
		if temp == 'n/a':
			return temp
		
		if Settings.FAHRENHEIT_OUTPUT:
			temp = temp * 9 // 5 + 32
		
		return str(temp)


class Fan:
	"""
	Functions related to the fan.
	
	"""
	
	def read():
		"""
		Read the fan sensor and return a named tuple (speed, level).
		
		`speed` is the fan speed in RPM.
		`level` is the firmware level ('auto', 'full-speed', or 0-7 as a `str`).
		
		"""
		
		# Read the fan speed
		with open(Fan.FAN_INPUT_PATH) as f:
			speed = f.read().rstrip()

		# Read the fan level, and convert it to the displayable string if required
		with open(Fan.PWM_ENABLE_PATH) as f:
			pwmMode = f.read().rstrip()
			if pwmMode == '0':
				level = 'full-speed'
			
			elif pwmMode == '1':
				with open(Fan.PWM_PATH) as f2:
					# The value read from the file is between 0-255, so convert it to the firmware level which is between 0-7
					level = Fan.HWMON_TO_FIRMWARE[f2.read().rstrip()]
			
			elif pwmMode == '2':
				level = 'auto'
		
		return Fan.FanResult(speed, level)
	
	def isWritable():
		"""
		Return `True` if the program is running with enough rights to write to the sysfs interface to be able to change the fan speed.
		
		"""
		
		return Fan._isWritable
	
	def setLevel(level):
		"""
		Set the fan level.
		
		level can be either 'auto', 'full-speed', or one of 0-7 as a `str`.
		
		"""
		
		# Only try writing to the interface if the program can
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
					# Convert the firmware level (0-7) to the hwmon level (0-255) and write it
					f.write(Fan.FIRMWARE_TO_HWMON[level])
	
	# Path of the file with the fan speed
	FAN_INPUT_PATH = HWMON_PATH + 'fan1_input'
	
	# Path of the file with the pwm mode
	PWM_ENABLE_PATH = HWMON_PATH + 'pwm1_enable'
	
	# Path of the file with the fan level
	PWM_PATH = HWMON_PATH + 'pwm1'
	
	# Path of the watchdog file
	WATCHDOG_PATH = HWMON_PATH + 'driver/fan_watchdog'
	
	"""Map of firmware fan levels (0-7) to hwmon levels (0-255)."""
	FIRMWARE_TO_HWMON = {str(i): str(level) for (i, level) in enumerate((0, 36, 72, 109, 145, 182, 218, 255))}
	
	"""Map of hwmon levels (0-255) to firmware fan levels (0-7)."""
	HWMON_TO_FIRMWARE = {v: k for (k, v) in FIRMWARE_TO_HWMON.items()}
	
	# Enable the fan watchdog. The fan watchdog resets the fan to BIOS mode if the fan level is not set for the given time. The watchdog is enabled with a time of two times the update interval.
	try:
		with open(WATCHDOG_PATH, 'w') as f:
			f.write(str(Settings.UPDATE_INTERVAL * 2))
			# If writing to the watchdog file succeeded, it means we can write to the fan level file too
			_isWritable = True
	except IOError as e:
		if e.errno == errno.EACCES:
			_isWritable = False
		else:
			raise
	
	"""
	Hold the fan speed and level, as returned by `Fan.read()`.
	
	`speed` is the fan speed in RPM.
	`level` is the firmware level ('auto', 'full-speed', or 0-7 as a `str`).
	
	"""
	FanResult = collections.namedtuple('FanResult', ['speed', 'level'])
