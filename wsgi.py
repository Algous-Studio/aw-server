# wsgi.py
import os, atexit
from aw_server.server import AWFlask
from aw_datastore import get_storage_methods

def create_app() -> AWFlask:
    storage_methods = get_storage_methods()
    storage_id = os.getenv("AW_STORAGE", "postgresql")
    storage_method = storage_methods.get(storage_id)
    if storage_method is None:
        raise ValueError(f"Unsupported storage: {storage_id}")

    host = os.getenv("AW_HOST", "0.0.0.0")
    cors = os.getenv("AW_CORS_ORIGINS", "")
    cors_origins = [o for o in cors.split(",") if o]

    app = AWFlask(
        host=host,
        testing=False,
        storage_method=storage_method,
        cors_origins=cors_origins,
        custom_static={},
    )
    # Закрываем пул только при завершении процесса воркера
    def _close_storage():
        storage = getattr(app.api.db, "storage_strategy", None)
        if storage and hasattr(storage, "close"):
            try:
                storage.close()
            except Exception:
                pass

    atexit.register(_close_storage)
    return app

app = create_app()
