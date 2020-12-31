#!/usr/bin/env python3
# pylint: disable=missing-function-docstring, missing-class-docstring
# pylint: disable=logging-not-lazy, logging-fstring-interpolation
# pylint: disable=wrong-import-position

# pylint: disable=line-too-long

""" Flask gui app """

import time
import logging
from gevent import monkey
monkey.patch_all()
from flask_socketio import SocketIO
from flask import Flask
from flask.views import View
from flask.logging import default_handler
from colorlog import ColoredFormatter
from bs4 import BeautifulSoup


# ------------------------------- logging --------------------------------------
stream = logging.StreamHandler()
LF = "%(log_color)s%(levelname)-8s%(reset)s | %(log_color)s%(message)s%(reset)s"
stream.setFormatter(ColoredFormatter(LF))
stream.setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)
logger.addHandler(stream)
logger.setLevel(logging.DEBUG)

default_handler.setLevel(logging.WARNING)


# -------------------------------- OBJS ----------------------------------------

class Obj:
    """ Abstract class OBJ """
    def __init__(self, name):
        self.name = name
        self.value = None

    def to_html(self):
        # pylint: disable=no-self-use
        """ return html entry """
        logger.error("Unimplemented method !")
        return ""

    def to_js_getter(self):
        # pylint: disable=no-self-use
        """ return js callback """
        return ""

    def to_js_setter(self):
        # pylint: disable=no-self-use
        """ return js setter """
        return ""

    def callback(self, value):
        """ client cb """
        self.value = value

    def __str__(self):
        return f"{self.__class__.__name__}::{self.name}({self.value})"

class ObjInputText(Obj):
    """ std input text """

    def to_html(self):
        """ return html entry """
        return '<input type="text" class="form-control" id="'+self.name+'" placeholder="msg"/>'

    def to_js_getter(self):
        """ return js callback """
        return "var "+self.name+"obj = $('#"+self.name+"').on('change', function() {\n"  + \
               "   text = $('#"+self.name+"').val()\n" + \
               "   console.log('"+self.name+"modif: ' + text)\n" + \
               "   socket.emit('user_event', { 'name': '"+self.name+"', 'data': text})\n" + \
               "})\n"


class ObjButton(Obj):
    """ std button """
    def __init__(self, name):
        super().__init__(name)
        self.on_click_cb = None

    def to_html(self):
        """ return html entry """
        return '<button type="button" class="btn btn-primary btn-lg" id="'+self.name+'">'+self.name+'</button>'

    def to_js_getter(self):
        """ return js callback """
        return "var "+self.name+"obj = $('#"+self.name+"').on('click', function() {\n"  + \
               "   console.log('"+self.name+" clicked')\n" + \
               "   socket.emit('user_event', { 'name': '"+self.name+"', 'data': 'x'})\n" + \
               "})\n"

    def callback(self, value):
        super().callback(value)
        if self.on_click_cb:
            self.on_click_cb()

    def set_on_click(self, cb):
        self.on_click_cb = cb

# ------------------------------ Frame -----------------------------------------

