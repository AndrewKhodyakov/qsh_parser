#!/usr/bin/env python
# -*- coding: utf-8 -*-
#===============================================================================
"""
    Попытки_написать_кодировик_декодировщик_leb__uleb
"""
from types import GeneratorType
#===============================================================================
#def shifting(integer, shift):
#    """
#    Сдвиг на лево
#    integer: целое число для проведения одного шага вычислений
#    shift: коллличесвто бит на которые неодбходимо производить сдвиг
#    """
#
#    int_to_str_of_bits = lambda integer: bin(integer).split('b')[1]
#    zero_padding = lambda str_of_bites, shift:\
#        '0' * ((shift + 1) - len(str_of_bites)) + str_of_bites
#    unity_padding = lambda seven_bits: '1' + seven_bits
#    get_seveb_bits = lambda str_of_bites: str_of_bites[-7:]
#    
#
#    result = []
#    integer = integer
#    shift = shift
#    while True:
#        rest = bin(integer >> shift)
#        if rest == '0b0': #exit
#            result.append(
#                zero_padding(
#                    int_to_str_of_bits(integer), shift
#                )
#            )
#            return result
#            break
#
#        else: #go on
#            result.append(
#                unity_padding(
#                    get_seveb_bits(
#                        int_to_str_of_bits(integer)
#                    )
#                )
#            )
#            integer = int(rest, 2)

int_to_str_of_bits = lambda integer: bin(integer).split('b')[1]
zero_padding = lambda str_of_bites, shift:\
    '0' * ((shift + 1) - len(str_of_bites)) + str_of_bites
unity_padding = lambda seven_bits: '1' + seven_bits
get_seveb_bits = lambda str_of_bites: str_of_bites[-7:]

class ULeb128:
    """
    """
    def __init__(self):
        """
        self.__shift: колличество бит для кодирования (7 по-умолчанию)
        self.__input: число поданное на вход
        self.__output: результат кодирвания в uleb128
        """
        self.__shift = 7
        self.__input = None
        self.__output = []

    def encoding(self, integer):
        """
        Кодирование числе в формат uleb128
        integer: - целое число для кодирования
        """
        if not isinstance(integer, int):
            raise TypeError('Type encoding input is not int')

        self.__input = integer

        while True:
            rest = bin(self.__input >> self.__shift)
            if rest == '0b0': #exit
                self.__output.append(
                    zero_padding(
                        int_to_str_of_bits(self.__input), self.__shift
                    )
                )
                break
        
            else: #go on
                self.__output.append(
                    unity_padding(
                        get_seveb_bits(
                            int_to_str_of_bits(self.__input)
                        )
                    )
                )
                self.__input = int(rest, 2)

        #TODO здесь определиться с тем как перкодировать полученное значенеие
        #при записи в файл
        self.__output = [hex(int(i, 2)) for i in self.__output]
          
    @property
    def result(self):
        """
        Return result
        """
        return self.__output
            

    def dencoding(self, byte_stream):
        """
        byte_stream: byte generator (генератор байт, отадет их по одной)
        """
        if not isinstance(byte_stream, GeneratorType):
            raise TypeError('Type decoding input is GeneratorType')

        #они записаны задом на перед, поэтому надо читать каждый до тех пор
        #пока не появится число начинающиеся на 0
        while True:
            
            if higt_bit == '0':
                break

    def __str_(self):
        """
        Detail short
        """
        print('ULeb_128_decoder\encoder')

    def __rep__(self):
        """
        Detail full
        """
        print('ULeb_128_decoder\encoder : input - {0}, output - {1}'.format(
            self.__input,
            self.__output
        ))

class Leb128:
    """
    """
    def __init__(self):
        """
        """
        pass

    def encoding(self, integer):
        """
        """
        pass

    def dencoding(self, byte):
        """
        """
        pass

    def __str_(self):
        print('ULeb_128_decoder\encoder')
#===============================================================================

if __name__ == "__main__":pass

