import aw_datastore
from aw_server.server import AWFlask

# Выбираем метод хранения. Здесь используется, например, Peewee.
storage_method = aw_datastore.get_storage_methods()["peewee"]

# Создаём экземпляр приложения
# Gunicorn сам управляет хостом и портом, поэтому host можно указать как "0.0.0.0".
app = AWFlask(
    host="0.0.0.0",
    testing=False,
    storage_method=storage_method,
    cors_origins=[],
    custom_static={}
)
