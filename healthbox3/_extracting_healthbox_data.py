
import requests


response = {
    "device_type": "HEALTHBOX3",
    "description": "Healthbox 3.0",
    "serial": "someSerialNumber",
    "warranty_number": "WARRANTY",
    "global": {
        "parameter": {
            "device name": {
                "unit": "",
                "value": "HEALTHBOX3[WARRANTY]"
            },
            "legislation country": {
                "unit": "",
                "value": "be"
            },
            "warranty": {
                "unit": "",
                "value": "WARRANTY"
            }
        }
    },
    "room": {
        "1": {
            "name": "Laundry room",
            "type": "LaundryRoom",
            "parameter": {
                "doors_open": {
                    "unit": "",
                    "value": False
                },
                "doors_present": {
                    "unit": "",
                    "value": False
                },
                "icon": {
                    "unit": "",
                    "value": ""
                },
                "measured_power": {
                    "unit": "",
                    "value": -1.0
                },
                "measured_voltage": {
                    "unit": "",
                    "value": -1.0
                },
                "measurement": {
                    "unit": "",
                    "value": -1.0
                },
                "offset": {
                    "unit": "",
                    "value": 0.0
                },
                "subzone": {
                    "unit": "",
                    "value": "[]\n"
                },
                "valve": {
                    "unit": "",
                    "value": "1"
                },
                "valve_warranty": {
                    "unit": "",
                    "value": ""
                },
                "nominal": {
                    "unit": "m³/h",
                    "value": 50.0
                }
            },
            "profile_name": "health",
            "actuator": [
                {
                    "name": "air valve[1]_HealthBox 3[Healthbox3]",
                    "type": "air valve",
                    "basic_id": 1,
                    "parameter": {
                        "flow_rate": {
                            "unit": "m³/h",
                            "value": 250.0
                        }
                    }
                }
            ],
            "sensor": [
                {
                    "basic_id": 1,
                    "name": "indoor temperature[1]_HealthBox 3[Healthbox3]",
                    "parameter": {
                        "temperature": {
                            "unit": "deg C",
                            "value": 23.08836181640624
                        }
                    },
                    "type": "indoor temperature"
                },
                {
                    "basic_id": 1,
                    "name": "indoor relative humidity[1]_HealthBox 3[Healthbox3]",
                    "parameter": {
                        "humidity": {
                            "unit": "pct",
                            "value": 30.2701416015625
                        }
                    },
                    "type": "indoor relative humidity"
                },
                {
                    "basic_id": 1,
                    "name": "indoor air quality index[1]_HealthBox 3[Healthbox3]",
                    "parameter": {
                        "index": {
                            "unit": "",
                            "value": 46.66332026222561
                        },
                        "main_pollutant": {
                            "unit": "",
                            "value": "indoor relative humidity"
                        }
                    },
                    "type": "indoor air quality index"
                }
            ]
        },
        "2": {
            "name": "Bathroom with toilet",
            "type": "BathRoom",
            "parameter": {
                "icon": {
                    "unit": "",
                    "value": ""
                },
                "measurement": {
                    "unit": "",
                    "value": -1.0
                },
                "offset": {
                    "unit": "",
                    "value": 0.0
                },
                "subzone": {
                    "unit": "",
                    "value": "[]\n"
                },
                "valve": {
                    "unit": "",
                    "value": "2"
                },
                "valve_warranty": {
                    "unit": "",
                    "value": "I4O709530001A47"
                },
                "nominal": {
                    "unit": "m³/h",
                    "value": 50.0
                }
            },
            "profile_name": "health",
            "actuator": [
                {
                    "name": "air valve[2]_HealthBox 3[Healthbox3]",
                    "type": "air valve",
                    "basic_id": 2,
                    "parameter": {
                        "flow_rate": {
                            "unit": "m³/h",
                            "value": 15.0
                        }
                    }
                }
            ],
            "sensor": [
                {
                    "basic_id": 2,
                    "name": "indoor temperature[2]_HealthBox 3[Healthbox3]",
                    "parameter": {
                        "temperature": {
                            "unit": "deg C",
                            "value": 23.94789044022278
                        }
                    },
                    "type": "indoor temperature"
                },
                {
                    "basic_id": 2,
                    "name": "indoor relative humidity[2]_HealthBox 3[Healthbox3]",
                    "parameter": {
                        "humidity": {
                            "unit": "pct",
                            "value": 27.403677424277104
                        }
                    },
                    "type": "indoor relative humidity"
                },
                {
                    "basic_id": 2,
                    "name": "indoor volatile organic compounds[2]_HealthBox 3[Healthbox3]",
                    "parameter": {
                        "concentration": {
                            "unit": "ppm",
                            "value": 878.5087565134127
                        },
                        "concentration_maximum": {
                            "unit": "ppm",
                            "value": 1730.395470712454
                        },
                        "raw": {
                            "unit": "ppm",
                            "value": 27098.0
                        }
                    },
                    "type": "indoor volatile organic compounds"
                },
                {
                    "basic_id": 2,
                    "name": "indoor air quality[2]_HealthBox 3[Healthbox3]",
                    "parameter": {
                        "co2": {
                            "unit": "ppm",
                            "value": 123456789.0
                        },
                        "concentration": {
                            "unit": "ppm",
                            "value": 01234567.89
                        },
                        "resistance": {
                            "unit": "ohm",
                            "value": 191629.0
                        },
                        "voc": {
                            "unit": "ppb",
                            "value": 178.0
                        }
                    },
                    "type": "indoor air quality"
                },
                {
                    "basic_id": 2,
                    "name": "indoor air quality index[2]_HealthBox 3[Healthbox3]",
                    "parameter": {
                        "index": {
                            "unit": "",
                            "value": 60.53146499210699
                        },
                        "main_pollutant": {
                            "unit": "",
                            "value": "indoor relative humidity"
                        }
                    },
                    "type": "indoor air quality index"
                }
            ]
        }
    },
    "sensor": [
        {
            "name": "global air quality index",
            "type": "global air quality index",
            "basic_id": 0,
            "parameter": {
                "index": {
                    "unit": "",
                    "value": 58.89601160589506
                },
                "main_pollutant": {
                    "unit": "",
                    "value": "indoor relative humidity"
                },
                "room": {
                    "unit": "",
                    "value": "Bathroom with toilet"
                }
            }
        }
    ]
}

