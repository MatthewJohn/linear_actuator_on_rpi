#!/usr/bin/python3


# chip L298N
# http://howtomechatronics.com/tutorials/arduino/arduino-dc-motor-control-tutorial-l298n-pwm-h-bridge/
# http://www.instructables.com/id/Arduino-Modules-L298N-Dual-H-Bridge-Motor-Controll/
# export PYTHONPATH=~/.local/lib/python2.7/
# try gpio readall for pinouts
# mount devpi locally
# sshfs -o idmap=user,nonempty pi@192.168.0.41:/home/pi ~/system/configurations/pi/remote/devpi/
# sync
# while true;do rsync -avh --progress --delete /home/nick/system/configurations/pi/code/door_control ~/system/configurations/pi/remote/devpi/;sleep 5;done
# run on remote
# clear; echo "" > /var/log/automation/pi.log ;./garage_control.py
# monitor log on pi
# watch cat /var/log/automation/pi.log


# TODO
# create pip requirements doc, install with ansible?
# add logging

# import sys
import RPi.GPIO as GPIO
import time
import logging
import garage_automation
from garage_automation.sensors import Sensors
from garage_automation.indicators import Indicators


configs = {
    'over_current_threshold': 1000,  # milliamps
    'actuator_full_stroke_duration': 20,  # seconds
    'led_red_pin': 8,
    'led_green_pin': 10
}
# globals, move to configs class?
actuator_pin_forwards = 24
actuator_pin_backwards = 26
switch_input = 7
bolts_closed_sensor = 11
# bolts_open_sensor = 13 can probably just assume this?
door_closed_sensor = 15


# ansible defines this log path
logging.basicConfig(format='%(asctime)s %(message)s', filename='/var/log/automation/pi.log', level=logging.DEBUG)
# logging.debug('This message should go to the log file')
logging.info('Script startup')
# logging.warning('And this, too')


try:
    GPIO.setmode(GPIO.BOARD)

    GPIO.setup(switch_input, GPIO.IN)
    GPIO.setup(bolts_closed_sensor, GPIO.IN)
    # GPIO.setup(bolts_open_sensor, GPIO.IN)
    GPIO.setup(door_closed_sensor, GPIO.IN)

    GPIO.setup(actuator_pin_backwards, GPIO.OUT)
    GPIO.setup(actuator_pin_forwards, GPIO.OUT)
    # make sure actuator pins are deactivated
    GPIO.output(actuator_pin_forwards, GPIO.LOW)
    GPIO.output(actuator_pin_backwards, GPIO.LOW)

    GPIO.setup(configs['led_green_pin'], GPIO.OUT)
    GPIO.setup(configs['led_red_pin'], GPIO.OUT)
    # make sure LED's are in default alarm/not ready state
    GPIO.output(configs['led_green_pin'], GPIO.LOW)
    GPIO.output(configs['led_red_pin'], GPIO.HIGH)


except Exception as e:
    logging.error("RuntimeError problem with GPIO init")
    logging.debug("exception:" + str(e))
    GPIO.cleanup()

try:
    indicators = Indicators(logging, GPIO, configs)
    sensors = Sensors(logging, bolts_closed_sensor)
    actuator = garage_automation.Actuator(logging, GPIO, actuator_pin_forwards, actuator_pin_backwards)
    control = garage_automation.Control(logging, actuator, sensors, indicators, configs)
except Exception as e:
    logging.error("ERROR initialising control classes")
    logging.debug("exception:" + str(e))
    GPIO.cleanup()


# Use BCM GPIO references
# instead of physical pin numbers
#GPIO.setmode(GPIO.BCM)
# mode = GPIO.getmode()
# print " mode =" + str(mode)

try:
    while True:
        # switch pulls low so we need to look for inverted state, slightly confusing
        if not GPIO.input(switch_input):
            control.change_state()
        # no interupts on the pi so we need to monitor the switch pin, better with threads?
        # https://stackoverflow.com/questions/22180915/non-polling-non-blocking-timer
        # http://raspi.tv/2013/how-to-use-interrupts-with-python-on-the-raspberry-pi-and-rpi-gpio-part-3

        control.check_lock_state()

        time.sleep(1)

except KeyboardInterrupt as e:
    logging.warning('Cought KeyboardInterrupt' + str(e))
except Exception as e:
    logging.error("ERROR Unhandled exception")
    logging.debug("Exception type", e.__class__.__name__)
    exit()

finally:
    GPIO.cleanup()
    logging.info("Garage Automation daemon terminating. GPIO cleaned up")
