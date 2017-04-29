#!/usr/bin/env python
# -*- coding: utf-8 -*-
#===============================================================================
"""
    Парсер_файлов_qsh по спецификации версии 4
"""
import os, sys
import json
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
    def __init__(self, msg):
        General.__init__(self, msg)

class FileSignatureError(General):
    def __init__(self, msg):
        General.__init__(self, msg)

class TouchMethodNoCall(General):
    def __init__(self, msg):
        super().__init__(msg)

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
        try:
            if getattr(self, attr).unpack_code:
                out = struct.unpack(getattr(self, attr).unpack_code,
                stream.read(getattr(self, attr).cursor_step))
                if len(out) > 0:
                    out = out[0]
            else:
                out = stream.read(getattr(self, attr).cursor_step)

        except Exception as e:
            msg = \
            'Got exception - {0}, details:\n\t- cursor position {1}\n;\t- file {2}'.\
            format(e, stream.tell(), stream.name)
            raise Exception(msg)

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


class RelativeType(BaseTypes):
    """
    It requires to stope last step value
    """
    def __init__(self):
        """
        _last: previos
        _sleb128: base type
        """
        super(RelativeType, self).__init__()
        self._last = 0

    def read(self, stream):
        """
        Тип Relative представляет собой число, закодированное в формате Leb128,
        показывающее разность между текущим значением и предыдущим.
        Первая разность берется относительно нуля.
        """
        out = None
        tmp = self.read_sleb(stream)
        out = tmp - self._last
        self._last = tmp
        return out

class Growing(BaseTypes):
    """
    It requires to stope last step value
    """
    def __init__(self):
        """
        Тип Growing является комплексным и состоит из одного или двух компонентов:
        uleb128:
            разность между текущим и предыдущим значением;
            если данная разность меньше нуля или больше 268435454,
            в этом поле указывается число 268435455, а значение разности указывается
            в следующем поле
        selb128:
            разность между текущим и предыдущим значением, если предыдущее поле
            содержит число 268435455; в ином случае данное поле отсутствует
        """
        super().__init__()
        self._last = 0

    def read(self, stream):
        """
        """
        out = None
        tmp = self.read_uleb(stream)
        if tmp >= 268435454:
            tmp = self.read_sleb(stream)

        out  = tmp - self._last
        self._last = out
        return out

class GrowingDateTime:
    """
    It requires to store last step value
    """
    def __init__(self, start_time=None):
        """
        Тип GrowDateTime представляет собой количество миллисекунд,
        которые прошли с полночи 00:00:00, 1 января 0001 года.
        Соответствует свойству Ticks структуры DateTime из .NET версии 4,
        деленому на константу TimeSpan.TicksPerMillisecond.
        Сохраняется в поле типа Growing.

        start_time: начало отсчета 
        """
        if start_time:
            self._start = start_time
        else:
            self._start = datetime(1, 1, 1)

        self._base = Growing()

    def read(self, stream):
        """
        После долгих экспериментов остановился на следующей схеме:
            Growing - это количество миллисекунд от стартового времени 
            ссчитанного в заголовке файла.
        """
        delta = timedelta(microseconds=(self._base.read(stream)*1000))
        if delta.days > 1:
            self._start = self._start + delta
            return self._start
        else:
            return self._start + delta

class AbsStruct:
    """
    abstruct
    """
    def __init__(self):
        """
        init
        """
        self._base = BaseTypes()

    def set_attr(self, attr_list, sub_attr_list):
        """
        set attr
        """
        for key in attr_list:
            setattr(self, key, namedtuple(key, sub_attr_list))

class Stock(AbsStruct):
    """
    Stock data
    """
    def __init__(stream):
        """
        set quotes count
        """
        super().__init__()
        self.quotes_count = BaseTypes().read_sleb(stream)
        self._quote = namedtuple('Quote', ['rate','volume'])
        self.quotes = None

    def set_quotes(self, stream):
        """
        set quotes values
        """
        pass

    def update_quotes(self, stream):
        pass

