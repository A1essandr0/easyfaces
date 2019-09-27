import os
from flask import Flask

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.getenv('FLASK_SECRET_KEY'),
        DATABASE=os.path.join(app.instance_path, 'imageapp.sqlite'),
    )

    if test_config is None:
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_mapping(test_config)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    from . import db, auth, images
    db.init_app(app)
    app.register_blueprint(auth.bp)
    app.register_blueprint(images.bp)
    app.add_url_rule('/', endpoint='index')

    return app
