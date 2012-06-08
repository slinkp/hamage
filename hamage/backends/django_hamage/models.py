"""
Django ORM back-end for hamagecontrol.

To use this you'll need to add 'hamage.backends.django_hamage'
to settings.INSTALLED_APPS.

"""

from django.db import models
import datetime
import json
import time

class HamageEntry(models.Model):
    """
    hamagecontrol 'entry' storage for Django ORM.
    """

    time = models.DateTimeField(default=datetime.datetime.now)

    path = models.CharField(max_length=2000)

    author = models.CharField(max_length=256)

    authenticated = models.BooleanField()

    ipnr = models.CharField(max_length=40)

    content = models.TextField()

    headers = models.TextField()

    rejected = models.BooleanField(help_text="Is it spam?")

    score = models.IntegerField('High = ham, low = spam')

    # Todo: allow assigning & returning a list
    reasons = models.TextField(help_text="json-encoded list of reasons this was ham/spam", blank=True, null=True)



class DjangoBackendFactory(object):

    @staticmethod
    def purge_entries(age):
        now = time.time()
        modtime = datetime.datetime.fromtimestamp(now - age)
        HamageEntry.objects.filter(time__lt=modtime).delete()

    @staticmethod
    def make_entry(time, path,
                   author, authenticated,
                   ipnr, headers, content,
                   rejected,
                   score,
                   reasons):
        entry = HamageEntry(
            time=datetime.datetime.fromtimestamp(time),
            path=path,
            author=author,
            authenticated=authenticated,
            ipnr=ipnr,
            headers=unicode(headers),
            content=content,
            rejected=rejected,
            score=score,
            reasons=json.dumps(reasons),
            )
        entry.save()


# TODO move this.
from hamage.filter import FilterSystem

# TODO move this.
from hamage.filter import Request, RejectContent

class DjangoRequestWrapper(Request):

    def __init__(self, dj_req):
        # Django puts all headers in META,
        # and (I think) also all the WSGI environ?
        super(DjangoRequestWrapper, self).__init__(environ=dj_req.META)

    @property
    def remote_addr(self):
        # TODO get remote address if set, IP if not? Check what trac does
        return '127.0.0.1'

class DjangoFilterSystem(FilterSystem):
    def __init__(self):
        from django.conf import settings
        super(DjangoFilterSystem, self).__init__(config=settings.HAMAGE_CONFIG)

    backend_factory = DjangoBackendFactory

    request_wrapper = DjangoRequestWrapper

    def test_content(self, request, content):
        author = 'FIXME'
        changes = 'FIXME'
        ip = 'FIXME'
        try:
            self.test(request, author, changes, ip)
            return True
        except RejectContent:
            return False
