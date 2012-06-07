import unittest
import mock

class TestMiddleware(unittest.TestCase):

    def _make_one(self, config):
        from hamage.middleware import HamageMiddleware
        self.mock_app = mock.Mock()
        self.start_response = mock.Mock()
        return HamageMiddleware(self.mock_app, config)

    def test_GET(self):
        middleware = self._make_one({})
        env = {'REQUEST_METHOD': 'GET'}
        middleware(env, self.start_response)
        self.assertEqual(self.mock_app.call_count, 1)
        self.assertEqual(self.start_response.call_count, 0)

    def test_POST__approved(self):
        middleware = self._make_one({'options': {}})
        middleware.handle_post = lambda environ, start_response: (True, 'ok')
        env = {'REQUEST_METHOD': 'POST', 'REMOTE_ADDR': '127.0.0.1',
               'HTTP_HOST': 'localhost'}
        middleware(env, self.start_response)
        self.assertEqual(self.mock_app.call_count, 1)
        self.assertEqual(self.start_response.call_count, 0)

    def test_POST__rejected(self):
        middleware = self._make_one({'options': {}})
        middleware.handle_post = lambda environ, start_response: (False, 'bad')
        env = {'REQUEST_METHOD': 'POST', 'REMOTE_ADDR': '127.0.0.1',
               'HTTP_HOST': 'localhost'}
        middleware(env, self.start_response)
        self.assertEqual(self.mock_app.call_count, 0)
        self.assertEqual(self.start_response.call_count, 1)


    @mock.patch('hamage.filter.FilterGraph')
    def test_handle_post__ok(self, mockFilterGraph):
        middleware = self._make_one({'options': {}})
        env = {'REQUEST_METHOD': 'POST', 'REMOTE_ADDR': '127.0.0.1',
               'HTTP_HOST': 'localhost'}
        mockFilterGraph.test.return_value = True
        middleware.handle_post(env, self.start_response)

    @mock.patch('hamage.filter.FilterGraph')
    def test_handle_post__nope(self, mockFilterGraph):
        middleware = self._make_one({'options': {}})
        env = {'REQUEST_METHOD': 'POST', 'REMOTE_ADDR': '127.0.0.1',
               'HTTP_HOST': 'localhost'}
        from hamage.filter import RejectContent
        mockFilterGraph.return_value.test.side_effect = RejectContent('oh no')
        middleware.handle_post(env, self.start_response)

if __name__ == '__main__':
    unittest.main()
