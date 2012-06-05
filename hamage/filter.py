import re
import logging
import time
from cStringIO import StringIO
from BeautifulSoup import UnicodeDammit
from difflib import SequenceMatcher

logger = logging.getLogger('hamage.filter')

def to_unicode(s, charset=None):
    if charset:
        overrideEncodings = [charset]
    else:
        overrideEncodings = []
    return UnicodeDammit(s, overrideEncodings=overrideEncodings).unicode

def shorten_line(text, maxlen=75):
    # Swiped from Trac.
    if len(text or '') < maxlen:
        return text
    cut = max(text.rfind(' ', 0, maxlen), text.rfind('\n', 0, maxlen))

    if cut < 0:
        cut = maxlen
    return text[:cut] + ' ...'


class Request(object):
    """
    TODO: what do we actually need here?
    maybe see http://packages.python.org/twod.wsgi/manual/request-objects.html
    for django compatibility?
    """
    def __init__(self, environ, headers):
        self.environ = environ  # The WSGI environment.
        self.headers = {}  # HTTP headers
        for key, value in headers.items():
            self.headers[key.lower()] = value

    @classmethod
    def from_wsgi_environ(kls, environ):
        """Factory to create a Request from a WSGI environment.
        """
        headers = dict([(key, val) for key, val in environ.items() if key.startswith('HTTP_')])
        return kls(environ, headers)

    # Making this up, TODO
    def has_attachment(self):
        return False

    #######################################
    # Trac compatibility. TODO

    # For compatibility w/ trac code; deprecate this
    def get_header(self, key):
        key = 'http_' + key.lower()
        return self.headers[key]

    @property
    def authname(self):
        return 'anonymous'

    path_info = ''


class RejectContent(Exception):
    """Exception raised when content is rejected by a filter."""

class ExternalLinksFilterStrategy(object):
    """Spam filter strategy that reduces the karma of a submission if the
    content contains too many links to external sites.
    """

    def __init__(self, config):
        self.karma_points = int(config.get('extlinks_karma', 2))
        self.max_links = int(config.get('extlinks_max_links', 4))
        self.allowed_domains = config.get('extlink_allowed_domains',
                                          set(['example.com', 'example.org'])
                                          )

    _URL_RE = re.compile('https?://([^/]+)/?', re.IGNORECASE)

    # IFilterStrategy methods

    def is_external(self):
        return False

    def test(self, req, author, content, ip):
        # TODO: req, author, content
        import pdb; pdb.set_trace()
        num_ext = 0
        allowed = self.allowed_domains.copy()
        allowed.add(req.get_header('Host'))

        for host in self._URL_RE.findall(content):
            if host not in allowed:
                logger.debug('"%s" is not in extlink_allowed_domains' % host)
                num_ext += 1
            else:
                logger.debug('"%s" is whitelisted.' % host)

        if num_ext > self.max_links:
            if(self.max_links > 0):
                return -abs(self.karma_points) * num_ext / self.max_links, \
                       'Maximum number of external links per post exceeded'
            else:
                return -abs(self.karma_points) * num_ext, \
                       'External links in post found'

    def train(self, req, author, content, ip, spam=True):
        pass



