#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2018-09-07
# @Filename: base.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)
#
# @Last modified by: José Sánchez-Gallego (gallegoj@uw.edu)
# @Last modified time: 2019-04-23 15:13:25


import asyncio
import enum


__ALL__ = ['CommandStatus', 'StatusMixIn']


class Maskbit(enum.Flag):
    """A maskbit enumeration. Intended for subclassing."""

    @property
    def active_bits(self):
        """Returns a list of flags that match the value."""

        return [bit for bit in self.__class__ if bit.value & self.value]


COMMAND_STATUS_TO_CODE = {
    'DONE': ':',
    'CANCELLED': 'f',
    'FAILED': 'f',
    'READY': 'i',
    'RUNNING': 'i',
    'CANCELLING': 'w',
    'FAILING': 'w',
    'DEBUG': 'd',
}


class CommandStatus(Maskbit):

    DONE = enum.auto()
    CANCELLED = enum.auto()
    FAILED = enum.auto()
    READY = enum.auto()
    RUNNING = enum.auto()
    CANCELLING = enum.auto()
    FAILING = enum.auto()
    DEBUG = enum.auto()

    ACTIVE_STATES = RUNNING | CANCELLING | FAILING
    FAILED_STATES = CANCELLED | FAILED
    FAILING_STATES = CANCELLING | FAILING
    DONE_STATES = DONE | FAILED_STATES
    ALL_STATES = READY | ACTIVE_STATES | DONE_STATES

    def __init__(self, *args):

        if self.name.upper() in COMMAND_STATUS_TO_CODE:
            self.code = COMMAND_STATUS_TO_CODE[self.name.upper()]
        else:
            self.code = None

    @property
    def is_combination(self):
        """Returns True if a flag is a combination."""

        if bin(self).count('1') > 1:
            return True
        return False

    @property
    def did_fail(self):
        """Command failed or was cancelled."""

        return self in self.FAILED_STATES

    @property
    def is_active(self):
        """Command is running, cancelling or failing."""

        return self in self.ACTIVE_STATES

    @property
    def is_done(self):
        """Command is done (whether successfully or not)."""

        return self in self.DONE_STATES

    @property
    def is_failing(self):
        """Command is being cancelled or is failing."""

        return self in self.FAILING_STATES


class StatusMixIn(object):
    """A mixin that provides status tracking with callbacks.

    Provides a status property that executes a list of callbacks when
    the status changes.

    Parameters
    ----------
    maskbit_flags : class
        A class containing the available statuses as a series of maskbit
        flags. Usually as subclass of `enum.Flag`.
    initial_status : str
        The initial status.
    callback_func : function
        The function to call if the status changes.
    call_now : bool
        Whether the callback function should be called when initialising.

    Attributes
    ----------
    callbacks : list
        A list of the callback functions to call.

    """

    def __init__(self, maskbit_flags, initial_status=None,
                 callback_func=None, call_now=False):

        self.flags = maskbit_flags
        self.callbacks = []
        self._status = initial_status
        self.watcher = None

        if callback_func is not None:
            if isinstance(callback_func, (list, tuple)):
                self.callbacks = callback_func
            else:
                self.callbacks.append(callback_func)

        if call_now is True:
            self.do_callbacks()

    def do_callbacks(self):
        """Calls functions in ``callbacks``."""

        assert hasattr(self, 'callbacks'), 'missing callbacks attribute.'

        loop = self.loop if hasattr(self, 'loop') else asyncio.get_event_loop()

        for func in self.callbacks:
            loop.call_soon(func)

    @property
    def status(self):
        """Returns the status."""

        return self._status

    @status.setter
    def status(self, value):
        """Sets the status."""

        if value != self._status:
            self._status = self.flags(value)
            self.do_callbacks()
            if self.watcher is not None:
                self.watcher.set()

    async def wait_for_status(self, value, loop=None):
        """Awaits until the status matches ``value``."""

        if self.status == value:
            return

        if loop is None:
            if hasattr(self, 'loop') and self.loop is not None:
                loop = self.loop
            else:
                loop = asyncio.get_event_loop()

        self.watcher = asyncio.Event(loop=loop)

        while self.status != value:
            await self.watcher.wait()
            if self.watcher is not None:
                self.watcher.clear()

        self.watcher = None
