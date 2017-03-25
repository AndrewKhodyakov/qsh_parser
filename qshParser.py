#!/usr/bin/env python
# -*- coding: utf-8 -*-
#===============================================================================
"""
    Парсер_файлов_qsh по спецификации версии 4
"""
import os, sys
import itertools
from  collections  import namedtuple
import struct
from datetime import datetime, timedelta, date
from leb_128 import Uleb128, Sleb128


class General(Exception):
    def __init__(self, msg):
        self.msg = msg
        print(self.msg)

class FileNotExists(General):
    def __init__(self,msg):
        General.__init__(self, msg)

class FileSignatureError(General):
    def __init__(self,msg):
        General.__init__(self, msg)

class BaseTypes:
    """
    Base types - a don`t require to save condition
    """
    data_types = dict.fromkeys(\
        ['_byte', '_uint16', '_uint32', '_int64', '_datetime', '_double'])

    def __init__(self):
        """
            init  - setup data types and their params for decoding
        """
        for inst in self.data_types:
            self.__dict__[inst] = namedtuple(inst,['cursor_step','unpack_code'])

        self._byte.cursor_step = 1
        self._byte.unpack_code = 'B'

        self._uint16.cursor_step = 2
        self._uint16.unpack_code = None

        self._uint32.cursor_step = 4
        self._uint32.unpack_code = None

        self._int64.cursor_step = 8
        self._int64.unpack_code = 'q'

        self._double.cursor_step = self._int64.cursor_step
        self._double.unpack_code = 'd'

        self._datetime.cursor_step = self._int64.cursor_step
        self._datetime.unpack_code = self._int64.unpack_code

        self._uleb128 = Uleb128(self._uint32.cursor_step)
        self._sleb128 = Sleb128(self._int64.cursor_step)


    def _read(self, attr, stream):
        """
        Read value from stream by type
        """
        out = None
        if getattr(self, attr).unpack_code:
            out = struct.unpack(getattr(self, attr).unpack_code,
            stream.read(getattr(self, attr).cursor_step))
            if len(out) > 0:
                out = out[0]
        else:
            out = stream.read(getattr(self, attr).cursor_step)

        return out


    def read_byte(self, stream):
        """
        Read uint_16
        """
        return self._read('_byte', stream)

    def read_uint16(self, stream):
        """
        Read uint_16
        """
        return self._read('_uint16', stream)


    def read_uint32(self, stream):
        """
        Read uint_32
        """
        return self._read('_uint32', stream)


    def read_int64(self, stream):
        """
        Read int_64
        """
        return self._read('_int64', stream)


    def read_double(self, stream):
        """
        Read int_64
        """
        return self._read('_double', stream)


    def read_datetime(self, stream):
        """
        Read datetime
        ----------------
        Тип DateTime представляет собой число, показывающее количество
        100-наносекундных интервалов, которые прошли с полночи 00:00:00,
        1 января 0001 года. Соответствует свойству Ticks структуры DateTime
        из .NET версии 4. Сохраняется в поле типа int64
        """
        out = None
        nano_seconds = self._read('_int64', stream)
        if nano_seconds:
            out = (datetime(1, 1, 1) + timedelta(microseconds = nano_seconds/10))
        return out


    def read_uleb(self, stream):
        """
        Read uleb 128
        """
        return self._uleb128.decode_from_stream(stream, 'read', 1)


    def read_sleb(self, stream):
        """
        Read sleb 128
        """
        return self._sleb128.decode_from_stream(stream, 'read', 1)


    def read_string(self, stream):
        """
        Read utf8 encoded byte array 
        Тип String является комплексным и состоит из следующих компонентов:
        - uleb128 - длинна массива - число бит для чтения
        """
        return bytes.decode(stream.read(self.read_uleb(stream)))


class RealtiveType(BaseTypes):
    """
    It requires to stope last step value
    """
    def __init__(self):
        pass

