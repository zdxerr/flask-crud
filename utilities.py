# -*- coding: utf-8 -*-
"""
    flaskext.crud.utilities

    :copyright: (c) 2012 by Christoph Schniedermeier.
    :license: BSD, see LICENSE for more details.
"""

from flask import request
from werkzeug import urls


def link_headers(p):
    """
    Create link headers using flask.ext.sqlalchemy.Pagination object.
    """
    LINK_STR = '<{}>; rel="{}"'
    base_url = urls.Href(request.base_url)
    links = {
        'first': 1 if not p.page == 1 else None,
        'prev': p.prev_num if p.has_prev else None,
        'next': p.next_num if p.has_next else None,
        'last': p.pages if not p.page == p.pages else None,
    }

    return {
        'access-control-expose-headers': 'Link',
        'link': ', '.join(LINK_STR.format(
            base_url(page=page, per_page=p.per_page), rel)
            for rel, page in links.items() if page)
    }
