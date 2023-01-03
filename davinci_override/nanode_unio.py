import RPi.GPIO as gpio
from davinci_override import interrupt_guard
import time

UNIO_STARTHEADER = 0x55
UNIO_READ        = 0x03
UNIO_CRRD        = 0x06
UNIO_WRITE       = 0x6c
UNIO_WREN        = 0x96
UNIO_WRDI        = 0x91
UNIO_RDSR        = 0x05
UNIO_WRSR        = 0x6e
UNIO_ERAL        = 0x6d
UNIO_SETAL       = 0x67

UNIO_TSTBY = 600
UNIO_TSS    = 10
UNIO_THDR    = 5
UNIO_QUARTER_BIT = 10
UNIO_FUDGE_FACTOR = 5

UNIO_PIN = 8

usleep = lambda x: time.sleep(x / 1000000.0)

def UNIO_OUTPUT():
    gpio.setup(UNIO_PIN, gpio.OUT)

def UNIO_INPUT():
    gpio.setup(UNIO_PIN, gpio.IN)


def set_bus(state: bool):
    gpio.output(UNIO_PIN, state)

def read_bus():
    return bool(gpio.input(UNIO_PIN))

def unio_inter_command_gap():
  set_bus(1)
  usleep(UNIO_TSS + UNIO_FUDGE_FACTOR)

def unio_standby_pulse():
  set_bus(0)
  UNIO_OUTPUT()
  usleep(UNIO_TSS + UNIO_FUDGE_FACTOR)
  set_bus(1)
  usleep(UNIO_TSTBY + UNIO_FUDGE_FACTOR)

def rwbit(w: bool):
  set_bus(not w)
  usleep(UNIO_QUARTER_BIT)
  a = read_bus()
  usleep(UNIO_QUARTER_BIT)
  set_bus(w)
  usleep(UNIO_QUARTER_BIT)
  b = read_bus()
  usleep(UNIO_QUARTER_BIT)
  return b and not a

def read_bit():
  UNIO_INPUT()
  b = rwbit(1)
  UNIO_OUTPUT()
  return b

def send_byte(b: int, mak: bool):
    for _ in range(8):
        rwbit(b & 0x80)
        b = b << 1
        
    rwbit(mak)
    return read_bit()

def read_byte(mak: bool):
    data = 0
    UNIO_INPUT()
    for _ in range(8):
        data = (data << 1) | rwbit(1)
    UNIO_OUTPUT()
    rwbit(mak)
    if read_bit():
        return data
    raise ValueError('NoSAK on read')

def unio_send(data, length: int, end: bool):
    for i, word in enumerate(data):
        last_byte = end and (i + 1) == len(data)
        if not send_byte(word, last_byte):
            return False
    return True

def unio_read(length: int):
    data = []
    for i in range(length):
        last_byte = (i + 1) == length
        byte = read_byte(last_byte)
        data.append(byte)
    return data

def unio_start_header():
  set_bus(0)
  usleep(UNIO_THDR + UNIO_FUDGE_FACTOR)
  send_byte(UNIO_STARTHEADER, True)

class NanodeUNIO:
    def __init__(self, address: int):
        self._addr = address
        UNIO_OUTPUT()

    def read(self, address: int, length: int):
        cmd = [self._addr, UNIO_READ, address >> 8, address & 0xFF]
        unio_standby_pulse()
        with interrupt_guard.InterruptGuard():
            unio_start_header()
            if not unio_send(cmd, 4, False):
                return False, []

            return unio_read(length)

    def start_write(self, buffer, address: int, length: int):
        if ((address & 0x0f) + length) > 16:
            return False  # would cross page boundary
        
        cmd = [self._addr, UNIO_WRITE, address >> 8, address & 0xff]
        unio_standby_pulse()
        with interrupt_guard.InterruptGuard():
            unio_start_header()
            if not unio_send(cmd, 4, False):
                return False

            return unio_send(buffer, length, True)

    def enable_write(self):
        cmd = [self._addr, UNIO_WREN]
        unio_standby_pulse()
        with interrupt_guard.InterruptGuard():
            unio_start_header()
            return unio_send(cmd, 2, True)

    def disable_write(self):
        cmd = [self._addr, UNIO_WRDI]
        unio_standby_pulse()
        with interrupt_guard.InterruptGuard():
            unio_start_header()
            return unio_send(cmd, 2, True)

    def read_status(self):
        cmd = [self._addr, UNIO_RDSR]
        unio_standby_pulse()
        with interrupt_guard.InterruptGuard():
            unio_start_header()
            if not unio_send(cmd, 2, False):
                return False

            status = unio_read(1)
            return status[0]

    def write_status(self, status: int):
        cmd = [self._addr, UNIO_WRSR, status]
        unio_standby_pulse()
        with interrupt_guard.InterruptGuard():
            unio_start_header()
            return unio_send(cmd, 3, True)

    def await_write_complete(self):
        cmd = [self._addr, UNIO_RDSR]
        unio_standby_pulse()
        status = 0
        flag = True
        while flag and status & 0x01:
            unio_inter_command_gap()
            with interrupt_guard.InterruptGuard():
                unio_start_header()
                if not unio_send(cmd, 2, False):
                    return False

                status = unio_read(1)[0]
        return True

    def simple_write(self, buffer, address: int, length: int):
        while length > 0:
            wlen = length
            if ((address & 0x0F) + wlen) > 16:
                wlen = 16 - (address & 0x0F)
            if not self.enable_write():
                return False
            if not self.start_write(buffer, address, wlen):
                return False
            if not self.await_write_complete():
                return False
            buffer = buffer[wlen:]
            address += wlen
            length -= wlen 
        return True
