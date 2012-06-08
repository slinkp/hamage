Configuration
=============




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

TODO

Once you've made one, register an entry point in your setup.py::

      entry_points={
          'hamage_backends: [
              'my_factory_name = mypackage.mymodule:MyClass,
              ],
      },

