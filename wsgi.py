# wsgi.py
from aw_server.server import AWFlask
from aw_datastore import get_storage_methods

# создаём приложение, передавая PostgresqlStorage в качестве storage_method
storage = get_storage_methods()["postgresql"]  # берёт наш класс
app = AWFlask(
    host="0.0.0.0",
    testing=False,
    storage_method=storage,
    cors_origins=[],
    custom_static={},
)
