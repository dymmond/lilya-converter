from lilya.apps import Lilya
from lilya.routing import Include, Path
from .views import health

urlpatterns = [Path('/', health, name='health'), Include(path='/api/', app='api.urls')]
app = Lilya(routes=urlpatterns)
