from flask import Blueprint, Flask

app = Flask(__name__)
bp = Blueprint("items", __name__, url_prefix="/items")


@bp.get("/")
def list_items():
    return {"items": []}


app.register_blueprint(bp)
