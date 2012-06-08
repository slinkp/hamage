import unittest
import mock
from hamage.filter import Request

class TestMiddleware(unittest.TestCase):

    def _make_one(self, config):
        from hamage.middleware import HamageMiddleware
        self.mock_app = mock.Mock()
        self.mock_app.return_value=['test body']
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
        middleware.handle_post = lambda request: (True, 'ok')
        env = {'REQUEST_METHOD': 'POST', 'REMOTE_ADDR': '127.0.0.1',
               'HTTP_HOST': 'localhost'}
        middleware(env, self.start_response)
        self.assertEqual(self.mock_app.call_count, 1)
        self.assertEqual(self.start_response.call_count, 0)

    def test_POST__rejected(self):
        middleware = self._make_one({'options': {}})
        middleware.handle_post = lambda request: (False, 'bad')
        env = {'REQUEST_METHOD': 'POST', 'REMOTE_ADDR': '127.0.0.1',
               'HTTP_HOST': 'localhost'}
        middleware.handle_spam = mock.Mock()
        middleware(env, self.start_response)
        self.assertEqual(self.mock_app.call_count, 0)
        self.assertEqual(self.start_response.call_count, 1)


    @mock.patch('hamage.middleware.FilterSystem')
    def test_handle_post__ok(self, mockFilterSystem):
        middleware = self._make_one({'options': {}})
        env = {'REQUEST_METHOD': 'POST', 'REMOTE_ADDR': '127.0.0.1',
               'HTTP_HOST': 'localhost'}
        request = Request.blank('/', env)
        mockFilterSystem.test.return_value = True
        mockFilterSystem._backend_factory = mock.Mock()
        result = middleware.handle_post(request)
        self.assertEqual(result, (True, ''))

    @mock.patch('hamage.middleware.FilterSystem')
    def test_handle_post__nope(self, mockFilterSystem):
        middleware = self._make_one({'options': {}})
        env = {'REQUEST_METHOD': 'POST', 'REMOTE_ADDR': '127.0.0.1',
               'HTTP_HOST': 'localhost'}
        request = Request.blank('/', env)
        from hamage.filter import RejectContent
        mockFilterSystem.return_value.test.side_effect = RejectContent('oh no')

        result = middleware.handle_post(request)
        self.assertEqual(result, (False, 'oh no'))


    def test_handle_spam(self):
        middleware = self._make_one({'options': {}})
        env = {'REQUEST_METHOD': 'POST', 'REMOTE_ADDR': '127.0.0.1',
               'HTTP_HOST': 'localhost'}
        request = Request.blank('/', env)

        def app_side_effect(environ, start_response):
            # need this to make webob.Request.get_response(app) happy
            start_response('200 OK', headers=[])
            return ['This is the response body']

        middleware.app.side_effect = app_side_effect
        middleware.handle_spam(request)
        # TODO: what to assert now?


if __name__ == '__main__':
    unittest.main()
