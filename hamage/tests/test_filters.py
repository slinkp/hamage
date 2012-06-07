import unittest
import mock

class TestFilterGraph(unittest.TestCase):

    def _request(self, environ=None, **kw):
        environ = environ or {}
        kw.setdefault('path_info', '/')
        environ.setdefault('REMOTE_ADDR', '127.0.0.1')
        from hamage.filter import Request
        req = Request(environ=environ, **kw)
        return req

    def _make_one(self, options={}):
        from hamage.filter import FilterGraph
        graph = FilterGraph({'options': options})
        graph._backend_factory = mock.Mock()
        return graph

    def test_no_filters(self):
        graph = self._make_one()
        req = self._request(host='example.org')
        graph.strategies = []
        retval = graph.test(req, 'John Doe', [(None, 'Foo bar')])
        self.assertEqual(retval, (0, []))

    def test_trust_authenticated(self):
        req = self._request(remote_user='john',
                            path_info='/foo',
                            remote_addr='127.0.0.1')
        graph = self._make_one({'trust_authenticated': True})
        strategy = mock.Mock()
        graph.strategies = [strategy]
        retval = graph.test(req, '', [])
        self.assertEqual(retval, (float('inf'), ['trusting authenticated user']))
        self.assertEqual(strategy.test.call_count, 0)

    def test_dont_trust_authenticated(self):
        req = self._request(remote_user='john',
                            path_info='/foo',
                            remote_addr='127.0.0.1')
        graph = self._make_one({'trust_authenticated': False})
        strategy = mock.Mock()
        strategy.test.return_value = (999, ['message'])
        graph.strategies = [strategy]
        retval = graph.test(req, '', [])
        # By default get 10 points for authenticating.
        expected = [('AuthenticatedUserScore', 10, 'User is authenticated'),
                    ('Mock', 999, ['message'])]
        self.assertEqual(retval, (1009, expected))
        self.assertEqual(strategy.test.call_count, 1)

    # def test_without_oldcontent(self):
    #     req = Mock(environ={}, path_info='/foo', authname='anonymous',
    #                remote_addr='127.0.0.1')
    #     FilterSystem(self.env).test(req, 'John Doe', [(None, 'Test')],
    #                                '127.0.0.1')
    #     self.assertEqual('Test', DummyStrategy(self.env).content)

    # def test_with_oldcontent(self):
    #     req = Mock(environ={}, path_info='/foo', authname='anonymous',
    #                remote_addr='127.0.0.1')
    #     FilterSystem(self.env).test(req, 'John Doe', [('Test', 'Test 1 2 3')],
    #                                 '127.0.0.1')
    #     self.assertEqual('Test 1 2 3', DummyStrategy(self.env).content)

    # def test_with_oldcontent_multiline(self):
    #     req = Mock(environ={}, path_info='/foo', authname='anonymous',
    #                remote_addr='127.0.0.1')
    #     FilterSystem(self.env).test(req, 'John Doe', [('Text\n1 2 3\n7 8 9',
    #                                                    'Test\n1 2 3\n4 5 6')],
    #                                                    '127.0.0.1')
    #     self.assertEqual('Test\n4 5 6', DummyStrategy(self.env).content)

    def test_bad_karma(self):
        req = self._request(path_info='/foo', remote_user='anonymous',
                            remote_addr='127.0.0.1')
        strategy = mock.Mock()
        strategy.test.return_value = (-999, 'rejected by fred')
        graph = self._make_one({'trust_authenticated': False})
        graph.strategies = [strategy]
        graph.reject_handler = mock.Mock()
        retval = graph.test(req, '', [])
        self.assertEqual(retval, (-999, [('Mock', -999, 'rejected by fred')]))
        self.assertEqual(graph.reject_handler.reject_content.call_count, 1)

    # def test_good_karma(self):
    #     req = Mock(environ={}, path_info='/foo', authname='anonymous',
    #                remote_addr='127.0.0.1')
    #     DummyStrategy(self.env).configure(5)
    #     FilterSystem(self.env).test(req, 'John Doe', [(None, 'Test')],
    #                                 '127.0.0.1')

    # def test_log_reject(self):
    #     req = Mock(environ={}, path_info='/foo', authname='anonymous',
    #                remote_addr='127.0.0.1')
    #     DummyStrategy(self.env).configure(-5, 'Blacklisted')
    #     try:
    #         FilterSystem(self.env).test(req, 'John Doe', [(None, 'Test')],
    #                                     '127.0.0.1')
    #         self.fail('Expected RejectContent exception')
    #     except RejectContent, e:
    #         pass

    #     log = list(LogEntry.select(self.env))
    #     self.assertEqual(1, len(log))
    #     entry = log[0]
    #     self.assertEqual('/foo', entry.path)
    #     self.assertEqual('John Doe', entry.author)
    #     self.assertEqual(False, entry.authenticated)
    #     self.assertEqual('127.0.0.1', entry.ipnr)
    #     self.assertEqual('Test', entry.content)
    #     self.assertEqual(True, entry.rejected)
    #     self.assertEqual(-5, entry.karma)
    #     self.assertEqual(['DummyStrategy (-5): Blacklisted'], entry.reasons)

    # def test_log_accept(self):
    #     req = Mock(environ={}, path_info='/foo', authname='anonymous',
    #                remote_addr='127.0.0.1')
    #     DummyStrategy(self.env).configure(5)
    #     FilterSystem(self.env).test(req, 'John Doe', [(None, 'Test')],
    #                                 '127.0.0.1')

    #     log = list(LogEntry.select(self.env))
    #     self.assertEqual(1, len(log))
    #     entry = log[0]
    #     self.assertEqual('/foo', entry.path)
    #     self.assertEqual('John Doe', entry.author)
    #     self.assertEqual(False, entry.authenticated)
    #     self.assertEqual('127.0.0.1', entry.ipnr)
    #     self.assertEqual('Test', entry.content)
    #     self.assertEqual(False, entry.rejected)
    #     self.assertEqual(5, entry.karma)
    #     self.assertEqual([], entry.reasons)

    def test_train_spam(self):
        import time
        entry = mock.Mock(
            time=time.time(), path='/foo',
            author='john', authenticated=False,
            ipnr='127.0.0.1', headers='',
            content='Test', rejected=False, karma=5, reasons=[],
            id=12345,
            )
        def _update(**kwargs):
            for key, val in kwargs.items():
                setattr(entry, key, val)
        entry.update = _update

        req = self._request(
            server_name='localhost', server_port='80', environ={'wsgi.url_scheme': 'http'},
            path_info='/foo', remote_user='anonymous', remote_addr='127.0.0.1')

        graph = self._make_one()
        strategy = mock.Mock()
        graph.strategies = [strategy]
        graph.backend_factory.get.return_value = entry

        graph.train(req, entry.id, spam=True)

        self.assertEqual(strategy.train.call_count, 1)
        # First arg is a constructed Request, not sure what to test about it.
        self.assertEqual(strategy.train.call_args[0][1:],
                         ('john', 'Test', '127.0.0.1'))
        self.assertEqual(strategy.train.call_args[1],
                         {'spam': True})

        self.assertEqual(True, entry.rejected)

    # def test_train_ham(self):
    #     entry = LogEntry(self.env, time.time(), '/foo', 'john', False,
    #                      '127.0.0.1', '', 'Test', True, -5, [])
    #     entry.insert()

    #     req = Mock(environ={'SERVER_NAME': 'localhost', 'SERVER_PORT': '80',
    #                         'wsgi.url_scheme': 'http'},
    #                path_info='/foo', authname='anonymous',
    #                remote_addr='127.0.0.1')
    #     FilterSystem(self.env).train(req, entry.id, spam=False)

    #     strategy = DummyStrategy(self.env)
    #     self.assertEqual(True, strategy.train_called)
    #     self.assertEqual('john', strategy.author)
    #     self.assertEqual('Test', strategy.content)
    #     self.assertEqual(False, strategy.spam)

    #     log = list(LogEntry.select(self.env))
    #     self.assertEqual(1, len(log))
    #     entry = log[0]
    #     self.assertEqual(False, entry.rejected)