class Growing(BaseTypes):
    """
    It requires to stope last step value
    """
    def __init__(self):
        pass


class GrowingDateTime(BaseTypes):
    """
    It requires to stope last step value
    """
    def __init__(self, start_time):
        pass


class DataStructReadingMethods(object):
    """
    Набор методов считывания данных встречающихся в файле
    """
    def __init__(self):
        """
        Сводим типы данных описанных в спецификации к прараметрам struct.unpack
        и шагам курсора
        """
        self.type_table = dict.fromkeys(['byte','uint16','uint32','int64',
                                        'double','Leb128','ULeb128','DateTime',
                                        'Relative','GrowingDateTime'])

        for k in self.type_table:
            self.type_table[k] = namedtuple(k,['cursor_step','unpack_code'])

        self.type_table['byte'].cursor_step = 1
        self.type_table['byte'].unpack_code = 'B'

        self.type_table['uint16'].cursor_step = 2 
#        self.type_table['uint16'].unpack_code = 

        self.type_table['uint32'].cursor_step = 4
#        self.type_table['uint32'].unpack_code = 

        self.type_table['int64'].cursor_step = 8 

        self.type_table['double'].cursor_step = 8
#        self.type_table['double'].unpack_code = 

        self.type_table['Leb128'].cursor_step = self.type_table['int64'].cursor_step
#        self.type_table['Leb128'].unpack_code =

        self.type_table['ULeb128'].cursor_step = self.type_table['uint32'].cursor_step
#        self.type_table['ULeb128'].unpack_code =

        self.type_table['DateTime'].cursor_step = self.type_table['int64'].cursor_step
        self.type_table['DateTime'].unpack_code ='q'

        self.type_table['Relative'].cursor_step = self.type_table['Leb128'].cursor_step
#        self.type_table['Relative'].unpack_code =

#        self.type_table['GrowingDateTime'].cursor_step =
#        self.type_table['GrowingDateTime'].unpack_code =


#        self.complex_type_table = dict.fromkeys(['String','Growing'])
#        self.complex_type_table['String'] = namedtuple(k,['len','unpack_code'])
#
#        self.type_table['FullInstrumentCode'] = namedtuple('FullInstrumentCode',['connector','ticker','auxcode','id','step'])
#



    def read_one_byte(self, stream):
        """
        Чтение одного ,byte
        """
        tmp = struct.unpack(self.type_table['byte'].unpack_code,
            stream.read(self.type_table['byte'].cursor_step))[0]
        return tmp

    def read_byte_array(self, stream, array_len):
        """
        Чтение массива бит utf8
        """
        string = bytes.decode(stream.read(array_len))
        return string

    def read_datetime(self, stream):
        """
        Чтение времени
        Тип DateTime представляет собой число, показывающее количество
        100-наносекундных интервалов, которые прошли с полночи 00:00:00,
        1 января 0001 года. Соответствует свойству Ticks структуры DateTime
        из .NET версии 4. Сохраняется в поле типа int64
        """
        date_str = struct.unpack(self.type_table['DateTime'].unpack_code,
            stream.read(self.type_table['DateTime'].cursor_step))[0]

        return (datetime(1, 1, 1) + timedelta(microseconds = date_str/10))

    def read_string(self, stream):
        """
        string - комплексный тип данных - состоит из:
            - ULeb128 - в котором написанно длина массива байт строки
            - byte[] - массив byte utf8
        Походу в версии 3 вместо Uleb128 - используется беззнаковое целое
длинной 8 бит
        """
#        string_len = struct.unpack(self.type_table['ULeb128'].unpack_code,
#            stream.read(self.type_table['ULeb128'].cursor_step))[0]
        string_len = self.read_one_byte(stream)

        string = self.read_byte_array(stream, string_len)
        return string

    def read_growing(self, stream):
        """
        Growing является комплексным и состоит из одного или двух компонентов:

            ULeb128 - разность между текущим и предыдущим значением; если
            данная разность меньше нуля или больше 268435454, в этом поле 
            указывается число 268435455, а значение разности указывается в 
            следующем поле

            Leb128 - разность между текущим и предыдущим значением, если
            предыдущее поле содержит число 268435455; в ином случае данное 
            поле отсутствует
        """
        first_path = stream.read(self.type_table['ULeb128'].cursor_step)
        print(first_path)
