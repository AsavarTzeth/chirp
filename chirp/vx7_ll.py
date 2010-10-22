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

from chirp import chirp_common, util, errors
from chirp.memmap import MemoryMap

POS_DUP    = 1
POS_STEP   = 1
POS_FREQ   = 2
POS_MODE   = 5
POS_TAG    = 6
POS_OFFSET = 15
POS_TONE   = 18
POS_DTCS   = 19
POS_TMODE  = 20

MEM_FLG_BASE = 0x1202
MEM_LOC_BASE = 0x1322
MEM_LOC_SIZE = 22

STEPS = list(chirp_common.TUNING_STEPS)
STEPS.remove(6.25)
STEPS.remove(30.0)
STEPS.append(100.0)
STEPS.append(9.0)

CHARSET = ["%i" % int(x) for x in range(0, 10)] + \
    [" "] + \
    [chr(x) for x in range(ord("A"), ord("Z")+1)] + \
    [chr(x) for x in range(ord("a"), ord("z")+1)] + \
    list(".,:;!\"#$%&'()*+-.=<>?@[?]^_\\{|}") + \
    list("?" * 100)

def get_mem_offset(number):
    return MEM_LOC_BASE + (number * MEM_LOC_SIZE)

def get_raw_memory(mmap, number):
    offset = get_mem_offset(number)
    return MemoryMap(mmap[offset:offset + MEM_LOC_SIZE])

def _get_freq_at(mmap, index):
    khz = (int("%02x" % ord(mmap[index]), 10) * 10000) + \
        (int("%02x" % ord(mmap[index+1]), 10) * 100) + \
        (int("%02x" % ord(mmap[index+2]), 10))

    mult1250 = (khz+0.5) / 12.5
    mult0625 = (khz+0.25) / 6.25
    
    if mult1250 == int(mult1250):
        khz += 0.5
    elif mult0625 == int(mult0625):
        khz += 0.25

    return khz / 1000.0

def _set_freq_at(mmap, index, freq):
    val = util.bcd_encode(freq, width=6)[:3]
    print "set freq %.4f: %s" % (freq, [val])
    mmap[index] = val

def get_freq(mmap):
    return _get_freq_at(mmap, POS_FREQ)

def set_freq(mmap, freq):
    print "Setting freq %f" % (freq * 10)
    return _set_freq_at(mmap, POS_FREQ, int(freq * 1000))

def get_duplex(mmap):
    val = (ord(mmap[POS_DUP]) & 0x30) >> 4

    dupmap = {
        0x00 : "",
        0x01 : "-",
        0x02 : "+",
        0x03 : "split", # non-standard repeater shift
        }

    return dupmap[val]

def set_duplex(mmap, duplex):
    val = (ord(mmap[POS_DUP]) & 0xCF)

    if duplex == "-":
        val |= 0x10
    elif duplex == "+":
        val |= 0x20
    elif duplex == "split":
        val |= 0x30

    print "Duplex is %s, val %02x" % (duplex, val)

    mmap[POS_DUP] = val

def get_offset(mmap):
    return _get_freq_at(mmap, POS_OFFSET)

def set_offset(mmap, offset):
    _set_freq_at(mmap, POS_OFFSET, int(offset * 1000))

def get_mode(mmap):
    val = (ord(mmap[POS_MODE]) & 0x03)

    modemap = {
        0x00 : "FM",
        0x01 : "AM",
        0x02 : "WFM",
        0x03 : "", # NOT SUPPORTED!
        }

    return modemap[val]

def set_mode(mmap, mode):
    modemap = {
        "FM"  : 0x00,
        "AM"  : 0x01,
        "WFM" : 0x02,
        }

    if not modemap.has_key(mode):
        raise errors.InvalidDataError("VX-7 does not support mode %s" % mode)

    val = ord(mmap[POS_MODE]) & 0xFC
    val |= modemap[mode]
    mmap[POS_MODE] = val    

def get_name(mmap):
    name = ""
    for i in mmap[POS_TAG:POS_TAG+8]:
        name += CHARSET[ord(i)]
    return name
        
def set_name(mmap, name):
    i = 0
    for char in name.ljust(8)[:8]:
        if not char in CHARSET:
            char = " "
        print "Charset index of `%s' is %i" % (char, CHARSET.index(char))
        mmap[POS_TAG+i] = CHARSET.index(char)
        i += 1

def get_ts(mmap):
    val = ord(mmap[POS_STEP]) & 0x0F

    return STEPS[val]

def set_ts(mmap, ts):
    if not ts in STEPS:
        raise errors.InvalidDataError("Unsupported tune step %.1f" % ts)

    val = ord(mmap[POS_STEP]) & 0xF0
    val |= STEPS.index(ts)
    mmap[POS_STEP] = val

def get_tmode(mmap):
    val = ord(mmap[POS_TMODE]) & 0x03

    tmodemap = {
        0x00 : "",
        0x01 : "Tone",
        0x02 : "TSQL",
        0x03 : "DTCS",
        }

    return tmodemap[val]

def set_tmode(mmap, tmode):
    tmodemap = {
        ""     : 0x00,
        "Tone" : 0x01,
        "TSQL" : 0x02,
        "DTCS" : 0x03,
        }
    
    if not tmodemap.has_key(tmode):
        raise errors.InvalidDataError("Tone mode %s not supported" % tmode)

    val = ord(mmap[POS_TMODE]) & 0xFC
    val |= tmodemap[tmode]
    mmap[POS_TMODE] = val