class TestExternalLinksFilterStrategy(unittest.TestCase):

    def _make_one(self):
        from hamage.filter import ExternalLinksFilterStrategy
        strategy = ExternalLinksFilterStrategy({})
        return strategy

    def _request(self, **kw):
        from hamage.filter import Request
        req = Request(environ={}, **kw)
        return req

    def test_no_links(self):
        req = self._request(host='example.org')
        strategy = self._make_one()
        retval = strategy.test(req, 'John Doe', 'Foo bar', '127.0.0.1')
        self.assertEqual(None, retval)

    def test_few_ext_links(self):
        req = self._request(host='example.org')
        strategy = self._make_one()
        retval = strategy.test(req, 'John Doe', '''
        <a href="http://spammers-site.com/fakehandbags">fakehandbags</a>
        <a href="http://spammers-site.com/fakewatches">fakewatches</a>
        ''', '127.0.0.1')
        self.assertEqual(None, retval)

    def test_too_many_links(self):
        req = self._request(host='127.0.0.1')
        strategy = self._make_one()
        retval = strategy.test(req, 'John Doe', '''
        <a href="http://spammers-site.com/fakehandbags">fakehandbags</a>
        <a href="http://spammers-site.com/fakewatches">fakewatches</a>
        <a href="http://spammers-site.com/fakehandbags">fakehandbags</a>
        <a href="http://spammers-site.com/fakewatches">fakewatches</a>
        <a href="http://spammers-site.com/fakehandbags">fakehandbags</a>
        <a href="http://spammers-site.com/fakewatches">fakewatches</a>
        ''', '127.0.0.1')
        self.assertEqual(
            (-3, 'Maximum number of external links per post exceeded'),
            retval
            )

    def test_many_ext_links_same_site(self):
        req = self._request(host='127.0.0.1')
        strategy = self._make_one()
        retval = strategy.test(req, 'John Doe', """
        <a href="http://example.org/page1">foo</a>
        <a href="http://example.org/page2">bar</a>
        <a href="http://example.org/page1">foo</a>
        <a href="http://example.org/page2">bar</a>
        <a href="http://example.org/page1">foo</a>
        <a href="http://example.org/page2">bar</a>
        """, '127.0.0.1')
        self.assertEqual(None, retval)

    def test_many_ext_links_raw(self):
        req = self._request(host='127.0.0.1')
        strategy = self._make_one()
        retval = strategy.test(req, 'John Doe', """
        http://spammers-site.com/fakehandbags
        http://spammers-site.com/fakewatches
        http://spammers-site.com/fakehandbags
        http://spammers-site.com/fakewatches
        http://spammers-site.com/fakehandbags
        http://spammers-site.com/fakewatches
        """, '127.0.0.1')
        self.assertEqual(
            (-3, 'Maximum number of external links per post exceeded'),
            retval
        )

    def test_many_ext_links_bbcode(self):
        req = self._request(host='127.0.0.1')
        strategy = self._make_one()
        retval = strategy.test(req, 'John Doe', """
        [url=http://spammers-site.com/fakehandbags]fakehandbags[/url]
        [url=http://spammers-site.com/fakewatches]fakewatches[/url]
        [url=http://spammers-site.com/fakehandbags]fakehandbags[/url]
        [url=http://spammers-site.com/fakewatches]fakewatches[/url]
        [url=http://spammers-site.com/fakehandbags]fakehandbags[/url]
        [url=http://spammers-site.com/fakewatches]fakewatches[/url]
        """, '127.0.0.1')
        self.assertEqual(
            (-3, 'Maximum number of external links per post exceeded'),
            retval
        )

    def test_scoring_with_max_links(self):
        strategy = self._make_one()
        strategy.max_links = 4
        strategy.karma_points = 3
        self.assertEqual(strategy._score(0), None)
        self.assertEqual(strategy._score(1), None)
        self.assertEqual(strategy._score(4), None)
        self.assertEqual(strategy._score(5),
                         (-4, 'Maximum number of external links per post exceeded'))
        # It's linear w/ number of links, but scaled down by max_links.
        self.assertEqual(strategy._score(100),
                         (-75, 'Maximum number of external links per post exceeded'))
        self.assertEqual(strategy._score(200),
                         (-150, 'Maximum number of external links per post exceeded'))

    def test_scoring_without_max_links(self):
        strategy = self._make_one()
        strategy.max_links = 0
        strategy.karma_points = 3
        self.assertEqual(strategy._score(0), None)
        strategy.max_links = -1
        self.assertEqual(strategy._score(0),
                         (0, 'External links in post found'))
        self.assertEqual(strategy._score(1),
                         (-3, 'External links in post found'))
        # It's linear w/ number of links.
        self.assertEqual(strategy._score(100),
                         (-300, 'External links in post found'))
        self.assertEqual(strategy._score(200),
                         (-600, 'External links in post found'))



if __name__ == '__main__':
    unittest.main()
