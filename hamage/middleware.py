
"""
WSGI middleware for spam detection.

"""
class HamageMiddleware(object):

    """
    Applies filters to relevant POST requests.
    """

    def __init__(self, app, config):
        self.app = app
        self.config = config

    def __call__(self, environ, start_response):
        # TODO: config hook to check whether this request is relevant.
        if environ['REQUEST_METHOD'].upper() == 'POST':
            approved, msg = self.handle_post(environ, start_response)
            if not approved:
                # TODO: config hook for response handler?
                # Or maybe rewrite REQUEST_METHOD to GET, call the app,
                # and inject the message into form?
                start_response('403 Forbidden', [('Content-type', 'text/plain')])
                return [msg]
        # TODO: handle rewriting forms?
        return self.app(environ, start_response)

    def handle_post(self, environ, start_response):
        from .filter import FilterGraph, Request, RejectContent
        filters = FilterGraph(self.config)
        request = Request.from_wsgi_environ(environ)
        # TODO:
        # Config needs to tell us which keys to care about.
        author = ''

        # Middleware has no way to get at existing data to know
        # if user is editing rather than creating;
        # so we treat all POSTs as new data.
        changes = []
        import pdb; pdb.set_trace()
        try:
            filters.test(request, author, changes)
            return (True, '')
        except RejectContent as e:
            return (False, str(e))
