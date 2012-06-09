==============
Hamage Control
==============

Prototype of a flexible, configurable, pluggable anti-spam system for
the web.  Usable as WSGI middleware, or as a library.

It's early. Needs a lot more docs :)

A PDF presentation with more background is here:
https://github.com/slinkp/pygotham_hamage_demo/blob/e5b5f24c742c13eb7eaca9569f7205d482c03c04/pygotham2_hamage_slides.pdf?raw=true

Configuration
=============

Basically you instantiate FilterSystem with a config dictionary.
See FilterSystem.__init__ docstring for a list of keys it checks for.


Creating Filters
===================

A Filter is a class with these methods::


 class MyFilterStrategy(object):

    def __init__(self, config):
       """Create a new instance. config is a dictionary."""

    def is_external(self):
        """Return True if data is passed to external servers"""

    def test(self, req, author, content, ip):
        """Test the given content submission.
        
        Should return a `(points, reason)` tuple to affect the score of the
        submission, where `points` is an integer, and `reason` is a brief
        description of why the score is being affected.
        
        If the filter strategy does not want (or is not able) to effectively
        test the submission, it should return `None`.
        """

    def train(self, req, author, content, ip, spam=True):
        """Train the filter by reporting a false negative or positive.
        
        The spam keyword argument is `True` if the content should be considered
        spam (a false negative), and `False` if the content was legitimate (a
        false positive).
        """

Once that's done, you need to register an entry point for it.
In your setup.py, do this::

      entry_points={
          'hamage_filters': [
              'my_factory_name = mypackage.mymodule:MyClass,
              ],
      },


Creating Backends
===================

Backends allow Hamage to use arbitrary data stores to log
and retrieve info about POST requests that came in.
Useful for admin moderation (TODO), IP throttling, etc.

Backends are classes with these methods::

 class MyBackend(object):

    def purge_entries(self, age):
        """Remove old recorded POST data from your data store.
        """

    def make_entry(self, time, path,
                   author, authenticated,
                   ipnr, headers, content,
                   rejected,
                   score,
                   reasons):
        """Store data about a POST request in your data store."""

    def get_log_entry(self, id):
        """Return a log entry with the given id. Useful for training, etc"""



There's currently one experimental Django backend under
backends/django_hamage/

To register a class as a backend, you have to make an entry point in
your setup.py::

      entry_points={
          'hamage_backends: [
              'my_factory_name = mypackage.mymodule:MyClass,
              ],
      },

