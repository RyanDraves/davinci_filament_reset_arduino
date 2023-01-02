# from RPi import GPIO as gpio
from __future__ import annotations
import RPi.GPIO as gpio

from . import nanode_unio
import logging
import time

NANODE_MAC_DEVICE = 0xa0
NANODE_MAC_ADDRESS = 0xfa

CODE = 0x00 # 1 Byte
MATERIAL = 0x01 # 1 Byte
COLOR = 0x02  # 2 Bytes
DATE = 0x05 # 4 Bytes
TOTALLEN = 0x08 # 4 Bytes
NEWLEN = 0x0C # 4 Bytes
HEADTEMP = 0x10 # 2 Bytes
BEDTEMP = 0x12 # 2Bytes
MLOC = 0x14 # 2 Bytes
DLOC = 0x16 # 2 Bytes
SN = 0x18	 # 12 Bytes
CRC = 0x24 # 2 Bytes
LEN2 = 0x34 # 4 Bytes

def increment_serial(buffer: list[int], address: int, length: int) -> int:
    buf = bytes(buffer)
    serial = int.from_bytes(buf, byteorder='big')
    new_serial = serial + 1
    logging.info(f'Read serial of {serial}')
    return new_serial

def dump_eeprom(unio: nanode_unio.NanodeUNIO, address: int, length: int) -> None:
    unio = nanode_unio.NanodeUNIO(NANODE_MAC_DEVICE)

    buf = unio.read(address, length)
    
    for i in range(0, 128, 16):
        hex_str = ''
        for j in range(16):
            hex_str += hex(buf[i + j])[2:] + ' '
        print(f'{hex(i)}: {hex_str}')

'''
These are the values to be written to the EEPROM
Make sure only one is uncommented.
By default its set for the starter ABS cartdridge with 120m of filament 

Verified with firmware 1.1.I
'''

# Value to write to the EEPROM for remaining filament lenght
# Default Starter Cartdridge is 120m
x = [0xc0, 0xd4, 0x01, 0x00]  # 120m
# char x[] = {0x80,0xa9,0x03,0x00}  # 240m
# char x[] = {0x80,0x1a,0x06,0x00}  # 400m

# extruder temp, default is 210 C for ABS
et = [0xd2, 0x00]  # 210 C 
# char et[] = {0xe6,0x00}  # 230 C
# char et[] = {0xf5,0x00}  # 245 C
# char et[] = {0xfa,0x00}  # 250 C

# bed temp 90 degrees, default ABS
bt = [0x5a, 0x00]  # 90C
# char bt[] = {0x32,0x00}  # 50C
# char bt[] = {0x28,0x00}  # 40C

# Materials

# char mt[] = {0x41}  # ABS
mt = [0x50]  # PLA
# char mt[] = {0x46}  # Flex


sr = 0
unio = nanode_unio.NanodeUNIO(NANODE_MAC_DEVICE)

if __name__ == '__main__':
    gpio.setmode(gpio.BOARD)

    while True:
        logging.info('Testing connection to Da Vinci EEPROM chip')
        if unio.read_status():
            break
        time.sleep(1)

  
    logging.info("Da Vinci EEPROM found...")
    logging.info("Reading the Davinci EEPROM Contents...")
    dump_eeprom(unio, 0,128)
        
    # Read the serial number
    buf = unio.read(SN, 12)
    # Increment the serial number
    new_serial = increment_serial(buf, 0, 12)	

    logging.info("Press enter to update EEPROM...")
    input()
    
    logging.info("Updating EEPROM...")
    unio.simple_write(x, TOTALLEN, 4)
    unio.simple_write(x, NEWLEN, 4)
    unio.simple_write(et, HEADTEMP, 2) # extruder temp
    unio.simple_write(bt, BEDTEMP, 2) # bed temp
    unio.simple_write(mt, MATERIAL, 1) # Material
    
    # Write the serial number
    unio.simple_write(buf, SN, 12) #Serial Number
    unio.simple_write(x, LEN2, 4)
    # same block from offset 0 is offset 64 bytes
    unio.simple_write(x, 64 + TOTALLEN, 4)
    unio.simple_write(x, 64 + NEWLEN, 4)
    unio.simple_write(et,64 + HEADTEMP, 2) # extruder temp
    unio.simple_write(bt,64 + BEDTEMP, 2) # bed temp
    unio.simple_write(mt,64 + MATERIAL, 1) # Material
    # Write the serial number
    unio.simple_write(buf, 64 + SN, 12) #Serial Number
    unio.simple_write(x, 64 + LEN2, 4)

    logging.info("Dumping Content after modification...")
    dump_eeprom(0, 128)

    gpio.cleanup()