# recursion to loop over dictionaries
def myprint(d):
    for k, v in d.items():
        if isinstance(v, dict):
            myprint(v)
        else:
            print("{0} : {1}".format(k, v))

def unravel(data, prev_title=""):
    # recursion function to find all the key value pairs
    if isinstance(data, dict): # check if dictionary
        for key, value in data.items(): # loop over dict
            if not isinstance(value, list) and not isinstance(value, dict):
                print("{0} {1} : {2} \n".format(prev_title, key, value))
            else:
                prev_title = prev_title + " : " + key + " : "
                unravel(value, prev_title) # if list or dict, recurse into function
    elif isinstance(data, list): # check if list
        for i in data: # loop over list
            unravel(i) # if list or dict, recurse into function


def _print_dataframe(
                 identifier,
                 name,
                 value,
                 unit=None,
                 description=None,
                 room=None,
                 ):
    print("sensor\n\tidentifier: {}\n\tname: {}\n\tvalue: {}\n\tunit: {}\n\tdescription: {}\n\troom: {}".format(identifier, name, value, unit, description, room))

def _extract_data(data):
    # a lot of boilerplate to be able to get the information out of the healthbox in a usable manner

    # get general (unnested) information
    for key, value in data.items():
        if not isinstance(value, list) and not isinstance(value, dict): # filtering out nested dicts and lists
            _print_dataframe(identifier=key, name=key, value=value)

    # get global information
    for key, value in data['global']['parameter'].items():
        _print_dataframe(identifier=key, name=key, value=value['value'])

    # get global sensor information
    for sensor in data['sensor']:
        identifier = str(sensor['basic_id']) + ' - ' + str(sensor['name'])
        _print_dataframe(identifier=identifier, name=sensor['type'], value=sensor['parameter']['index']['value'], unit=sensor['parameter']['index']['unit'], room=sensor['basic_id'])



    # get sensor per room information
    for key, roomnr in data['room'].items(): # loop over the available rooms
        for sensor in roomnr['sensor']: # dive into sensors per room
            # jump into parameter -> first dict in this dict -> get unit and value
            for key, value in sensor['parameter'].items():
                sub_key   = key
                sub_value = value['value']
                sub_unit  = value['unit']
                identifier = str(sensor['basic_id']) + ' - ' +  str(sensor['name'] + ' - ' + str(sub_key))
                _print_dataframe(identifier=identifier, name=sensor['type'], value=sub_value, unit=sub_unit, room=sensor['basic_id'])

ip = "someIP"
# response = requests.get("http://{}/v2/api/data/current".format(ip)).json()
_extract_data(response)