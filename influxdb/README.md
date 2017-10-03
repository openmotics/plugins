# InfluxDB client

An InlfuxDB client plugin, sending various data to an InfluxDB instance.

## Configuration

```
config_description = [{'name': 'url',
                       'type': 'str',
                       'description': 'The enpoint for the InfluxDB using HTTP. E.g. http://1.2.3.4:8086'},
                      {'name': 'database',
                       'type': 'str',
                       'description': 'The InfluxDB database name to witch statistics need to be send.'},
                      {'name': 'intervals',
                       'type': 'section',
                       'description': 'Optional interval overrides',
                       'repeat': True,
                       'min': 0,
                        'content': [{'name': 'component', 'type': 'str'},
                                    {'name': 'interval', 'type': 'int'}]},
                       {'name': 'tags',
                        'type': 'section',
                        'description': 'Additional tags which are added based on the name of a power sensor',
                        'repeat': True,
                        'min': 0,
                        'content': [{'name': 'name',
                                     'type': 'str',
                                     'description': 'name of the power input'},
                                    {'name': 'tags',
                                     'type': 'section',
                                     'repeat': True,
                                     'description': 'Key/Value pairs indicating the additional tags to be added for the selected name. Don\'t use name, type or id as key',
                                     'content': [{'name': 'tag key',
                                                  'type': 'str',
                                                  'description': 'tag key'},
                                                 {'name': 'tag value',
                                                  'type': 'str',
                                                  'description': 'tag value'}]},
                                   ]
                       }]
```

The ```url``` and ```database``` parameters are self-explaining. The ```intervals``` parameter allows to override
the build-in intervals on which data will be pushed. The components are documented below, the interval is the frequency
(in seconds) with which the data should be sent (approximately). The ```tags``` parameter allows to add additional tags to the power metrics. As such you can add additional logical tags to your measurements linked to the name of the sensor. More detail and an example is provided below.

## Data

