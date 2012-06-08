import re
import logging

logger = logging.getLogger('hamage.filter.extlinks')

class ExternalLinksFilterStrategy(object):
    """Spam filter strategy that reduces the karma of a submission if the
    content contains too many links to external sites.
    """

    def __init__(self, config):
        self.karma_points = int(config.get('extlinks_karma', 2))
        self.max_links = int(config.get('extlinks_max_links', 4))
        self.allowed_domains = config.get('extlinks_allowed_domains',
                                          set(['example.com', 'example.org'])
                                          )

    _URL_RE = re.compile('https?://([^/]+)/?', re.IGNORECASE)

    # IFilterStrategy methods

    def is_external(self):
        return False

    def test(self, req, author, content, ip):
        num_ext = 0
        allowed = self.allowed_domains.copy()
        allowed.add(req.host)

        for host in self._URL_RE.findall(content):
            if host not in allowed:
                logger.debug('"%s" is not in extlink_allowed_domains' % host)
                num_ext += 1
            else:
                logger.debug('"%s" is whitelisted.' % host)
        return self._score(num_ext)

    def _score(self, num_ext):
        if num_ext > self.max_links:
            if(self.max_links > 0):
                return -abs(self.karma_points) * num_ext / self.max_links, \
                       'Maximum number of external links per post exceeded'
            else:
                return -abs(self.karma_points) * num_ext, \
                       'External links in post found'
        return None

    def train(self, req, author, content, ip, spam=True):
        pass

