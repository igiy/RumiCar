#!/usr/bin/python

# MIT License
# 
# Copyright (c) 2017 John Bryan Moore
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITYz, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for full license information.

# Azure IoT Hubサンプル
# D2Cでセンサーから物体までの距離を送信

import random
import time

import sys
sys.path.append('..')

import time
import pigpio
import VL53L0X

# Using the Python Device SDK for IoT Hub:
#   https://github.com/Azure/azure-iot-sdk-python
# The sample connects to a device-specific MQTT endpoint on your IoT Hub.
from azure.iot.device import IoTHubDeviceClient, Message

# The device connection string to authenticate the device with your IoT hub.
# Using the Azure CLI:
# az iot hub device-identity show-connection-string --hub-name {YourIoTHubName} --device-id MyNodeDevice --output table
CONNECTION_STRING = ""

# Define the JSON message to send to IoT Hub.
MSG_TXT = '{{"distance": {distance}, "control": {control}}}'

# 操舵用の設定
LEFT = 0
CENTER = 1
RIGHT = 2

# 走行用の設定
FREE = 0
REVERSE = 1
FORWARD = 2
BRAKE = 3

# DRV8835のピン設定
AIN1 = 17
AIN2 = 27
BIN1 = 18
BIN2 = 13

# PWM周波数
AIN_FREQUENCY = 490
BIN_FREQUENCY = 960

# VL53L0Xのピン設定
SHDN0 = 23
SHDN1 = 24
SHDN2 = 25

pi = pigpio.pi()

# 各GPIOの初期化
pi.set_mode(AIN1, pigpio.OUTPUT)
pi.set_mode(AIN2, pigpio.OUTPUT)
pi.set_mode(BIN1, pigpio.OUTPUT)
pi.set_mode(BIN2, pigpio.OUTPUT)
pi.set_mode(SHDN1, pigpio.OUTPUT)

pi.set_PWM_frequency(AIN1, AIN_FREQUENCY)
pi.set_PWM_frequency(AIN2, AIN_FREQUENCY)

def rc_drive(direc, ipwm):
    if direc == FREE:
        pi.hardware_PWM(BIN1, BIN_FREQUENCY, 0)
        pi.hardware_PWM(BIN2, BIN_FREQUENCY, 0)
    elif direc == REVERSE:
        pi.hardware_PWM(BIN1, BIN_FREQUENCY, 0)
        pi.hardware_PWM(BIN2, BIN_FREQUENCY, ipwm)
    elif direc == FORWARD:
        pi.hardware_PWM(BIN1, BIN_FREQUENCY, ipwm)
        pi.hardware_PWM(BIN2, BIN_FREQUENCY, 0)
    elif direc == BRAKE:
        pi.hardware_PWM(BIN1, BIN_FREQUENCY, ipwm)
        pi.hardware_PWM(BIN2, BIN_FREQUENCY, ipwm)
    else:
        return 0

if __name__ == "__main__":

    client = IoTHubDeviceClient.create_from_connection_string(CONNECTION_STRING)

    # Set all shutdown pins low to turn off each VL53L0X
    pi.write(SHDN1, 0)

    # Keep all low for 500 ms or so to make sure they reset
    time.sleep(0.50)

    # Create one object per VL53L0X
    sensor1 = VL53L0X.VL53L0X(address=0x2D)

    # set SHDN1 to input in order to use VL53L0X's pull-up resistor
    pi.set_mode(SHDN1, pigpio.INPUT)
    time.sleep(0.50)

    # call to start ranging 
    sensor1.start_ranging(VL53L0X.VL53L0X_HIGH_SPEED_MODE)

    timing = sensor1.get_timing()
    if (timing < 20000):
        timing = 20000

    speed = 900000

    while True:
        try:
            distance = sensor1.get_distance()
            control = ''
            if distance < 300:
                if distance > 120:
                    rc_drive(FORWARD, speed)
                    control = 'FORWARD'
                elif distance < 80:
                    rc_drive(REVERSE, speed)
                    control = 'REVERSE'
                else:
                    rc_drive(BRAKE, speed); 
                    control = 'BRAKE'
            else:
                rc_drive(FREE, speed)
                control = 'FREE'
            # Build the message with simulated telemetry values.
            msg_txt_formatted = MSG_TXT.format(distance=distance, control=control)
            message = Message(msg_txt_formatted)
            client.send_message(message)
            time.sleep(timing/1000000.00)
        except KeyboardInterrupt:
            sensor1.stop_ranging()
            pi.write(SHDN0, 0)
            pi.set_mode(BIN1, pigpio.INPUT)
            pi.set_mode(BIN2, pigpio.INPUT)
            pi.stop()

