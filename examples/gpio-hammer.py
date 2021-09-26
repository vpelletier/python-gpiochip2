# -*- coding: utf-8 -*-
# Copyright (C) 2021  Vincent Pelletier <plr.vincent@gmail.com>
#
# This file is part of python-gpiochip2.
# python-gpiochip2 is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# python-gpiochip2 is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with python-gpiochip2.  If not, see <http://www.gnu.org/licenses/>.

"""
A python port of kernel's tools/gpio/gpio-hammer.c
...with some liberties taken on the exact output and arguments.
"""
import argparse
import itertools
import time
from gpiochip2 import (
    GPIOChip,
    GPIO_V2_LINE_FLAG,
)

def int2bin(value, length):
    mask = 1
    result = []
    for _ in range(length):
        result.append('1' if value & mask else '0')
        mask <<= 1
    return '[' + ', '.join(result) + ']'

def main():
    parser = argparse.ArgumentParser(
        description='Hammer GPIO lines, 0->1->0->1...',
    )
    parser.add_argument(
        '--name',
        required=True,
        help='Hammer GPIOs on a named device',
    )
    parser.add_argument(
        '--offset',
        required=True,
        action='append',
        type=int,
        help='Offset[s] to hammer, at least one, several can be stated',
    )
    parser.add_argument(
        '--count',
        type=int,
        help='Do <COUNT> loops (optional, infinite loop if not stated)',
    )
    args = parser.parse_args()
    line_count = len(args.offset)
    iterator = (
        itertools.repeat(None)
        if args.count is None else
        range(args.count)
    )
    swirr = itertools.cycle(r'-\|/')
    with GPIOChip(args.name, 'w+b') as gpiochip:
        with gpiochip.openLines(
            line_list=args.offset,
            flags=GPIO_V2_LINE_FLAG.OUTPUT,
            consumer='gpio-hammer'.encode('ascii'),
        ) as gpio_lines:
            value = gpio_lines.lines
            print(
                'Hammer lines %r on %s, initial states: %s' % (
                    args.offset,
                    args.name,
                    int2bin(value, line_count),
                ),
            )
            try:
                for _ in iterator:
                    value = ~value
                    gpio_lines.lines = value
                    value = gpio_lines.lines
                    print(
                        '[%s] %s' % (
                            next(swirr),
                            int2bin(value, line_count),
                        ),
                        end='\r',
                        flush=True,
                    )
                    time.sleep(1)
            except KeyboardInterrupt:
                pass

if __name__ == '__main__':
    main()