class Trades(AbsStruct):
    """
    Trades stream
    """
    def __init__(self):
        """
        create data struct
        """
        super().__init__()
        self.set_attr(['_trade_type', '_exchange_date_time', '_exchange_trade_number',\
            '_bid_number', '_transaction_price', '_transaction_volume', '_open_interest'],
            ['value', 'data_type', 'bit_mask'])

        self._trade_type.bit_mask = 3
        self._trade_type.value = None

        self._exchange_date_time.data_type = GrowingDateTime()
        self._exchange_date_time.bit_mask = 4
        self._exchange_date_time.value = None

        self._exchange_trade_number.data_type = Growing()
        self._exchange_trade_number.bit_mask = 8
        self._exchange_trade_number.value = None

        self._bid_number.data_type = RelativeType()
        self._bid_number.bit_mask = 16
        self._bid_number.value = None

        self._transaction_price.data_type = RelativeType()
        self._transaction_price.bit_mask = 32 
        self._transaction_price.value = None

        self._transaction_volume.data_type = self._base
        self._transaction_volume.bit_mask = 64
        self._transaction_volume.value = None

        self._open_interest.data_type = RelativeType()
        self._open_interest.bit_mask = 128
        self._open_interest.value = None


    def read(self, stream):
        """
        stream
        """
        mask = self._base.read_byte(stream)

        self._set_trade_direction(mask, stream)

        for key in ['_exchange_date_time', '_exchange_trade_number',\
            '_bid_number', '_transaction_price', '_transaction_volume', '_open_interest']:
            attr = getattr(self, key)

            if (mask & attr.bit_mask) == attr.bit_mask:
                if key == '_transaction_volume':
                    attr.value = attr.data_type.read_sleb(stream)
                else:
                    attr.value = attr.data_type.read(stream)

            elif (mask & attr.bit_mask) == 0:
                pass

            else: 
                msg = 'Can`t read {} in file {} - position {}'.format(\
                    key, stream.name, stream.tell())
                raise TypeError(msg)


    def _set_trade_direction(self, mask, stream):
        """
        Устанавливаем направление сделки
        mask: маска
        """
        if (mask & self._trade_type.bit_mask) == 0:
            self._trade_type.value = 'UNKNOWN'

        elif (mask & self._trade_type.bit_mask) == 1:
            self._trade_type.value = 'ASK'

        elif (mask & self._trade_type.bit_mask) == 2:
            self._trade_type.value = 'BID'

        else:
            msg = 'Can`t defaune trade direction file: {} - position: {}'.\
                format(stream.name, stream.tell())
            raise TypeError(msg)

    @property
    def data(self):
        """
        Convert all data to dict
        """
        out = {}
        for key in ['_trade_type', '_exchange_date_time', '_exchange_trade_number',\
        '_bid_number', '_transaction_price', '_transaction_volume', '_open_interest']:
            tmp = getattr(self, key).value
            if key == '_exchange_date_time':
                tmp = tmp.isoformat()

            out[key.strip('_')] = tmp

        return out

    def __repr__(self):
        """
        Вывод данных об одной сделке
        """
        return json.dumps(self.data)


class Header(AbsStruct):
    """
    file header data type
    """
    _attrs = ['_signature', '_format_version', '_app_name','_user_comment',\
            '_record_start_time', '_stream_count', '_head_len']
    _sub_attrs = ['value', 'read']

    def __init__(self):
        """
        init
        """
        super().__init__()
        self.set_attr(self._attrs, self._sub_attrs)

        for attr in self._attrs:
            getattr(self, attr).value = None

        self._signature.read = self._base.read_byte
        self._format_version.read = self._base.read_byte
        self._app_name.read = self._base.read_string
        self._user_comment.read = self._base.read_string
        self._record_start_time.read = self._base.read_datetime
        self._stream_count.read = self._base.read_byte

    def read(self, stream):
        """
        read header
        """
        for i in range(19):
            if self._signature.value is None:
                self._signature.value = ''
            _tmp = self._signature.read(stream)
            self._signature.value = self._signature.value + chr(_tmp)

        for key in  ['_format_version', '_app_name', '_user_comment',
            '_record_start_time', '_stream_count']:
            getattr(self, key).value = getattr(self, key).read(stream)

        self._head_len = stream.tell()

    @property
    def data(self):
        """
        get dict
        """
        out = {}
        for attr in self._attrs:
            if attr == '_head_len':
                _tmp = getattr(self, attr)
            else:
                _tmp = getattr(self, attr).value
            out[attr.strip('_')] = _tmp

        return out

    def __repr__(self):
        """
        instance print format
        """
        out = '\tHeader:\n'
        for attr in self._attrs:
            if attr == '_head_len':
                rest = str(getattr(self, attr)) + '\n'
            else:
                rest = str(getattr(self, attr).value) + '\n'

            out = out + '\t'*2 + attr.strip('_') + ' :: ' + rest

        return out

