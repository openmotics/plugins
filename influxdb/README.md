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
                                   {'name': 'interval', 'type': 'int'}]}]
```

The ```url``` and ```database``` parameters are self-explaining. The ```intervals``` parameter allows to override
the build-in intervals on which data will be pushed. The components are documented below, the interval is the frequency
(in seconds) with which the data should be sent (approximately).

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
