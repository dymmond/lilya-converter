from lilya.apps import Lilya as Flask
from lilya.routing import Router as Blueprint
app = Flask()
bp = Blueprint()

@bp.get('/items')
def list_items():
    return {'items': []}
app.include(path='/', app=bp)