class Stream(AbsStruct):
    """
    read stream
    """
    _attrs = ['_type', '_tool']
    _sub_attrs = ['value', 'read']

    def __init__(self):
        """
        init
        """
        super().__init__()
        self.set_attr(self._attrs, self._sub_attrs)
        for attr in self._attrs:
            getattr(self, attr).value = None

        self._type.read = self._base.read_byte
        self._tool.read = self._base.read_string


    def read(self, stream):
        """
        read
        """
        _tmp = self._type.read(stream)
        if _tmp not in [16, 32]:
            _msg = 'Unsupported stream type - {}'.format(_tmp)
            raise FileSignatureError(_msg)
        if _tmp == 16:
            self._type.value = 'Stock'
        elif _tmp == 32:
            self._type.value = 'Deals'

        self._tool.value = self._tool.read(stream)

    @property
    def data(self):
        """
        get dict
        """
        out = {}
        for attr in self._attrs:
             out[attr.strip('_')] = getattr(self, attr).value
        return out

    def __repr__(self):
        """
        instance print format
        """
        out = '\tStream:\n'
        for attr in self._attrs:
            out = out + '\t'*2 + attr.strip('_') + ' :: ' + \
                getattr(self, attr).value + '\n'
        return out

class Frame(AbsStruct):
    """
    frame
    """
    _attrs = ['_grow_dt', '_stream']
    _sub_attrs = ['value', 'read']

    def __init__(self, growing_dt):
        """
        init
        """
        super().__init__()
        self.set_attr(self._attrs, self._sub_attrs)
        
        for attr in self._attrs:
            getattr(self, attr).value = None

        self._grow_dt.read = growing_dt.read
        self._stream.read = self._base.read_byte

    def read(self, stream, one_stream=True):
        """
        read
        """
        self._grow_dt.value = self._grow_dt.read(stream)
        if not one_stream:
            self._sub_attrs.value = self._sub_attrs.read(stream)

    @property
    def data(self):
        """
        get data
        """
        return {attr.strip('_'):getattr(self, attr).value for attr in self._attrs}

    def __repr__(self):
        """
        pratty print
        """
        _tmp = {}
        for attr in self.data:
            if '_grow_dt' in attr:
                _tmp[attr.strip('_')] = getattr(self, attr).value.isoformat()
            else:
                _tmp[attr.strip('_')] = getattr(self, attr).value

        return json.dumps(_tmp)

