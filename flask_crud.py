# -*- coding: utf-8 -*-
"""
    flaskext.crud

    :copyright: (c) 2012 by Christoph Schniedermeier.
    :license: BSD, see LICENSE for more details.
"""


from flask import request, Response, jsonify, views, render_template, abort
import sqlalchemy.exc

from utilities import link_headers

content_types = {
    'application/json': jsonify,
    'text/html': None,
    'text/csv': None
}


class View(views.MethodView):
    def __init__(self, app, db, model, per_page):
        self.app = app
        self.db = db
        self.model = model
        self.per_page = per_page

    def get(self, id):
        accepted_content = request.accept_mimetypes.best_match(content_types)
        query = self.model.query

        if id:
            return jsonify(query.get_or_404(id).to_dict())
        else:
            q = request.values.get('q')
            if q:
                query = query.filter_by(name=q)

            p = query.paginate(
                request.values.get('page', 0, type=int),
                request.values.get('per_page', self.per_page, type=int)
            )

            data = {self.model.__tablename__ + 's':
                    [r.to_dict() for r in p.items]}

            if accepted_content == 'text/html':
                return render_template('test.html', result=data)
            elif accepted_content == 'text/csv':
                return jsonify(data)

            return (jsonify(data), 200, link_headers(p))

    def post(self):
        data = request.values.to_dict()
        if request.json:
            data = request.json

        if False:
            column_values = dict((k, v) for k, v in request.values.items(True)
                                 if k in self.model.__table__.columns.keys())
            item = self.model.query.filter_by(**column_values).first()
            if not item:
                item = self.model(**data)
                self.db.session.add(item)
                self.db.session.commit()
        try:
            item = self.model(**data)
        except TypeError:
            abort(400)

        self.db.session.add(item)
        try:
            self.db.session.commit()
        except sqlalchemy.exc.IntegrityError, ecx:
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
        except sqlalchemy.exc.IntegrityError, ecx:
            abort(409, ecx.orig)
        return Response(status=204)


class Rest:
    def __init__(self, app, db):
        self.app = app
        self.db = db

    def api(self, methods=None, results_per_page=10):
        def dec(model):
            view = View.as_view('api_' + model.__tablename__, self.app,
                                self.db, model, results_per_page)
            path = '/' + model.__tablename__ + '/'
            self.app.add_url_rule(path, defaults={'id': None},
                                  view_func=view, methods=['GET', ])
            self.app.add_url_rule(path, view_func=view, methods=['POST', ])
            self.app.add_url_rule(path + '<int:id>', view_func=view,
                                  methods=['GET', 'PUT', 'DELETE'])

            self.app.add_url_rule(path + '<slug>', view_func=view,
                                  methods=['GET'])

            return model
        return dec