#        if 
#        second_path = 

    
class QshParser(object):
    """
    Собственно сам парсер - набор методов читающих части структуры файла:
        Структура файла:
        Заголовок файла
            - заголовок потока 1,
            .......... 
            - заголовок потока n(при наличии),
                - заголовок кадра 1,
                - данные кадра 1,
                .......... 
                - заголовок кадра n,
                - данные кадра n,
    """
    def __init__(self, path_to_file):
        """
        path_to_file - путь к файлу формата qsh
        """
        if not os.path.exists(path_to_file):
            msg = u'Путь к файлу {0} не найден'.format(path_to_file)
            raise FileNotExists(msg)

        self.path_to_file = path_to_file
        self.stream = open(self.path_to_file, 'rb')

        self.reading_methods = DataStructReadingMethods()

        self.file_header = namedtuple('FileHeader',
                                            ['signature',
                                            'format_version',
                                            'app_name',
                                            'user_comment',
                                            'time_record',
                                            'stream_count',
                                            'head_len',])

        self.streams_types = {
                                b'\x10':'Stock',
                                b'\x20':'Deals',
                                b'\x30':'Orders',
                                b'\x40':'Trades',
                                b' ':'Trades', #почему то так встречается во всех файлах Trades
                                b'\x50':'Messages',
                                b'\x60':'AuxInfo',
                                b'\x70':'OrdLog' }
        self.stream_headers = {}
        

        self.read_file_metadata() #подготовка к считываню данных 


    def __get_file_header(self):
        """
        Читаем заголовок файла
        Структура:
        byte[] - сигнатура файла = «QScalp History Data» 
            (только символы UTF8, без нуля в конце)
        byte - мажорная версия формата файла = 4
        String - имя приложения, с помощью которого записан данный файл
        String - произвольный пользовательский комментарий
        DateTime - дата и время начала записи файла (UTC)
        byte - количество информационных потоков в файле
        """
        self.file_header.signature =\
            self.reading_methods.read_byte_array(self.stream, 19)
                                            #тут хардкод, см описание функции
        if 'QScalp History Data' not in self.file_header.signature:
            msg = u'Ошибка сигнатуры файла - проверьте тип файла.'
            raise FileSignatureError(msg)


        self.file_header.format_version = self.reading_methods.read_one_byte(self.stream)
    
        self.file_header.app_name = self.reading_methods.read_string(self.stream)

        self.file_header.user_comment = self.reading_methods.read_string(self.stream)

        self.file_header.time_record = self.reading_methods.read_datetime(self.stream)

        self.file_header.stream_count = self.reading_methods.read_one_byte(self.stream)

        self.file_header.head_len = self.stream.tell()


    def __get_stream_header(self):
        """
        Читаем заголовок потока
        Структура:
        byte - идентификатор потока:
            Stock = 0x10 Deals = 0x20 Orders = 0x30 Trades = 0x40
            Messages = 0x50 AuxInfo = 0x60 OrdLog = 0x70
        String -полный код инструмента, которому соответствует поток; для
            потока «Messages» отсутствует
        """
        stream_header_struct = namedtuple(
            'Stream_header',[
                    'stream_type',
                    'instrument_code',
                    'name'
            ]
        )

        for i in range(self.file_header.stream_count):
            stream_id = self.stream.read(1) #здесь чтение без преобразования

            self.stream_headers[stream_id] = stream_header_struct
            self.stream_headers[stream_id].stream_type = stream_id
            self.stream_headers[stream_id].name = self.streams_types[stream_id]

            if stream_id != '\x50': #для сообщений названия инструмента нет
                self.stream_headers[stream_id].instrument_code =\
                     self.reading_methods.read_string(self.stream)

    
    def __get_frame_header(self):
        """
        Читаем заголовок кадра
        Структура:
        GrowDateTime - штамп времени (UTC)
        byte - номер потока (начинающийся с нуля) в соответствии со 
            списком заголовков потоков, которому принадлежит кадр; 
            указывается,только если файл содержит более одного потока
        """
        print('\n' + str(self.stream.tell()))

    def __get_frame_data(self):
        """
        Читаем данные из  кадра
        """
        pass

    def read_file_metadata(self):
        """
        Сначала будут прочитанны заголовки файла и потоков и собранны мета данные о файле
        """
        self.stream = open(self.path_to_file, 'rb')
        self.__get_file_header()
        self.__get_stream_header()
        self.__get_frame_header()

    def __next(self):
        """
        Метод дающий значения при дергании его в цикле
        """
        #TODO подумай как тут лучше сделать - отдавать по шагово или сразу все
        #читать и отдавать
        pass
    
    def print_file_metadata(self):
        """
        Вывод считанного заголовка файла
        """
        print(u'File signature:\
                           {0}'.format(self.file_header.signature))
        print(u'Format version:\
                           {0}'.format(self.file_header.format_version))
        print(u'Application name:\
                           {0}'.format(self.file_header.app_name))
        print(u'User comment:\
                           {0}'.format(self.file_header.user_comment))
        print(u'Time start record:\
                           {0}'.format(self.file_header.time_record))
        print(u'Data stream count:\
                            {0}'.format(self.file_header.stream_count))


    def print_strems_headers(self):
        """
        Вывод информации о потоках имеющихся в файле
        """
        for k in self.stream_headers:
            print(u'-'*40)
            print(u'Stream name:\
                           {0}'.format(self.stream_headers[k].name))
            print(u'Stream code:\
                           {0}'.format(self.stream_headers[k].stream_type))
            print(u'Stream instrument code:\
                           {0}'.format(self.stream_headers[k].instrument_code))
            print(u'-'*40 + u'\n')