All data is send using the [Line Protocol](https://influxdb.com/docs/v1.0/write_protocols/line.html):

### Outputs

When an output is changed (on, off or changed dimmer value), the data is send to InfluxDB. At a configurable (name
```outputs```, default```60```) interval, all data is send again. So if for some reason a state change would have been
missed, it will be corrected after that moment.

* *key*: 'output', comma separated with following extra tags:
  * *id*: id of the output
  * *name*: name of the output - this one is mandatory for an output to be send to InfluxDB
  * *module_type*: either 'dimmer' or 'output', referring to the module providing the output
  * *type*: either 'relay' or 'light', as configured in the interface
  * *floor*: the floor to which an output is assigned
* *fields*:
  * *value*: integer number of the level of the output. 0, 100 or a value between 0 and 100 in case of a dimmer

Example:

```
output,id=12,name=kitchen,module_type=dimmer,type=light value=12i
```

### Inputs

When an input is pressed, the input press is send to InfluxDB by sending a boolean TRUE value for that input. This
is considered an 'event'

* *key*: 'event', comma separated with following extra tags:
  * *id*: id of the input
  * *name*: name of the input - this one is mandatory for an input to be send to InfluxDB
  * *type*: 'input' - Since multiple events might be used (in the future)
* *fields*:
  * *value*: boolean TRUE

Example:

```
input,id=3,name=doorbell,type=input value=true
```

### System

At a configurable interval (name ```system```, default ```60```) the plugin will send system information to
InfluxDB.

* *key*: 'system', comma separated with following extra tags:
  * *name*: 'gateway'
* *fields*:
  * *service_uptime*: amount (float) of seconds the service (plugin) is running
  * *system_uptime*: amount (float) of seconds the system is running

Example:

```
system,name=gateway service_uptime=145.3,system_uptime=43356.2
```

### Sensors

At a configurable interval (name ```sensors```, default ```60```), all sensor data (where available) is send to InfluxDB.

* *key*: 'sensor', comma separated with following extra tags:
  * *id*: id of the sensor
  * *name*: name of the sensor - this one is mandatory for a sensor to be send to InfluxDB
* *fields*:
  * *temp*: temperature (float) value of the sensor, omitted if not available for that sensor
  * *hum*: relative humidity (float) value of the sensor, omitted if not available for that sensor
  * *bright*: brightness (float) value of the sensor, omitted if not available for that sensor

Example:

```
sensor,id=5,name=outdoors temp=8.5,hum=83.5,bright=23.0
```

### Thermostats

At a configurable interval (name ```thermostats```, default ```60```), thermostat information is send to InfluxDB.

* *key*: 'thermostat', comma separated with following extra tags:
  * *id*: id of the thermostat:
    * G.0 for global thermostat information
    * H.*xx* for heating thermostat *xx*
    * C.*xx* for cooling thermostat *xx*
  * *name*: name of the thermostat
* *fields*:
  * Global thermostat:
    * *on*: whether the global thermostat is on (boolean) or not
    * *cooling*: whether the global thermostat mode is on cooling (true) or heating (false) (boolean)
  * Heating/cooling thermostats:
    * *setpoint*: setpoint id (integer) of the thermostat. ```0```-```2``` for day/night temperatures, ```3``` for away, ```4``` for vacation and ```5``` for party
    * *output0*: id of the primary output (integer) of the thermostat. *255* if not in use
    * *output1*: id of the secondairy output (integer) of the thermostat. *255* if not in use
    * *outside*: outside temperature (float)
    * *mode*: thermostat mode (integer). See the wiki for more information
    * *type*: thermostat type (string). ```tbs``` indicate "time based switching", ```normal``` otherwise
    * *automatic*: indicates (boolean) whether the thermostat is on automatic mode
    * *current_setpoint*: the current setpoint (float)
    * *temperature*: the current temperature of the linked sensor (only in ```normal``` mode)

Example:

```
thermostat,id=G.0,name=Global\ thermostat on=true,cooling=false
thermostat,id=H.12,name=Living setpoint=0,output0=12,output1=255,outside=8.5,mode=7,type=normal,automatic=true,current_setpoint=22,temperature=21.5
```

### Errors

At a configurable interval (name ```errors```, default ```120```), module error statistics are send to InfluxDB.

* *key*: 'error', comma separated with following extra tags:
  * *type*: one of 'Input', 'Temperature', 'Output', 'Dimmer', 'Shutter', 'OLED'
  * *id*: the module ID
  * *name*: the concatination from the type and the id
* *fields*:
  * *value*: amount (integer) of errors for this module

Example:

```
error,type=Input,id=2,name=Input\ 2 value=2i
```

### Pulse counters

At a configurable interval (name ```pulsecounters```, default ```30```), pulse counters are send to InfluxDB.

* *key*: 'counter', comma separated with following extra tags:
  * *name*: name of the pulse counter - this one is mandatory for a pulse counter to be send to InfluxDB
  * *input*: id of the input that drives the pulse counter
* *fields*:
  * *value*: counter (integer)

Example:

```
counter,name=water,input=2 value=274533i
```

### Power (OpenMotics - Power Module or Energy Module)

At a configurable interval (name ```power_openmotics```, default ```10```), power data is send to InfluxDB.

* *key*: 'energy', comma separated with following extra tags:
  * *type*: 'openmotics'
  * *id*: concatenation of the module address and power input
  * *name*: name of the power input - this one is mandatory for a power input to be send to InfluxDB
* *fields*:
  * *voltage*: the voltage corresponding with the CT (in Volt, RMS)
  * *current*: the current measured on the CT (in Ampere, RMS)
  * *frequency*: frequency of the voltage (net frequency)
  * *power*: real power (not the apparent power - it takes phase shifting into account. In Watt)
  * *counter*: total consumed power (in Watt-hours)
  * *counter_day*: total consumed power during day-time (in Watt-hours)
  * *counter_night*: total consumed power during nigt-time (in Watt-hours)

Example:

```
energy,type=openmotics,id=E8.2,name=Dryer voltage=231.5,current=2.12,frequency=49.99,power=482.3,counter=5024.0,counter_day2500.0,couner_night=2524.0
```

### Power analytics (OpenMotics - Energy Module)

At a configurable interval (name ```power_openmotics_analytics```, default ```60```), detailled power analytics data is send to InfluxDB.

Harmonics:

* *key*: 'energy_analytics', comma separated with following extra tags:
  * *type*: 'frequency',
  * *id*: concatenation of the module address and power input
  * *name*: name of the power input - this one is mandatory for a power input to be send to InfluxDB
* *fields*:
  * *current_harmonics*: the current harmonics of the corresponding CT
  * *current_phase*: the current phase of the corresponding CT
  * *voltage_harmonics*: the voltage harmonics of the corresponding CT
  * *voltage_phase*: the voltage phase of the corresponding CT

Time based information (So called oscilloscope view)

* *key*: 'energy_analytics', comma separated with following extra tags:
  * *type*: 'time',
  * *id*: concatenation of the module address and power input
  * *name*: name of the power input - this one is mandatory for a power input to be send to InfluxDB
* *fields*:
  * *voltage*: the voltage component of the corresponding CT sample
  * *current*: the current component of the corresponding CT sample

The data send is of a full period of the net frequency in 80 samples. 50Hz = 20ms, so every sample is separated by 250us. For display purposes,
the sample separation is increased by a factor of 1000, so in InfluxDB, every sample will be 250ms apart.

### Power (Fibaro - If the Fibaro plugin is installed and devices reporting power are found)

At a configurable interval (name ```power_fibaro```, default ```15```), power data is send to InfluxDB.

* *key*: 'energy', comma separated with the following extra tags:
  * *type*: 'fibaro'
  * *id*: deviceID from the Fibaro system
  * *name*: name of the device - this one is mandatory for power to be send to InfluxDB
* *fields*:
  * *power*: the power as reported by the device (in Watt)
  * *counter*: the total power consumed by the device (in Watt-hours)

Example:

```
energy,type=fibaro,id=13,name=xbox360 power=253.4,counter=58223.0
```

### Additional tags on power metrics

Suppose you have multiple power sensors deployed, possibly across multiple modules. By default, only 3 tags are added to your measurement:

* type: hardcoded to openmotics
* name: the name you chose for this power sensor
* id: the device ID

Without any additional tags, you can only encode additional metadata in the name and afterwards use regular expressions within influxdb to create more powerful queries. By adding additional tags, writing such queries becomes much easier and straight forward.

Imagine you have several measuring points for a single room. Some are outlets, others on lights. Or you have multiple lines covering a single device (multi phase). You can now add additional tags to each measurement, encoding the actual location or a device name.

As an example: have a house with 2 floors, each floor has 2 rooms. Every room has 2 sensors, one for all outlets and one covering all lights. The sensors are named according to their position on the module, e.g., no information encoded in the name. We could now add tags to the sensors. 

sensor_1, room=kitchen, floor=groundfloor, category=outlet
sensor_2, room=kitchen, floor=groundfloor, category=light
sensor_3, room=badroom, floor=upper, category=outlet
sensor_3, room=bedroom, floor=upper, category=light

In influxdb, we now have the power to calculate overall light consumption or get the values for the entire groundfloor. 

Tag name and tag value can be specified independently for each sensor.


