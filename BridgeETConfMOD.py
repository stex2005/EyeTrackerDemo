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
        self.fixation_time              = numpy.array([30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0])
        self.exit                       = False
        self.fixation_bar               = False
        self.bar                        = [-1 -1]
        self.check_fixation             = False
        self.img                        = None
        self.state_variable             = -1
        #nuova aggiunta
        self.old_state_variable         = -1

        # parameters for different areas of the screen
        self.webcam_size                = 610
        self.webcam_size_norm_w         = 780.0/1280.0
        self.webcam_size_norm_h         = 780.0/1024.0
        self.webcam_pos                 = numpy.array([334.5, 208.0])
        self.fixation_area              = 0.2 # metà larghezza dell'area di fissazione normalizzata, i.e. 0.1 = 10%
        self.fixation_samples_tol       = 25
        self.button_fixation_tol        = 10
        self.conf_box_w                 = 220.0/1280.0
        self.conf_box_h                 = 230.0/1024.0
        # joystick_butt_pos inidica le posizioni (normalizzate) sullo schermo delle frecce per usare l'ET come joystick
        # la struttura della matrice ha sulle righe xmin xmax ymin ymax e sulle colonne avanti indietro right left up down 
        self.joystick_butt_pos          = numpy.array([[335.0/1280.0, 630.0/1280.0, 20.0/1024.0, 251.0/1024.0], #up
            [650.0/1280.0, 945.0/1280.0, 20/1024.0, 251.0/1024.0],  # down
            [965.0/1280.0, 1260.0/1280.0, 271.0/1024.0, 502.0/1024],  # right
            [20.0/1280.0, 315.0/1280.0, 271.0/1024.0, 502.0/1024],  # left
            [20.0/1280.0, 315.0/1280.0, 522.0/1024.0, 753.0/1024],  # forward
            [965.0/1280.0, 1260.0/1280.0, 522.0/1024.0, 753.0/1024],  # back
            [20.0/1280.0, 313.0/1280.0, 773.0/1024.0, 1004.0/1024.0],  # supination
            [965.0/1280.0, 1260.0/1280.0, 773.0/1024.0, 1004.0/1024.0]])  # pronation

        # la struttura della lista ha sulle righe xmin, xmax, ymnin, ymax
        self.emergency_butt_pos         = [20.0/1280.0, 315.0/1280.0, 20.0/1024.0, 251.0/1024.0]
        self.standby_butt_pos           = [965.0/1280.0, 1260.0/1280, 20.0/1024.0, 251.0/1024.0]
        self.save_butt_pos              = [335.0/1280.0,630.0/1280,773.0/1024.0,1004.0/1024.0]
        self.recall_butt_pos            = [650.0/1280.0,945.0/1280,773.0/1024,1004.0/1024.0]

        # HOME BUTTONS POSITION
        self.off_tracker_butt_pos = [95.0 / 1280.0, 395.0 / 1280.0, 362.0 / 1024.0, 662.0 / 1024.0]
        self.settings_butt_pos = [490.0 / 1280.0, 790.0 / 1280.0, 362.0 / 1024.0, 662.0 / 1024.0]
        self.precontrol_butt_pos = [885.0 / 1280.0, 1185.0 / 1280.0, 362.0 / 1024.0, 662.0 / 1024.0]

        # SETTINGS BUTTONS POSITION
        self.back_hall_butt_pos = [20.0 / 1280.0, 252.0 / 1280.0, 20.0 / 1024.0, 252.0 / 1024.0]
        self.ball_xpos = [352, 474, 596, 718, 840, 962, 1084]
        self.arrow_ypos = [424.423, 617.423, 810.423]
        self.i_r = 2
        self.i_b = 2
        self.i_o = 3  #indice valido anche per fix time
        self.i_a = 0
        # Ordine bottoni è: UP;DOWN;LEFT;RIGHT.
        self.settings_joystick_butt_pos = numpy.array([[272.0 / 1280.0, 504.0 / 1280.0, 20.0 / 1024.0, 252.0 / 1024.0], \
                                                       [524.0 / 1280.0, 726.0 / 1280.0, 20 / 1024.0, 252.0 / 1024.0], \
                                                       [776.0 / 1280.0, 1008.0 / 1280.0, 20.0 / 1024.0, 252.0 / 1024], \
                                                       [1028.0 / 1280.0, 1260.0 / 1280.0, 20.0 / 1024.0, 252.0 / 1024]])


        # la struttura della matrice ha sulle righe xmin xmax ymin ymax e sulle colonne mem1 mem2
        self.mem_butt_pos               = numpy.array([[0.0/1280.0, 230.0/1280.0, 705.0/1024, 935.0/1024], \
            [0.0/1280.0, 230.0/1280.0, 935.0/1024, 1165.0/1024]])
        self.joystick                   = numpy.array([0, 0, 0, 0, 0, 0])
        self.joystick_reset             = numpy.array([0, 0, 0, 0, 0, 0])
        self.joystick_toll              = 25

        self.demo                       = True
        self.demo_coord                 = numpy.array([0.0, 0.0, 0.0])

        #self.ETtarget_coord             = [50, 0, 0]
        #self.ETtarget_coord             = [-75, 96, 120]
        #self.ETtarget_coord             = [10, -180, -80]
        self.ETtarget_coord             = [75, -60, 100]

        #Area Salvataggio
        self.saving_zone_exit_butt = numpy.array([22.0/1280.0, 314.0/1280.0, 20.0/1024.0, 251.0/1024.0])

        #Area Richiama Posizione
        self.recall_zone_butt = numpy.array([[21.0/1280.0, 312.0/1280.0, 20.0/1024.0, 251.0/1024.0], [965.0/1280.0, 1259.0/1280.0, 20.0/1024.0, 251.0/1024.0]])