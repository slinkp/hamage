"""
Django ORM back-end for hamagecontrol.

To use this you'll need to add 'hamage.backends.django_hamage'
to settings.INSTALLED_APPS.

"""

from django.db import models

class HamageEntry(models.Model):

    timestamp = models.DateTimeField()

    path = models.CharField(max_length=2000)

    author = models.CharField(max_length=256)

    is_authenticated = models.BooleanField()

    ip = models.CharField(max_length=40)

    content = models.TextField()

    headers = TextField()

    is_spam = models.BooleanField()


class BackendFactory(object):

    @staticmethod
    def purge_entries(age):
        modtime = now - age
        HamageEntry.objects.filter(modtime__lt=modtime).delete()

    @staticmethod
    def make_entry(timestamp, path,
                   author, is_authenticated,
                   ip, headers, content,
                   is_spam,
                   score,
                   reasons):
        entry = HamageEntry(timestamp=timestamp,
                            path=path,
                            author=author,
                            is_authenticated=is_authenticated,
                            ip=ip,
                            headers=unicode(headers),
                            content=content,
                            is_spam=is_spam,
                            ,
