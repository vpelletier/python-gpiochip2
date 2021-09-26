# -*- coding: utf-8 -*-
# Copyright (C) 2018-2021  Vincent Pelletier <plr.vincent@gmail.com>
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
Low-level ctypes translation of linux/gpio.h

You should not have to import this file outside this package.
"""

import ctypes
import enum
from ioctl_opt import IOR, IOWR

# pylint: disable=invalid-name, too-few-public-methods, invalid-name
# pylint: disable=missing-class-docstring

GPIO_MAX_NAME_SIZE = 32

class gpiochip_info(ctypes.Structure):
    _fields_ = (
        ('name', ctypes.c_char * GPIO_MAX_NAME_SIZE),
        ('label', ctypes.c_char * GPIO_MAX_NAME_SIZE),
        ('lines', ctypes.c_uint32),
    )

# Maximum number of requested lines.
GPIO_V2_LINES_MAX = 64

# The maximum number of configuration attributes associated with a line request.
GPIO_V2_LINE_NUM_ATTRS_MAX = 10

@enum.unique
class GPIO_V2_LINE_FLAG(enum.IntEnum):
    USED                 = 1 << 0
    ACTIVE_LOW           = 1 << 1
    INPUT                = 1 << 2
    OUTPUT               = 1 << 3
    EDGE_RISING          = 1 << 4
    EDGE_FALLING         = 1 << 5
    OPEN_DRAIN           = 1 << 6
    OPEN_SOURCE          = 1 << 7
    BIAS_PULL_UP         = 1 << 8
    BIAS_PULL_DOWN       = 1 << 9
    BIAS_DISABLED        = 1 << 10
    EVENT_CLOCK_REALTIME = 1 << 11

class gpio_v2_line_values(ctypes.Structure):
    _fields_ = (
        ('bits', ctypes.c_uint64),
        ('mask', ctypes.c_uint64),
    )

@enum.unique
class GPIO_V2_LINE_ATTR_ID(enum.IntEnum):
    FLAGS         = 1
    OUTPUT_VALUES = 2
    DEBOUNCE      = 3

class _gpio_v2_line_attribute_u(ctypes.Union):
    _fields_ = (
        ('flags', ctypes.c_uint64),
        ('values', ctypes.c_uint64),
        ('debounce_period_us', ctypes.c_uint32),
    )

class gpio_v2_line_attribute(ctypes.Structure):
    _anonymous_ = ('u', )
    _fields_ = (
        ('id', ctypes.c_uint32),
        ('padding', ctypes.c_uint32),
        ('u', _gpio_v2_line_attribute_u),
    )

class gpio_v2_line_config_attribute(ctypes.Structure):
    _fields_ = (
        ('attr', gpio_v2_line_attribute),
        ('mask', ctypes.c_uint64),
    )

class gpio_v2_line_config(ctypes.Structure):
    _fields_ = (
        ('flags', ctypes.c_uint64),
        ('num_attrs', ctypes.c_uint32),
        ('padding', ctypes.c_uint32 * 5),
        ('attrs', gpio_v2_line_config_attribute * GPIO_V2_LINE_NUM_ATTRS_MAX),
    )

class gpio_v2_line_request(ctypes.Structure):
    _fields_ = (
        ('offsets', ctypes.c_uint32 * GPIO_V2_LINES_MAX),
        ('consumer', ctypes.c_char * GPIO_MAX_NAME_SIZE),
        ('config', gpio_v2_line_config),
        ('num_lines', ctypes.c_uint32),
        ('event_buffer_size', ctypes.c_uint32),
        ('padding', ctypes.c_uint32 * 5),
        ('fd', ctypes.c_int32),
    )

class gpio_v2_line_info(ctypes.Structure):
    _fields_ = (
        ('name', ctypes.c_char * GPIO_MAX_NAME_SIZE),
        ('consumer', ctypes.c_char * GPIO_MAX_NAME_SIZE),
        ('offset', ctypes.c_uint32),
        ('num_attrs', ctypes.c_uint32),
        ('flags', ctypes.c_uint64),
        ('attrs', gpio_v2_line_attribute * GPIO_V2_LINE_NUM_ATTRS_MAX),
        ('padding', ctypes.c_uint32 * 4),
    )

@enum.unique
class GPIO_V2_LINE_CHANGED_TYPE(enum.IntEnum):
    REQUESTED = 1
    RELEASED  = 2
    CONFIG    = 3

class gpio_v2_line_info_changed(ctypes.Structure):
    _fields_ = (
        ('info', gpio_v2_line_info),
        ('timestamp_ns', ctypes.c_uint64),
        ('event_type', ctypes.c_uint32),
        ('padding', ctypes.c_uint32 * 5),
    )

@enum.unique
class GPIO_V2_LINE_EVENT_ID(enum.IntEnum):
    RISING_EDGE  = 1
    FALLING_EDGE = 2

class gpio_v2_line_event(ctypes.Structure):
    _fields_ = (
        ('timestamp_ns', ctypes.c_uint64),
        ('id', ctypes.c_uint32),
        ('offset', ctypes.c_uint32),
        ('seqno',  ctypes.c_uint32),
        ('line_seqno',  ctypes.c_uint32),
        ('padding', ctypes.c_uint32 * 6),
    )

GPIO_GET_CHIPINFO_IOCTL = IOR(0xB4, 0x01, gpiochip_info)
GPIO_V2_GET_LINEINFO_IOCTL = IOWR(0xB4, 0x05, gpio_v2_line_info)
GPIO_V2_GET_LINEINFO_WATCH_IOCTL = IOWR(0xB4, 0x06, gpio_v2_line_info)
GPIO_V2_GET_LINE_IOCTL = IOWR(0xB4, 0x07, gpio_v2_line_request)
GPIO_GET_LINEINFO_UNWATCH_IOCTL = IOWR(0xB4, 0x0C, ctypes.c_uint32)
GPIO_V2_LINE_SET_CONFIG_IOCTL = IOWR(0xB4, 0x0D, gpio_v2_line_config)
GPIO_V2_LINE_GET_VALUES_IOCTL = IOWR(0xB4, 0x0E, gpio_v2_line_values)
GPIO_V2_LINE_SET_VALUES_IOCTL = IOWR(0xB4, 0x0F, gpio_v2_line_values)
