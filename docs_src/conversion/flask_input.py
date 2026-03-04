from flask import Blueprint, Flask

app = Flask(__name__)
api = Blueprint("api", __name__, url_prefix="/api")


@api.route("/items", endpoint="list_items", strict_slashes=False)
def list_items():
    return {"items": []}


app.register_blueprint(api)