class ApplicationFrame():
    """
    Frame handler
    Create Flask view and widgets handlers from template file
    """
    def _create_widget(self, div):
        """
        Create widget from obj div : id=obj.<ObjClass>.<name>
        Exemple : id=obj.ObjButton.mySuperButton
        """
        # get id
        divid = div.get('id')
        if divid is None:
            return
        # format
        array = divid.split('.')
        if array[0] != "obj":
            return
        # check array
        if len(array) != 3:
            logger.error(f"Invalid format : {divid} in {div}")
            return
        # find class
        if not array[1] in globals().keys():
            logger.error(f"Invalid class : {array[1]} in {div}")
            return
        obj_class = globals()[array[1]]
        # name
        obj_name = array[2]
        if obj_name in self.widgets.keys():
            logger.error(f"Existing name : {obj_name} in {div}")
            return
        # Create widget
        widget = obj_class(obj_name)
        # Push widget
        self.widgets[obj_name] = widget
        # Apprend widget
        minisoup = BeautifulSoup(widget.to_html(), "html5lib")
        div.replace_with(minisoup.body.contents[0])

    def __init__(self, template_name, application):
        """
        template.html --> (result.html/js/css, widgets)
        """
        self.name = template_name
        self.application = application  # Application
        self.widgets = {}  # widgets
        # open file
        with open(template_name, "r" ) as f:
            html_doc = f.read()
        self.soup = BeautifulSoup(html_doc, "html5lib")
        # Create Objects & html
        for div in self.soup.find_all('div'):
            # print("DIV:" + str(div))
            self._create_widget(div)
        # apprend script
        getters = "".join(map(lambda o: o.to_js_getter(), self.widgets.values()))
        setters = "".join(map((lambda i: "case '"+i[0]+"':\n"+i[1].to_js_setter()+"break;\n"), self.widgets.items()))

        script = ('<script src="//cdnjs.cloudflare.com/ajax/libs/socket.io/2.2.0/socket.io.js" integrity="sha256-yr4fRk/GU1ehYJPAs8P4JlTgu0Hdsp4ZKrx8bDEDC3I=" crossorigin="anonymous"></script>\n'
                  '<script type="text/javascript">\n'
                  '//var socket = io.connect(null, {port: location.port, rememberTransport: false});\n'
                  'var socket = io();\n'
                  "socket.on( 'connect', function(data) {\n"
                  "    console.log('On connect :'+ data)\n"
                  "    socket.emit( 'debug', 'User Connected')\n"
                  "})\n"
                  "socket.on('on_ping', function(data) {\n"
                  "    console.log('On ping :' + data)\n"
                  "    console.log('Send pong')\n"
                  "    socket.emit('on_pong', {'rawdata': data})\n"
                  "})\n"
                  "socket.on( 'user_event', function( eventdata ) {\n"
                  "    console.log('name:' + eventdata.name + ' data:' + eventdata.data)\n"
                  "    console.log('On user_event :' + eventdata + ' ' + typeof eventdata)\n"
                  "    console.log(eventdata.name)\n"
                  "    switch(eventdata.name){\n" + setters + "}\n"
                  "})\n"
                  "" + getters + "\n"
                  "</script>\n")

        header = ('<title>pyconsole</title>\n'
                  '<link rel="icon" href="data:,">\n'
                  '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
                  '<script src="https://ajax.googleapis.com/ajax/libs/jquery/1.12.4/jquery.min.js"></script>\n'
                  '<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.4.1/css/bootstrap.min.css">\n'
                  '<script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.4.1/js/bootstrap.min.js"></script>\n')

        for content in BeautifulSoup(script, "html5lib").head.contents:
            self.soup.body.append(content)

        self.soup.head.append(BeautifulSoup(header, "html5lib"))

        self.soup.prettify("utf-8")
        logger.info(f"Initialisation {template_name} done")
        logger.info(self.soup)
        logger.info(self)
        # write output in file (DEBUG)
        with open(".".join(self.name.split('.')[:-1]) + "-gen.html", 'w') as f:
            f.write(self._render_html())

    def _render_html(self):
        """ render template output (html) """
        return str(self.soup)

    # class HandlerObj
    def frame_callback(self, objname, value):
        """ Update internal value from client """
        logger.info(f"UPDATE_INTERNALS {objname}:{value}")
        if not objname in self.widgets.keys():
            logger.error(f"Inexisting object {objname}")
            return None
        return self.widgets[objname].callback(value)

    def frame_set(self, objname, value):
        """ Update internal and client from server """
        if not objname in self.widgets.keys():
            logger.error(f"Inexisting object {objname}")
            return None
        return self.widgets[objname].set(value)

    def to_view(self):
        """ Return flask view """
        class FrameView(View):
            def __init__(self, html):
                self.html = html

            def dispatch_request(self):
                return self.html

        return FrameView.as_view('aaaa', self._render_html())


    def __str__(self):
        """ str """
        return "\n".join(str(k)+":"+str(v) for k, v in self.widgets.items())

    def __getitem__(self, arg):
        return self.widgets[arg]

# ------------------------------ FLASK APP -------------------------------------
class Application:
    def __init__(self, mainframename):
        # Init flask
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'secret!'
        #self.logger.addHandler(create_logger(self.app))
        # https://flask-socketio.readthedocs.io/en/latest/
        self.socketio = SocketIO(self.app, ping_interval=10)
        # Views
        self.main_frame = ApplicationFrame(mainframename, self)
        self.app.add_url_rule('/', view_func=self.main_frame.to_view())
        # Views socketio
        self.socketio.on_event('connect', self.handler_connect)
        self.socketio.on_event('disconnect', self.handler_disconnect)
        self.socketio.on_event('on_pong', self.handler_pong)
        self.socketio.on_event('user_event', self.handler_user_event)
        self.socketio.on_event('debug', self.handler_debug)
        logger.info("[Application] init done")


    def ping(self):
        self.socketio.emit('on_ping', str(time.time_ns()))

    def handler_pong(self, data):
        # pylint: disable=no-self-use
        ping = (time.time_ns() - int(data["rawdata"]))/1000000
        logger.info("[Application] handler_pong :" + str(ping) + "ms")

    def handler_connect(self):
        logger.info('[Application] handler_connect')
        logger.info("[Application] send ping ...")
        self.ping()

    def handler_disconnect(self):
        # pylint: disable=no-self-use
        logger.info('[Application] handler_disconnect')
        # shutdown server

    def handler_user_event(self, event_data):
        logger.info('[Application] handler_user_event: ' + str(event_data))
        obj_name = event_data['name']
        obj_data = event_data['data']
        self.main_frame.frame_callback(obj_name, obj_data)

    def send_user_event(self, name, data):
        event_data = {'name': name, 'data': data}
        self.socketio.emit('user_event', event_data)

    def handler_debug(self, data):
        # pylint: disable=no-self-use
        logger.info("[Application] client debug: " + data)

    def run(self, debug=False):
        #  host="0.0.0.0" , debug=False
        self.socketio.run(self.app, debug=debug, port=5000)


if __name__ == '__main__':

    def back_end_app():
        """ user application """
        # just do logging
        for widget in app.main_frame.widgets.values():
            logger.warning(str(widget))

    app = Application('templates/main_view.html')

    app.main_frame['myButt'].set_on_click(back_end_app)

    app.run(debug=True)
    print("DONE")
