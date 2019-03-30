# Python MySmartBlinds Smart Bridge Client

[![PyPI version](https://badge.fury.io/py/smartblinds-client.svg)](https://badge.fury.io/py/smartblinds-client)
[![Build Status](https://travis-ci.org/ianlevesque/smartblinds-client.svg?branch=master)](https://travis-ci.org/ianlevesque/smartblinds-client)

This is an unofficial client for the [MySmartBlinds Smart Bridge](https://www.mysmartblinds.com/products/smart-hub). You 
must have configured your blinds and bridge with the official iOS or Android app first in order to use this.

USE AT YOUR OWN RISK.

## Usage

```python

from smartblinds_client import SmartBlindsClient

client = SmartBlindsClient("email", "password")
client.login()

blinds, rooms = client.get_blinds_and_rooms()
print(blinds)
print(rooms)
print(blinds[0].name)

states = client.get_blinds_state(blinds)
print(states[blinds[0].encoded_mac].position)

client.set_blinds_position(blinds, 100)

```
