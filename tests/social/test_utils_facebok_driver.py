import facebook
from datetime import timedelta
from solariat_bottle.tests.base import BaseCase
from solariat_bottle.utils.facebook_driver import FacebookRateLimitInfo, FacebookRequestLog, GraphAPI, \
    FacebookRateLimitError, THROTTLING_USER, THROTTLING_APP, THROTTLING_API_PATH, \
    ERROR_MISUSE
from mock import patch


def raise_exception_for(resp):
    def _inner(*args, **kwargs):
        print args, kwargs
        raise facebook.GraphAPIError(resp)
    return _inner


def shift_rate_limit_info(rate_limit_info, time_shift=None):
    """Shift rate limit item in time.
    time_shift == None leads to expiring rate limit
    """
    time_shift = time_shift or timedelta(seconds=rate_limit_info.remaining_time + 1)
    rate_limit_info.update(wait_until=rate_limit_info.wait_until - time_shift,
                           failed_request_time=rate_limit_info.failed_request_time - time_shift)
    return rate_limit_info


class FacebookDriverTestCase(BaseCase):

    def test_success_request(self):
        success_response = {'comments': []}
        graph = GraphAPI(access_token='test', channel='test channel id')
        self.assertEqual(FacebookRequestLog.objects.count(), 0)
        with patch.object(facebook.GraphAPI, 'request') as patched_request:
            patched_request.return_value = success_response
            self.assertEqual(graph.get_object('something'), success_response)
        self.assertEqual(FacebookRequestLog.objects.count(), 1)
        self.assertFalse(FacebookRateLimitInfo.objects.count(),
                         msg="FacebookRateLimitInfo is not empty after successful request")

    def test_graph_error_request(self):

        errors = [
            ("user blocked", THROTTLING_USER),
            ("app blocked", THROTTLING_APP),
            ("specific api blocked", THROTTLING_API_PATH),
            ("misuse", ERROR_MISUSE)
        ]
        error_responses = [
            {"error": {"message": msg, "type": "OAuthException", "code": code, "fbtrace_id": "ANQo35ChQvj"}}
            for msg, code in errors
        ]

        graph = GraphAPI(access_token='test', channel='test channel id')
        for error_response in error_responses:
            error_code = error_response['error']['code']
            backoff_config = FacebookRateLimitInfo.LIMITS_CONFIG[error_code]

            with patch.object(facebook.GraphAPI, 'request') as patched_request:
                patched_request.side_effect = raise_exception_for(error_response)
                patched_request.return_value = error_response
                path = 'some/path/to/raise/%s' % error_code
                full_path = "%s/%s" % (graph.version, path)
                self.assertEqual(FacebookRequestLog.objects(path=full_path).count(), 0)
                graph.access_token = 'test_%s' % error_code
                self.assertRaises(facebook.GraphAPIError, lambda: graph.get_object(path))
                patched_request.assert_called_with(full_path, {}, None, None, None)
                self.assertEqual(FacebookRequestLog.objects(path=full_path).count(), 1)
                log_item = FacebookRequestLog.objects.get(path=full_path)

                rate_limit_info_list = list(FacebookRateLimitInfo.objects(access_token=graph.access_token))
                self.assertTrue(len(rate_limit_info_list) == 1, msg="No FacebookRateLimitInfo for access token %s" % graph.access_token)
                rli = rate_limit_info_list[0]

                self.assertTupleEqual(
                    (rli.error_code, rli.path, rli.wait_until, rli.channel, rli.log_item),
                    (error_code, full_path, rli.failed_request_time + timedelta(seconds=backoff_config.start), str(graph._channel), log_item.id)
                )

                # rate limit not expired:
                # - should raise rate limit exception
                # - should not call GraphAPI
                # - should not add any additional rate limit info docs
                patched_request.reset_mock()
                rli_count = FacebookRateLimitInfo.objects.count()
                shift_rate_limit_info(rli, time_shift=timedelta(seconds=backoff_config.start-1))
                self.assertRaises(rli.exc.__class__, lambda: graph.get_object(path))
                patched_request.assert_not_called()
                self.assertEquals(FacebookRateLimitInfo.objects.count(), rli_count)

                # expire rate limit by few moments but still return error response from graph api
                # so the wait interval should be increased:
                # - should *not* raise rate limit exception but GraphAPI error
                # - thus there should be call to GraphAPI
                # - and new rate limit info doc should be added with extended wait time
                shift_rate_limit_info(rli)
                patched_request.reset_mock()
                rli_count = FacebookRateLimitInfo.objects.count()
                self.assertRaises(facebook.GraphAPIError, lambda: graph.get_object(path))
                patched_request.assert_called_with(full_path, {}, None, None, None)
                self.assertEquals(FacebookRateLimitInfo.objects.count(), rli_count + 1)
                last_rli = FacebookRateLimitInfo.objects().sort(id=-1)[:1][0]

                next_wait_interval = min(backoff_config.end, rli.wait_time * backoff_config.factor)
                if backoff_config.factor > 1.0:
                    self.assertAlmostEqual((last_rli.wait_until - rli.failed_request_time).total_seconds(),
                                           next_wait_interval,
                                           places=2)
                    self.assertAlmostEqual(
                        (last_rli.wait_until -
                        (rli.failed_request_time + timedelta(seconds=next_wait_interval))).total_seconds(),
                        0.0, places=2)
                    self.assertTrue((last_rli.wait_until - last_rli.failed_request_time).total_seconds() < next_wait_interval)
                else:
                    self.assertEqual((last_rli.wait_until - last_rli.failed_request_time).total_seconds(), next_wait_interval)

                # expire rate limit by (last_wait_interval * backoff_config.factor)
                # so the next wait interval should be backoff_config.start:
                # - should *not* raise rate limit exception but GraphAPI error
                # - should call GraphAPI
                # - new rate limit info doc should be added with backoff_config.start wait interval
                rli.delete()
                rli = last_rli
                shift_rate_limit_info(rli, time_shift=timedelta(seconds=next_wait_interval * backoff_config.factor))
                next_wait_interval = backoff_config.start
                patched_request.reset_mock()
                rli_count = FacebookRateLimitInfo.objects.count()
                self.assertRaises(facebook.GraphAPIError, lambda: graph.get_object(path))
                patched_request.assert_called_with(full_path, {}, None, None, None)
                self.assertEquals(FacebookRateLimitInfo.objects.count(), rli_count + 1)
                last_rli = FacebookRateLimitInfo.objects().sort(id=-1)[:1][0]
                self.assertEqual((last_rli.wait_until - last_rli.failed_request_time).total_seconds(), next_wait_interval)

    def test_graph_error_request_api_path_specific(self):
        """Tests that path specific errors don't block requests to other paths
        and user/app level errors block requests to all paths"""
        errors = [
            ("user blocked", THROTTLING_USER, False),
            ("app blocked", THROTTLING_APP, False),
            ("specific api blocked", THROTTLING_API_PATH, True),
            ("misuse", ERROR_MISUSE, True)
        ]
        error_responses = [
            ({"error": {"message": msg, "type": "OAuthException", "code": code, "fbtrace_id": "ANQo35ChQvj"}},
                is_path_specific)
            for msg, code, is_path_specific in errors
        ]
        success_response = {'response': 'ok'}

        graph = GraphAPI(access_token='test', channel='test channel id')
        for error_response, is_path_specific in error_responses:
            error_code = error_response['error']['code']
            with patch.object(facebook.GraphAPI, 'request') as patched_request:
                patched_request.side_effect = raise_exception_for(error_response)
                patched_request.return_value = error_response
                path = 'some/path/to/raise/%s' % error_code
                full_path = "%s/%s" % (graph.version, path)
                self.assertEqual(FacebookRequestLog.objects(path=full_path).count(), 0)
                graph.access_token = 'test_%s' % error_code
                self.assertRaises(facebook.GraphAPIError, lambda: graph.get_object(path))
                self.assertRaises(FacebookRateLimitError, lambda: graph.get_object(path))
            with patch.object(facebook.GraphAPI, 'request') as patched_request:
                patched_request.return_value = success_response
                if is_path_specific:
                    graph.get_object(path + 'other')
                    patched_request.assert_called_with(full_path + 'other', {}, None, None, None)
                else:
                    self.assertRaises(FacebookRateLimitError, lambda: graph.get_object(path + 'other'))
                    patched_request.assert_not_called()
