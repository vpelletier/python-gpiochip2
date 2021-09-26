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
A python port of kernel's tools/gpio/gpio-watch.c
"""
import argparse
import select
from gpiochip2 import (
    GPIOChip,
    GPIO_V2_LINE_CHANGED_TYPE,
)

EVENT_CAPTION_DICT = {
    GPIO_V2_LINE_CHANGED_TYPE.REQUESTED: 'requested',
    GPIO_V2_LINE_CHANGED_TYPE.RELEASED: 'released',
    GPIO_V2_LINE_CHANGED_TYPE.CONFIG: 'config changed',
}

def main():
    parser = argparse.ArgumentParser(
        description='Monitor unrequested lines for property changes using the '
        'character device.',
    )
    parser.add_argument(
        'gpiochip',
        help='Path of the character device to monitor',
    )
    parser.add_argument(
        'line',
        nargs='+',
        type=int,
        help='GPIO line to monitor',
    )
    args = parser.parse_args()
    with GPIOChip(args.gpiochip, 'w+b') as gpiochip:
        for line in args.line:
            try:
                gpiochip.watchLineInfo(line)
            except:
                print('unable to set up line watch')
                raise
        poll = select.poll()
        poll.register(gpiochip, select.POLLIN | select.POLLPRI)
        try:
            while True:
                poll.poll(5000)
                try:
                    event = gpiochip.getEvent()
                except:
                    print('error polling for linechanged fd')
                    raise
                print(
                    'line %i: %s at %i' % (
                        event['info']['offset'],
                        EVENT_CAPTION_DICT[event['event_type']],
                        event['timestamp_ns'],
                    ),
                )
        except KeyboardInterrupt:
            pass

if __name__ == '__main__':
    main()
