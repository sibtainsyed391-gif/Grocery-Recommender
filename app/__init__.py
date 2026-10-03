import os
from flask import Flask
from app.recommender import Recommender
from app.db import BASE

def create_app():
    app = Flask(__name__)
    app.config["RECOMMENDER"] = Recommender(
        rules_path=os.path.join(BASE, "data", "processed", "rules.csv"),
        raw_path=os.path.join(BASE, "data", "processed", "all_transactions.csv"))
    from app.routes import bp
    app.register_blueprint(bp)
    return app