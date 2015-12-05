# InfluxDB client

An InlfuxDB client plugin, sending various data to an InfluxDB instance.

## Todo

* Send sensor data (temperature/humidity/brightness)
* Send power data (from energy modules and/or pulse counters

## Configuration

```
config_description = [{'name': 'url',
                       'type': 'str',
                       'description': 'The enpoint for the InfluxDB using HTTP. E.g. http://1.2.3.4:8086'},
                      {'name': 'database',
                       'type': 'str',
                       'description': 'The InfluxDB database name to witch statistics need to be send.'}]
```

## Data

All data is send using the [Line Protocol](https://influxdb.com/docs/v0.9/write_protocols/line.html):

### Outputs

When an output is changed (on, off or changed dimmer value), the data is send to InfluxDB. At a one minute interval,
all data is send again. So if for some reason a state change would have been missed, it will be corrected after a minute

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

When an input is pressed, the input press is send to InfluxDB by sending a boolean TRUE value for that input, and after
one second a boolean FALSE value. At this moment, the time the input is actually pressed is not taken into account

* *key*: 'input', comma separated with following extra tags:
  * *id*: id of the input
  * *name*: name of the input - this one is mandatory for an input to be send to InfluxDB
* *fields*:
  * *value*: boolean TRUE or FALSE

Example:

```
input,id=3,name=doorbell value=true
```

### Sensors

At a one minute interval, all sensor data (where available) is send to InfluxDB.

* *key*: 'sensor', comma separated with following extra tags:
  * *id*: id of the sensor
  * *name*: name of the sensor - this one is mandatory for a sensor to be send to InfluxDB
* *fields*:
  * *temp*: temperature (float) value of the sensor, omitted if not available for that sensor
  * *hum*: relative humidity (float) value of the sensor, omitted if not available for that sensor
  * *bright*: brightness (float) value of the sensor, omitted if not available for that sensor

Example:

```
sensor,id=5,name=outdoors temp=8.5,hum=83.5
```
