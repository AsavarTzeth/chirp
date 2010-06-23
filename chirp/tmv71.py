#!/usr/bin/python
#
# Copyright 2010 Dan Smith <dsmith@danplanet.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from chirp import chirp_common, errors
from chirp import tmv71_ll

class TMV71ARadio(chirp_common.IcomFileBackedRadio):
    BAUD_RATE = 9600
    VENDOR = "Kenwood"
    MODEL = "TM-V71A"

    mem_upper_limit = 200
    _memsize = 32512
    _model = "" # FIXME: REMOVE

    def _detect_baud(self):
        for baud in [9600, 19200, 38400, 57600]:
            self.pipe.setBaudrate(baud)
            self.pipe.write("\r\r")
            self.pipe.read(32)
            try:
                id = tmv71_ll.get_id(self.pipe)
                print "Radio %s at %i baud" % (id, baud)
                return True
            except errors.RadioError:
                pass

        raise errors.RadioError("No response from radio")

    def get_raw_memory(self, number):
        return tmv71_ll.get_raw_mem(self._mmap, number)

    def get_memory(self, number):
        return tmv71_ll.get_memory(self._mmap, number)

    def set_memory(self, mem):
        return tmv71_ll.set_memory(self._mmap, mem)

    def sync_in(self):
        self._detect_baud()
        self._mmap = tmv71_ll.download(self)

    def sync_out(self):
        self._detect_baud()
        tmv71_ll.upload(self)
