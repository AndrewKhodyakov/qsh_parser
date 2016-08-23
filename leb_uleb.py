#!/usr/bin/env python
# -*- coding: utf-8 -*-
#===============================================================================
"""
    Попытки_написать_кодировик_декодировщик_leb__uleb
"""
#===============================================================================
class ULeb128:
    """
    """
    def __init__(self):
        """
        """
        self.__shift = 7
        self.__input = None
        self.__output = None

    def encoding(self, integer):
        """
        """
        if isinstance(integer, int):
            raise TypeError('Type encoding input is int')

        self.__input = integer
        
        

    def dencoding(self, byte):
        """
        """
        pass

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

if __name__=="__main__":pass

