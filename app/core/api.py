from flask import Flask
from flask import Response, request, json, url_for


class FlaskApi(Flask):

    def make_response(self, rv):
        if isinstance(rv, ApiResponse):
            return rv.to_response()
        return Flask.make_response(self, rv)


class ApiResponse:
    """Base class for API responses.
    Returns a :class:`~werkzeug.Response`.

    :param body: :class:`~flask_sqlalchemy.BaseQuery` or a subclass
    :param status: Response status code as defined in RFC 2616
    :param headers: Dictionary of additional headers
    """
    def __init__(self, body, status=200, headers={}):
        self.body = body
        self.status = status
        self.headers = headers

    def to_response(self):
        rv = Response(json.dumps(self.body),
                      status=self.status,
                      mimetype='application/json')
        rv.headers.extend(self.headers)
        if not self.body:
            rv.status_code = 204
        return rv

    def __repr__(self):
        fmt = '{}({}, status={}, headers={})'
        return fmt.format(self.__class__.__name__, repr(self.body),
                          self.status, self.headers)


class ApiPagedResponse(ApiResponse):
    """Paged ApiResponse.

    :param body: :class:`~flask_sqlalchemy.BaseQuery` or a subclass
    :param status: Response status code as defined in RFC 2616
    :param headers: Dictionary of additional headers
    :param max_per_page: Maximum number of items per page.
                         Overrides the ``per_page`` argument.
    :param filterfn: Filter function to be applied to each item
    :param exclude: list or tuple of fields to be excluded from
                    serialization
    """
    def __init__(self, body, status=200, headers={}, max_per_page=20,
                 filterfn=None, exclude=None):
        super().__init__(body, status, headers)
        self.maxperpage = max_per_page
        self.filterfn = filterfn
        self.exclude = exclude

    def to_response(self):
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', self.maxperpage, type=int),
                       self.maxperpage)
        paged = self.body.paginate(page, per_page)

        items = [i.serialize(self.exclude) for i in paged.items]

        if self.filterfn:
            items = list(map(self.filterfn, items))

        rv = Response(json.dumps({'page': page, 'count': paged.total,
                                  'items': items}),
                      status=self.status,
                      mimetype='application/json')

        rv.headers.extend(self.headers)
        links = []
        fmt = '<{}>; rel="First"'
        links.append(fmt.format(
            url_for(request.endpoint,
                    page=1,
                    per_page=per_page,
                    _external=True)))
        fmt = '<{}>; rel="Last"'
        links.append(fmt.format(
            url_for(request.endpoint,
                    page=paged.pages,
                    per_page=per_page,
                    _external=True)))
        if paged.has_prev:
            fmt = '<{}>; rel="Previous"'
            links.append(fmt.format(
                url_for(request.endpoint,
                        page=paged.prev_num,
                        per_page=per_page,
                        _external=True)))
        if paged.has_next:
            fmt = '<{}>; rel="Next"'
            links.append(fmt.format(
                url_for(request.endpoint,
                        page=paged.next_num,
                        per_page=per_page,
                        _external=True)))

        rv.headers['Link'] = ','.join(links)
        return rv

    def __repr__(self):
        fmt = '{}({}, status={}, max_per_page={}, filterfn={}, exclude={})'
        return fmt.format(self.__class__.__name__, repr(self.body),
                          self.status, self.maxperpage, self.filterfn,
                          self.exclude)


class ApiException(Exception):

    def __init__(self, msg, status=400):
        self.msg = msg
        self.status = status

    def to_response(self):
        return ApiResponse({'message': self.msg}, status=self.status)


class ApiValidationException(ApiException):

    def __init__(self, msg, status=422, validator=None):
        super().__init__(msg, status)
        self.validator = None

    def to_response(self):
        return ApiResponse({'message': self.msg, 'validator': self.validator},
                           status=self.status)
