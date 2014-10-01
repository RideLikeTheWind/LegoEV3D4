#!/usr/bin/python

from ev3.ev3dev import Ev3Dev, Key, Motor
from threading import Thread
from time import sleep
from json import loads as json_loads
from web import application as web_application
import logging
import signal
import sys
import os
import socket

logger = logging.getLogger(__name__)
r2d2 = None

class RESTServer(Thread):

    def __init__(self, _r2d2):
        Thread.__init__(self)

        global r2d2
        r2d2 = _r2d2

        urls = []
        class_name_to_object = {}

        def add_url(class_object, url):
            class_name = class_object.__name__
            class_name_to_object[class_name] = class_object
            urls.append(url)
            urls.append(class_name)

        add_url(self.move_start, '/move-start/(\w+)/(\d+)/?')
        add_url(self.move_stop,  '/move-stop/?')

        self.www = web_application(tuple(urls), class_name_to_object)

    def run(self):

        # Start the web server
        try:
            self.www.run()
        except:
            logger.error('Could not start REST API web server')

    class move_start():

        def GET(self, direction, speed):
            r2d2.move(direction, int(speed))
            return None

    class move_stop():

        def GET(self):
            r2d2.move('stop', None)
            return None


class LegoR2D2(Ev3Dev):

    def __init__(self):

        # Logger init
        logging.basicConfig(filename='/var/log/r2d2.log',
                            level=logging.DEBUG,
                            format='%(asctime)s %(levelname)7s: %(message)s')

        # Color the errors and warnings in red
        logging.addLevelName( logging.ERROR, "\033[91m%s\033[0m" % logging.getLevelName(logging.ERROR))
        logging.addLevelName( logging.WARNING, "\033[91m%s\033[0m" % logging.getLevelName(logging.WARNING))


        # EV3 init
        Ev3Dev.__init__(self)
        self.head        = Motor(port=Motor.PORT.A)
        self.right_wheel = Motor(port=Motor.PORT.B)
        self.left_wheel  = Motor(port=Motor.PORT.C)
        #print '%d%%' % self.get_battery_percentage(7945400)

        # "kill/kill -9" init
        signal.signal(signal.SIGTERM, self.signal_term_handler)
        signal.signal(signal.SIGINT, self.signal_int_handler)
        self.shutdown_flag = False

        self.rest_server = RESTServer(self)
        self.rest_server.start()


    def signal_term_handler(self, signal, frame):
        logger.error('Caught SIGTERM')
        self.shutdown_flag = True

    def signal_int_handler(self, signal, frame):
        logger.error('Caught SIGINT')
        self.shutdown_flag = True

    def move(self, direction, speed):

        if direction == 'forward':
            self.left_wheel.run_forever(speed * -1, regulation_mode=False)
            self.right_wheel.run_forever(speed * -1, regulation_mode=False)

        elif direction == 'backward':
            self.left_wheel.run_forever(speed, regulation_mode=False)
            self.right_wheel.run_forever(speed, regulation_mode=False)

        elif direction == 'left':
            self.left_wheel.run_forever(speed, regulation_mode=False)
            self.right_wheel.run_forever(speed * -1, regulation_mode=False)

        elif direction == 'right':
            self.left_wheel.run_forever(speed * -1, regulation_mode=False)
            self.right_wheel.run_forever(speed, regulation_mode=False)

        elif direction == 'lookleft':
            self.head.position=0
            self.head.run_position_limited(position_sp=45,
                                           speed_sp=800,
                                           stop_mode=Motor.STOP_MODE.COAST,
                                           ramp_up_sp=100,
                                           ramp_down_sp=100)

        elif direction == 'lookright':
            self.head.position=0
            self.head.run_position_limited(position_sp=-45,
                                           speed_sp=800,
                                           stop_mode=Motor.STOP_MODE.COAST,
                                           ramp_up_sp=100,
                                           ramp_down_sp=100)

        elif direction == 'stop':
            self.left_wheel.stop()
            self.right_wheel.stop()


    # This looks a little silly but we leave this loop running so we
    # can catch SIGTERM and SIGINT
    def run(self):

        while True:
            sleep(1)

            if self.shutdown_flag:
                return

    def shutdown(self):
        self.move('stop', None)

        logger.info('REST server shutdown begin')
        self.rest_server.www.stop()
        self.rest_server.join()
        self.rest_server = None
        logger.info('REST server shutdown complete')


if __name__ == '__main__':
    r2 = LegoR2D2()
    r2.run()
    r2.shutdown()
