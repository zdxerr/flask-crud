# -*- coding: utf-8 -*-
"""
    flaskext.crud.utilities

    :copyright: (c) 2012 by Christoph Schniedermeier.
    :license: BSD, see LICENSE for more details.
"""

from sqlalchemy import Date, DateTime
from sqlalchemy.sql.expression import ColumnElement
from sqlalchemy.ext.associationproxy import AssociationProxy
from sqlalchemy.orm import RelationshipProperty

from flask import request
from werkzeug import urls

from dateutil.parser import parse as parse_datetime


def link_headers(pagination):
    """
    Create link headers using flask.ext.sqlalchemy.Pagination object.
    """
    link_str = '<{}>; rel="{}"'
    base_url = urls.Href(request.base_url)
    links = {
        'first': 1 if not pagination.page == 1 else None,
        'prev': pagination.prev_num if pagination.has_prev else None,
        'next': pagination.next_num if pagination.has_next else None,
        'last': (pagination.pages 
                 if not pagination.page == pagination.pages else None),
    }

    return {
        'access-control-expose-headers': 'Link',
        'link': ', '.join(link_str.format(
            base_url(page=page, per_page=pagination.per_page), rel)
            for rel, page in links.items() if page)
    }




def is_date_field(model, fieldname):
    """
    Returns ``True`` if and only if the field of `model` corresponds to either 
    a `Date` object or a `Datetime` object.
    """
    field = getattr(model, fieldname, None)
    if isinstance(field, ColumnElement):
        fieldtype = field.type
    else:
        if isinstance(field, AssociationProxy):
            field = field.remote_attr
        if hasattr(field, 'property'):
            prop = field.property
            if isinstance(prop, RelationshipProperty):
                return False
            fieldtype = prop.columns[0].type
        else:
            return False
    return isinstance(fieldtype, Date) or isinstance(fieldtype, DateTime)


def strings_to_dates(model, data):
    """
    Returns a new dictionary with all the mappings of `data` but with date 
    strings mapped to `datetime.datetime` objects.
    """
    result = {}
    for key, value in data.items():
        if is_date_field(model, key) and value is not None:
            if value.strip() == '':
                result[key] = None
            else:
                result[key] = parse_datetime(value)
        else:
            result[key] = value
    return result
