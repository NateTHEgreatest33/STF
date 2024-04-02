# System Testing Framework (STF)

System testing framework contains all the python libraries needed to write full system tests.

## Features

- **Power cycle unit under test**: remotely power cycle the unit! 
- **Full UART connection**: manage and access console connection from your test!
- **messageAPI functionality built-in**: python library writen for communicating via the messageAPI
- **Results generation**: results generation built in!

## Recommended Wiring
To test the system  the following is the recommended wiring setup. While some ports/pins can be modified, using the following connections is reccomended

![Wiring Diagram](https://i.imgur.com/6F9yapH.png)

## Quick Start Example

```python
  from pi_pico import pi_pico
  from results import results

  Pico = pi_pico()
  Log = results( __file__ )

  Log.test_step( "power cycle pico" )
  Pico.power_cycle()

  Log.compare_less_than( expected=7, actual=5, "Example 7 < 5 Test Case" )

  # Results generation is done upon test exit
```
