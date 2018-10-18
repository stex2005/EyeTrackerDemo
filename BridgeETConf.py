# -*- coding: utf-8 -*-
import ConfigParser
import math
import numpy

class BridgeETCoordClass:
    def __init__(self):

        # per ET
        self.gaze_POR                   = []
        self.screen_w                   = 1280
        self.screen_h                   = 1024
        self.gazedata_copy              = None
        self.gazedata_array             = []
        self.gaze_sate_var              = 0
        self.fixation_time              = 60
        self.exit                       = False
        self.fixation_bar               = False
        self.bar                        = [-1 -1]
        self.check_fixation             = False
        self.img                        = None
        self.state_variable             = -1

        # parameters for different areas of the screen
        self.webcam_size                = 780
        self.webcam_size_norm_w         = 780.0/1280.0
        self.webcam_size_norm_h         = 780.0/1024.0
        self.webcam_pos                 = numpy.array([240.0, 250.0])
        self.fixation_area              = 0.2 # metà larghezza dell'area di fissazione normalizzata, i.e. 0.1 = 10%
        self.fixation_samples_tol       = 25
        self.button_fixation_tol        = 10
        self.conf_box_w                 = 220.0/1280.0
        self.conf_box_h                 = 230.0/1024.0
        # joystick_butt_pos inidica le posizioni (normalizzate) sullo schermo delle frecce per usare l'ET come joystick
        # la struttura della matrice ha sulle righe xmin xmax ymin ymax e sulle colonne avanti indietro right left up down 
        self.joystick_butt_pos          = numpy.array([[380.0/1280.0, 610.0/1280.0, 0, 230.0/1024], \
            [670.0/1280.0, 900.0/1280.0, 0, 230.0/1024], \
            [1050.0/1280.0, 1280.0/1280.0, 240.0/1024.0, 470.0/1024], \
            [0.0/1280.0, 230.0/1280.0, 240.0/1024.0, 470.0/1024], \
            [0.0/1280.0, 230.0/1280.0, 475.0/1024.0, 705.0/1024], \
            [1050.0/1280.0, 1280.0/1280.0, 475.0/1024.0, 705.0/1024]])
        self.joystick                   = numpy.array([0, 0, 0, 0, 0, 0])
        self.joystick_reset             = numpy.array([0, 0, 0, 0, 0, 0])
        self.joystick_toll              = 10

        self.demo                       = True
        self.demo_coord                 = numpy.array([0.0, 0.0, 0.0])