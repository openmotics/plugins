# RTI integration plugin

This plugin provides a very simple protocol to use with a custom RTI driver. 

## Protocol

### General format

The protocol has the form of `identifier=value`;
* `identifier` defines to what entity the value must be applied or applies
* `value` holds the (new) value for that entity

For example:
* `output.5.state=on`: This will turn Output with id 5 on.
* `groupaction.12=execute`: This will execute GroupAction/Automation 12

The gateway will not respond to a message, and every message can be assumed to be
received and processed. If an error occurs while processing, an
error response will be sent under the form of  `identifier=error|<message>`.
Malformed messages will be discarded without notification.

For example:
* `output.5.state=error|Communication timed out`

However, the gateway will send the same messages if an entity's state is changed.
This means that when the message `output.5.state=on` is sent to the gateway (as a
command), and this results in output 5's state to be actually changed, the 
gateway will in turn send the message `output.5.state=on` (as an event) to the 
RTI device. If no state was changed because of the message (e.g. the output was 
already on), no message (event) will be sent by the gateway.

### Messages

* `automation.<id>=execute`
  * Command: Executes automation `<id>`
  * Event: This message will not be used as an event, since an automation has no state.
    Only state changes as a result of the execution will result in messages 
    (events) being sent from the gateway
* `output.<id>.state=<on|off|toggle>`
  * Command: Turns output `<id>` on or off, or toggles it current state
  * Event: Reports the current state of the output. The state `toggle` won't be used in this case
* `output.<id>.dimmer=<value>`
  * Command: Sets the dimmer value for output `<id>` to `<value>` (integer, 0-100)
  * Event: Reports the current dimmer value for output `<id>` as `<value>`
* `output=request_current_states`
  * Command: Requests that the gateway sends events for all the output states
  * Event: This message is not available as event. Instead, multiple 
    `output.<id>.state=<on|off>` and `output.<id>.dimmer=<value>` messages can be
    expected
* `thermostat.<id>.preset=<away|party|vacation|auto>`
  * Command: Sets the preset for thermostat `<id>`
  * Event: Reports the new preset for thermostate `<id>`
* `thermostat.<id>.setpoint=<setpoint>`
  * Command: Sets the setpoint for thermostat `<id>`
  * Event: Reports the new setpoint for thermostat `<id>`
* `thermostat.<id>.temperature=<value>`
  * Command: This is a red-only value
  * Event: Reports the current temperature for thermostat `<id>`.
* `thermostat.request_current_states`
  * Command: Requests that the gateway sends events for all thermostat states
  * Event: This message is not available as an event. Instead, multiple
    `thermostat.<id>.xxx=xxx` messages can be expected
* `thermostat_group.<id>.state=<on|off>`
  * Command: Turns on or off thermostat group `<id>`
  * Event: Thermostat group `<id>` was turned on or off
* `thermostat_group.<id>.mode=<cooling|heating>`
  * Command: Changes the mode for thermostat group `<id>` to `cooling` or `heating`
  * Event: The mode for thermostat group `<id>` was changed
* `thermostat_group.request_current_states`
  * Command: Requests that the gateway sends events for all thermostat group states
  * Event: This message is not available as an event. Instead, multiple
    `thermostat_group.<id>.xxx=xxx` messages can be expected

## TODOs

* Upload RTI driver to this repository, if possible
