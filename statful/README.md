# Statful client

An Statful client plugin, sending various data to Statful.

## Configuration

```
config_description = [{'name': 'token',
                       'type': 'str',
                       'description': 'Statful API token for authentication.'},
                      {'name': 'add_custom_tag',
                       'type': 'str',
                       'description': 'Add custom tag to statistics'},
                      {'name': 'batch_size',
                       'type': 'int',
                       'description': 'The maximum batch size of grouped metrics to be send to Statful.'}]
```

The ```token``` parameter is self-explaining. The ```custom_tag``` parameter allows to push a tag key `custom_tag` with a user-input value.
The ```batch_size``` parameter defines the maximum size of metrics on a batch. 

## Data

All data is send using the [Metrics Ingestion Protocol](https://www.statful.com/docs/metrics-ingestion-protocol.html#Metrics-Ingestion-Protocol):

### Outputs

When an output is changed (on, off or changed dimmer value), the data is sent to Statful. At a fixed interval (30 seconds), all data is send again. So if for some reason a state change would have been missed, it will be corrected after that moment.

* *key*: 'openmotics.output.value', comma separated with following extra tags:
  * *id*: id of the output
  * *name*: name of the output
  * *module_type*: either 'dimmer' or 'output', referring to the module providing the output
  * *type*: either 'relay' or 'light', as configured in the interface
  * *floor*: the floor to which an output is assigned
* *fields*:
  * *value*: integer number of the level of the output. 0, 100 or a value between 0 and 100 in case of a dimmer

Example:

```
openmotics.output.value,id=12,name=kitchen,module_type=dimmer,type=light 12
```

### Inputs

When an input is pressed, the input press is sent to Statful by sending an integer (1, corresponding to boolean TRUE) value for that input. This is considered an 'event'.

* *key*: 'openmotics.input.value', comma separated with following extra tags:
  * *id*: id of the input
  * *name*: name of the input  
  * *type*: 'input' - Since multiple events might be used (in the future)
* *fields*:
  * *value*: integer 1

Example:

```
openmotics.input.value,id=3,name=doorbell,type=input 1
```

### System

At a fixed interval (30 seconds) the plugin will send system information to Statful.

* *key*: 'openmotics.system.${field_name}', comma separated with following extra tags:
  * *name*: 'gateway'
 
* Support *fields*:
  * *cloud_buffer_length*: length (integer) of the on-disk buffer of metrics to be send to the Cloud
  * *cloud_queue_length*:  length (integer) of the memory queue of metrics to be send to the Cloud
  * *cloud_time_ago_send*: time (seconds) passed since the last time metrics were send to the Cloud
  * *cloud_time_ago_try*: time (seconds) passed since the last try sending metrics to the Cloud
  * *cpu_load_1*: system cpu load over 1 minute
  * *cpu_load_5*: system cpu load over 5 minutes
  * *cpu_load_15*: system cpu load over 15 minutes
  * *cpu_percent*: system cpu percentage
  * *disk_eol_info*: eMMC Pre EOL information
  * *disk_free*: free disk (bytes)
  * *disk_percent*: used disk percentage
  * *disk_read_bytes*: disk read bytes
  * *disk_read_count*: disk read count
  * *disk_total*: total disk size (bytes)
  * *disk_used*: disk used (bytes)
  * *disk_write_bytes*: disk write bytes
  * *disk_write_count*: disk write count
  * *memory_active*: active memory (bytes)
  * *memory_available*: available memory (bytes)
  * *memory_free*: free memory (bytes)
  * *memory_inactive*: inactive memory (bytes)
  * *memory_percent*: used memory percentage
  * *memory_shared*: shared memory (bytes)
  * *memory_total*: total memory (bytes)
  * *memory_used*: used memory (bytes)
  * *metric_interval*: interval on which OM metrics are collected
  * *metrics_in*: inbound metrics processed
  * *metrics_out*: outbound metrics processed
  * *net_bytes_recv*: network bytes received
  * *net_bytes_sent*: network bytes sent
  * *net_packets_recv*: network packets received
  * *net_packets_sent*: network packets sent
  * *queue_length*: metrics queue length
  * *service_uptime*: amount (float) of seconds the service (plugin) is running
  * *system_uptime*: amount (float) of seconds the system is running

Example:

```
openmotics.system.service_uptime,name=gateway 145.3
```

### Sensors

At a fixed interval (30 seconds), all sensor data (where available) is sent to Statful.

* *key*: 'openmotics.sensor.${field_name}', comma separated with following extra tags:
  * *id*: id of the sensor
  * *name*: name of the sensor
  
* Support *fields*:  
  * *temp*: temperature (float) value of the sensor, omitted if not available for that sensor
  * *hum*: relative humidity (float) value of the sensor, omitted if not available for that sensor
  * *bright*: brightness (float) value of the sensor, omitted if not available for that sensor

Example:

```
openmotics.sensor.temp,id=5,name=outdoors 8.5
```

### Thermostats

At a fixed interval (30 seconds), thermostat information is sent to Statful.

* *key*: 'openmotics.thermostat.${field_name}', comma separated with following extra tags:
  * *id*: id of the thermostat:
    * G.0 for global thermostat information
    * H.*xx* for heating thermostat *xx*
    * C.*xx* for cooling thermostat *xx*
  * *name*: name of the thermostat

* Support *fields*:  
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
openmotics.thermostat.on,id=G.0,name=Global_thermostat 1
openmotics.thermostat.current_setpoint,id=H.12,name=Living current_setpoint=22
```

### Errors

At a fixed interval (30 seconds), module error statistics are sent to Statful.

* *key*: 'openmotics.error.value', comma separated with following extra tags:
  * *type*: one of 'Input', 'Temperature', 'Output', 'Dimmer', 'Shutter', 'OLED'
  * *id*: the module ID
  * *name*: the concatination from the type and the id
* *fields*:
  * *value*: amount (integer) of errors for this module

Example:

```
openmotics.error.value,type=Input,id=2,name=Input_2 2
```

### Pulse counters

At a fixed interval (30 seconds), pulse counters are sent to Statful.

* *key*: 'openmotics.counter.value', comma separated with following extra tags:
  * *name*: name of the pulse counter
  * *input*: id of the input that drives the pulse counter
* *fields*:
  * *value*: counter (integer)

Example:

```
openmotics.counter.value,name=water,input=2 274533
```

### Power (OpenMotics - Power Module or Energy Module)

At a fixed interval (30 seconds), power data is sent to Statful.

* *key*: 'openmotics.energy.${field_name}', comma separated with following extra tags:
  * *type*: 'openmotics'
  * *id*: concatenation of the module address and power input
  * *name*: name of the power input

* Support *fields*:
  * *voltage*: the voltage corresponding with the CT (in Volt, RMS)
  * *current*: the current measured on the CT (in Ampere, RMS)
  * *frequency*: frequency of the voltage (net frequency)
  * *power*: real power (not the apparent power - it takes phase shifting into account. In Watt)
  * *counter*: total consumed power (in Watt-hours)
  * *counter_day*: total consumed power during day-time (in Watt-hours)
  * *counter_night*: total consumed power during nigt-time (in Watt-hours)

Example:

```
openmotics.energy.voltage,type=openmotics,id=E8.2,name=Dryer 231.5
```

### Power analytics (OpenMotics - Energy Module)

At a fixed interval (30 seconds), detailed power analytics data is sent to Statful.

Harmonics:

* *key*: 'openmotics.energy_analytics.${field_name}', comma separated with following extra tags:
  * *type*: 'frequency',
  * *id*: concatenation of the module address and power input
  * *name*: name of the power input

* Support *fields*:
  * *current_harmonics*: the current harmonics of the corresponding CT
  * *current_phase*: the current phase of the corresponding CT
  * *voltage_harmonics*: the voltage harmonics of the corresponding CT
  * *voltage_phase*: the voltage phase of the corresponding CT

Time based information (So called oscilloscope view)

* *key*: 'openmotics.energy_analytics.${field_name}', comma separated with following extra tags:
  * *type*: 'time',
  * *id*: concatenation of the module address and power input
  * *name*: name of the power input 

* Support *fields*:
  * *voltage*: the voltage component of the corresponding CT sample
  * *current*: the current component of the corresponding CT sample

The data sent is of a full period of the net frequency in 80 samples. 50Hz = 20ms, so every sample is separated by 250us. For display purposes,
the sample separation is increased by a factor of 1000, so in Statful, every sample will be 250ms apart.

### Power (Fibaro - If the Fibaro plugin is installed and devices reporting power are found)

At a fixed interval (30 seconds), power data is sent to Statful.

* *key*: 'openmotics.energy.${field_name}', comma separated with the following extra tags:
  * *type*: 'fibaro'
  * *id*: deviceID from the Fibaro system
  * *name*: name of the device

* Support *fields*:
  * *power*: the power as reported by the device (in Watt)
  * *counter*: the total power consumed by the device (in Watt-hours)

Example:

```
openmotics.energy.power,type=fibaro,id=13,name=xbox360 253.4
```
