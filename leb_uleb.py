#!/usr/bin/env python
# -*- coding: utf-8 -*-
#===============================================================================
"""
    Попытки_написать_кодировик_декодировщик_leb__uleb
    Во всех операциях сдвиг применяется:

    При кодировании <<:
        для определения того что делать дельше
        - если старший бит (результат сдвига - остаток и от него можно отрезать
            дальше -  продолжаем числоб и на следующей итерации рассмтариваем
            именно остаток от сдивага);

    При декодировании >>:
        для сборки большого числа и выделения новых ячеек в нем
"""
from types import GeneratorType
#===============================================================================
int_to_str_of_bits = lambda integer: bin(integer).split('b')[1]
zero_padding = lambda str_of_bites, shift:\
    '0' * ((shift + 1) - len(str_of_bites)) + str_of_bites
unity_padding = lambda seven_bits: '1' + seven_bits
get_seven_bits = lambda str_of_bites: str_of_bites[-7:]

class ULeb128:
    """
    Тип данных ULeb128 - согласно алгоритму:
        https://en.wikipedia.org/wiki/LEB128
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
        self.__output = []
        if not isinstance(integer, int):
            raise TypeError('Type encoding input is not int')

        self.__input = integer
        #TODO  здесь надо убрать все преобразования из целого в строку и сплты
        #- работу  продолэать исключительно с интом и бинращиной

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
                        get_seven_bits(
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
            

    def decoding(self, byte_stream):
        """
        byte_stream: byte generator (генератор байт, отадет их по одной)
        """
        self.__output = 0
        if not isinstance(byte_stream, GeneratorType):
            raise TypeError('Type decoding input is GeneratorType')

        value = 0
        count = 0 #множитель на сколько сдвигать послежующий байт

        while True:
            try:
                byte = next(byte_stream)
            except StopIteration:
                break

            if value == 0:
                #если это первый байт из числа - берем семь младших байт и сохраняем его отдельно
                value = value | (byte & 127)
            else:
                #если следующий сдвигаем влево, берем семь младших байт и прибовляем туда предидущий
                rest = ((byte & 127) << (self.__shift * count))
                value = rest | value 

            if (byte & 128) == 0:
                break

            count += 1
                    

        self.__output = value

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
    Тип данных Leb128 - согласно алгоритму:
        https://en.wikipedia.org/wiki/LEB128
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

