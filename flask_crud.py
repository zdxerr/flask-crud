# -*- coding: utf-8 -*-
"""
    flaskext.crud

    :copyright: (c) 2012 by Christoph Schniedermeier.
    :license: BSD, see LICENSE for more details.
"""
import werkzeug
from flask import request, Response, jsonify, views, abort
import sqlalchemy.exc

from utilities import link_headers, strings_to_dates

from functools import wraps

def check_auth(username, password):
    return (username == 'admin' and password == 'secretx')

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            abort(401)
        return f(*args, **kwargs)

    return decorated


class View(views.MethodView):
    def __init__(self, app, db, model, per_page, query_func):
        """
        """
        self.app = app
        self.db = db
        self.model = model
        self.per_page = per_page
        self.query_func = query_func

    def get(self, id):
        query = self.model.query

        if id:
            return jsonify({self.model.__tablename__: query.get_or_404(id)})
        else:
            search_query = request.values.get('q')
            if search_query:
                query = query.filter_by(name=search_query)

            if self.query_func:
                query = self.query_func(query)

            pagination = query.paginate(
                request.values.get('page', 1, type=int),
                request.values.get('per_page', self.per_page, type=int),
                error_out=False
            )

            name = self.model.__tablename__
            data = {name: pagination.items}
            return (jsonify(data), 200, link_headers(pagination))

    def post(self):
        data = request.values.to_dict()
        if request.json:
            data = request.json

        # parse strings for date and datetime columns
        data = strings_to_dates(self.model, data)

        try:
            item = self.model(**data)
        except TypeError as error:
            abort(400)

        self.db.session.add(item)
        try:
            self.db.session.commit()
        except sqlalchemy.exc.IntegrityError as ecx:
            abort(409, ecx.orig)

        return jsonify(id=item.id), 201

    def delete(self, id):
        item = self.model.query.get_or_404(id)
        self.db.session.delete(item)
        self.db.session.commit()
        return Response(status=204)

    def put(self, id):
        data = request.values
        if request.json:
            data = request.json

        item = self.model.query.get_or_404(id)
        for k, v in data.iteritems():
            if k in self.model.__table__.columns.keys():
                setattr(item, k, v)
        try:
            self.db.session.commit()
        except sqlalchemy.exc.IntegrityError as ecx:
            abort(409, ecx.orig)
        return Response(status=204)


class Rest:
    def __init__(self, app=None, db=None):
        self.app = app
        self.db = db
        self.models = {}

    def init_app(self, app):
        self.app = app
        self.add_rules()

    def __add_rule(self, model, methods, results_per_page, query_func):
        path = '/' + model.__tablename__ + '/'
        self.app.logger.debug("Add rule '%s' for methods: %s", path, 
                              ', '.join(methods))

        view = View.as_view('api_' + model.__tablename__, self.app,
                            self.db, model, results_per_page, query_func)
        view.decorators = [requires_auth]
        self.app.add_url_rule(path, defaults={'id': None},
                              view_func=view, methods=['GET', ])
        self.app.add_url_rule(path, view_func=view, methods=['POST', ])
        self.app.add_url_rule(path + '<int:id>', view_func=view,
                              methods=['GET', 'PUT', 'DELETE'])

    def add_rules(self):
        """
        Add all previously defined model routes to the application.
        """
        for model, rule in self.models.items():
            self.__add_rule(model, **rule)

    def api(self, methods=None, results_per_page=10, query_func=None):
        """
        Define new model.
        """
        def dec(model):
            """
            Decorator function memoizes model and its parameters.
            """
            self.models[model] = {
                'methods': methods,
                'results_per_page': results_per_page,
                'query_func': query_func
            }
            return model
        return dec