class QSHParser:
    """
        Парсер:
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

        self._io_stream = open(path_to_file, 'rb')
        self._header = Header()
        self._stream = Stream()
        self._stream_dt = None
        self._pyload = None

    def touch(self):
        """
        Read header and stream
        """
        self._header.read(self._io_stream)
        if self._header.data.get('stream_count') > 1:
            _msg = 'More than one stream in file {}'.format(self._stream.name)
            raise FileSignatureError(_msg)

        self._stream_dt = GrowingDateTime(self._header.data.get('_record_start_time'))
        self._stream.read(self._io_stream)

        if self._stream.data.get('type') == 'Stock':
            self._pyload = Stock()

        elif self._stream.data.get('type') == 'Deals':
            self._pyload = Trades()

    def read(self):
        """
        Read one frame data
        """
        if self._stream_dt is None:
            _msg = 'Call touch method at first'
            raise TouchMethodNoCall(_msg)

        _frame = Frame(self._stream_dt)
        _frame.read(self._io_stream)
        self._pyload.read(self._io_stream)
        return self._pyload.data

    def __repr__(self):
        """
        print format
        """
        if self._stream_dt is None:
            _rest = '\n\tNo inforamtion, call touch method.'
        else:
            _rest = '\n' + str(self._header) + '\n' + str(self._stream)
        return  'File: {}, cursor position: {}'.\
            format(self._io_stream.name, self._io_stream.tell()) + _rest
        

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

    class TestTypeClassess(unittest.TestCase):
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

            self.relative_data_one = BytesIO(b'\x9b\xf1Y')
            self.relative_data_two = BytesIO(b'\x9b\xf1Y')
            self.growing_uleb_one = BytesIO(b'\xe5\x8e&')
            self.growing_uleb_two = BytesIO(b'\xe5\x8e&')
            self.growing_uleb_sleb = BytesIO(b'\xfe\xff\xff\x7f\x01')
            self.growing_datetime_data = BytesIO(b'\xb9$')

            self.trades_data = BytesIO(\
                b'\xad@f\xff\xff\xff\x7f\x98\xca\xe9\xe0\xee\xb9\x0e\x92\xf7\x00\n')
            self.header_data = BytesIO(\
                b'QScalp History Data\x04\x0eQshWriter.5488\x14ITinvest QSH Service\x00wb\x9c\xcd"\xd2\x08\x01')
            self.stream_data = BytesIO(b' \x14SmartCOM:GAZP:::0.01')
            self.frame_data = BytesIO(b'\xad@')

            self.base = BaseTypes()
            self.relative = RelativeType()
            self.growing = Growing()
            self.base_time = datetime.now()
            self.growing_datetime = GrowingDateTime(self.base_time)
            self.trade = Trades()
            self.header = Header()
            self.stream = Stream()

        def test_a_simple(self):
            """
            test elementary types
            """
            self.assertEqual(self.base.read_byte(self.one_byte), 4)
            self.assertEqual(self.base.read_string(self.string), 'QshWriter.5488')
            self.assertEqual(self.base.read_datetime(self.date_time).date(),date(year=2015, month=3, day=2))

        def test_b_complex(self):
            """
            test complex types
            """
            #relative
            self.relative.read(self.relative_data_one)
            self.assertEqual(self.relative.read(self.relative_data_two), 0)

            #growing
            self.growing.read(self.growing_uleb_one)
            self.assertEqual(self.growing.read(self.growing_uleb_two), 0)

            self.assertEqual(self.growing.read(self.growing_uleb_sleb), 1)

            #growing datetime
            self.assertEqual((self.growing_datetime.read(self.growing_datetime_data)\
                - self.base_time).seconds, 4)

        def test_c_data_struct(self):
            """
            test data struct
            """
            grow_dt = GrowingDateTime(self.base_time)
            grow_dt.read(self.trades_data)
            self.trade.read(self.trades_data)
            self.assertDictEqual(self.trade.data, 
                {"trade_type": "BID", "exchange_date_time": "2015-03-02T09:59:59",\
                "exchange_trade_number": None, "bid_number": None,\
                "transaction_price": 15250, "transaction_volume": 10,\
                "open_interest": None})

        def test_d_file_header(self):
            """
            test file header reading
            """
            self.header.read(self.header_data)
            self.assertTrue(self.header._signature.value == 'QScalp History Data')
            self.assertTrue(self.header._format_version.value == 4)
            self.assertTrue(self.header._app_name.value == 'QshWriter.5488')
            self.assertTrue(self.header._user_comment.value == 'ITinvest QSH Service')
            self.assertTrue(self.header._record_start_time.value ==\
                datetime(year=2015, month=3, day=2, hour=6, minute=59, second=50))
            self.assertTrue(self.header._stream_count.value == 1)
            self.assertTrue(self.header._head_len == 65)

        def test_e_stream_header(self):
            """
            test stream header
            """
            self.stream.read(self.stream_data)
            self.assertTrue(self.stream._type.value == 'Deals')
            self.assertTrue(self.stream._tool.value == 'SmartCOM:GAZP:::0.01')

        def test_f_stream_header(self):
            """
            test frame
            """
            frame = Frame(self.growing_datetime)
            frame.read(self.frame_data)
            _tmp = frame.data.get('grow_dt') - self.base_time
            self.assertTrue(str(_tmp) in '0:00:08.237000')

    suite = unittest.TestSuite()
    suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(TestTypeClassess))
    unittest.TextTestRunner().run(suite)

def _if__name__is__main():
    """
    main func
    """
    arg = sys.argv
    help_msg = """Input next arguments:\n
        --run_self_test - for run unittests;\n
        --read_file full_path_to_file - for read from file.\n"""

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
