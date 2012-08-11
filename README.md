PyTPFanControl is a Linux clone of troubadix's TPFanControl. It uses the procfs interface exposed by the thinkpad-acpi kernel module to allow you to monitor and control the temperature and fan speeds of your Thinkpad.

### Usage
    /path/to/tpfc.py

This will run the script without superuser rights. The script cannot modify the fan speed without write access to the kernel interface, so the controls for modifying the fan speed will be locked.

    gksu /path/to/tpfc.py    OR    kdesu /path/to/tpfc.py

This will run the script with superuser rights, so you can also set the fan speed.

### Requirements
- thinkpad-acpi in your kernel
- PySide

### Notes
- The script currently has the names of sensors hard-coded to work for the T61.
- SMART mode (custom fan speeds according to temperature) isn't implemented yet, but manual mode is.