def get_tone(mmap):
    val = ord(mmap[POS_TONE]) & 0x1F

    return chirp_common.TONES[val]

def set_tone(mmap, tone):
    val = ord(mmap[POS_TONE]) & 0xE0

    if tone not in chirp_common.TONES:
        raise errors.InvalidDataError("Tone %.1f not supported" % tone)

    val |= chirp_common.TONES.index(tone)
    mmap[POS_TONE] = val

def get_dtcs(mmap):
    val = ord(mmap[POS_DTCS]) & 0x3F

    if val > 0x67:
        raise errors.InvalidDataError("Unknown DTCS code 0x%02x" % val)

    return chirp_common.DTCS_CODES[val]

def set_dtcs(mmap, dtcs):
    val = ord(mmap[POS_DTCS]) & 0xC0

    if dtcs not in chirp_common.DTCS_CODES:
        raise errors.InvalidDataError("DTCS code %03i not supported" % dtcs)

    val |= chirp_common.DTCS_CODES.index(dtcs)
    mmap[POS_DTCS] = val

def is_used(mmap, number):
    byte = int(number / 2)
    nibble = number % 2

    if nibble:
        mask = 0x20
    else:
        mask = 0x02

    return (ord(mmap[MEM_FLG_BASE + byte]) & mask)

def set_is_used(mmap, number, used):
    byte = int(number / 2)
    nibble = number % 2

    val = ord(mmap[MEM_FLG_BASE + byte])

    if nibble:
        bits = 0x30
        mask = 0x0F
    else:
        bits = 0x03
        mask = 0xF0

    val &= mask
    if used:
        val |= bits

    print "Used bitfield for %i: %02x (%s)" % (number, val, used)

    mmap[MEM_FLG_BASE + byte] = val

def get_skip(map, number):
    byte = int(number / 2)
    nibble = number % 2
    val = ord(map[MEM_FLG_BASE + byte])

    if nibble:
        val >>= 4

    if val & 0x08:
        return "P"
    elif val & 0x04:
        return "S"
    else:
        return ""

def set_skip(map, number, skip):
    byte = int(number / 2)
    nibble = number % 2

    val = ord(map[MEM_FLG_BASE + byte])

    if skip == "P":
        bits = 0x08
    elif skip == "S":
        bits = 0x04
    else:
        bits = 0x00

    if nibble:
        bits <<= 4
        mask = 0x3F
    else:
        mask = 0xF3

    map[MEM_FLG_BASE + byte] = (val & mask) | bits

def get_memory(_map, number):
    index = number - 1
    mem = chirp_common.Memory()
    mem.number = number
    if not is_used(_map, index):
        mem.empty = True
        return mem

    mmap = get_raw_memory(_map, index)
    mem.freq = get_freq(mmap)
    mem.duplex = get_duplex(mmap)
    mem.mode = get_mode(mmap)
    mem.name = get_name(mmap)
    mem.tuning_step = get_ts(mmap)
    mem.rtone = mem.ctone = get_tone(mmap)
    mem.dtcs = get_dtcs(mmap)
    mem.tmode = get_tmode(mmap)
    mem.offset = get_offset(mmap)
    mem.skip = get_skip(_map, index)

    return mem
    
def set_unknowns(mmap):
    mmap[0]  = 0x05
    mmap[1]  = 0x00 # Low power, Simplex, 5kHz
    mmap[5]  = 0x30 # Constant in upper 6 bits
    mmap[14] = 0x00
    mmap[18] = 0x00 # Base tone freq
    mmap[19] = 0x00 # DCS code of 023
    mmap[20] = 0x00 # No tone
    mmap[21] = 0x00

def set_memory(_map, mem):
    index = mem.number - 1
    mmap = get_raw_memory(_map, index)

    if not is_used(_map, index):
        set_unknowns(mmap)

    set_freq(mmap, mem.freq)
    set_duplex(mmap, mem.duplex)
    set_mode(mmap, mem.mode)
    set_name(mmap, mem.name)
    set_ts(mmap, mem.tuning_step)
    set_tone(mmap, mem.ctone)
    set_dtcs(mmap, mem.dtcs)
    set_tmode(mmap, mem.tmode)
    set_offset(mmap, mem.offset)

    _map[get_mem_offset(index)] = mmap.get_packed()
    set_is_used(_map, index, True)
    set_skip(_map, index, mem.skip)

    return _map

def erase_memory(map, number):
    set_is_used(map, number-1, False)
    return map

def update_checksum(mmap):
    cs = 0
    for i in range(0x0592, 0x0611):
        cs += ord(mmap[i])
    cs %= 256
    print "Checksum1 old=%02x new=%02x" % (ord(mmap[0x0611]), cs)
    mmap[0x0611] = cs

    cs = 0
    for i in range(0x0612, 0x0691):
        cs += ord(mmap[i])
    cs %= 256
    print "Checksum2 old=%02x new=%02x" % (ord(mmap[0x0691]), cs)
    mmap[0x0691] = cs

    cs = 0
    for i in range(0x0000, 0x3F52):
        cs += ord(mmap[i])
    cs %= 256
    print "Checksum3 old=%02x new=%02x" % (ord(mmap[0x3F52]), cs)
    mmap[0x3F52] = cs
