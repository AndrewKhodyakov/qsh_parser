"""
    uleb/leb python implimintation - tutorial:
        - https://en.wikipedia.org/wiki/LEB128
"""
#TODO возможно не надо выставлять бит подписи, и проверять его установку,
#надо сомтреть как python работет с отрицательными числами
import unittest
from itertools import count

class BaseLEB128:
    """
    base class for DRY
    """
    def __init__(self, base_byte_number):
        """
        base_byte_number: base byte coding number
        """
        self.base_byte_number = base_byte_number
        self.to_encode = None
        self.to_decode = None

    @property
    def __check_sign_bit(self):
        """
        Check number, for encoding
        """
        out = False
        if (self.__class__.__name__ in 'Sleb128') & (self.to_encode < 0):
            out = True
        return out

    def __preporate_bytes_for_encode(self):
        """
        Split input number into 7-bit group and add 1 on all group,
        excpet last group
        """
        end_flag = 1
        sign_bit = 0
        for byte_group in range(self.base_byte_number):
            if byte_group == (self.base_byte_number - 1):
                end_flag = 0
#                if self.__check_sign_bit:
#                    sign_bit = 64

            yield ((self.to_encode >> (byte_group*7)) & 127) |\
                ((128 | sign_bit)*end_flag)


    def encode(self, number_to_encode):
        """
        number_to_encode: naumber for encode in to uleb128
        """
        self.to_encode = number_to_encode
        step = count(1)
        out = 0

        for byte in self.__preporate_bytes_for_encode():
            out = out | byte << 8*(self.base_byte_number - next(step))

        return out.to_bytes(self.base_byte_number, byteorder='big')


    @property
    def __check_number_sign(self):
        """
        Check number sign
        """
        out = False
        if (self.__class__.__name__ in 'Sleb128') &\
            ((self.to_decode[self.base_byte_number - 1] & 64) == 64):
            out = True
        return out

    def decode(self, byte_to_decode):
        """
        byte_to_decode: byte to decode in to large number
        """
        self.to_decode = byte_to_decode
        step = count(1)
        out = 0

        strip_first_byte = [self.to_decode[byte_num] & 127\
            for byte_num in range(self.base_byte_number)]

        strip_first_byte.reverse()

        for byte in strip_first_byte:
            out = out | byte << 7*(self.base_byte_number - next(step))

        if self.__check_number_sign:
            out = - (1 << self.base_byte_number*7) | out
        return out


class Uleb128(BaseLEB128):
    """
    Unsigned LEB128 encode/decode class

    uleb128 - https://en.wikipedia.org/wiki/LEB128
    """
    pass


class Sleb128(BaseLEB128):
    """
    Signed LEB128 encode/decode class
    sleb128 - https://en.wikipedia.org/wiki/LEB128
    """
    pass


class TestUleb128EncodeDecode(unittest.TestCase):
    """
    Try etalon from - https://en.wikipedia.org/wiki/LEB128
    """
    def setUp(self):
        """
        save etalons
        """
        self.number = 624485
        self.bytes = b'\xe5\x8e&'
        self.uleb128 = Uleb128(3)

    def test_encode(self):
        """
        enocde
        """
        self.assertEqual(self.bytes, self.uleb128.encode(self.number))

    def test_decode(self):
        """
        decode
        """
        self.assertEqual(self.number, self.uleb128.decode(self.bytes))


class TestSleb128EncodeDecode(unittest.TestCase):
    """
    Try etalon from - https://en.wikipedia.org/wiki/LEB128
    """
    def setUp(self):
        """
        save etalons
        """
        self.number = -624485
        self.bytes = b'\x9b\xf1Y'
        self.sleb128 = Sleb128(3)

    def test_encode(self):
        """
        enocde
        """
        self.assertEqual(self.bytes, self.sleb128.encode(self.number))

    def test_decode(self):
        """
        decode
        """
        self.assertEqual(self.number, self.sleb128.decode(self.bytes))

if __name__ == "__main__":
    unittest.main()
