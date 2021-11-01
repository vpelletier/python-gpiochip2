Pythonic API for Linux's gpiochip chardev ABI v2.

Features
--------

- Manage multiple GPIO lines at the same time, with bit operation affecting the
  entire line group at once (`|=`, `&=`, `^=`).
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

    from gpiochip2 import GPIOChip, GPIO_V2_LINE_FLAG, EXPECT_PRECONFIGURED
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
            # Expect the GPIO lines to be correctly preconfigured (ex: by board-
            # specific firmware or devicetree).
            expect_preconfigured=EXPECT_PRECONFIGURED.DIRECTION,
            expect_preconfigured_dict={
                # Expect line 26 to have its edge detection preconfigured
                # in addition to its direction
                2: EXPECT_PRECONFIGURED.DIRECTION | EXPECT_PRECONFIGURED.EDGE,
            },
        ) as gpio_lines:
            # Read lines state
            value = gpio_lines.value
            # Change lines state
            gpio_lines.value = 0b100 # set line 26, clear lines 21 and 20
            # Set line 21
            gpio_lines |= 2 # 1 << 1
            # Clear line 26
            gpio_lines &= 4 # 1 << 2
            # Read event
            gpio_lines.getEvent()

Notes on bit operations:

``gpio_lines.lines |= some_mask`` will read then write the GPIO, while
``gpio_lines |= some_mask`` only needs to write, making it more efficient.

The same applies to ``&=``, but not to other operators.

See also the `examples` directory for more realistic code.
