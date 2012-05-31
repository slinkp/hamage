import unittest
import mock

class TestFilterGraph(unittest.TestCase):

    def _request(self, **headers):
        from hamage.filter import Request
        req = Request(environ={}, headers=headers)
        return req

    def _make_one(self):
        from hamage.filter import FilterGraph
        return FilterGraph({'options': {}})

    def test_no_filters(self):
        graph = self._make_one()
        graph._backend_factory = mock.Mock()
        req = self._request(host='example.org')
        graph.strategies = []
        retval = graph.test(req, 'John Doe', [(None, 'Foo bar')], '127.0.0.1')
        self.assertEqual(retval, None)


class TestExternalLinksFilterStrategy(unittest.TestCase):

    def _make_one(self):
        from hamage.filter import ExternalLinksFilterStrategy
        elfs = ExternalLinksFilterStrategy({})
        return elfs

    def _request(self, **headers):
        from hamage.filter import Request
        req = Request(environ={}, headers=headers)
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



if __name__ == '__main__':
    unittest.main()