class FilterGraph(object):


    def request_wrapper(self, request):
        """Subclasses can override this to adapt a framework-native request
        implementation into something compatible with our Request class.
        """
        return request

    def __init__(self, config):
        self.log = logger

        # TODO: entry points
        # http://stackoverflow.com/questions/774824/explain-python-entry-points
        self.strategies = [ExternalLinksFilterStrategy(config)]

        config = config['options']

        # The minimum score required for a submission to be allowed
        self.min_karma = int(config.get('min_karma', 0))

        # Karma given to authenticated users, if "trust_authenticated" is false.
        self.authenticated_karma = int(config.get('authenticated_karma', '10'))

        # Whether all content submissions and spam filtering activity should
        # be logged to the database.
        self.logging_enabled = bool(config.get('logging_enabled', True))

        # The number of days after which log entries should be purged.
        self.purge_age = int(config.get('purge_age', '7'))

        # Allow usage of external services.
        self.use_external = bool(config.get('use_external', True))

        #"""Allow training of external services.""")
        self.train_external = bool(config.get('train_external', True))

        # Whether content submissions by authenticated users should be
        # trusted without checking for potential spam or other abuse.
        self.trust_authenticated = bool(config.get('trust_authenticated', True))

        # The karma given to attachments.
        self.attachment_karma = int(config.get('attachment_karma', '0'))

        # The handler used to reject content.
        self.reject_handler = self
        self._backend_factory = None

        # Whether to check x-forwarded-for headers.
        self.isforwarded = bool(config.get('is_forwarded'))

    @property
    def backend_factory(self):
        """Persistence system for storing entries, ... what else?
         TODO: this should be an entry point passed by config?
         """
        if self._backend_factory is None:
            from .backends.django_hamage.models import DjangoBackendFactory
            self._backend_factory = DjangoBackendFactory
        return self._backend_factory

    # IRejectHandler methods
    def reject_content(self, req, message):
        raise RejectContent(message)

    def _get_ip(self, req):
        if self.isforwarded:
            x_forwarded = req.headers.get('x-forwarded-for')
            if x_forwarded and x_forwarded != '':
                return x_forwarded.split(',',1)[0]
        return req.environ['REMOTE_ADDR']


    # Public methods
    def test(self, req, author, changes):
        """Test a submission against the registered filter strategies.
        
        @param req: the request object
        @param author: the name of the logged in user, or 'anonymous' if the
            user is not logged in
        @param changes: a list of `(old_content, new_content)` tuples for every
            modified "field", where `old_content` may contain the previous
            version of that field (if available), and `new_content` contains
            the newly submitted content
        @param ip: the submitters IP
        """
        req = self.request_wrapper(req)
        score = 0
        if self.trust_authenticated:
            # Authenticated users are trusted
            if req.authname and req.authname != 'anonymous':
                return

        ip = self._get_ip(req)

        reasons = []
        if req.authname and req.authname != 'anonymous':
            reasons.append(("AuthenticatedUserScore", self.authenticated_karma,
            "User is authenticated"))
            score += self.authenticated_karma

        if req.has_attachment() and self.attachment_karma != 0:
            reasons.append(("AttachmentScore", self.attachment_karma,
            "Attachment weighting"))
            score += self.attachment_karma

        if not author:
            author = 'anonymous'
        content = self._combine_changes(changes)
        abbrev = shorten_line(content)
        self.log.debug('Testing content %r submitted by "%s"', abbrev, author)

        for strategy in self.strategies:
            retval = None
            try:
                if self.use_external or not strategy.is_external():
                    retval = strategy.test(req, author, content, ip)
            except Exception, e:
                self.log.exception('Filter strategy raised exception: %s', e)
            else:
                if retval:
                    points, reason = retval
                    self.log.debug('Filter strategy %r gave submission %d '
                                   'karma points (reason: %r)', strategy,
                                   points, reason)
                    score += points
                    if reason:
                        reasons.append((strategy.__class__.__name__, points,
                                        reason))

        if self.logging_enabled:
            headers = '\n'.join(['%s: %s' % (k[5:].replace('_', '-').title(), v)
                                 for k, v in req.environ.items()
                                 if k.startswith('HTTP_')])
            self.log_entry(time.time(), req.path_info, author,
                           req.authname and req.authname != 'anonymous',
                           ip, headers, content, score < self.min_karma,
                           score, ['%s (%d): %s' % r for r in reasons])
            self.purge_log_entries(self.purge_age)


        if score < self.min_karma:
            ip = self._get_ip(req)
            self.log.warn('Rejecting submission %r by "%s" (%r) because it '
                          'earned only %d karma points (%d are required) for '
                          'the following reason(s): %r', abbrev, author,
                          ip, score, self.min_karma,
                          ['%s: (%s) %s' % r for r in reasons])
            msg = ', '.join([r[2] for r in reasons if r[1] < 0])
            if msg:
                msg = ' (%s)' % msg
            self.reject_handler.reject_content(req, 'Submission rejected as '
                                               'potential spam %s' % msg)

    def train(self, req, log_id, spam=True):
        environ = {}
        for name, value in req.environ.items():
            if not name.startswith('HTTP_'):
                environ[name] = value

        entry = self.get_log_entry(log_id)
        if entry:
            self.log.debug('Marking as %s: %r submitted by "%s"',
                           spam and 'spam' or 'ham',
                           shorten_line(entry.content),
                           entry.author)
            fakeenv = environ.copy()
            for header in entry.headers.splitlines():
                name, value = header.split(':', 1)
                if name == 'Cookie': # breaks SimpleCookie somehow
                    continue
                cgi_name = 'HTTP_%s' % name.strip().replace('-', '_').upper()
                fakeenv[cgi_name] = value.strip()
            fakeenv['REQUEST_METHOD'] = 'POST'
            fakeenv['PATH_INFO'] = entry.path
            fakeenv['wsgi.input'] = StringIO('')
            fakeenv['REMOTE_ADDR'] = entry.ipnr
            if entry.authenticated:
                fakeenv['REMOTE_USER'] = entry.author

            for strategy in self.strategies:
                if (self.use_external and self.train_external) or not strategy.is_external():
                    strategy.train(Request(fakeenv, None),
                               entry.author or 'anonymous',
                               entry.content, entry.ipnr, spam=spam)

            entry.update(rejected=spam)


    # Internal methods

    def _combine_changes(self, changes, sep='\n\n'):
        fields = []
        for old_content, new_content in changes:
            new_content = to_unicode(new_content)
            if old_content:
                # If the user is editing content, we only really want
                # to test their new content;
                # unchanged and presumably already-approved content
                # would spuriously increase their ham score.
                old_content = to_unicode(old_content)
                new_content = self._get_added_lines(old_content, new_content)
            fields.append(new_content)
        return sep.join(fields)

    def _get_added_lines(self, old_content, new_content):
        buf = []
        old_lines = old_content.splitlines()
        new_lines = new_content.splitlines()
        matcher = SequenceMatcher(None, old_lines, new_lines)
        for group in matcher.get_grouped_opcodes(0):
            for tag, i1, i2, j1, j2 in group:
                if tag in ('insert', 'replace'):
                    buf.append('\n'.join(new_lines[j1:j2]))

        return '\n'.join(buf)

    ###########################################################
    # Persistent logging of requests.

    def log_entry(self, *args, **kw):
        self.backend_factory.make_entry(*args, **kw)


    def purge_log_entries(self, age):
        self.backend_factory.purge_entries(age)


    def get_log_entry(self, id):
        return self.backend_factory.get(id)

