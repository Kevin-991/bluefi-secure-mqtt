# Secure MQTT Communication with BlueFi

## Project Overview

This project implements wireless communication between two HiiBot BlueFi boards using WiFi and MQTT.  
A custom communication protocol is designed, including command words, data length, encoding format, checksum, and simple encryption.

## Hardware

- HiiBot BlueFi × 2
- WiFi router or mobile hotspot
- Computer for serial debugging

## Software

- CircuitPython 9.2.8
- MQTT protocol
- Python libraries for BlueFi

## System Design

Board A publishes encrypted command messages.  
Board B subscribes to the topic, decrypts the message, verifies checksum, and executes the command.

## Features

- WiFi communication
- MQTT publish/subscribe mechanism
- Custom command protocol
- Checksum verification
- Simple encryption
- Serial debug output

## Demo

Add images or video links here.

## My Role

I designed the communication protocol, wrote the code for both boards, tested the MQTT connection, and solved communication failure issues during debugging.

## Results

The two BlueFi boards successfully exchanged messages through MQTT.
