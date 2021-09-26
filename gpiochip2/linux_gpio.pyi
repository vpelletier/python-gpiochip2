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
Declare __init__ signatures and struct attributes types.

Unfortunately, mypy does not seem to be able to use a stub to augment an
available module, so this means duplicating almost the entire thing (everything
that is being imported, anyway).
"""

import ctypes
import enum
from typing import Optional, Iterable
from ioctl_opt import IOR, IOWR

class gpiochip_info(ctypes.Structure):
    name: bytes
    label: bytes
    lines: int

    def __init__(self, name: bytes=b'', label: bytes=b'', lines: int=0):
        ...

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
    bits: int
    mask: int

    def __init__(self, bits: int=0, mask: int=0):
        ...

@enum.unique
class GPIO_V2_LINE_ATTR_ID(enum.IntEnum):
    FLAGS         = 1
    OUTPUT_VALUES = 2
    DEBOUNCE      = 3

class _gpio_v2_line_attribute_u(ctypes.Union):
    flags: int
    values: int
    debounce_period_us: int

    def __init__(self, flags: int=0, values: int=0, debounce_period_us: int=0):
        ...

class gpio_v2_line_attribute(ctypes.Structure):
    id: int
    flags: int
    values: int
    debounce_period_us: int
    u: _gpio_v2_line_attribute_u

    def __init__(
        self,
        id: int=0,
        flags: int=0,
        values: int=0,
        debounce_period_us: int=0,
        u: Optional[_gpio_v2_line_attribute_u]=None,
    ):
        ...

class gpio_v2_line_config_attribute(ctypes.Structure):
    attr: gpio_v2_line_attribute
    mask: int

    def __init__(
        self,
        attr: Optional[gpio_v2_line_attribute]=None,
        mask: int=0,
    ):
        ...

class gpio_v2_line_config(ctypes.Structure):
    flags: int
    num_attrs: int
    attrs: list[gpio_v2_line_config_attribute]

    def __init__(
        self,
        flags: int=0,
        num_attrs: int=0,
        attrs: Iterable[gpio_v2_line_config_attribute]=(),
    ):
        ...

class gpio_v2_line_request(ctypes.Structure):
    offsets: list[int]
    consumer: bytes
    config: gpio_v2_line_config
    num_lines: int
    event_buffer_size: int
    fd: int

    def __init__(
        self,
        offsets: Iterable[int]=(),
        consumer: bytes=b'',
        config: Optional[gpio_v2_line_config]=None,
        num_lines: int=0,
        event_buffer_size: int=0,
        fd: int=0,
    ):
        ...

class gpio_v2_line_info(ctypes.Structure):
    name: bytes
    consumer: bytes
    offset: int
    num_attrs: int
    flags: int
    attrs: list[gpio_v2_line_attribute]

    def __init__(
        self,
        name: bytes=b'',
        consumer: bytes=b'',
        offset: int=0,
        num_attrs: int=0,
        flags: int=0,
        attrs: Iterable[gpio_v2_line_attribute]=(),
    ):
        ...

@enum.unique
class GPIO_V2_LINE_CHANGED_TYPE(enum.IntEnum):
    REQUESTED = 1
    RELEASED  = 2
    CONFIG    = 3

class gpio_v2_line_info_changed(ctypes.Structure):
    info: gpio_v2_line_info
    timestamp_ns: int
    event_type: int

    def __init__(
        self,
        info: Optional[gpio_v2_line_info]=None,
        timestamp_ns: int=0,
        event_type: int=0,
    ):
        ...

@enum.unique
class GPIO_V2_LINE_EVENT_ID(enum.IntEnum):
    RISING_EDGE  = 1
    FALLING_EDGE = 2

class gpio_v2_line_event(ctypes.Structure):
    timestamp_ns: int
    id: int
    offset: int
    seqno: int
    line_seqno: int

    def __init__(
        self,
        timestamp_ns: int=0,
        id: int=0,
        offset: int=0,
        seqno: int=0,
        line_seqno: int=0,
    ):
        ...

GPIO_GET_CHIPINFO_IOCTL = IOR(0xB4, 0x01, gpiochip_info)
GPIO_V2_GET_LINEINFO_IOCTL = IOWR(0xB4, 0x05, gpio_v2_line_info)
GPIO_V2_GET_LINEINFO_WATCH_IOCTL = IOWR(0xB4, 0x06, gpio_v2_line_info)
GPIO_V2_GET_LINE_IOCTL = IOWR(0xB4, 0x07, gpio_v2_line_request)
GPIO_GET_LINEINFO_UNWATCH_IOCTL = IOWR(0xB4, 0x0C, ctypes.c_uint32)
GPIO_V2_LINE_SET_CONFIG_IOCTL = IOWR(0xB4, 0x0D, gpio_v2_line_config)
GPIO_V2_LINE_GET_VALUES_IOCTL = IOWR(0xB4, 0x0E, gpio_v2_line_values)
GPIO_V2_LINE_SET_VALUES_IOCTL = IOWR(0xB4, 0x0F, gpio_v2_line_values)
