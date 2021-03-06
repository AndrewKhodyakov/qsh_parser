#!/usr/bin/env python
# -*- coding: utf-8 -*-
#===============================================================================
"""
    Парсер_файлов_qsh по спецификации версии 4
"""
import os
import sys
import json
from  collections  import namedtuple
import struct
from datetime import datetime, timedelta, date
import pytz
from leb_128 import Uleb128, Sleb128

LOCAL_TZ = pytz.timezone('Europe/Moscow')

class General(Exception):
    """
    general exceprion
    """
    def __init__(self, msg):
        self.msg = msg
        super().__init__(msg)

class FileNotExists(General):
    """
    file not exists
    """
    def __init__(self, msg):
        super().__init__(msg)

class FileSignatureError(General):
    """
    bad file signature
    """
    def __init__(self, msg):
        super().__init__(msg)

class TouchMethodNoCall(General):
    """
    touch method not call
    """
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
            self.__dict__[inst] = namedtuple(inst, ['cursor_step', 'unpack_code'])

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
                out = struct.unpack(getattr(self, attr).unpack_code,\
                stream.read(getattr(self, attr).cursor_step))
                if len(out) > 0:
                    out = out[0]
            else:
                out = stream.read(getattr(self, attr).cursor_step)

        except Exception as excpt:
            msg = \
            'Got exception - {0}, details:\n\t- cursor position {1}\n;\t- file {2}'.\
            format(excpt, stream.tell(), stream.name)
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
            out = (datetime(1, 1, 1) + timedelta(microseconds=nano_seconds/10))
        return out.replace(tzinfo=pytz.utc).astimezone(LOCAL_TZ)


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
        self._last = self.read_sleb(stream) + self._last
        return self._last

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
        read method
        """
        _tmp = self.read_uleb(stream)
        if _tmp > 268435454:
            _tmp = self.read_sleb(stream)

        self._last = self._last + _tmp
        return self._last

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
            self._start = datetime(1, 1, 1) + delta
            out = self._start
        else:
            out = self._start + delta

        return out

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
    One stock data
    """
    _attrs = ['_rate', '_volume']
    _sub_attrs = ['value', 'data_type']

    def __init__(self):
        """
        set quote struct
        """
        super().__init__()
        self.set_attr(self._attrs, self._sub_attrs)

        self._rate.data_type = RelativeType()
        self._volume.data_type = self._base

    def read(self, stream):
        """
        read
        """
        for attr in self._attrs:
            if attr == '_volume':
                getattr(self, attr).value =\
                     getattr(self, attr).data_type.read_sleb(stream)
            else:
                getattr(self, attr).value = getattr(self, attr).data_type.read(stream)

    @property
    def data(self):
        """
        Convert all data to dict
        """
        return {attr.strip('_'):getattr(self, attr).value for attr in self._attrs}

    def __repr__(self):
        """
        reprint
        """
        return json.dumps(self.data)


class Stocks(AbsStruct):
    """
    one frame sotcks set
    """
    _attrs = ['_number', '_quote', '_timestamp']
    _sub_attrs = ['value', 'date_type']

    def __init__(self):
        """
        set quotes set struct
        """
        super().__init__()
        self.set_attr(self._attrs, self._sub_attrs)

        self._number.data_type = self._base
        self._number.value = None
        self._quote.data_type = Stock()
        self._quote.value = []

    def read(self, stream, timestamp):
        """
        time_stump
        """
        self._timestamp.value = timestamp
        self._number.value = self._number.data_type.read_sleb(stream)

        if len(self._quote.value) != 0:
            self._quote.value = []

        for quote in range(self._number.value):
            self._quote.data_type.read(stream)
            self._quote.value.append(self._quote.data_type.data)

    @property
    def data(self):
        """
        Convert all data to list
        """
        return {'timestamp':self._timestamp.value, 'quotes':self._quote.value}

    def __repr__(self):
        """
        reprint
        """
        _tmp = self.data
        _tmp['timestamp'] = _tmp.get('timestamp').isoformat()
        return json.dumps(_tmp)


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
            '_bid_number', '_transaction_price', '_transaction_volume', '_open_interest'],\
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
            out[key.strip('_')] = tmp

        return out

    def __repr__(self):
        """
        Вывод данных об одной сделке
        """
        _tmp = self.data
        _tmp['exchange_date_time'] = _tmp.get('exchange_date_time').isoformat()
        return json.dumps(_tmp)


