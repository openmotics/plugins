# Polysun plugin

This plugin maps a virtual Shutter module to the actual relay outputs connected to the Polysun controller.

## Background info

#### Behavior

The Polysun controller expects two buttons to be connected to the controller. The controller reacts as follows to the
buttons:
* When the up or down button is pressed, the system will first rotate the blinds.
* If the user releases the button while the blinds are still rotating, the rotation stops.
* If the users keeps pressing the button until after the rotation is completed, the blinds will start moving up/down respectively.
* As soon as the vertical movement has started, the user can release the up/down button. The system will continue the movement
until the blinds are completely open/closed.
* The user can stop this vertical movement by briefly pressing either the up or down button.
* Once stopped (either because the blinds are completely open/closed or by a stop action), the system behaves again as stated
at the top of this list.

If a user thus only wants to rotate the blinds, the up or down button can be used, depending on the desired state.

#### OpenMotics native shutters

Shutters as implemented in OpenMotics lack this rotation and can only go up or down. These shutters however need to have a
dedicated control in the various end-user interfaces (browser, app, etc.).

#### Polysun plugin

The Polysun plugin will map an OpenMotics Shutter up/down movement to the correct button actions (as described above). 
When instructing the Shutter to go up/down, the plugin will hold the Polysun up/down button for a configurable amount of
time. This will make sure the blinds are completely rotated and then start to move up/down. After this time has passed
the up/down button will be "released" to make sure that the user still has manual control

## Hardware setup

This plugin expects following hardware setup:
* An Output is connected to the controller's UP contact
* An Output is connected to the controller's DOWN contact
* There is an Input linked to each of the Outputs with a "Output follows Input"-configuration.
  * This makes sure that the physical buttons behave exactly as stated in Polysun documentation

The plugin will directly steer the Outputs connected to the controller. It will do that once upon every Shutter action
so a user can always use the buttons to change/abort an action by this plugin

## Configuration

The configuration consists of 3 parts:
1. Add a virtual Shutter module (using "maintenance mode")
2. Configure the virtual shutter
3. Configure the plugin

#### Add a sirtual Shutter module

To add a virtual shutter:
1. Open maintenance mode (portal > settings > CLI or cloud > settings > maintenance) and connect (enter `connect`)
2. Type `add virtual module r`
3. Type `error list` and confirm an `r` module is added at the bottom
4. Exit maintenance mode (enter `disconnect`)

#### Configure the virtual Shutter module

Open the shutters configuration (portal > settings > outputs > select shutter > edit or cloud > configuration >
outputs > select shutter). The shutter can be named as desired.

The timers however need to be chosen carefully as they must be slightly longer than the maximum time it takes to
completely rotate the blinds and start the vertical movement. Once this timer elapsed, the plugin will release the buttons

#### Plugin configuration

The configuration of this plugin consists of a set of mappings:
* A Shutter ID (ID of the virtual shutter)
* An Output ID for the UP direction (ID of the physical output)
* An Output ID for the DOWN direction (ID of the physical output)

The plugin does not validate this configuration for conflicts and assumes there is no overlap in configuration.
Multiple Polysun blinds controlled by one OpenMotics Shutter is not supported. For this functionality Shutter Groups can
be created.
