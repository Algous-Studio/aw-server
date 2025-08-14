# aw-server/wsgi_gevent.py
from gevent import monkey
monkey.patch_all()  # socket, dns, ssl, threading, subprocess и т.д.

# сделать psycopg2 кооперативным (иначе PG-вызовы блокируют greenlet)
try:
    import psycogreen.gevent
    psycogreen.gevent.patch_psycopg()
except Exception:
    pass

# импорт приложения ПОСЛЕ patch
from wsgi import create_app  # или: from wsgi import app
app = create_app()
