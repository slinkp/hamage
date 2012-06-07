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

    time = models.DateTimeField()

    path = models.CharField(max_length=2000)

    author = models.CharField(max_length=256)

    authenticated = models.BooleanField()

    ipnr = models.CharField(max_length=40)

    content = models.TextField()

    headers = models.TextField()

    rejected = models.BooleanField(help_text="Is it spam?")

    score = models.IntegerField()

    # Todo: allow assigning & returning a list
    reasons = models.TextField(help_text="json-encoded list of reasons this was ham/spam", blank=True, null=True)



class DjangoBackendFactory(object):

    @staticmethod
    def purge_entries(age):
        now = time.time()
        modtime = datetime.datetime.fromtimestamp(now - age)
        HamageEntry.objects.filter(timestamp__lt=modtime).delete()

    @staticmethod
    def make_entry(timestamp, path,
                   author, is_authenticated,
                   ip, headers, content,
                   is_spam,
                   score,
                   reasons):
        entry = HamageEntry(
            timestamp=datetime.datetime.fromtimestamp(timestamp),
            path=path,
            author=author,
            is_authenticated=is_authenticated,
            ip=ip,
            headers=unicode(headers),
            content=content,
            is_spam=is_spam,
            score=score,
            reasons=json.dumps(reasons),
            )
        entry.save()


# TODO move this.
from hamage.filter import FilterGraph

# TODO move this.
from hamage.filter import Request, RejectContent

class DjangoRequestWrapper(Request):

    def __init__(self, dj_req):
        self.django_req = dj_req
        # Django puts all headers in META,
        # and (I think) also all the WSGI environ?
        super(DjangoRequestWrapper, self).__init__(environ=dj_req.META, headers=dj_req.META) 

    @property
    def remote_addr(self):
        # TODO get remote address if set, IP if not? Check what trac does
        return '127.0.0.1'

class DjangoFilterGraph(FilterGraph):
    def __init__(self):
        from django.conf import settings
        super(DjangoFilterGraph, self).__init__(config=settings.HAMAGE_CONFIG)

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
