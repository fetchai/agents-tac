# -*- coding: utf-8 -*-
from multiprocessing import Process

import visdom.server

from tac.gui.panel import create_app

if __name__ == '__main__':
    app = create_app()
    app.run("127.0.0.1", 5000, debug=True, use_reloader=False)
