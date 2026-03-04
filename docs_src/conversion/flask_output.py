from lilya.apps import Lilya as Flask
from lilya.routing import Router as Blueprint

app = Flask()
api = Blueprint()


@api.route('/api/items', name='list_items', methods=['GET'])
def list_items():
    return {'items': []}


app.include(path='/', app=api)
