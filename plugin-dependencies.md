<!-- - API -->
<!--   - / -->
<!-- - Connector -->
<!--   - / -->
<!-- - Metrics -->
<!--   - [type]: str -->
<!--     - tags: [] -->
<!--     - values: [] -->
<!-- - Decorators -->

# Plugin Dependencies

This file is an overview of what plugins have dependencies on gateway resources and other resources.


## Astro

### Gateway Resources

- API
  - do_basic_action
- Connector
  - /
- Metrics
  - /
- Decorators
  - backgroundtask

### Other

- /


## Dummy

### Gateway Resources

- API
  - /
- Connector
  - sensor
    - subscribe_status_event
    - register
    - report_state
  - ventilation
    - subscribe_status_event
    - attach_set_auto
    - attach_set_manual
    - register
    - report_status
  - measurement counter
    - subscribe_status_event
    - register
    - report_counter_state
    - report_realtime_state
  - hotwater
    - register
    - report_status
    - subscribe_status_event
    - attach_set_state
    - attach_set_setpoint
- Metrics
  - /
- Decorators
  - sensor_status
  - measurement_counter_status
  - ventilation_status
  - hot_water_status

### Other

- /


## fibaro

### Gateway Resources

- API
  - set_virtual_sensor
- Connector
  - /
- Metrics
  - energy
    - tags:
      - name
      - id
      - type
    - values
      - power [W]
      - counter [Wh]
- Decorators
  - output_status
  - background_task
  - om_metric_data

### Other

- /


## Flooding

### Gateway Resources

- API
  - get_total_energy
  - set_output
- Connector
  - /
- Metrics
  - /
- Decorators
  - background_task

### Other

- /


## hello_world

### Gateway Resources

- API
  - /
- Connector
  - /
- Metrics
  - /
- Decorators
  - /

### Other

- /


## Hue

### Gateway Resources

- API
  - set_output
  - get_sensor_configurations
- Connector
  - sensor.register
  - sensor.set_status
- Metrics
  - /
- Decorators
  - output_status
  - background_task

### Other

- /


## influxDB

### Gateway Resources

- API
  - /
- Connector
  - /
- Metrics
  - /
- Decorators
  - om_metric_receive

### Other

- /


## modbusTCPSensor

### Gateway Resources

- API
  - set_virtual_sensor
  - do_basic_action
- Connector
  - /
- Metrics
  - /
- Decorators
  - background_task

### Other

- Library
  - PyModbusTCP  --  0.1.7


## mqtt-client

### Gateway Resources

- API
  - get_input_configurations
  - get_input_status
  - get_output_configurations
  - get_output_status
  - get_sensor_configurations
  - get_power_modules
  - get_realtime_power
  - get_total_energy
  - set_output
- Connector
  - /
- Metrics
  - /
- Decorators
  - input_status
  - output_status
  - receive_events
  - background_task (3x)

### Other

- Library
  - paho_mqtt  --  1.5.0


## OpenWeatherMap

### Gateway Resources

- API
  - /
- Connector
  - sensor
    - report_status
    - register_temperature_celcius
- Metrics
  - /
- Decorators
  - background_task

### Other

- /


## PolySun

### Gateway Resources

- API
  - shutter_report_lost_position
  - get_features
  - set_output
- Connector
  - /
- Metrics
  - /
- Decorators
  - background_task
  - shutter_status
  - input_status

### Other

- /


## Pushetta

### Gateway Resources

- API
  - /
- Connector
  - /
- Metrics
  - /
- Decorators
  - input_status

### Other

- /


## PushSafer

### Gateway Resources

- API
  - /
- Connector
  - /
- Metrics
  - /
- Decorators
  - input_status

### Other

- /


## RTD10

### Gateway Resources

- API
  - set_output
- Connector
  - thermostat
    - get_thermostats
- Metrics
  - /
- Decorators
  - thermostat_status

### Other

- /


## RTI

### Gateway Resources

- API
  - do_group_action
  - set_output
  - do_basic_action
  - get_output_status
  - get_thermostat_status
  - get_thermostat_group_status
- Connector
  - thermostat
    - set_preset
    - set_setpoint
    - set_state
    - set_mode
    - update_thermostat
- Metrics
  - /
- Decorators
  - background_task (2x)
  - thermostat_group_status
  - thermostat_status
  - output_status

### Other

- /


## SensorDotCommunity

### Gateway Resources

- API
  - get_sensor_configuration
- Connector
  - sensor
    - register
    - set_status
- Metrics
  - /
- Decorators
  - /

### Other

- /


## SMASensors

### Gateway Resources

- API
  - /
- Connector
  - sensor
    - register
    - report_status
- Metrics
  - /
- Decorators
  - background_task

### Other

- /


## SMAWebConnect

### Gateway Resources

- API
  - get_pulse_counter_configurations
  - get_pulse_counter_status
- Connector
  - /
- Metrics
  - sma
    - tags
      - device
    - metrics
      - online
      - grid_power
      - frequency
      - voltage_l1
      - voltage_l2
      - voltage_l3
      - current_l1
      - current_l2
      - current_l3
      - pv_power
      - pv_voltage
      - pv_current
      - pv_gen_meter
      - total_yield
      - daily_yield
      - grid_power_supplied
      - grid_power_absorbed
      - grid_total_yield
      - grid_total_absorbed
      - current_consumption
      - total_consumption
- Decorators
  - background_task
  - om_metric_data

### Other

- /


## StatFul

### Gateway Resources

- API
  - /
- Connector
  - /
- Metrics
  - /
- Decorators
  - background_task
  - om_metric_receive

### Other

- /


## Syncer

### Gateway Resources

- API
  - get_input_configurations
  - get_output_configurations
  - get_shutter_configurations
  - get_input_status
  - get_output_status
  - get_shutter_status
- Connector
  - input
    - subscribe_status_event
  - output
    - subscribe_status_event
  - shutter
    - subscribe_status_event
  - sensor
    - register
    - report_status
- Metrics
  - /
- Decorators
  - background_task

### Other

- /


## tasmotaHTTP

### Gateway Resources

- API
  - get_output_status
- Connector
  - /
- Metrics
  - /
- Decorators
  - background_task

### Other

- /


## Ventilation

### Gateway Resources

- API
  - get_sensor_configurations
  - get_sensor_humidity_status
  - get_sensor_temperature_status
  - set_output
- Connector
  - /
- Metrics
  - ventilation
    - tags:
      - name
      - id
    - values:
      - dewpoint
      - absolute_humidity
      - level
      - medium
      - high
      - mean
      - stddev
      - sample
- Decorators
  - background_task
  - om_metric_data

### Other

- /

