Pythonic API for linux's gpiochip chardev ABI v2.

Features
--------

- Manage multile GPIO lines at the same time, with bit operation affecting the
  entire line group at the same time (`|=`, `&=`, `^=`).
- Get file event notification of timestamped line events (rising edge, falling
  edge).
- Get file event notifications (select, poll, epoll...) of gpiochip-level and
  line-level events.
- Control line parameters (pull-up, pull-down, active-low, debouncing, ...).
- Pure python module: no compilation needed, not limited to CPython.

Requirements
------------

- Linux >=5.10.0 for GPIO chardev ABI v2
- python stdlib >=3.7.10 (not tested with earlier versions, they may work)

Examples
--------

Warning: this example is **not** meant to be executed as-is. Depending on what
is connected to the GPIO lines used here (which is entirely board-dependent),
this could cause all sort of problems, including permanent hardware damage.

This is only to be taken as a quick overview of this module's API.

.. code:: python

    from gpiochip2 import GPIOChip, GPIO_V2_LINE_FLAG
    with GPIOChip('/dev/gpiochip0', 'w+b') as gpiochip:
        # Get information about the gpio chip itself
        gpiochip.getInfo()
        # Get information about line 20
        gpiochip.getLineInfo(20)
        with gpiochip.openLines(
            line_list=[20, 21, 26],
            flags=GPIO_V2_LINE_FLAG.OUTPUT,
            consumer='sample-name'.encode('ascii'),
            flags_dict={
                # Line 26 is an input and produces event on falling edges
                2: GPIO_V2_LINE_FLAG.INPUT | GPIO_V2_LINE_FLAG.EDGE_FALLING,
            },
            default_dict={
                # Drive line 20 low immediately on opening
                0: False,
            },
        ) as gpio_lines:
            # Read lines state
            value = gpio_lines.lines
            # Change lines state
            gpio_lines.lines = 0b11
            # Invert line 20
            gpio_lines ^= 1 # 1 << 0
            # Set line 21
            gpio_lines |= 2 # 1 << 1
            # Clear line 21
            gpio_lines &= 2 # 1 << 1
            # Read event
            lines.getEvent()

See also the `examples` directory for more realistic code.
