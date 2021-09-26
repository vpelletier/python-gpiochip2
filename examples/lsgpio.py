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
A python port of kernel's tools/gpio/lsgpio.c
"""
import argparse
import glob
from gpiochip2 import (
    GPIOChip,
    GPIO_V2_LINE_FLAG,
)

FLAGNAMES = (
    ('used',           GPIO_V2_LINE_FLAG.USED),
    ('input',          GPIO_V2_LINE_FLAG.INPUT),
    ('output',         GPIO_V2_LINE_FLAG.OUTPUT),
    ('active-low',     GPIO_V2_LINE_FLAG.ACTIVE_LOW),
    ('open-drain',     GPIO_V2_LINE_FLAG.OPEN_DRAIN),
    ('open-source',    GPIO_V2_LINE_FLAG.OPEN_SOURCE),
    ('pull-up',        GPIO_V2_LINE_FLAG.BIAS_PULL_UP),
    ('pull-down',      GPIO_V2_LINE_FLAG.BIAS_PULL_DOWN),
    ('bias-disabled',  GPIO_V2_LINE_FLAG.BIAS_DISABLED),
    ('clock-realtime', GPIO_V2_LINE_FLAG.EVENT_CLOCK_REALTIME),
)

def main():
    parser = argparse.ArgumentParser(
        description='List GPIO chips, lines and states.',
    )
    parser.add_argument(
        '-n',
        dest='name',
        help='List GPIOs on a named device',
    )
    args = parser.parse_args()
    for gpio_name in (
        [args.name]
        if args.name else
        glob.glob('/dev/gpiochip*')
    ):
        with GPIOChip(gpio_name, 'w+b') as gpiochip:
            chip_info_dict = gpiochip.getInfo()
            print(
                'GPIO chip: %s, %s, %i GPIO lines' % (
                    chip_info_dict['name'].decode('utf-8', errors='replace'),
                    chip_info_dict['label'].decode('utf-8', errors='replace'),
                    chip_info_dict['lines'],
                ),
            )
            for line in range(chip_info_dict['lines']):
                line_info_dict = gpiochip.getLineInfo(line)
                print('\tline %(offset)2i:' % line_info_dict, end='')
                if line_info_dict['name']:
                    print(
                        ' "%s"' % (
                            line_info_dict['name'].decode(
                                'utf-8',
                                errors='replace',
                            ),
                        ),
                        end='',
                    )
                else:
                    print(' unnamed', end='')
                if line_info_dict['consumer']:
                    print(
                        ' "%s"' % (
                            line_info_dict['consumer'].decode(
                                'utf-8',
                                errors='replace',
                            ),
                        ),
                        end='',
                    )
                else:
                    print(' unused', end='')
                line_flags = line_info_dict['flags']
                if line_flags:
                    flag_name_list = [
                        x
                        for x, y in FLAGNAMES
                        if line_flags & y
                    ]
                    if (
                        line_flags & GPIO_V2_LINE_FLAG.EDGE_RISING and
                        line_flags & GPIO_V2_LINE_FLAG.EDGE_FALLING
                    ):
                        flag_name_list.append('both-edges')
                    elif line_flags & GPIO_V2_LINE_FLAG.EDGE_RISING:
                        flag_name_list.append('rising-edges')
                    elif line_flags & GPIO_V2_LINE_FLAG.EDGE_FALLING:
                        flag_name_list.append('falling-edges')
                    if 'debounce_period_us' in line_info_dict:
                        flag_name_list.append(
                            'debounce_period=%iusec' %
                            line_info_dict['debounce_period_us'],
                        )
                    print(' [%s]' % ', '.join(flag_name_list), end='')
                print()

if __name__ == '__main__':
    main()
