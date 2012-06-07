
"""
WSGI middleware for spam detection.

"""
from .filter import FilterGraph, Request, RejectContent

class HamageMiddleware(object):

    """
    Applies filters to relevant POST requests.
    """

    def __init__(self, app, config):
        self.app = app
        self.config = config
        self.path_config = {}

    def __call__(self, environ, start_response):
        do_handle = False
        request = Request(environ)
        if environ['REQUEST_METHOD'].upper() == 'POST':
            path_configs = self.config['options'].get('path_configs')
            if path_configs:
                for path_config in self.config['options']['path_configs']:
                    if path_config['path'] == request.path_info:
                        do_handle = True
                        self.path_config = path_config
                        break
            else:
                do_handle = True

        if do_handle:
            approved, msg = self.handle_post(request)
            if not approved:
                # TODO: use the message.
                response = self.handle_spam(request)
                start_response(response.status, response.headerlist)
                return response.app_iter

        # TODO: handle injecting form fields
        return self.app(environ, start_response)

    def handle_post(self, request):
        """This takes a WebOb request and returns spam status and
        reason(s) as (bool, str).
        """
        filters = FilterGraph(self.config)

        author = request.POST.get(self.path_config.get('author_field', 'name')) or u''

        # Middleware has no way to get at existing data to know
        # if user is editing rather than creating;
        # so we treat all POSTs as new data.
        changes = []
        # TODO: allow config to determine which fields we filter on.
        for val in request.POST.values():
            changes.append((None, val))
        try:
            filters.test(request, author, changes)
            return (True, '')
        except RejectContent as e:
            return (False, str(e))


    def handle_spam(self, request):
        """
        A WebOb request handler that we use to return appropriate response if
        handle_post() decided the post was spam.

        By default, we:
        * call self.application as if it's a GET request at the path
          of the original referrer.
        * inject an error message if the result is html.
        * return that.

        This is maybe over-ambitious for the default behavior?
        Override this if you like.
        """
        # A much simpler default would be:
        # start_response('403 Forbidden', [('Content-type', 'text/plain')])
        # return ["Your content looks like spam."]

        import urlparse
        from formencode import htmlfill
        new_request = request.copy()
        # TODO: handle webob's multidict - keys can appear more than once
        defaults = dict(new_request.POST)
        new_request.method = 'GET'
        form_path = urlparse.urlparse(request.referer).path
        new_request.path_info = form_path
        new_request.referer = request.referer
        response = new_request.get_response(self.app)
        form = response.body
        if self.path_config:
            errors = {self.path_config['error_field']: 'Possible spam blocked.'}
        else:
            # TODO: if we're handling all fields with no config,
            # we have nowhere to write errors.
            errors = {}
        response.body = htmlfill.render(form, defaults, errors=errors)
        return response
