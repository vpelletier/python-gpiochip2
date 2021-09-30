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
A pure-pyton gpio implemtation using gpiochip chardev.

/sys/class/gpio/* are for shell scripts and hacks.
Real programs should use real APIs, like the one exposed on /dev/gpiochip* .
This package allows programs to use the latter.
"""

from collections import defaultdict
from collections.abc import Iterable
from ctypes import sizeof
import enum
import errno
from fcntl import ioctl
import io
from typing import TYPE_CHECKING, Union, Optional, Dict, List
from .linux_gpio import (
    gpiochip_info,
    GPIO_GET_CHIPINFO_IOCTL,
    GPIO_GET_LINEINFO_UNWATCH_IOCTL,
    GPIO_V2_GET_LINEINFO_IOCTL,
    GPIO_V2_GET_LINEINFO_WATCH_IOCTL,
    GPIO_V2_GET_LINE_IOCTL,
    gpio_v2_line_attribute,
    GPIO_V2_LINE_ATTR_ID,
    GPIO_V2_LINE_CHANGED_TYPE,
    gpio_v2_line_config,
    gpio_v2_line_config_attribute,
    gpio_v2_line_event,
    GPIO_V2_LINE_EVENT_ID,
    GPIO_V2_LINE_FLAG,
    GPIO_V2_LINE_GET_VALUES_IOCTL,
    gpio_v2_line_info,
    gpio_v2_line_info_changed,
    gpio_v2_line_request,
    GPIO_V2_LINE_SET_CONFIG_IOCTL,
    GPIO_V2_LINE_SET_VALUES_IOCTL,
    gpio_v2_line_values,
)
from ._version import get_versions
__version__ = get_versions()['version']
del get_versions

if TYPE_CHECKING:
    # The intent is just to react to missing modules/module members, but
    # mypy is not happy when a given type is inisialised in multiple ways.
    from _typeshed import WriteableBuffer # pylint: disable=import-error
    from typing import TypedDict

    class GPIOChipInfo(TypedDict): # pylint: disable=too-few-public-methods
        """
        Information about a GPIO chip
        """
        name: bytes
        label: bytes
        lines: int

    class GPIOLineInfoBase(TypedDict): # pylint: disable=too-few-public-methods
        """
        Mandatory information about a GPIO line
        """
        name: bytes
        consumer: bytes
        offset: int
        flags: int

    class GPIOLineInfo(
        GPIOLineInfoBase,
        total=False,
    ): # pylint: disable=too-few-public-methods
        """
        Information about a GPIO line
        """
        values: int
        debounce_period_us: int

    class GPIOLineEvent(TypedDict): # pylint: disable=too-few-public-methods
        """
        GPIO line event
        """
        timestamp_ns: int
        id: int
        offset: int
        seqno: int
        line_seqno: int

    class GPIOChipEvent(TypedDict): # pylint: disable=too-few-public-methods
        """
        GPIO chip event
        """
        info: GPIOLineInfo
        timestamp_ns: int
        event_type: int
else:
    GPIOChipInfo = GPIOLineInfo = GPIOLineEvent = GPIOChipEvent = object
    WriteableBuffer = object

# Note: only listing globals which actually make sense to use outside of this
# package.
__all__ = (
    'GPIOChip', 'GPIOLines',
    'GPIO_V2_LINE_FLAG', 'GPIO_V2_LINE_CHANGED_TYPE', 'GPIO_V2_LINE_EVENT_ID',
    'EXPECT_PRECONFIGURED', 'FlagMismatch',
)

# Note: line_index_list should be Iterable[int], but pypy3 Iterable,
# as of 7.3.5 (implementing stdlib 3.7.10), does not have __class_getitem__.
# So instead use an Union of the types we are in fact providing this argument.
def _lineIndexList2Mask(
    line_index_list: Union[List[int], Dict[int, bool]],
    line_count: int,
) -> int:
    mask = 0
    for line_index in line_index_list:
        if not 0 <= line_index < line_count:
            raise ValueError(
                'line index out of bounds: %r' % (line_index, ),
            )
        mask |= 1 << line_index
    return mask

def _getLineConfigurationStruct(
    line_count: int,
    flags: int,
    flags_dict: Optional[Dict[int, int]],
    default_dict: Optional[Dict[int, bool]],
    debounce_period_us_dict: Optional[Dict[int, int]],
) -> gpio_v2_line_config:
    result = gpio_v2_line_config(flags=flags)
    attribute_index = 0
    if flags_dict:
        reverse_flags_dict = defaultdict(list)
        for line_index, line_flags in flags_dict.items():
            reverse_flags_dict[line_flags].append(line_index)
        for line_flags, line_index_list in reverse_flags_dict.items():
            attr = result.attrs[attribute_index]
            attribute_index += 1
            attr.attr.id = GPIO_V2_LINE_ATTR_ID.FLAGS
            attr.attr.flags = line_flags
            attr.mask = _lineIndexList2Mask(
                line_index_list=line_index_list,
                line_count=line_count,
            )
    if default_dict:
        attr = result.attrs[attribute_index]
        attribute_index += 1
        attr.attr.id = GPIO_V2_LINE_ATTR_ID.OUTPUT_VALUES
        attr.attr.values = sum(1 << x for x, y in default_dict.items() if y)
        attr.mask = _lineIndexList2Mask(
            line_index_list=default_dict,
            line_count=line_count,
        )
    if debounce_period_us_dict:
        reverse_debounce_dict = defaultdict(list)
        for line_index, line_debounce in debounce_period_us_dict.items():
            reverse_debounce_dict[line_debounce].append(line_index)
        for line_debounce, line_index_list in reverse_debounce_dict.items():
            attr = result.attrs[attribute_index]
            attribute_index += 1
            attr.attr.id = GPIO_V2_LINE_ATTR_ID.DEBOUNCE
            attr.attr.debounce_period_us = line_debounce
            attr.mask = _lineIndexList2Mask(
                line_index_list=line_index_list,
                line_count=line_count,
            )
    result.num_attrs = attribute_index
    return result

class IOCTLFileIO(io.FileIO):
    """
    Base class for a device node able to run ioctls.
    """
    def _ioctl(
        self,
        request: int,
        arg: Union[
            WriteableBuffer, # pylint: disable=used-before-assignment
            int,
        ]=0,
    ) -> None:
        status = ioctl(self.fileno(), request, arg)
        if status == -1:
            raise OSError

    def seekable(self) -> bool:
        """
        Chardevs are not seekable.
        """
        return False

    def seek(self, pos: int, whence: int=0) -> int:
        """
        Always raises OSError.
        """
        raise OSError(errno.ENOTSUP)

    def tell(self) -> int:
        """
        Always raises OSError.
        """
        raise OSError(errno.ENOTSUP)

    def truncate(self, size: Union[int, None]=None) -> int:
        """
        Always raises OSError.
        """
        raise OSError(errno.ENOTSUP)

class GPIOLines(IOCTLFileIO):
    """
    Wrapper for GPIO line set file handles.
    Implements ioctl calls in a pytonic way.
    """
    def __init__(self, line_count: int, *args, **kw): # type: ignore
        """
        Do not call this directly.

        Use GPIOChip.openLines to get an instance of this class.
        """
        self.__line_count = line_count
        self.__all_line_mask = (1 << line_count) - 1
        super().__init__(*args, **kw)

    def setConfiguration(
        self,
        flags: int,
        flags_dict: Optional[Dict[int, int]]=(), # type: ignore
        default_dict: Optional[Dict[int, bool]]=(), # type: ignore
        debounce_period_us_dict: Optional[Dict[int, int]]=(), # type: ignore
    ) -> None:
        """
        Update lines configuration.

        See GPIOChip.openLines for usage.
        """
        self._ioctl(
            GPIO_V2_LINE_SET_CONFIG_IOCTL,
            _getLineConfigurationStruct(
                line_count=self.__line_count,
                flags=flags,
                flags_dict=flags_dict,
                default_dict=default_dict,
                debounce_period_us_dict=debounce_period_us_dict,
            ),
        )

    def getEvent(self) -> Union[GPIOLineEvent, None]:
        """
        Read and and decode a line event.

        If an entire event could be read, returns a dict with the following
        keys:
        - timestamp_ns (int)
          The timestamp at which the kernel noticed the event on the GPIO line,
          in nanoseconds.
        - id (int)
          One of GPIO_V2_LINE_EVENT_ID constants.
        - offset (int)
          The line index within this instance.
        - seqno (int)
          The global sequence number of this event in this instance.
        - line_seqno (int)
          The sequence number of this event on the line identified by "offset".
        If nothing was read (file is in O_NONBLOCK mode), returns None.
        If an unexpected number of bytes was read, raises IOError.
        """
        event = gpio_v2_line_event()
        byte_count = self.readinto(event)
        if byte_count is None:
            return None
        if byte_count != sizeof(event):
            raise IOError(
                'Expected %i bytes, got %r' % (
                    sizeof(event),
                    byte_count,
                ),
            )
        return {
            'timestamp_ns': event.timestamp_ns,
            'id': GPIO_V2_LINE_EVENT_ID(event.id),
            'offset': event.offset,
            'seqno': event.seqno,
            'line_seqno': event.line_seqno,
        }

    @property
    def value(self) -> int:
        """
        Returns a bitfield of lines managed by this instance.

        Reads the lines.
        """
        line_values = gpio_v2_line_values(mask=self.__all_line_mask)
        self._ioctl(GPIO_V2_LINE_GET_VALUES_IOCTL, line_values)
        return line_values.bits

    @value.setter
    def value(self, value: int) -> None:
        """
        Change all lines to given bitfield.

        Does not read the lines.
        """
        mask = self.__all_line_mask
        if value < 0:
            # Caller probably used "~value", mask it to get a ctypes-usable
            # integer.
            value &= mask
        self._ioctl(
            GPIO_V2_LINE_SET_VALUES_IOCTL,
            gpio_v2_line_values(bits=value, mask=mask),
        )

    def __iand__(self, value: int) -> 'GPIOLines':
        """
        Make some lines inactive.

        Does not read the lines.
        """
        self._ioctl(
            GPIO_V2_LINE_SET_VALUES_IOCTL,
            gpio_v2_line_values(
                bits=value,
                mask=(~value) & 0xffffffff_ffffffff,
            ),
        )
        return self

    def __ior__(self, value: int) -> 'GPIOLines':
        """
        Make some lines active.

        Does not read the lines.
        """
        self._ioctl(
            GPIO_V2_LINE_SET_VALUES_IOCTL,
            gpio_v2_line_values(bits=value, mask=value),
        )
        return self

@enum.unique
class EXPECT_PRECONFIGURED(enum.IntFlag): # pylint: disable=invalid-name
    """
    For use in GPIOChip.openLines arguments expect_preconfigured{,_dict}.
    """
    ACTIVE_LEVEL = 1 << 0
    DIRECTION    = 1 << 1
    EDGE         = 1 << 2
    DRIVE        = 1 << 3
    BIAS         = 1 << 4

_EXPECT_PRECONFIGURED_LIST = (
    (
        EXPECT_PRECONFIGURED.ACTIVE_LEVEL,
        GPIO_V2_LINE_FLAG.ACTIVE_LOW,
    ),
    (
        EXPECT_PRECONFIGURED.DIRECTION,
        (
            GPIO_V2_LINE_FLAG.INPUT |
            GPIO_V2_LINE_FLAG.OUTPUT
        ),
    ),
    (
        EXPECT_PRECONFIGURED.EDGE,
        (
            GPIO_V2_LINE_FLAG.EDGE_RISING |
            GPIO_V2_LINE_FLAG.EDGE_FALLING
        ),
    ),
    (
        EXPECT_PRECONFIGURED.DRIVE,
        (
            GPIO_V2_LINE_FLAG.OPEN_DRAIN |
            GPIO_V2_LINE_FLAG.OPEN_SOURCE
        ),
    ),
    (
        EXPECT_PRECONFIGURED.BIAS,
        (
            GPIO_V2_LINE_FLAG.BIAS_PULL_UP |
            GPIO_V2_LINE_FLAG.BIAS_PULL_DOWN |
            GPIO_V2_LINE_FLAG.BIAS_DISABLED
        ),
    ),
)

class FlagMismatch(Exception):
    """
    Raised when a line's flags do not match the expected value.
    """
    def __init__(
        self,
        line: int,
        line_flags: int,
        request_flags: int,
        expectation: int,
        mask: int,
    ):
        super().__init__(
            'Line %i flags %r do not match expected value: %r' % (
                line,
                line_flags & mask,
                request_flags & mask,
            )
        )
        self.line = line
        self.line_flags = line_flags
        self.request_flags = request_flags
        self.expectation = expectation
        self.mask = mask

class GPIOChip(IOCTLFileIO):
    """
    Wrapper for the /dev/gpiochip* device class.
    Implements GPIOv2 ioctl calls in a pythonic way.
    """
    def openLines( # pylint: disable=too-many-arguments
        self,
        line_list: List[int],
        consumer: bytes,
        flags: int=0,
        flags_dict: Optional[Dict[int, int]]=(), # type: ignore
        default_dict: Optional[Dict[int, bool]]=(), # type: ignore
        debounce_period_us_dict: Optional[Dict[int, int]]=(), # type: ignore
        event_buffer_size: int=0,
        expect_preconfigured: int=0,
        expect_preconfigured_dict: Optional[Dict[int, int]]=(), # type: ignore
    ) -> GPIOLines:
        """
        Request GPIO lines.

        line_list (list of int)
            The line indexes (relative to the current gpio chip) to request
            access to. The order in which these lines are given is used to
            identify lines.
            Ex: with "line_list=[4, 0]", line with index 0 is the 5th GPIO line
            managed by this chip, and line with index 1 is the 1st GPIO line
            managed by this chip.
        flags (int)
            Bitmask of GPIO_V2_LINE_FLAG.* constants.
        consumer (bytes)
            Nice name so a human checking gpio usage can identify what is using
            which line.
            Encoding rules are unclear, printable 7-bits ASCII should be a safe
            subset.
        flags_dict (int: int)
            Per-line flags, taking precedence over the global one.
            Key is the line index in line_list.
            Value is a bitmask of GPIO_V2_LINE_FLAG.* constants.
        default_dict (int: bool)
            For lines requested for output, the value to set them to.
            Key is the line index in line_list.
            Value is initial desired line status. True for active state, False
            for inactive state.
        debounce_period_us_dict (int: int)
            Key is the line index in line_list.
            Value is the debounce period, in microseconds.
        event_buffer_size (int)
            Even buffer size hint for the kernel.
            When 0, a sensible default is chosen by the kernel, so you should
            only need to tweak this if your event handling falls behind and
            events get lost.
            The kernel may disobey this value (ex: if it is too large).
        expect_preconfigured (int)
            Bitmask of EXPECT_PRECONFIGURED.* .
            In a well-configured board, the GPIO lines should come already
            somewhat preconfigured. This parameter controls which line
            properties are being checked before requesting the lines, to avoid
            opening an unexpected line, potentially wrecking havoc on the
            system.
            Note that you can reconfigure lines after opening, using
            GPIOLines.setConfiguration .
            If there is a mismatch, raises FlagMismatch.
        expect_preconfigured_dict (int: int)
            Like expect_preconfigured, but per-line.
            Key is the line index in line_list.
            Value is a bitmask of EXPECT_PRECONFIGURED.* .

        Returns a GPIOLines instance.
        """
        flags_dict = dict(flags_dict) # type: ignore
        if expect_preconfigured or expect_preconfigured_dict:
            expect_preconfigured_dict = dict(
                expect_preconfigured_dict, # type: ignore
            )
            for index, line in enumerate(line_list):
                line_flags = self.getLineInfo(line)['flags']
                flags = flags_dict.get(line, flags)
                expectation = expect_preconfigured_dict.get(
                    index,
                    expect_preconfigured,
                )
                mask = sum(
                    y
                    for x, y in _EXPECT_PRECONFIGURED_LIST
                    if expectation & x
                )
                if flags & mask != line_flags & mask:
                    raise FlagMismatch(
                        line=line,
                        line_flags=line_flags,
                        request_flags=flags,
                        expectation=expectation,
                        mask=mask,
                    )
        line_count = len(line_list)
        line_request = gpio_v2_line_request(
            consumer=consumer,
            config=_getLineConfigurationStruct(
                line_count=line_count,
                flags=flags,
                flags_dict=flags_dict,
                default_dict=default_dict,
                debounce_period_us_dict=debounce_period_us_dict,
            ),
            num_lines=line_count,
            event_buffer_size=event_buffer_size,
        )
        for index, line in enumerate(line_list):
            line_request.offsets[index] = line
        self._ioctl(GPIO_V2_GET_LINE_IOCTL, line_request)
        return GPIOLines(
            file=line_request.fd,
            mode='w+b',
            line_count=line_count,
        )

    def getInfo(self) -> GPIOChipInfo:
        """
        Get information about the gpiochip.

        Return a dict with keys:
        - "name" (bytes)
          The kernel name for this chip (ex: b"gpiochip0")
        - "label" (bytes)
          A functional name for this chip, like a chip model.
        - lines (int)
          The number of lines on this chip.
        """
        result = gpiochip_info()
        self._ioctl(GPIO_GET_CHIPINFO_IOCTL, result)
        return {
            'name': result.name,
            'label': result.label,
            'lines': result.lines,
        }

    @staticmethod
    def _decodeLineInfo(line_info: gpio_v2_line_info) -> GPIOLineInfo:
        result = {
            'name': line_info.name,
            'consumer': line_info.consumer,
            'offset': line_info.offset,
            'flags': GPIO_V2_LINE_FLAG(line_info.flags),
        }
        for attr in line_info.attrs[:line_info.num_attrs]:
            attr_id = attr.id
            if attr_id == GPIO_V2_LINE_ATTR_ID.FLAGS:
                result['flags'] = GPIO_V2_LINE_FLAG(attr.flags)
            elif attr_id == GPIO_V2_LINE_ATTR_ID.OUTPUT_VALUES:
                result['values'] = attr.values
            elif attr_id == GPIO_V2_LINE_ATTR_ID.DEBOUNCE:
                result['debounce_period_us'] = attr.debounce_period_us
        return result # type: ignore

    def getLineInfo(self, line: int) -> GPIOLineInfo:
        """
        Get information about a given line.

        line (int)
            The index of requested line on this chip.

        Returns a dict with the following keys:
        - "name" (bytes)
          The name of this line, if any, chosen by the chip driver (ex:
          configured in devicetree)
        - "consumer" (bytes)
          The name, if any, given by the current consumer of this line.
        - "offset" (int)
          The number of this ine on this chip.
        - "flags" (int)
          Bitmask of GPIO_V2_LINE_FLAG.* constants.
        - "values" (int, optional)
          The state this line is driven at, if it is an output.
        - "debounce_period_us" (int, optional)
          The debounce period of this line, in microseconds.
        """
        line_info = gpio_v2_line_info(
            offset=line,
        )
        self._ioctl(GPIO_V2_GET_LINEINFO_IOCTL, line_info)
        return self._decodeLineInfo(line_info)

    def watchLineInfo(self, line: int) -> None:
        """
        Request line status changes (see GPIO_V2_LINE_CHANGED_TYPE.*) to trigger
        file events (POLLIN, POLLPRI) on this file.

        Available events can be retrieved with getEvent.

        line (int)
            The index of requested line on this chip.
        """
        self._ioctl(
            GPIO_V2_GET_LINEINFO_WATCH_IOCTL,
            gpio_v2_line_info(offset=line),
        )

    def unwatchLineInfo(self, line: int) -> None:
        """
        Disable file event generation for changes to given line.

        line (int)
            The index of requested line on this chip.
        """
        self._ioctl(GPIO_GET_LINEINFO_UNWATCH_IOCTL, line)

    def getEvent(self) -> Union[GPIOChipEvent, None]:
        """
        Read and decode one line info change event.

        If an entire event could be read, returns a dict with the following
        keys:
        - "info" (dict)
          See getLineInfo.
        - "timestamp_ns" (int)
          The timestamp at which this event happened, in nanoseconds.
        - "event_type" (int)
          One of the GPIO_V2_LINE_CHANGED_TYPE.* constants.
        If nothing was read (file is in O_NONBLOCK mode), returns None.
        If an unexpected number of bytes was read, raises IOError.
        """
        event = gpio_v2_line_info_changed()
        byte_count = self.readinto(event)
        if byte_count is None:
            return None
        if byte_count != sizeof(event):
            raise IOError(
                'Expected %i bytes, got %r' % (
                    sizeof(event),
                    byte_count,
                ),
            )
        return {
            'info': self._decodeLineInfo(event.info),
            'timestamp_ns': event.timestamp_ns,
            'event_type': GPIO_V2_LINE_CHANGED_TYPE(event.event_type),
        }