class Header(AbsStruct):
    """
    file header data type
    """
    _attrs = ['_signature', '_format_version', '_app_name', '_user_comment',\
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
        self._head_len = None

    def read(self, stream):
        """
        read header
        """
        for i in range(19):
            if self._signature.value is None:
                self._signature.value = ''
            _tmp = self._signature.read(stream)
            self._signature.value = self._signature.value + chr(_tmp)

        for key in  ['_format_version', '_app_name', '_user_comment',\
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
        self._version = [4]

    def touch(self):
        """
        Read header and stream
        """
        if self._stream_dt is None:
            self._header.read(self._io_stream)
            if self._header.data.get('stream_count') > 1:
                _msg = 'More than one stream in file {}'.format(self._stream.name)
                raise FileSignatureError(_msg)

            self._stream_dt = GrowingDateTime(self._header.data.get('record_start_time'))
            self._stream.read(self._io_stream)

            if self._stream.data.get('type') == 'Stock':
                self._pyload = Stocks()

            elif self._stream.data.get('type') == 'Deals':
                self._pyload = Trades()

        _tmp = self._header.data.get('format_version')
        if _tmp not in self._version:
            raise Warning('{} are not support version {}'.\
                format(self.__class__.__name__, _tmp))

    def read(self):
        """
        Read one frame data
        """
        if self._stream_dt is None:
            _msg = 'Call touch method at first'
            raise TouchMethodNoCall(_msg)

        _frame = Frame(self._stream_dt)
        _frame.read(self._io_stream)

        if self._pyload.__class__.__name__ == 'Stocks':
            self._pyload.read(stream=self._io_stream,\
                timestamp=_frame.data.get('grow_dt'))

        elif self._pyload.__class__.__name__ == 'Trades':
            self._pyload.read(self._io_stream)

        return self._pyload.data

    def frame_to_json(self):
        """
        Convert pyload to json
        """
        return str(self._pyload)

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

    def __iter__(self):
        """
        make parser itarable
        """
        while True:
            try:
                yield self.read()
            except StopIteration as i_stop:
                self._io_stream.close()
                raise StopIteration


def _read_mode(path_to_file):
    """
    read from file
    path_to_file: full path to file
    """
    qsh = QSHParser(path_to_file)
    qsh.touch()
    print(qsh)
    print('\n' + '-'*50 + '\n')
    for data in qsh:
        print(qsh.frame_to_json())

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

            self.relative_data_one = BytesIO(b'\xe5\x8e&')
            self.relative_data_two = BytesIO(b'\x9b\xf1Y')

            self.growing_uleb_one = BytesIO(b'\xe5\x8e&')
            self.growing_uleb_two = BytesIO(b'\xe5\x8e&')

            self.growing_uleb_sleb = BytesIO(b'\xfe\xff\xff\x7f\x01')
            self.growing_datetime_data = BytesIO(b'\xb9$')

            self.stocks_data =\
BytesIO(b'1\xff\x82\x01\x01\xa1~\x01A\x01\xee~\x03\xa4\x7f\x01U\x03\x94~\x01\xcc~\x02v\x02v\x02v\x02v\x02\x8b~\x03N\x02N\x03~\x14Z\x02c\x14\x7f\x01_\x14\xef~~N~N~N}P\xb8~l\x7f]\x7fu\x7f]\x7fg\x7f\x00\x7ftvPN`\x7f}\x7fo\x7fF\x7fR\x7fE}}\x98xO\x7fv\x7fa\x7f\\\x7f\xbd}\x9c\x7f{\x7f^\x7fuXN\x7f')
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
            self.assertEqual(self.base.read_datetime(self.date_time).date(),\
                date(year=2015, month=3, day=2))

        def test_b_complex(self):
            """
            test complex types
            """
            #relative
            self.relative.read(self.relative_data_one)
            self.assertEqual(self.relative.read(self.relative_data_two), 0)

            #growing
            self.growing.read(self.growing_uleb_one)
            self.assertEqual(self.growing.read(self.growing_uleb_two), 1248970)
            self.assertEqual(self.growing.read(self.growing_uleb_sleb), 269684424)

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
            self.assertDictEqual(self.trade.data,\
                {"trade_type": "BID", "exchange_date_time": datetime(2015, 3, 2, 9, 59, 59),\
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
                LOCAL_TZ.localize(datetime(year=2015, month=3, day=2, hour=9, minute=59, second=50)))
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

        def test_i_stream_header(self):
            """
            test stocks and stock
            """
            stocks = Stocks()
            stocks.read(self.stocks_data, self.base_time)
            self.assertTrue(len(stocks.data.get('quotes')) == stocks._number.value)

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
