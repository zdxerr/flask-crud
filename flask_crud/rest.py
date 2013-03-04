
from flask import request, Response, jsonify, views, render_template, abort
import sqlalchemy.exc

content_types = {
    'application/json': jsonify,
    'text/html': None,
    'text/csv': None
}


class View(views.MethodView):
    def __init__(self, app, db, model):
        self.app = app
        self.db = db
        self.model = model

    def get(self, id):
        accepted_content = request.accept_mimetypes.best_match(content_types)
        q = request.values.get('q')
        if id:
            return jsonify(self.model.query.get_or_404(id).to_dict())
        elif q:
            return jsonify(self.model.query.filter_by(name=q).first().to_dict())
        else:
            k = self.model.__tablename__ + 's'
            v = [r.to_dict() for r in self.model.query.all()]
            if accepted_content == 'text/html':
                return render_template('test.html', result={k: v})
            elif accepted_content == 'text/csv':
                return jsonify({k: v})
            return jsonify({k: v})

    def post(self):
        data = request.values.to_dict()
        if request.json:
            data = request.json

        if False:
            column_values = {k: v for (k, v) in request.values.iteritems(True)
                             if k in self.model.__table__.columns.keys()}
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

    def api(self, methods=None):
        def dec(model):
            view = View.as_view('api_' + model.__tablename__, self.app,
                                self.db, model)
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
