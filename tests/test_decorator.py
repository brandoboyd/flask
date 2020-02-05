from mock import Mock
import unittest
from solariat_bottle.utils.decorators import log_response


class TestLogDecorator(unittest.TestCase):

    def test_decorator(self):

        logger_mock = Mock()
        logger_mock.debug = Mock()
        test_dict = {"a":777, "b":888}


        @log_response(logger=logger_mock)
        def func():
            return test_dict

        res = func()
        self.assertEqual(res, test_dict)
        logger_mock.debug.assert_called_once_with(str(test_dict))

        logger_mock.debug = Mock()
        @log_response(logger=logger_mock, log_level='prod')
        def f2():
            return test_dict

        res2 = f2()
        self.assertEqual(res2, test_dict)
        assert not logger_mock.debug.called