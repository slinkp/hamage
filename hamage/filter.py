import logging
import time
import webob.request
from cStringIO import StringIO
from BeautifulSoup import UnicodeDammit
from difflib import SequenceMatcher
from pkg_resources import iter_entry_points

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



class Request(webob.request.Request):
    """
    Thin wrapper around webob.Request.
    """
    #######################################
    # Trac compatibility. TODO can we get rid of these?

    @property
    def authname(self):
        # TODO: this should also be pluggable?
        # REMOTE_USER works with eg. repoze.who, but
        # our application may well do something different.
        return self.remote_user or 'anonymous'

    def has_attachment(self):
        pass

class RejectContent(Exception):
    """Exception raised when content is rejected by a filter."""


def get_filters():
    return iter_entry_points('hamage_filters')

def get_filter(name):
    try:
        filt = list(iter_entry_points('hamage_filters', name=name))[0]
    except IndexError:
        return None
    return filt.load()


class FilterSystem(object):

    def request_wrapper(self, request):
        """Subclasses can override this to adapt a framework-native request
        implementation into something compatible with our Request class.
        """
        return request

    def __init__(self, config):
        self.log = logger

        self.config = config['options']

        self.strategies = []
        for name in config['filters']:
            self.strategies.append(get_filter(name)(self.config))

        config = self.config

        # The minimum score required for a submission to be allowed
        self.min_karma = int(config.get('min_karma', 0))

        # Karma given to authenticated users, if "trust_authenticated" is false.
        self.authenticated_karma = int(config.get('authenticated_karma', '10'))

        # Whether all content submissions and spam filtering activity should
        # be logged to the database.
        # Needed by some filters, notably the IP throttle.
        self.logging_enabled = bool(config.get('logging_enabled', True))

        # The number of days after which log entries should be purged.
        # TODO unused.
        self.purge_age = int(config.get('purge_age', '7'))

        # Allow usage of external services.
        self.use_external = bool(config.get('use_external', True))

        # Allow training of external services.
        self.train_external = bool(config.get('train_external', True))

        # Whether content submissions by authenticated users should be
        # trusted without checking for potential spam or other abuse.
        self.trust_authenticated = bool(config.get('trust_authenticated', True))

        # The karma given to attachments.
        # TODO unused.
        self.attachment_karma = int(config.get('attachment_karma', '0'))

        # The handler used to reject content.
        # Just needs a reject_content(req, message) method.
        self.reject_handler = self
        self._backend_factory = None

        # Whether to check x-forwarded-for headers.
        self.isforwarded = bool(config.get('is_forwarded'))

    @property
    def backend_factory(self):
        """Persistence system for storing entries, ... what else?
        Looked up via self.config['backend_factory'] which should
        name an entry point in the 'hamage_backends' group.
        """
        if self._backend_factory is None:
            name = self.config['backend_factory']
            backend = list(iter_entry_points('hamage_backends', name=name))[0]
            self._backend_factory = backend.load()
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
        Returns (score, [reasons]) or raises RejectContent when the
        score is less than ``self.min_karma``.

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
                return (float('inf'), ['trusting authenticated user'])

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
                    failpass = 'FAIL' if (retval and retval[0] < 0) else 'PASS'
                    karma = retval[0] if retval else 0
                    # Log lines like '127.0.0.1: ExternalLinksFilter FAIL karma -999'
                    message = '%s: %s %s karma %s' % (ip, strategy.__class__.__name__, failpass, karma)
                    self.log.info(message)
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
            # TODO if we use webob we can just do headers = req.headers
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
        return score, reasons

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
                    strategy.train(Request(fakeenv),
                               entry.author or 'anonymous',
                               entry.content, entry.ipnr, spam=spam)

            entry.update(rejected=spam)


    # Internal methods

    def _combine_changes(self, changes, sep='\n\n'):
        # If the user is editing content, we only really want
        # to test their new content;
        # unchanged and presumably already-approved content
        # would spuriously increase their ham score.
        fields = []
        for old_content, new_content in changes:
            new_content = to_unicode(new_content)
            if old_content:
                old_content = to_unicode(old_content)
                new_content = self._get_added_lines(old_content, new_content)
            fields.append(new_content)
        return sep.join(fields)

    def _get_added_lines(self, old_content, new_content):
        # Gets just the added lines in the new content, as a string.
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