def _read_mode(path_to_file):
    """
    read from file
    path_to_file: full path to file
    """
    qsh = QshParser(path_to_file)
    qsh.read_file_metadata()
    qsh.print_file_metadata()
    qsh.print_strems_headers()


def _run_unittests():
    """
    run tests
    """
    from io import BytesIO
    import unittest

    class TestBaseTypes(unittest.TestCase):
        """
        BaseTypes tests
        """
        def setUp(self):
            """
            save etalons
            """
            self.one_byte = BytesIO(b'\x04')
            self.string = BytesIO(b'\x0eQshWriter.5488')
            self.date_time = BytesIO(b'\x00wb\x9c\xcd"\xd2\x08')
            self.base = BaseTypes()

        def test_a_simple(self):
            """
            test elementary types
            """
            self.assertEqual(self.base.read_byte(self.one_byte), 4)
            self.assertEqual(self.base.read_string(self.string), 'QshWriter.5488')
            self.assertEqual(self.base.read_datetime(self.date_time).date(),date(year=2015, month=3, day=2))

    suite = unittest.TestSuite()
    suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(TestBaseTypes))
    unittest.TextTestRunner().run(suite)

def _if__name__is__main():
    """
    main func
    """
    arg = sys.argv
    help_msg = 'Input next arguments:\n'
    help_msg = help_msg + '\t' + '--run_self_test - for run unittests;\n'
    help_msg = help_msg + '\t' + '--read_file full_path_to_file - for read from file.\n'
    if len(arg) == 1:
        print(help_msg)
    else:
        if '--run_self_test' in arg[1]:
            _run_unittests()
        elif '--read_file' in arg[1]:
            _read_mode(arg[2])
        else:
            print(help_msg)


if __name__ == "__main__":
    _if__name__is__main()
