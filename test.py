#!/usr/bin/env python3

import os


def launch(url):
    """ Launch chrome app """
    print(f"launch google-chrome-stable --app={url}")
    os.system(f'google-chrome-stable --chrome-frame --user-data-dir="./chrometmp" --window-size=900,600 --app={url}')

launch("file:///home/pirx/flask-gui-app/test.html")
