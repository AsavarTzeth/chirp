#!/usr/bin/python
#
# Copyright 2011 Dan Smith <dsmith@danplanet.com>
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

from chirp import chirp_common, icf, util
from chirp import bitwise

mem_format = """
struct {
    u32 freq;
    u32 offset;
    u8 unknown1:2,
       rtone:6;
    u8 unknown2:2,
       ctone:6;
    u8 unknown3:1,
       dtcs:7;
    u8 unknown4:2,
       unknown5:2,
       tuning_step:4;
    u8 unknown6:2,
       tmode:2,
       duplex:2,
       unknown7:2;
    u8 power:2,
       is_fm:1,
       unknown8:1,
       dtcs_polarity:2,
       unknown9:2;
    u8 unknown[2];
} memory[200];

#seekto 0x0E20;
u8 skips[25];

#seekto 0x0EB0;
u8 used[25];

#seekto 0x0E40;
struct {
  u8 bank_even:4,
     bank_odd:4;
} banks[100];
"""

TMODES = ["", "Tone", "TSQL", "DTCS"]
POWER = ["High", "Low", "Med"]
DTCS_POLARITY = ["NN", "NR", "RN", "RR"]
STEPS = [5.0, 10.0, 12.5, 15, 20, 25, 30, 50]
MODES = ["FM", "AM"]
DUPLEX = ["", "", "-", "+"]
POWER_LEVELS_VHF = [chirp_common.PowerLevel("High", watts=50),
                    chirp_common.PowerLevel("Low", watts=5),
                    chirp_common.PowerLevel("Mid", watts=15)]
POWER_LEVELS_UHF = [chirp_common.PowerLevel("High", watts=35),
                    chirp_common.PowerLevel("Low", watts=5),
                    chirp_common.PowerLevel("Mid", watts=15)]

class IC2720Radio(icf.IcomCloneModeRadio):
    VENDOR = "Icom"
    MODEL = "IC-2720H"
    
    _model = "\x24\x92\x00\x01"
    _memsize = 5152
    _endframe = "Icom Inc\x2eA0"

    _ranges = [(0x0000, 0x1400, 32)]

    def get_features(self):
        rf = chirp_common.RadioFeatures()
        rf.has_name = False
        rf.memory_bounds = (0, 199)
        rf.valid_modes = list(MODES)
        rf.valid_tmodes = list(TMODES)
        rf.valid_duplexes = list(set(DUPLEX))
        rf.valid_tuning_steps = list(STEPS)
        rf.valid_bands = [(118.0, 999.99)]
        rf.valid_skips = ["", "S"]
        rf.valid_power_levels = POWER_LEVELS_VHF
        return rf

    def get_banks(self):
        return [chr(ord("A") + i) for i in range(0,10)]
        
    def process_mmap(self):
        self._memobj = bitwise.parse(mem_format, self._mmap)

    def get_raw_memory(self, number):
        return self._memobj.memory[number].get_raw()

    def get_memory(self, number):
        bitpos = (1 << (number % 8))
        bytepos = (number / 8)

        _mem = self._memobj.memory[number]
        _skp = self._memobj.skips[bytepos]
        _usd = self._memobj.used[bytepos]
        _bnk = self._memobj.banks[number / 2]

        mem = chirp_common.Memory()
        mem.number = number

        if _usd & bitpos:
            mem.empty = True
            return mem

        mem.freq = _mem.freq / 1000000.0
        mem.offset = _mem.offset / 1000000.0
        mem.rtone = chirp_common.TONES[_mem.rtone]
        mem.ctone = chirp_common.TONES[_mem.ctone]
        mem.dtcs = chirp_common.DTCS_CODES[_mem.dtcs]
        mem.tmode = TMODES[_mem.tmode]
        mem.dtcs_polarity = DTCS_POLARITY[_mem.dtcs_polarity]
        mem.tuning_step = STEPS[_mem.tuning_step]
        mem.mode = _mem.is_fm and "FM" or "AM"
        mem.duplex = DUPLEX[_mem.duplex]

        mem.skip = (_skp & bitpos) and "S" or ""

        if number % 2:
            mem.bank = int(_bnk.bank_odd)
        else:
            mem.bank = int(_bnk.bank_even)
        if mem.bank == 0x0A:
            mem.bank = None

        if int(mem.freq / 100) == 1:
            mem.power = POWER_LEVELS_VHF[_mem.power]
        else:
            mem.power = POWER_LEVELS_UHF[_mem.power]

        return mem

    def set_memory(self, mem):
        bitpos = (1 << (mem.number % 8))
        bytepos = (mem.number / 8)

        _mem = self._memobj.memory[mem.number]
        _skp = self._memobj.skips[bytepos]
        _usd = self._memobj.used[bytepos]
        _bnk = self._memobj.banks[mem.number / 2]
        
        if mem.empty:
            _usd |= bitpos
            return

        _mem.freq = int(mem.freq * 1000000)
        _mem.offset = int(mem.offset * 1000000)
        _mem.rtone = chirp_common.TONES.index(mem.rtone)
        _mem.ctone = chirp_common.TONES.index(mem.ctone)
        _mem.dtcs = chirp_common.DTCS_CODES.index(mem.dtcs)
        _mem.tmode = TMODES.index(mem.tmode)
        _mem.dtcs_polarity = DTCS_POLARITY.index(mem.dtcs_polarity)
        _mem.tuning_step = STEPS.index(mem.tuning_step)
        _mem.is_fm = mem.mode == "FM"
        _mem.duplex = DUPLEX.index(mem.duplex)
        
        if mem.skip == "S":
            _skp |= bitpos
        else:
            _skp &= ~bitpos

        if mem.bank is None:
            val = 0x0A
        else:
            val = int(mem.bank)

        if mem.number % 2:
            _bnk.bank_odd = val
        else:
            _bnk.bank_even = val

        if mem.power:
            _mem.power = POWER_LEVELS_VHF.index(mem.power)
        else:
            _mem.power = 0
