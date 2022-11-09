# Tutorial - how to set up with thermometer and switch

 In this tutorial we'll set up a PID controller for a heated box, using a thermometer and an on/off switch for a heating element.

 The tutorial assumes that you have already installed the PID controller in the custom_components folder.

 First, we define the sensor. We name it `pid_thermometer`, and we use the prefix `pid_th_` for all of the different inputs to be able to identify them in the Home Assistant UI.

 ```yaml
#configuration.yaml
...
pid_controller:

sensor:
- platform: pid_controller
  name: pid_thermometer
  enabled: '{{ states("input_boolean.pid_th_enabled") }}'
  set_point: '{{ states("input_number.pid_th_set_point") }}'
  p: '{{ states("input_number.pid_th_proportional") }}'
  i: '{{ states("input_number.pid_th_integral") }}'
  d: '{{ states("input_number.pid_th_derivative") }}'
  entity_id: input_number.pid_th_reading
  invert: '{{ states("input_boolean.pid_th_invert") }}'
  precision: '{{ states("input_number.pid_th_precision") }}'
  minimum: '{{ states("input_number.pid_th_minimum") }}'
  maximum: '{{ states("input_number.pid_th_maximum") }}'
  round: '{{ states("input_select.pid_th_round") }}'
  sample_time: '{{ states("input_number.pid_th_sample_time") }}'
  windup: '{{ states("input_number.pid_th_windup") }}'

...
 ```

This will give us a PID controller sensor output named `pid_thermometer` (with ID `sensor.pid_thermometer`). The output will be a value between 

We then need to add the inputs. These need to be named as in the pid_controller definition above.

 ```yaml
 #configuration.yaml
...
input_boolean:
  pid_th_invert:
    name: Invert
    initial: no
  pid_th_enabled:
    name: Enabled

input_select:
  pid_th_round:
    initial: Round
    options:
      - Floor
      - Ceil
      - Round

input_number:
  pid_th_sample_time:
    name: Sample Time
    initial: 0
    min: 0
    max: 30
    step: 1

  pid_th_minimum:
    name: Minimum
    initial: 0
    min: 0
    max: 5
    step: 1

  pid_th_maximum:
    name: Maximum
    initial: 5
    min: 0
    max: 50
    step: 1

  pid_th_set_point:
    name: Set Point
    initial: 15
    min: 0
    max: 30
    step: 1 

  pid_th_proportional:
    name: Proportional
    initial: 0
    min: 0
    max: 10
    step: 0.01

  pid_th_integral:
    name: Integral
    initial: 0
    min: 0
    max: 10
    step: 0.01

  pid_th_derivative:
    name: Derivative
    initial: 0
    min: 0
    max: 10
    step: 0.01

  pid_th_precision:
    name: Precision
    initial: 2
    min: 0
    max: 10
    step: 1

  pid_th_windup:
    name: Windup
    initial: 0
    min: 0
    max: 30
    step: 1
  
  pid_th_reading:
    name: Sensor Reading
    initial: 0
    min: -1000
    max: 1000
    step: 1
 ```

We can now restart Home Assistant, and the sensors will be visible among our entities.

![Added entities][tutorial_01]

Due to a bug in the current version, it is not possible to use the sensor entity ID directly in a reliable fashion. We need to create an automation script that reads out our sensor value and assigns the value to the number `pid_th_reading`. This script could look as follows.

 ```yaml
alias: pid_th_setsensor
description: "Sets the value of pid_th_reading to sensor value every minute."
trigger:
  - platform: time_pattern
    minutes: /1
action:
  - service: input_number.set_value
    data_template:
      entity_id: input_number.pid_th_reading
      value: "{{ states('sensor.th09_temperature_2') }}"
mode: single
 ```

Now, let's view the settings and the output of `sensor.pid_thermometer` on two entity cards.

![Output of PID controller entities][tutorial_02]

As you can see, the temperature reading is 23.6 (entry at the bottom of the first entity card), and since our maximum output is set to 50, the PID controller reacts by setting it to the maximum allowed value.

In our case, we only have a switch where the values are on and off, so we reduce the maximum output to 1.

![Set maximum output to 1][tutorial_03]

To handle this switch, we can add an automation script that runs every minute, checks if the value of the PID controller is 0 or 1, and turns the heating element on or off, respectively.

 ```yaml
 alias: Torkskåp 2
description: ""
trigger:
  - platform: time_pattern
    minutes: /1
condition: []
action:
  - if:
      - condition: numeric_state
        entity_id: sensor.pid_thermometer
        attribute: raw_state
        above: "0"
    then:
      - type: turn_on
        device_id: cc748add268463df4c095660b16fbbc6
        entity_id: switch.rtx_power_plug_switch
        domain: switch
    else:
      - type: turn_off
        device_id: cc748add268463df4c095660b16fbbc6
        entity_id: switch.rtx_power_plug_switch
        domain: switch
mode: single

 ```

 We now have everything in place to start experimenting with different values for `P`, `I`, `D` and `windup`, according to the tutorial in the README.

***
 [tutorial_01]: https://raw.githubusercontent.com/soloam/ha-pid-controller/master/tutorial/resources/tutorial_01.png
[tutorial_02]: https://raw.githubusercontent.com/soloam/ha-pid-controller/master/tutorial/resources/tutorial_02.png