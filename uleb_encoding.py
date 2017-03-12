"""
    uleb/leb python implimintation - tutorial:
        - https://en.wikipedia.org/wiki/LEB128
"""
import unittest
from itertools import count
from itertools import chain

class BaseLEB128:
    """
    base class for DRY
    """
    def __init__(self, base_byte_number):
        """
        base_byte_number: base byte encoding number
        """
        if not isinstance(base_byte_number, int):
            msg = 'Base number should be a integer'
            raise TypeError(msg)

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

        if self.__check_sign_bit:
            sign_bit = 1
        else:
            sign_bit = 0

        for bite_group in range(self.base_byte_number):
            if bite_group == (self.base_byte_number - 1):
                end_flag = 0

            yield ((self.to_encode >> (bite_group*7)) & 127) |\
                ((128 | sign_bit)*end_flag)


    def encode(self, number_to_encode):
        """
        number_to_encode: naumber for encode in to uleb128
        """
        if not isinstance(number_to_encode, int):
            msg = 'Number to encode should be integer'
            raise TypeError(msg)

        if (self.base_byte_number * 8) < number_to_encode.bit_length():
            msg = 'Base_byte_number - {} is not enough for encoding - {}'.\
                format(self.base_byte_number, number_to_encode)
            raise OverflowError(msg)

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
            ((self.to_decode[len(self.to_decode) - 1] & 64) == 64):
            out = True
        return out


    def decode(self, byte_to_decode):
        """
        bytes_to_decode: bytes for decode in to large number
        """
        if not isinstance(byte_to_decode, bytes):
            msg = 'Value to decode should be a bytes type'
            raise TypeError(msg)

        self.to_decode = byte_to_decode
        byte_number = len(self.to_decode)
        step = count(1)
        out = 0

        strip_first_byte = [byte & 127 for byte in self.to_decode]

        strip_first_byte.reverse()

        for byte in strip_first_byte:
            out = out | byte << 7*(byte_number - next(step))

        if self.__check_number_sign:
            out = -(1 << byte_number*7) | out

        return out


    def decode_from_stream(self, stream, method=None):
        """
        If bytes reading from stream
        stream: stream obj
        method: method to get data
        """
        if not method:
            msg = 'Set method to get data from stream'
            raise AttributeError(msg)

        if not hasattr(stream, method):
            msg = 'Stream {} didnt have method {}'.format(stream, method)
            raise AttributeError(msg)

        out = 0
        step = count(0)

        while True:
            byte = getattr(stream, method)()
            out = out | (byte << 8*next(step))

            if (byte & 128) == 0:
                break

        out = out.to_bytes(next(step), byteorder='little')
        return  self.decode(out)


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
        self.stream = chain(self.bytes)

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

    def test_decode_stream(self):
        """
        Test for stream decoding
        """
        self.assertEqual(self.number, self.sleb128.decode_from_stream(
            self.stream, '__next__'))

if __name__ == "__main__":
    unittest.main()
