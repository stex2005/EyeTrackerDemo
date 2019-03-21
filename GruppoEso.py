
#!/usr/bin/python

import sys

sys.path.append("C:\Python27\Lib\site-packages\gtk-2.0")
sys.path.append("C:\Users\Stefano\PycharmProjects\EyeTracker Demo\\tobii-analytics-sdk-3.1.0-win-Win32\Python27\Modules")

import pygtk

pygtk.require('2.0')
import gtk

# from tobii.eye_tracking_io.basic import EyetrackerException

glib_idle_add = None
glib_timeout_add = None
try:
    import glib

    glib_idle_add = glib.idle_add
    glib_timeout_add = glib.timeout_add
except:
    glib_idle_add = gtk.idle_add

    glib_timeout_add = gtk.timeout_add

import os
import math

import tobii.eye_tracking_io.mainloop
import tobii.eye_tracking_io.browsing
import tobii.eye_tracking_io.eyetracker

from tobii.eye_tracking_io.types import Point2D, Blob

from BridgeConf import BridgeCoordClass, BridgeClass, BridgeConfClass
#from BridgeETConf import BridgeETCoordClass

from BridgeETConfMOD import BridgeETCoordClass
#from BridgeJoint import Joint
#from BridgeCtrl import Thread_ControlClass
import numpy
import threading, time
from PIL import Image

import scipy.misc
import time
import cv2
import pandas as pd

# definizione variabili per salvare file
# text_01 = open("validity.txt","w")
# text_02 = open("camerapos.txt","w")
# text_03 = open("calib.txt","w")
# text_04 = open("age.txt","w")

global Streaming_x
global Streaming_y
global Protoresult_x
global Protoresult_y
global Punti_base_x
global Punti_base_y

Streaming_x = []
Streaming_y = []
Protoresult_x = []
Protoresult_y = []
Punti_base_x = []
Punti_base_y =[]


#Thread per check tempo fissazione protocollo
class Threading_Protocol(threading.Thread):

    def __init__(self, ETCoord,Threading_Protocol):

        threading.Thread.__init__(self)
        self.stop = threading.Event()
        self.ETCoord = ETCoord
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.canvas = gtk.DrawingArea()
        self.window.add(self.canvas)
        self.canvas.connect("expose_event", self.on_expose)
        self.points = [(0.1, 0.1), (0.8, 0.1), (0.4, 0.9), (0.8,0.4),(0.6,0.2),(0.1,0.6),(0.5,0.5),(0.9,0.9),(0.2,0.3)]

        self.point_index = -1
        self.running = False
        self.Threading_Protocol=Threading_Protocol


    def run(self):

        self.ETCoord.state_variable = 5  # Entriamo nel protocollo
        self.window.fullscreen()
        self.window.show_all()
        self.point_index = -1

        self.wait_for_add()
        self.running = True

        while self.running == True:
            if self.ETCoord.state_variable == 6:
                self.wait_for_add()
                self.ETCoord.state_variable = 5
            time.sleep(0.1)

    def terminate(self):
        self.window.destroy()
        eb.main()
        self.running = False
        self.ETCoord.state_variable= -1

    def wait_for_add(self):
        self.point_index += 1
        self.add_point()
        if self.point_index != len(self.points):
            self.redraw()

    def add_point(self):
        print(self.point_index)
        if self.point_index < len(self.points):
            p = Point2D()
            p.x, p.y = self.points[self.point_index]
        self.on_add_completed()

        return False
    def on_add_completed(self):
        if self.point_index == len(self.points):
            print "Fine Protocollo"
            # This was the last calibration point

            a = time.strftime("%B %d - ore %H.%M")

            
            p={'x':Protoresult_x, 'y':Protoresult_y}
            dfp = pd.DataFrame(data=p)
            dfp.to_csv('Ptr %s.csv' % a , at=False, index=False)

            s={'x':Streaming_x, 'y':Streaming_y}
            dfs = pd.DataFrame(data=s)

            dfs.to_csv('Str %s.csv' % a , at=False, index=False)

            t={'x':Punti_base_x, 'y':Punti_base_y}
            dft = pd.DataFrame(data=t)
            dft.to_csv('Punti_base %s.csv' % a , at=False, index=False)



            self.terminate()
        else:
            self.ETCoord.state_variable = 5

        return False

    def on_expose(self, widget, event):
        context = widget.window.cairo_create()
        context.rectangle(event.area.x, event.area.y, event.area.width, event.area.height)
        context.clip()

        self.draw(context)
        return False
    def draw(self, ctx):
        if self.point_index >= -1:
            x, y = self.points[self.point_index]

            bounds = self.canvas.get_allocation()
            # Draw calibration dot
            ctx.set_source_rgb(255, 0, 0)
            radius = 0.012 * bounds.width
            ctx.arc(bounds.width * x, bounds.height * y, radius, 0, 2 * math.pi)
            ctx.fill()

            # Draw center dot
            ctx.set_source_rgb(0, 0, 0);
            radius = 2;
            ctx.arc(bounds.width * x, bounds.height * y, radius, 0, 2 * math.pi)
            ctx.fill()

    def redraw(self):
        if self.canvas.window:
            alloc = self.canvas.get_allocation()
            rect = gtk.gdk.Rectangle(0, 0, alloc.width, alloc.height)
            self.canvas.window.invalidate_rect(rect, True)
        else:
            print "error mega error"




class Thread_TrackingClass(threading.Thread):



    def __init__(self, ETCoord, Coord, trackstatus, eyetracker):

        threading.Thread.__init__(self)
        self.stop = threading.Event()
        self.running = False

        self.ETCoord = ETCoord
        self.Coord = Coord
        self.trackstatus = trackstatus
        self.eyetracker = eyetracker

        self.ETCoord.gaze_POR = numpy.array([0.0, 0.0])
        self.ETCoord.gazedata_copy = []

        # contatori per la verifica delle fissazioni sui pulsanti
        self.i_ok = 0
        self.i_no = 0
        self.i_exit = 0
        self.i_joystick = numpy.array([0, 0, 0, 0, 0, 0, 0, 0])  # up down right left...

        self.i_ok_reset = 0
        self.i_no_reset = 0
        self.i_exit_reset = 0
        self.i_joystick_reset = numpy.array([0, 0, 0, 0, 0, 0, 0, 0])  # up down right left...

        # contatori per la verifica delle fissazioni sulla webcam
        self.delay_start = 0
        self.camp_primo = -1
        self.check_quadrato = False
        self.counter = 0
        self.camp_in = 0
        self.camp_out = 0
        self.somma_x = 0
        self.somma_y = 0

        # nome file per calibrazione
        self.name_file_calib = 1

        #punti per il protocollo da aggiornare a fronte di qualsiasi cambiamento
        self.circle=False

        # New buttons counters
        #save button
        self.i_save = 0
        self.i_save_reset = 0
        #recall button
        self.i_recall = 0
        self.i_recall_reset = 0

        self.i_old=-1

        # Home buttons counters
        self.i_precontrol = 0
        self.i_precontrol_reset = 0

        self.i_settings = 0
        self.i_settings_reset = 0

        self.i_off_tracker = 0
        self.i_off_tracker_reset = 0

        self.i_off_tracker = 0
        self.i_off_tracker_reset = 0

        # Settings buttons counters
        self.i_settings = 0
        self.i_settings_reset = 0
        self.i_settings_joystick = numpy.array([0, 0, 0, 0, 0, 0])
        self.i_settings_joystick_reset = numpy.array([0, 0, 0, 0, 0, 0])
        self.i_back_home = 0
        self.i_back_home_reset = 0

        #Contatori zona salvataggio
        self.i_back_control=0
        self.i_back_control_reset=0

        #Contatori zona recall position
        self.i_recall_butt = numpy.array([0, 0])
        self.i_recall_butt_reset = numpy.array([0, 0])

    def run(self):

        self.running = True

        if self.eyetracker is not None:
            self.eyetracker.StopTracking()
            self.eyetracker.events.OnGazeDataReceived -= self.on_gazedata

        self.gazedata = None
        if self.eyetracker is not None:
            self.eyetracker.events.OnGazeDataReceived += self.on_gazedata
            self.eyetracker.StartTracking()

    def on_gazedata(self, error, gaze):

        if hasattr(gaze, 'TrigSignal'):
            print "Trig signal:", gaze.TrigSignal

        self.ETCoord.gazedata_copy = {'left': {'validity': gaze.LeftValidity,
                                               'camera_pos': gaze.LeftEyePosition3DRelative,
                                               'screen_pos': gaze.LeftGazePoint2D},
                                      'right': {'validity': gaze.RightValidity,
                                                'camera_pos': gaze.RightEyePosition3DRelative,
                                                'screen_pos': gaze.RightGazePoint2D}}
        # print gaze.LeftEyePosition3DRelative

        self.ETCoord.gaze_POR = (
        (gaze.LeftGazePoint2D.x + gaze.RightGazePoint2D.x) / 2, (gaze.LeftGazePoint2D.y + gaze.RightGazePoint2D.y) / 2)


        '''Protoste'''
        if self.ETCoord.state_variable == 5 and self.delay_start <= 180:
            self.delay_start = self.delay_start + 1

        if self.ETCoord.state_variable == 5 and self.delay_start >= 180:

            if self.ETCoord.gaze_POR[0]!=-1 and self.ETCoord.gaze_POR[1]!=-1:

                if self.camp_primo == -1:
                    self.camp_primo = self.ETCoord.gaze_POR
                    Punti_base_x.append(self.camp_primo[0])
                    Punti_base_y.append(self.camp_primo[1])
                    self.check_circle = True
                    self.counter = 0


                if self.check_circle and self.counter < self.ETCoord.fixation_time[self.ETCoord.i_o]:

                    self.counter = self.counter + 1
                    if math.sqrt(((self.ETCoord.gaze_POR[0] - self.camp_primo[0])*1280)**2 + ((self.ETCoord.gaze_POR[1] - self.camp_primo[1])*1024)**2)<30:

                        Streaming_x.append(self.ETCoord.gaze_POR[0])
                        Streaming_y.append(self.ETCoord.gaze_POR[1])
                        self.camp_in = self.camp_in + 1
                        self.somma_x = self.somma_x + self.ETCoord.gaze_POR[0]
                        self.somma_y = self.somma_y + self.ETCoord.gaze_POR[1]
                    else:
                        self.camp_out = self.camp_out + 1
                        if self.camp_out > self.ETCoord.fixation_samples_tol:
                            self.counter = 0
                            self.camp_primo = -1
                            self.check_circle = False
                            self.somma_x = 0
                            self.somma_y = 0
                            self.camp_out = 0
                            self.camp_in = 0
                elif self.counter >= self.ETCoord.fixation_time[self.ETCoord.i_o]:
                    self.ETCoord.bar = [self.somma_x / self.camp_in, self.somma_y / self.camp_in]
                    Protoresult_x.append(self.ETCoord.bar[0])
                    Protoresult_y.append(self.ETCoord.bar[1])
                    self.ETCoord.state_variable = 6
                    self.counter = 0
                    self.camp_primo = -1
                    self.check_circle = False
                    self.somma_x = 0
                    self.somma_y = 0
                    self.camp_in = 0
                    self.camp_out = 0
                    self.delay_start = 0

        '''START PRE-CONTROL'''
        if self.ETCoord.state_variable == 10:
            if self.ETCoord.gaze_POR[0] >= self.ETCoord.precontrol_butt_pos[0] and self.ETCoord.gaze_POR[1] >= \
                    self.ETCoord.precontrol_butt_pos[2] and self.ETCoord.gaze_POR[0] <= \
                    self.ETCoord.precontrol_butt_pos[1] and \
                    self.ETCoord.gaze_POR[1] <= self.ETCoord.precontrol_butt_pos[3]:
                self.i_precontrol = self.i_precontrol + 1
            else:
                if self.i_precontrol_reset >= self.ETCoord.button_fixation_tol:
                    self.i_precontrol = 0
                    self.i_precontrol_reset = 0
                else:
                    self.i_precontrol_reset = self.i_precontrol_reset + 1

            if self.i_precontrol >= self.ETCoord.fixation_time[self.ETCoord.i_o]:
                print "PRE-CONTROL"
                self.ETCoord.old_state_variable = self.ETCoord.state_variable
                self.ETCoord.state_variable = 0  # Stato della zona pre-controllo
                self.i_precontrol = 0
                self.i_precontrol_reset = 0

                '''SETTINGS'''

        if self.ETCoord.state_variable == 10:
            if self.ETCoord.gaze_POR[0] >= self.ETCoord.settings_butt_pos[0] and self.ETCoord.gaze_POR[1] >= \
                    self.ETCoord.settings_butt_pos[2] and self.ETCoord.gaze_POR[0] <= self.ETCoord.settings_butt_pos[1] and \
                    self.ETCoord.gaze_POR[1] <= self.ETCoord.settings_butt_pos[3]:
                self.i_settings = self.i_settings + 1
            else:
                if self.i_settings_reset >= self.ETCoord.button_fixation_tol:
                    self.i_settings = 0
                    self.i_settings_reset = 0
                else:
                    self.i_settings_reset = self.i_settings_reset + 1

            if self.i_settings >= self.ETCoord.fixation_time[self.ETCoord.i_o]:
                print "SETTINGS"
                self.ETCoord.old_state_variable = self.ETCoord.state_variable
                self.ETCoord.state_variable = 11  # Stato della zona Settings
                self.i_settings = 0
                self.i_settings_reset = 0

            '''KILL THE PROGRAM'''
        if self.ETCoord.state_variable == 10:
            if self.ETCoord.gaze_POR[0] >= self.ETCoord.off_tracker_butt_pos[0] and self.ETCoord.gaze_POR[1] >= \
                    self.ETCoord.off_tracker_butt_pos[2] and self.ETCoord.gaze_POR[0] <= self.ETCoord.off_tracker_butt_pos[
                1] and \
                    self.ETCoord.gaze_POR[1] <= self.ETCoord.off_tracker_butt_pos[3]:
                self.i_off_tracker = self.i_off_tracker + 1
            else:
                if self.i_off_tracker_reset >= self.ETCoord.button_fixation_tol:
                    self.i_off_tracker = 0
                    self.i_off_tracker_reset = 0
                else:
                    self.i_off_tracker_reset = self.i_off_tracker_reset + 1

            if self.i_off_tracker >= self.ETCoord.fixation_time[self.ETCoord.i_o]:
                print "PROGRAM KILLED"
                self.i_off_tracker = 0
                self.i_off_tracker_reset = 0
                self.ETCoord.exit = True
                self.running = False
                self.ETCoord.old_state_variable = self.ETCoord.state_variable
                self.ETCoord.state_variable = -1

            '''BACK TO HOME FROM SETTINGS'''
        if self.ETCoord.state_variable == 11:
            if self.ETCoord.gaze_POR[0] >= self.ETCoord.back_hall_butt_pos[0] and self.ETCoord.gaze_POR[1] >= \
                    self.ETCoord.back_hall_butt_pos[2] and self.ETCoord.gaze_POR[0] <= self.ETCoord.back_hall_butt_pos[
                1] and \
                    self.ETCoord.gaze_POR[1] <= self.ETCoord.back_hall_butt_pos[3]:
                self.i_back_home = self.i_back_home + 1
            else:
                if self.i_back_home_reset >= self.ETCoord.button_fixation_tol:
                    self.i_back_home = 0
                    self.i_back_home_reset = 0
                else:
                    self.i_back_home_reset = self.i_back_home_reset + 1

            if self.i_back_home >= self.ETCoord.fixation_time[self.ETCoord.i_o]:
                print "Back to hall"
                self.ETCoord.old_state_variable = self.ETCoord.state_variable
                self.ETCoord.state_variable = 10  # Stato della zona Settings
                self.i_back_home = 0
                self.i_back_home_reset = 0

        '''Settings_joystick buttons '''
        if self.ETCoord.state_variable == 11:
            for i in range(0, 4):

                if self.ETCoord.gaze_POR[0] >= self.ETCoord.settings_joystick_butt_pos[i, 0] and \
                        self.ETCoord.gaze_POR[0] <= self.ETCoord.settings_joystick_butt_pos[i, 1] and \
                        self.ETCoord.gaze_POR[1] >= self.ETCoord.settings_joystick_butt_pos[i, 2] and \
                        self.ETCoord.gaze_POR[1] <= self.ETCoord.settings_joystick_butt_pos[i, 3]:
                    self.i_settings_joystick[i] = self.i_settings_joystick[i] + 1
                else:
                    if self.i_settings_joystick_reset[i] >= self.ETCoord.button_fixation_tol:
                        self.i_settings_joystick[i] = 0
                        self.i_settings_joystick_reset[i] = 0
                    else:
                        self.i_settings_joystick_reset[i] = self.i_settings_joystick_reset[i] + 1

                if self.i_settings_joystick[i] >= self.ETCoord.fixation_time[self.ETCoord.i_o]:
                    self.ETCoord.old_state_variable = self.ETCoord.state_variable
                    self.ETCoord.state_variable = 20 + i
                    self.i_settings_joystick = numpy.array([0, 0, 0, 0, 0, 0])
                    self.i_settings_joystick_reset = numpy.array([0, 0, 0, 0, 0, 0])

                    if self.ETCoord.state_variable == 20:  # freccia in giu
                        if self.ETCoord.i_a == 0:
                            self.ETCoord.i_a = 2
                        else:
                            self.ETCoord.i_a = self.ETCoord.i_a - 1

                        self.ETCoord.state_variable = self.ETCoord.old_state_variable

                    elif self.ETCoord.state_variable == 21:  # freccia in su
                        if self.ETCoord.i_a == 2:
                            self.ETCoord.i_a = 0
                        else:
                            self.ETCoord.i_a = self.ETCoord.i_a + 1
                        self.ETCoord.state_variable = self.ETCoord.old_state_variable

                    elif self.ETCoord.state_variable == 22:  # freccia a sinistra
                        if self.ETCoord.i_a == 0:
                            if self.ETCoord.i_b == 0:
                                self.ETCoord.i_b = 6
                            else:
                                self.ETCoord.i_b = self.ETCoord.i_b - 1

                        if self.ETCoord.i_a == 1:
                            if self.ETCoord.i_o == 0:
                                self.ETCoord.i_o = 6
                            else:
                                self.ETCoord.i_o = self.ETCoord.i_o - 1

                        if self.ETCoord.i_a == 2:
                            if self.ETCoord.i_r == 0:
                                self.ETCoord.i_r = 6
                            else:
                                self.ETCoord.i_r = self.ETCoord.i_r - 1

                        self.ETCoord.state_variable = self.ETCoord.old_state_variable

                    elif self.ETCoord.state_variable == 23:  # freccia a destra
                        if self.ETCoord.i_a == 0:
                            if self.ETCoord.i_b == 6:
                                self.ETCoord.i_b = 0
                            else:
                                self.ETCoord.i_b = self.ETCoord.i_b + 1

                        if self.ETCoord.i_a == 1:
                            if self.ETCoord.i_o == 6:
                                self.ETCoord.i_o = 0
                            else:
                                self.ETCoord.i_o = self.ETCoord.i_o + 1

                        if self.ETCoord.i_a == 2:
                            if self.ETCoord.i_r == 6:
                                self.ETCoord.i_r = 0
                            else:
                                self.ETCoord.i_r = self.ETCoord.i_r + 1

                        self.ETCoord.state_variable = self.ETCoord.old_state_variable

        ''' Back to Hall /Pre control '''
        if self.ETCoord.state_variable == 0 or self.ETCoord.state_variable == 1:

            if self.ETCoord.gaze_POR[0] >= self.ETCoord.emergency_butt_pos[0] and self.ETCoord.gaze_POR[1] >= \
                    self.ETCoord.emergency_butt_pos[2] and self.ETCoord.gaze_POR[0] < self.ETCoord.emergency_butt_pos[1] and \
                    self.ETCoord.gaze_POR[1] < self.ETCoord.emergency_butt_pos[3]:
                self.i_exit = self.i_exit + 1
            else:
                if self.i_exit_reset >= self.ETCoord.button_fixation_tol:
                    self.i_exit = 0
                    self.i_exit_reset = 0
                else:
                    self.i_exit_reset = self.i_exit_reset + 1

            if self.i_exit >= self.ETCoord.fixation_time[self.ETCoord.i_o]:
                if self.ETCoord.state_variable == 0:
                    print "BACK TO HALL"
                    self.i_exit = 0
                    self.i_exit_reset = 0
                    self.ETCoord.old_state_variable = self.ETCoord.state_variable
                    self.ETCoord.state_variable = 10
                elif self.ETCoord.state_variable == 1:
                    print "BACK TO PRE-CONTROL"
                    self.ETCoord.old_state_variable = self.ETCoord.state_variable
                    self.ETCoord.state_variable = 0
                    self.i_exit = 0
                    self.i_exit_reset = 0

        '''SAVE POSITION'''
        ##DEFINIRE POSIZIONI E VARIABILI
        if self.ETCoord.state_variable == 0 or self.ETCoord.state_variable == 1:

            if self.ETCoord.gaze_POR[0] >= self.ETCoord.save_butt_pos[0] and self.ETCoord.gaze_POR[1] >= \
                    self.ETCoord.save_butt_pos[2] and self.ETCoord.gaze_POR[0] <= self.ETCoord.save_butt_pos[1] and \
                    self.ETCoord.gaze_POR[1] <= self.ETCoord.save_butt_pos[3]:
                self.i_save = self.i_save + 1
            else:
                if self.i_save_reset >= self.ETCoord.button_fixation_tol:
                    self.i_save = 0
                    self.i_save_reset = 0
                else:
                    self.i_save_reset = self.i_save_reset + 1

            if self.i_save >= self.ETCoord.fixation_time[self.ETCoord.i_o]:
                print "Area Salvataggio"

                self.ETCoord.old_state_variable = self.ETCoord.state_variable
                self.ETCoord.state_variable = 12
                self.i_save = 0
                self.i_save_reset = 0

        '''Zona Salvataggio'''
        if self.ETCoord.state_variable == 12:
            if self.ETCoord.gaze_POR[0] >= self.ETCoord.saving_zone_exit_butt[0] and self.ETCoord.gaze_POR[1] >= \
                    self.ETCoord.saving_zone_exit_butt[2] and self.ETCoord.gaze_POR[0] <= self.ETCoord.saving_zone_exit_butt[
                1] and \
                    self.ETCoord.gaze_POR[1] <= self.ETCoord.saving_zone_exit_butt[3]:
                self.i_back_control = self.i_back_control + 1
            else:
                if self.i_back_control_reset >= self.ETCoord.button_fixation_tol:
                    self.i_back_control = 0
                    self.i_back_control_reset = 0
                else:
                    self.i_back_control_reset = self.i_back_control_reset + 1

            if self.i_back_control >= self.ETCoord.fixation_time[self.ETCoord.i_o]:
                print "Ritorno al PreControllo/Controllo"
                self.ETCoord.state_variable = self.ETCoord.old_state_variable
                self.i_back_control = 0
                self.i_back_control_reset = 0


        '''RECALL POSITION'''
        ##DEFINIRE POSIZIONI
        if self.ETCoord.state_variable == 0 or self.ETCoord.state_variable == 1:
            if self.ETCoord.gaze_POR[0] >= self.ETCoord.recall_butt_pos[0] and self.ETCoord.gaze_POR[1] >= \
                    self.ETCoord.recall_butt_pos[2] and self.ETCoord.gaze_POR[0] <= self.ETCoord.recall_butt_pos[1] and \
                    self.ETCoord.gaze_POR[1] <= self.ETCoord.recall_butt_pos[3]:
                self.i_recall = self.i_recall + 1
            else:
                if self.i_recall_reset >= self.ETCoord.button_fixation_tol:
                    self.i_recall = 0
                    self.i_recall_reset = 0
                else:
                    self.i_recall_reset = self.i_recall_reset + 1

            if self.i_recall >= self.ETCoord.fixation_time[self.ETCoord.i_o]:

                print "Zona Richiama Posizione"
                self.ETCoord.old_state_variable = self.ETCoord.state_variable
                self.ETCoord.state_variable = 13

                self.i_recall = 0
                self.i_recall_reset = 0

        '''Zona Richiama Posizione'''
        if self.ETCoord.state_variable == 13:
            for i in range(0, 2):
                if self.ETCoord.gaze_POR[0] >= self.ETCoord.recall_zone_butt[i][0] and self.ETCoord.gaze_POR[1] >= \
                        self.ETCoord.recall_zone_butt[i][2] and self.ETCoord.gaze_POR[0] <= self.ETCoord.recall_zone_butt[i][1] and \
                        self.ETCoord.gaze_POR[1] <= self.ETCoord.recall_zone_butt[i][3]:
                    self.i_recall_butt[i] = self.i_recall_butt[i] + 1
                else:
                    if self.i_recall_butt_reset[i] >= self.ETCoord.button_fixation_tol:
                        self.i_recall_butt[i] = 0
                        self.i_recall_butt_reset[i] = 0
                    else:
                        self.i_recall_butt_reset[i] = self.i_recall_butt_reset[i] + 1

                if self.i_recall_butt[i] >= self.ETCoord.fixation_time[self.ETCoord.i_o]:

                    if i == 0: #Bottone Uscita
                        self.ETCoord.state_variable = self.ETCoord.old_state_variable
                        print "Ritorno al Precontrollo/Controllo"
                        self.i_recall_butt[i] = 0
                        self.i_recall_butt_reset[i] = 0
                    else:
                        print "Attivazione Richiama Posizione"
                        self.ETCoord.state_variable = 14
                        self.i_recall_butt[i] = 0
                        self.i_recall_butt_reset[i] = 0

        '''Attivazione Richiama Posizione'''

        if self.ETCoord.state_variable == 14:
            if self.ETCoord.gaze_POR[0] >= self.ETCoord.saving_zone_exit_butt[0] and self.ETCoord.gaze_POR[1] >= \
                    self.ETCoord.saving_zone_exit_butt[2] and self.ETCoord.gaze_POR[0] <= self.ETCoord.saving_zone_exit_butt[
                1] and \
                    self.ETCoord.gaze_POR[1] <= self.ETCoord.saving_zone_exit_butt[3]:
                self.i_back_control = self.i_back_control + 1
            else:
                if self.i_back_control_reset >= self.ETCoord.button_fixation_tol:
                    self.i_back_control = 0
                    self.i_back_control_reset = 0
                else:
                    self.i_back_control_reset = self.i_back_control_reset + 1

            if self.i_back_control >= self.ETCoord.fixation_time[self.ETCoord.i_o]:
                print "Ritorno alla Zona Richiama Posizione"
                self.ETCoord.state_variable = self.ETCoord.state_variable - 1
                self.i_back_control = 0
                self.i_back_control_reset = 0



        ''' STAND-BY, i.e the controller is on, but no fixation is detected but for the emergency exit '''
        # state_variable = 0
        # check if the user is looking at the start button
        if self.ETCoord.state_variable == 0:
            if self.ETCoord.gaze_POR[0] >= self.ETCoord.standby_butt_pos[0] and self.ETCoord.gaze_POR[1] >= \
                    self.ETCoord.standby_butt_pos[2] and self.ETCoord.gaze_POR[0] < self.ETCoord.standby_butt_pos[1] and \
                    self.ETCoord.gaze_POR[1] < self.ETCoord.standby_butt_pos[3]:
                self.i_ok = self.i_ok + 1
            else:
                if self.i_ok_reset >= self.ETCoord.button_fixation_tol:
                    self.i_ok = 0
                    self.i_ok_reset = 0
                else:
                    self.i_ok_reset = self.i_ok_reset + 1

            if self.i_ok >= self.ETCoord.fixation_time[self.ETCoord.i_o]:
                self.ETCoord.old_state_variable = self.ETCoord.state_variable
                self.ETCoord.state_variable = 1
                self.i_ok = 0
                self.i_ok_reset = 0
                # save figure to file
                # scipy.misc.imsave(str(self.name_file_calib)+'.jpg',self.ETCoord.img)
                # self.name_file_calib = self.name_file_calib+1

        ''' LOOKING FOR FIXATIONS, i.e. the algorithm chacks whether the user is looking at a.webcam, b.virtual joystick '''
        if self.ETCoord.state_variable == 1 and self.delay_start <= 180:  # se ho iniziato ad acquisire per cercare fixation
            self.delay_start = self.delay_start + 1

        if self.ETCoord.state_variable == 1 and self.delay_start >= 180 :

            ''' b. check joystick buttons '''
            for i in range(0, 8):

                if self.ETCoord.gaze_POR[0] >= self.ETCoord.joystick_butt_pos[i, 0] and \
                        self.ETCoord.gaze_POR[0] <= self.ETCoord.joystick_butt_pos[i, 1] and \
                        self.ETCoord.gaze_POR[1] >= self.ETCoord.joystick_butt_pos[i, 2] and \
                        self.ETCoord.gaze_POR[1] <= self.ETCoord.joystick_butt_pos[i, 3]:
                    self.i_joystick[i] = self.i_joystick[i] + 1
                else:
                    if self.i_joystick_reset[i] >= self.ETCoord.button_fixation_tol:
                        self.i_joystick[i] = 0
                        self.i_joystick_reset[i] = 0
                    else:
                        self.i_joystick_reset[i] = self.i_joystick_reset[i] + 1

                if self.i_joystick[i] >= self.ETCoord.fixation_time[self.ETCoord.i_o]:

                    if self.i_old != i:
                        self.i_old = i
                        if i < 6:
                            print "hai attivato il bottone " + str(i)
                        elif i == 6:
                            print "Bottone Supinazione Attivato"
                        else:
                            print "Bottone Pronazione Attivato"
                        self.ETCoord.old_state_variable = self.ETCoord.state_variable
                    self.ETCoord.state_variable = 3

        '''
        1. smooth feedback visivo
        etc.
        '''
        # scrivo dati nel file per check
        # text_03.write("\n{0}".format(self.ETCoord.gaze_POR))

        try:
            glib_idle_add(self.trackstatus.handle_gazedata, error, self.ETCoord.gazedata_copy)
        except Exception, ex:
            print "  Exception occured: %s" % (ex)


    def terminate(self):
        self.running = False




class TrackStatus(gtk.DrawingArea):
    MAX_AGE = 30.0

    def __init__(self, ETCoord):
        gtk.DrawingArea.__init__(self)
        self.eyetracker = None
        self.set_size_request(300, 300)
        self.connect("expose_event", self.on_expose)

        self.gazedata = None
        self.gaze_data_history = []

        self.ETCoord = ETCoord

    def handle_gazedata(self, error, gazedata):
        self.gazedata = gazedata
        self.gaze_data_history.append(self.gazedata)
        if len(self.gaze_data_history) > TrackStatus.MAX_AGE:
            self.gaze_data_history.pop(0)
        self.redraw()

    def redraw(self):
        if self.window:
            alloc = self.get_allocation()
            rect = gtk.gdk.Rectangle(0, 0, alloc.width, alloc.height)
            self.window.invalidate_rect(rect, True)
            self.window.process_updates(True)

    def draw_eye(self, ctx, validity, camera_pos, screen_pos, age):
        screen_pos_x = screen_pos.x - .5
        screen_pos_y = screen_pos.y - .5

        eye_radius = 0.075
        iris_radius = 0.03
        pupil_radius = 0.01

        opacity = 1 - age * 1.0 / TrackStatus.MAX_AGE
        if validity <= 1:
            ctx.set_source_rgba(1, 1, 1, opacity)
            ctx.arc(1 - camera_pos.x, camera_pos.y, eye_radius, 0, 2 * math.pi)
            ctx.fill()

            ctx.set_source_rgba(.5, .5, 1, opacity)
            ctx.arc(1 - camera_pos.x + ((eye_radius - iris_radius / 2) * screen_pos_x),
                    camera_pos.y + ((eye_radius - iris_radius / 2) * screen_pos_y), iris_radius, 0, 2 * math.pi)
            ctx.fill()

            ctx.set_source_rgba(0, 0, 0, opacity)
            ctx.arc(1 - camera_pos.x + ((eye_radius - iris_radius / 2) * screen_pos_x),
                    camera_pos.y + ((eye_radius - iris_radius / 2) * screen_pos_y), pupil_radius, 0, 2 * math.pi)
            ctx.fill()

    def draw(self, ctx):
        ctx.set_source_rgb(0., 0., 0.)
        ctx.rectangle(0, 0, 1, .9)
        ctx.fill()

        # paint left rectangle
        if self.gazedata is not None and self.gazedata['left']['validity'] == 0:
            ctx.set_source_rgb(0, 1, 0)
        else:
            ctx.set_source_rgb(1, 0, 0)
        ctx.rectangle(0, .9, .5, 1)
        ctx.fill()

        # paint right rectangle
        if self.gazedata is not None and self.gazedata['right']['validity'] == 0:
            ctx.set_source_rgb(0, 1, 0)
        else:
            ctx.set_source_rgb(1, 0, 0)
        ctx.rectangle(.5, .9, 1, 1)
        ctx.fill()

        if self.gazedata is None:
            return

        # paint eyes
        for eye in ('left', 'right'):
            (validity, age, camera_pos, screen_pos) = self.find_gaze(eye)

            self.draw_eye(ctx, validity, camera_pos, screen_pos, age)

    def find_gaze(self, eye):
        i = 0
        for gaze in reversed(self.gaze_data_history):
            if gaze[eye]['validity'] <= 1:
                return (gaze[eye]['validity'], i, gaze[eye]['camera_pos'], gaze[eye]['screen_pos'])
            i += 1
        return (gaze[eye]['validity'], 0, gaze[eye]['camera_pos'], gaze[eye]['screen_pos'])

    def on_expose(self, widget, event):
        context = widget.window.cairo_create()
        context.rectangle(event.area.x, event.area.y, event.area.width, event.area.height)
        context.clip()

        rect = widget.get_allocation()
        context.scale(rect.width, rect.height)

        self.draw(context)
        return False


class CalibPlot(gtk.DrawingArea):
    def __init__(self, eyetracker):
        gtk.DrawingArea.__init__(self)

        self.set_size_request(300, 300)
        self.connect("expose_event", self.on_expose)

        self.calib = None
        self.eyetracker = eyetracker

    def set_eyetracker(self, eyetracker):
        if eyetracker is None:
            return

        try:
            self.calib = eyetracker.GetCalibration(
                lambda error, calib: glib_idle_add(self.on_calib_response, error, calib))
        except Exception, ex:
            print "  Exception occured: %s" % (ex)
            self.calib = None
        self.redraw()

    def on_calib_response(self, error, calib):
        if error:
            print "on_calib_response: Error"
            self.calib = None
            self.redraw()
            return False

        self.calib = calib
        self.redraw()
        return False

    def redraw(self):
        if self.window:
            alloc = self.get_allocation()
            rect = gtk.gdk.Rectangle(0, 0, alloc.width, alloc.height)
            self.window.invalidate_rect(rect, True)
            self.window.process_updates(True)

    def on_expose(self, widget, event):
        context = widget.window.cairo_create()
        context.rectangle(event.area.x, event.area.y, event.area.width, event.area.height)
        context.clip()

        rect = widget.get_allocation()
        context.scale(rect.width, rect.height)

        self.draw(context)

    def draw(self, ctx):
        ctx.rectangle(0, 0, 1, 1)
        ctx.set_source_rgb(1, 1, 1)
        ctx.fill()

        if self.calib is None:
            ctx.move_to(0, 0)
            ctx.line_to(1, 1)
            ctx.move_to(0, 1)
            ctx.line_to(1, 0)
            ctx.set_source_rgb(0, 0, 0)
            ctx.set_line_width(0.001)
            ctx.stroke()
            return

        points = {}
        for data in self.calib.plot_data:
            points[data.true_point] = {'left': data.left, 'right': data.right}

        if len(points) == 0:
            ctx.move_to(0, 0)
            ctx.line_to(1, 1)
            ctx.move_to(0, 1)
            ctx.line_to(1, 0)
            ctx.set_source_rgb(0, 0, 0)
            ctx.set_line_width(0.001)
            ctx.stroke()
            return

        for p, d in points.iteritems():
            ctx.set_line_width(0.001)
            if d['left'].status == 1:
                ctx.set_source_rgb(1.0, 0., 0.)
                ctx.move_to(p.x, p.y)
                ctx.line_to(d['left'].map_point.x, d['left'].map_point.y)
                ctx.stroke()

            if d['right'].status == 1:
                ctx.set_source_rgb(0., 1.0, 0.)
                ctx.move_to(p.x, p.y)
                ctx.line_to(d['right'].map_point.x, d['right'].map_point.y)
                ctx.stroke()

            ctx.set_line_width(0.005)
            ctx.set_source_rgba(0., 0., 0., 0.05)
            ctx.arc(p.x, p.y, 0.01, 0, 2 * math.pi)
            ctx.stroke()

class Calibration:
    def __init__(self):

        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.canvas = gtk.DrawingArea()
        self.window.add(self.canvas)
        self.canvas.connect("expose_event", self.on_expose)
        self.points = [(0.1, 0.1), (0.5, 0.1), (0.9, 0.1), (0.1, 0.5), (0.5, 0.5), (0.9, 0.5), (0.1, 0.9), (0.5, 0.9),
                       (0.9, 0.9)]
        self.point_index = -1
        self.on_calib_done = None

    def run(self, tracker, on_calib_done):
        self.window.fullscreen()
        self.window.show_all()
        self.on_calib_done = on_calib_done
        self.tracker = tracker
        self.point_index = -1
        self.tracker.StartCalibration(lambda error, r: glib_idle_add(self.on_calib_start, error, r))

    def on_calib_start(self, error, r):
        if error:
            self.on_calib_done(False, "Could not start calibration because of error. (0x%0x)" % error)
            return False

        self.wait_for_add()
        return False

    def on_expose(self, widget, event):
        context = widget.window.cairo_create()
        context.rectangle(event.area.x, event.area.y, event.area.width, event.area.height)
        context.clip()

        self.draw(context)
        return False

    def draw(self, ctx):
        if self.point_index >= -1:
            x, y = self.points[self.point_index]

            bounds = self.canvas.get_allocation()

            # Draw calibration dot
            ctx.set_source_rgb(255, 0, 0)
            radius = 0.012 * bounds.width
            ctx.arc(bounds.width * x, bounds.height * y, radius, 0, 2 * math.pi)
            ctx.fill()

            # Draw center dot
            ctx.set_source_rgb(0, 0, 0);
            radius = 2;
            ctx.arc(bounds.width * x, bounds.height * y, radius, 0, 2 * math.pi)
            ctx.fill()

    def wait_for_add(self):
        self.point_index += 1
        self.redraw()
        glib_timeout_add(1500, self.add_point)

    def add_point(self):
        p = Point2D()
        p.x, p.y = self.points[self.point_index]
        self.tracker.AddCalibrationPoint(p, lambda error, r: glib_idle_add(self.on_add_completed, error, r))
        return False

    def on_add_completed(self, error, r):
        if error:
            self.on_calib_done(False, "Add Calibration Point failed because of error. (0x%0x)" % error)
            return False

        if self.point_index == len(self.points) - 1:
            # This was the last calibration point
            self.tracker.ComputeCalibration(lambda error, r: glib_idle_add(self.on_calib_compute, error, r))
        else:
            self.wait_for_add()

        return False

    def on_calib_compute(self, error, r):
        if error == 0x20000502:
            print "CalibCompute failed because not enough data was collected"
            self.on_calib_done(False, "Not enough data was collected during calibration procedure.")
        elif error != 0:
            print "CalibCompute failed because of a server error"
            self.on_calib_done(False,
                               "Could not compute calibration because of a server error.\n\n<b>Details:</b>\n<i>%s</i>" % (
                               error))
        else:
            self.on_calib_done(True, "")



        self.tracker.StopCalibration(None)
        self.window.destroy()
        return False

    def redraw(self):
        if self.canvas.window:
            alloc = self.canvas.get_allocation()
            rect = gtk.gdk.Rectangle(0, 0, alloc.width, alloc.height)
            self.canvas.window.invalidate_rect(rect, True)
        else:
            print "else"


class Control:

    def __init__(self, ETCoord, Coord):
        self.running = False
        self.ETCoord = ETCoord
        self.Coord = Coord
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.canvas = gtk.DrawingArea()

        self.canvas.set_size_request(self.ETCoord.screen_w, self.ETCoord.screen_h)
        self.window.add(self.canvas)
        self.canvas.connect("expose_event", self.on_expose)

        # load background images
        # self.pixbuf_bk = gtk.gdk.pixbuf_new_from_file('UI-Official DEFINITIVA.png')
        # set algorithm parameters
        # self.ETCoord.gazedata_array  = numpy.zeros((2,self.ETCoord.fixation_time))
        # connect to webcam
        self.cam = cv2.VideoCapture(1)
        self.delay = 0
        self.i_arc=0

    def run(self, tracker):

        self.running = True

        self.window.fullscreen()
        self.window.show_all()
        self.tracker = tracker

        # set state_variable = 0 -> stand-by
        self.ETCoord.state_variable = 10

        while self.running:
            self.redraw()
            time.sleep(0.1)

    def on_expose(self, widget, event):

        context = widget.window.cairo_create()
        context.rectangle(event.area.x, event.area.y, event.area.width, event.area.height)
        # context.rectangle(0, 0, self.ETCoord.screen_w, self.ETCoord.screen_h)
        context.clip()

        self.draw(context)
        return False

    def draw(self, ctx):

        bounds = self.canvas.get_allocation()
        ctx.save()


        if self.ETCoord.state_variable == 0 or self.ETCoord.state_variable == 2 and self.ETCoord.old_state_variable == 0:

            self.ETCoord.img = None
            self.ret_val, self.ETCoord.img = self.cam.read()

            if self.ret_val == True:
                self.ETCoord.img = cv2.flip(self.ETCoord.img, 1)
                self.ETCoord.img = cv2.resize(self.ETCoord.img, (self.ETCoord.webcam_size, self.ETCoord.webcam_size), interpolation=cv2.INTER_AREA)
                self.ETCoord.img = cv2.cvtColor(self.ETCoord.img,cv2.COLOR_BGR2RGB)
                self.pixbuf = None
                self.pixbuf = gtk.gdk.pixbuf_new_from_data(self.ETCoord.img, gtk.gdk.COLORSPACE_RGB, False, 8, self.ETCoord.img.shape[0], self.ETCoord.img.shape[1], self.ETCoord.img.shape[0] * 3)
                ctx.set_source_pixbuf(self.pixbuf, self.ETCoord.webcam_pos[0], self.ETCoord.webcam_pos[1])
                ctx.paint()
                #ctx.restore()
                #ctx.save()
                self.pixbuf_bk = gtk.gdk.pixbuf_new_from_file('1-Background.png')
                ctx.set_source_pixbuf(self.pixbuf_bk, 0, 0)
                ctx.paint()
                #ctx.restore()
                self.pixbuf_bk = gtk.gdk.pixbuf_new_from_file('0-Su.png')
                ctx.set_source_pixbuf(self.pixbuf_bk, self.ETCoord.joystick_butt_pos[0][0] * 1280.0, self.ETCoord.joystick_butt_pos[0][2] * 1024.0)
                ctx.paint()
                self.pixbuf_bk = gtk.gdk.pixbuf_new_from_file('0-giu.png')
                ctx.set_source_pixbuf(self.pixbuf_bk, self.ETCoord.joystick_butt_pos[1][0] * 1280.0, self.ETCoord.joystick_butt_pos[1][2] * 1024.0)
                ctx.paint()
                self.pixbuf_bk = gtk.gdk.pixbuf_new_from_file('0-Destra.png')
                ctx.set_source_pixbuf(self.pixbuf_bk, self.ETCoord.joystick_butt_pos[2][0] * 1280.0, self.ETCoord.joystick_butt_pos[2][2] * 1024.0)
                ctx.paint()
                self.pixbuf_bk = gtk.gdk.pixbuf_new_from_file('0-Sinistra.png')
                ctx.set_source_pixbuf(self.pixbuf_bk, self.ETCoord.joystick_butt_pos[3][0] * 1280.0, self.ETCoord.joystick_butt_pos[3][2] * 1024.0)
                ctx.paint()
                self.pixbuf_bk = gtk.gdk.pixbuf_new_from_file('0-Doppio su.png')
                ctx.set_source_pixbuf(self.pixbuf_bk, self.ETCoord.joystick_butt_pos[4][0] * 1280.0, self.ETCoord.joystick_butt_pos[4][2] * 1024.0)
                ctx.paint()
                self.pixbuf_bk = gtk.gdk.pixbuf_new_from_file('0-Doppio giu.png')
                ctx.set_source_pixbuf(self.pixbuf_bk, self.ETCoord.joystick_butt_pos[5][0] * 1280.0, self.ETCoord.joystick_butt_pos[5][2] * 1024.0)
                ctx.paint()
                self.pixbuf_bk = gtk.gdk.pixbuf_new_from_file('0-Supinazione.png')
                ctx.set_source_pixbuf(self.pixbuf_bk, self.ETCoord.joystick_butt_pos[6][0] * 1280.0, self.ETCoord.joystick_butt_pos[6][2] * 1024.0)
                ctx.paint()
                self.pixbuf_bk = gtk.gdk.pixbuf_new_from_file('0-Pronazione.png')
                ctx.set_source_pixbuf(self.pixbuf_bk, self.ETCoord.joystick_butt_pos[7][0] * 1280.0, self.ETCoord.joystick_butt_pos[7][2] * 1024.0)
                ctx.paint()
                self.pixbuf_bk = gtk.gdk.pixbuf_new_from_file('1-Off.png')
                ctx.set_source_pixbuf(self.pixbuf_bk, self.ETCoord.emergency_butt_pos[0] * 1280.0, self.ETCoord.emergency_butt_pos[2] * 1024.0)
                ctx.paint()
                self.pixbuf_bk = gtk.gdk.pixbuf_new_from_file('1-Start Control.png')
                ctx.set_source_pixbuf(self.pixbuf_bk, self.ETCoord.standby_butt_pos[0] * 1280.0, self.ETCoord.standby_butt_pos[2] * 1024.0)
                ctx.paint()
                self.pixbuf_bk = gtk.gdk.pixbuf_new_from_file('1-Save.png')
                ctx.set_source_pixbuf(self.pixbuf_bk, self.ETCoord.save_butt_pos[0] * 1280.0, self.ETCoord.save_butt_pos[2] * 1024.0)
                ctx.paint()
                self.pixbuf_bk = gtk.gdk.pixbuf_new_from_file('1-Recall.png')
                ctx.set_source_pixbuf(self.pixbuf_bk, self.ETCoord.recall_butt_pos[0] * 1280.0, self.ETCoord.recall_butt_pos[2] * 1024.0)
                ctx.paint()



        elif self.ETCoord.state_variable == 1 or self.ETCoord.state_variable == 2 and self.ETCoord.old_state_variable == 1 or self.ETCoord.state_variable == 3:

            self.ETCoord.img = None
            self.ret_val, self.ETCoord.img = self.cam.read()

            if self.ret_val == True:
                self.ETCoord.img = cv2.flip(self.ETCoord.img, 1)
                self.ETCoord.img = cv2.resize(self.ETCoord.img, (self.ETCoord.webcam_size, self.ETCoord.webcam_size), interpolation=cv2.INTER_AREA)
                self.ETCoord.img = cv2.cvtColor(self.ETCoord.img,cv2.COLOR_BGR2RGB)
                self.pixbuf = None
                self.pixbuf = gtk.gdk.pixbuf_new_from_data(self.ETCoord.img, gtk.gdk.COLORSPACE_RGB, False, 8, self.ETCoord.img.shape[0], self.ETCoord.img.shape[1], self.ETCoord.img.shape[0] * 3)
                ctx.set_source_pixbuf(self.pixbuf, self.ETCoord.webcam_pos[0], self.ETCoord.webcam_pos[1])
                ctx.paint()
                #ctx.restore()
                #ctx.save()
                self.pixbuf_bk = gtk.gdk.pixbuf_new_from_file('1-Background.png')
                ctx.set_source_pixbuf(self.pixbuf_bk, 0, 0)
                ctx.paint()
                #ctx.restore()
                self.pixbuf_bk = gtk.gdk.pixbuf_new_from_file('1-Su.png')
                ctx.set_source_pixbuf(self.pixbuf_bk, self.ETCoord.joystick_butt_pos[0][0] * 1280.0, self.ETCoord.joystick_butt_pos[0][2] * 1024.0)
                ctx.paint()
                self.pixbuf_bk = gtk.gdk.pixbuf_new_from_file('1-giu.png')
                ctx.set_source_pixbuf(self.pixbuf_bk, self.ETCoord.joystick_butt_pos[1][0] * 1280.0, self.ETCoord.joystick_butt_pos[1][2] * 1024.0)
                ctx.paint()
                self.pixbuf_bk = gtk.gdk.pixbuf_new_from_file('1-Destra.png')
                ctx.set_source_pixbuf(self.pixbuf_bk, self.ETCoord.joystick_butt_pos[2][0] * 1280.0, self.ETCoord.joystick_butt_pos[2][2] * 1024.0)
                ctx.paint()
                self.pixbuf_bk = gtk.gdk.pixbuf_new_from_file('1-Sinistra.png')
                ctx.set_source_pixbuf(self.pixbuf_bk, self.ETCoord.joystick_butt_pos[3][0] * 1280.0, self.ETCoord.joystick_butt_pos[3][2] * 1024.0)
                ctx.paint()
                self.pixbuf_bk = gtk.gdk.pixbuf_new_from_file('1-Doppio su.png')
                ctx.set_source_pixbuf(self.pixbuf_bk, self.ETCoord.joystick_butt_pos[4][0] * 1280.0, self.ETCoord.joystick_butt_pos[4][2] * 1024.0)
                ctx.paint()
                self.pixbuf_bk = gtk.gdk.pixbuf_new_from_file('1-Doppio giu.png')
                ctx.set_source_pixbuf(self.pixbuf_bk, self.ETCoord.joystick_butt_pos[5][0] * 1280.0, self.ETCoord.joystick_butt_pos[5][2] * 1024.0)
                ctx.paint()
                self.pixbuf_bk = gtk.gdk.pixbuf_new_from_file('1-Supinazione.png')
                ctx.set_source_pixbuf(self.pixbuf_bk, self.ETCoord.joystick_butt_pos[6][0] * 1280.0, self.ETCoord.joystick_butt_pos[6][2] * 1024.0)
                ctx.paint()
                self.pixbuf_bk = gtk.gdk.pixbuf_new_from_file('1-Pronazione.png')
                ctx.set_source_pixbuf(self.pixbuf_bk, self.ETCoord.joystick_butt_pos[7][0] * 1280.0, self.ETCoord.joystick_butt_pos[7][2] * 1024.0)
                ctx.paint()
                self.pixbuf_bk = gtk.gdk.pixbuf_new_from_file('1-Off.png')
                ctx.set_source_pixbuf(self.pixbuf_bk, self.ETCoord.emergency_butt_pos[0] * 1280.0, self.ETCoord.emergency_butt_pos[2] * 1024.0)
                ctx.paint()
                self.pixbuf_bk = gtk.gdk.pixbuf_new_from_file('1-Start Control.png')
                ctx.set_source_pixbuf(self.pixbuf_bk, self.ETCoord.standby_butt_pos[0] * 1280.0, self.ETCoord.standby_butt_pos[2] * 1024.0)
                ctx.paint()
                self.pixbuf_bk = gtk.gdk.pixbuf_new_from_file('1-Save.png')
                ctx.set_source_pixbuf(self.pixbuf_bk, self.ETCoord.save_butt_pos[0] * 1280.0, self.ETCoord.save_butt_pos[2] * 1024.0)
                ctx.paint()
                self.pixbuf_bk = gtk.gdk.pixbuf_new_from_file('1-Recall.png')
                ctx.set_source_pixbuf(self.pixbuf_bk, self.ETCoord.recall_butt_pos[0] * 1280.0, self.ETCoord.recall_butt_pos[2] * 1024.0)
                ctx.paint()



        elif self.ETCoord.state_variable == 10:

            self.pixbuf_bk = gtk.gdk.pixbuf_new_from_file('10-Background Hall.png')
            ctx.set_source_pixbuf(self.pixbuf_bk, 0, 0)
            ctx.paint()
            #ctx.restore()
            self.pixbuf_bk = gtk.gdk.pixbuf_new_from_file('10-Bottone Controllo.png')
            ctx.set_source_pixbuf(self.pixbuf_bk, self.ETCoord.precontrol_butt_pos[0] * 1280.0, self.ETCoord.precontrol_butt_pos[2] * 1024.0)
            ctx.paint()
            self.pixbuf_bk = gtk.gdk.pixbuf_new_from_file('10-Bottone Settings.png')
            ctx.set_source_pixbuf(self.pixbuf_bk, self.ETCoord.settings_butt_pos[0] * 1280.0,
                                  self.ETCoord.settings_butt_pos[2] * 1024.0)
            ctx.paint()
            self.pixbuf_bk = gtk.gdk.pixbuf_new_from_file('10-Bottone Spegnimento.png')
            ctx.set_source_pixbuf(self.pixbuf_bk, self.ETCoord.off_tracker_butt_pos[0] * 1280.0,
                                  self.ETCoord.off_tracker_butt_pos[2] * 1024.0)
            ctx.paint()


        elif self.ETCoord.state_variable == 11:
            self.pixbuf_bk = gtk.gdk.pixbuf_new_from_file('settings_clean.png')
            ctx.set_source_pixbuf(self.pixbuf_bk, 0, 0)
            ctx.paint()
            #ctx.restore()
            ctx.save()
            ctx.set_source_pixbuf(gtk.gdk.pixbuf_new_from_file('red_ball_2.0.png'),
                                  self.ETCoord.ball_xpos[self.ETCoord.i_r], 805)
            ctx.paint()
            #ctx.restore()
            ctx.save()
            ctx.set_source_pixbuf(gtk.gdk.pixbuf_new_from_file('blue_ball_2.0.png'),
                                  self.ETCoord.ball_xpos[self.ETCoord.i_b], 419)
            ctx.paint()
            #ctx.restore()
            ctx.save()
            ctx.set_source_pixbuf(gtk.gdk.pixbuf_new_from_file('orange_ball_2.0.png'),
                                  self.ETCoord.ball_xpos[self.ETCoord.i_o], 612.5)
            ctx.paint()
            #ctx.restore()
            ctx.save()
            ctx.set_source_pixbuf(gtk.gdk.pixbuf_new_from_file('arrow.png'), 38,
                                  self.ETCoord.arrow_ypos[self.ETCoord.i_a])
            ctx.paint()
            #ctx.restore()
            ctx.save()

        elif self.ETCoord.state_variable == 12:
            self.pixbuf_bk = gtk.gdk.pixbuf_new_from_file('Savings rect NO ARROW.png')
            ctx.set_source_pixbuf(self.pixbuf_bk, 0, 0)
            ctx.paint()
            #ctx.restore()

        elif self.ETCoord.state_variable == 13:
            self.pixbuf_bk = gtk.gdk.pixbuf_new_from_file('recall position trasp.png')
            ctx.set_source_pixbuf(self.pixbuf_bk, 0, 0)
            ctx.paint()
            #ctx.restore()

        elif self.ETCoord.state_variable == 14:
            self.pixbuf_bk = gtk.gdk.pixbuf_new_from_file('recall position rect.png')
            ctx.set_source_pixbuf(self.pixbuf_bk, 0, 0)
            ctx.paint()
            #ctx.restore()

        # gaze visual feedback colors
        print self.ETCoord.state_variable
        if self.ETCoord.state_variable == 0 or self.ETCoord.state_variable == 12 or self.ETCoord.state_variable == 13:
            ctx.set_source_rgb(0, 0, 255)

        if self.ETCoord.state_variable == 1 or self.ETCoord.state_variable == 14:
            ctx.set_source_rgb(0, 255, 0)
            # controllo abilitato

        elif self.ETCoord.state_variable == 2:
            ctx.set_source_rgb(255, 255, 0)
            if self.delay < 6:
                self.delay = self.delay + 1
            else:
                self.ETCoord.state_variable = self.ETCoord.old_state_variable
                self.delay = 0

            # (RGB((int)distance % 255, 255 - ((int)distance % 255), 50))
        elif self.ETCoord.state_variable == 3:
            ctx.set_source_rgb(255, 255, 0)
            self.ETCoord.state_variable = 1
            # bottone direzionale


        elif self.ETCoord.state_variable == 4:
            ctx.set_source_rgb(255, 0, 255)

        else:
            ctx.set_source_rgb(0, 0, 255)

        if self.ETCoord.gaze_POR[0] >= 0 and self.ETCoord.gaze_POR[1] >= 0:

            ctx.arc(self.ETCoord.screen_w * self.ETCoord.gaze_POR[0],
                          self.ETCoord.screen_h * self.ETCoord.gaze_POR[1], 20, 0, 2*math.pi)
            ctx.fill()

        if self.ETCoord.exit == True:
            self.running = False
            self.terminate()


    def redraw(self):

        if self.canvas.window:
            alloc = self.canvas.get_allocation()  # NOTTE
            rect = gtk.gdk.Rectangle(0, 0, alloc.width, alloc.height)
            # rect = gtk.gdk.Rectangle(0, 0, 1024, 1280)
            self.canvas.window.invalidate_rect(rect, True)  # NOTTE
            self.canvas.window.process_updates(True)  # NOTTE

    def terminate(self):

        # scrittura dei file
        #text_save2file_POR = open("POR.txt", "w")
        #text_save2file_p0 = open("p0.txt", "w")
        #text_save2file_DemoCoord = open("DemoCoord.txt", "w")
        #text_save2file_POR.write("\n{0}".format(save2file_POR))
        #text_save2file_p0.write("\n{0}".format(save2file_p0))
        #text_save2file_DemoCoord.write("\n{0}".format(save2file_DemoCoord))
        #text_save2file_POR.close()
        #text_save2file_p0.close()
        #text_save2file_DemoCoord.close()

        self.running = False
        self.window.destroy()


def show_message_box(parent, message, title="", buttons=gtk.BUTTONS_OK):
    def close_dialog(dlg, rid):
        dlg.destroy()

    msg = gtk.MessageDialog(parent=parent, buttons=buttons)
    msg.set_markup(message)
    msg.set_modal(False)
    msg.connect("response", close_dialog)
    msg.show()


class EyetrackerBrowser:

    def __init__(self, ETCoord, Coord, Conf, trackstatus, Bridge,Threading_Protocol):

        self.ETCoord = ETCoord
        self.Coord = Coord
        self.Conf = Conf
        self.trackstatus = trackstatus
        self.Bridge = Bridge
        self.Threading_Protocol=Threading_Protocol

        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.connect("delete_event", self.delete_event)
        self.window.connect("destroy", self.destroy)
        self.window.set_border_width(5)
        self.window.set_size_request(960, 480)  # dimensioni finestra principale (larghezza, altezza)

        self.eyetracker = None
        self.eyetrackers = {}
        self.liststore = gtk.ListStore(str, str, str)

        self.treeview = gtk.TreeView(self.liststore)
        self.treeview.connect("row-activated", self.row_activated)

        self.pid_column = gtk.TreeViewColumn("PID")
        self.pid_cell = gtk.CellRendererText()
        self.treeview.append_column(self.pid_column)
        self.pid_column.pack_start(self.pid_cell, True)
        self.pid_column.set_attributes(self.pid_cell, text=0)

        self.model_column = gtk.TreeViewColumn("Model")
        self.model_cell = gtk.CellRendererText()
        self.treeview.append_column(self.model_column)
        self.model_column.pack_start(self.model_cell, True)
        self.model_column.set_attributes(self.model_cell, text=1)

        self.status_column = gtk.TreeViewColumn("Status")
        self.status_cell = gtk.CellRendererText()
        self.treeview.append_column(self.status_column)
        self.status_column.pack_start(self.status_cell, True)
        self.status_column.set_attributes(self.status_cell, text=2)

        self.trackstatus = TrackStatus(self.ETCoord)
        self.calibplot = CalibPlot(self.eyetracker)

        self.table = gtk.Table(3, 3)  # raws, columns
        self.table.set_col_spacings(4)
        self.table.set_row_spacings(4)
        # table.attach(child, left_attach, right_attach, top_attach, bottom_attach)
        # tabella ET
        self.treeview_label = gtk.Label()
        self.treeview_label.set_alignment(0.0, 0.5)
        self.treeview_label.set_markup("<b>Discovered Eyetrackers:</b>")
        self.table.attach(self.treeview_label, 0, 1, 0, 1, xoptions=gtk.FILL, yoptions=gtk.FILL)
        self.table.attach(self.treeview, 0, 1, 1, 2)
        # tabella calibration plot
        self.calibplot_label = gtk.Label()
        self.calibplot_label.set_markup("<b>Calibration Plot:</b>")
        self.calibplot_label.set_alignment(0.0, 0.5)
        self.table.attach(self.calibplot_label, 1, 2, 0, 1, xoptions=gtk.FILL, yoptions=gtk.FILL)
        self.table.attach(self.calibplot, 1, 2, 1, 2)
        # tabella track_status (feedback ET)
        self.trackstatus_label = gtk.Label()
        self.trackstatus_label.set_markup("<b>Trackstatus:</b>")
        self.trackstatus_label.set_alignment(0.0, 0.5)
        self.table.attach(self.trackstatus_label, 2, 3, 0, 1, xoptions=gtk.FILL, yoptions=gtk.FILL)
        self.table.attach(self.trackstatus, 2, 3, 1, 2)

        # bottone per run calibration
        self.buttonbar = gtk.HButtonBox()
        self.buttonbar.set_border_width(0)
        self.buttonbar.set_spacing(10)
        self.buttonbar.set_layout(gtk.BUTTONBOX_END)

        self.button = gtk.Button("Calibrazione")
        self.button.connect("clicked", self.on_calib_button_clicked)
        self.button.set_sensitive(False)

        self.buttonbar.add(self.button)

        # bottone per start control
        self.buttonbar_sc = gtk.HButtonBox()
        self.buttonbar_sc.set_border_width(0)
        self.buttonbar_sc.set_spacing(10)
        self.buttonbar_sc.set_layout(gtk.BUTTONBOX_END)

        self.button_sc = gtk.Button("Inizio Protocollo")
        self.button_sc.connect("clicked", self.on_sc_button_clicked)
        self.button_sc.set_sensitive(False)

        self.buttonbar_sc.add(self.button_sc)

        # bottone per load patient
        self.button_lp = gtk.Button("Inizio Controllo")
        self.button_lp.connect("clicked", self.on_lp_button_clicked)
        self.button_lp.set_sensitive(True)

        self.buttonbar_sc.add(self.button_lp)

        self.eyetracker_label = gtk.Label()
        self.eyetracker_label.set_markup("<b>No eyetracker selected (double-click to choose).</b>")
        self.eyetracker_label.set_alignment(0.0, 0.5)
        self.table.attach(self.eyetracker_label, 0, 2, 2, 3, xoptions=gtk.FILL, yoptions=gtk.FILL)
        self.table.attach(self.buttonbar, 1, 2, 2, 3, xoptions=gtk.FILL, yoptions=gtk.FILL)
        self.table.attach(self.buttonbar_sc, 2, 3, 2, 3, xoptions=gtk.FILL, yoptions=gtk.FILL)


        # metto la tabella sulla finestra
        self.window.add(self.table)
        self.window.show_all()

        # Setup Eyetracker stuff
        tobii.eye_tracking_io.init()
        self.mainloop_thread = tobii.eye_tracking_io.mainloop.MainloopThread()
        self.browser = tobii.eye_tracking_io.browsing.EyetrackerBrowser(self.mainloop_thread,
                                                                        lambda t, n, i: glib_idle_add(
                                                                            self.on_eyetracker_browser_event, t, n, i))


    def row_activated(self, treeview, path, user_data=None):
        # When an eyetracker is selected in the browser list we create a new
        # eyetracker object and set it as the active one
        model = treeview.get_model()
        iter = model.get_iter(path)
        self.button.set_sensitive(False)
        self.calibplot.set_eyetracker(None)

        self.eyetracker_info = self.eyetrackers[model.get_value(iter, 0)]
        print "Connecting to:", self.eyetracker_info
        tobii.eye_tracking_io.eyetracker.Eyetracker.create_async(self.mainloop_thread,
                                                                 self.eyetracker_info,
                                                                 lambda error, eyetracker: glib_idle_add(
                                                                     self.on_eyetracker_created, error, eyetracker))

    # def on_eyetracker_created(self, error, eyetracker, eyetracker_info):
    def on_eyetracker_created(self, error, eyetracker):
        if error:
            print "  Connection to %s failed because of an exception: %s" % (self.eyetracker_info, error)
            if error == 0x20000402:
                show_message_box(parent=self.window,
                                 message="The selected unit is too old, a unit which supports protocol version 1.0 is required.\n\n<b>Details:</b> <i>%s</i>" % error)
            else:
                show_message_box(parent=self.window, message="Could not connect to %s" % (self.eyetracker_info))
            return False

        self.eyetracker = eyetracker
        ''' Define ET tracking thread '''
        print 'EndEff0', self.Coord.EndEff0
        self.ControlThread = Thread_TrackingClass(self.ETCoord, self.Coord, self.trackstatus, self.eyetracker)
        self.ControlThread.start()

        try:
            # self.trackstatus.set_eyetracker(self.eyetracker)
            self.calibplot.set_eyetracker(self.eyetracker)
            self.button.set_sensitive(True)
            self.button_sc.set_sensitive(True)
            self.eyetracker_label.set_markup("<b>Connected to Eyetracker: %s</b>" % (self.eyetracker_info))
            print "   --- Connected!"
        except Exception, ex:
            print "  Exception occured: %s" % (ex)
            show_message_box(parent=self.window,
                             message="An error occured during initialization of track status or fetching of calibration plot: %s" % (
                             ex))

        # @@@@@ inizia la thread dell'ET
        # self.ControlThread.run()

        return False

    def on_eyetracker_upgraded(self, error):
        try:
            self.trackstatus.set_eyetracker(self.eyetracker)
            self.calibplot.set_eyetracker(self.eyetracker)
            self.button.set_sensitive(True)
            self.button_sc.set_sensitive(True)
            self.eyetracker_label.set_markup("<b>Connected to Eyetracker: %s</b>" % (self.eyetracker_info))
            print "   --- Connected!"
        except Exception, ex:
            print "  Exception occured: %s" % (ex)
            show_message_box(parent=self.window,
                             message="An error occured during initialization of track status or fetching of calibration plot: %s" % (
                             ex))
        return False

    def on_calib_button_clicked(self, button):
        # Start the calibration procedure
        if self.eyetracker is not None:
            self.calibration = Calibration()
            self.calibration.run(self.eyetracker,
                                 lambda status, message: glib_idle_add(self.on_calib_done, status, message))

    def on_sc_button_clicked(self, button):
        # Start the protocol procedure
        print 'Start Protocol'
        if self.eyetracker is not None:
            self.Threading_Protocol = Threading_Protocol(self.ETCoord,self.Threading_Protocol)
            self.Threading_Protocol.start()





    def on_lp_button_clicked(self, button):
        # Read the conf file and start control
        print 'Start Control'
        if self.eyetracker is not None:
            self.control = Control(self.ETCoord, self.Coord)
            self.control.run(self.eyetracker)



    def JointInitialization(self):

        ''' Joints class init '''
        for i in range(0, len(self.Bridge.J)):
            self.Bridge.J[i] = Joint(i + 1,
                                     self.Conf.serial.COM[i],
                                     self.Conf.Jmax[i],
                                     self.Conf.Jmin[i],
                                     self.Conf.Ratio[i],
                                     self.Conf.Offset[i],
                                     self.Conf.Target[i],
                                     self.Coord)
        self.Coord.Jpos = [10, -40, 30, 90, 0]
        ''' Define control threads '''
        self.ControlThread = Thread_ControlClass(self.Bridge, self.Conf, self.Coord, Debug=False)
        self.ControlThread.start()

    def close_dialog(self, dialog, response_id):
        dialog.destroy()

    def on_calib_done(self, status, msg):
        # When the calibration procedure is done we update the calibration plot
        if not status:
            show_message_box(parent=self.window, message=msg)

        self.calibplot.set_eyetracker(self.eyetracker)
        self.calibration = None
        return False

    def on_eyetracker_browser_event(self, event_type, event_name, ei):
        # When a new eyetracker is found we add it to the treeview and to the
        # internal list of eyetracker_info objects
        if event_type == tobii.eye_tracking_io.browsing.EyetrackerBrowser.FOUND:
            self.eyetrackers[ei.product_id] = ei
            self.liststore.append(('%s' % ei.product_id, ei.model, ei.status))
            return False

        # Otherwise we remove the tracker from the treeview and the eyetracker_info list...
        del self.eyetrackers[ei.product_id]
        iter = self.liststore.get_iter_first()
        while iter is not None:
            if self.liststore.get_value(iter, 0) == str(ei.product_id):
                self.liststore.remove(iter)
                break
            iter = self.liststore.iter_next(iter)

        # ...and add it again if it is an update message
        if event_type == tobii.eye_tracking_io.browsing.EyetrackerBrowser.UPDATED:
            self.eyetrackers[ei.product_id] = ei
            self.liststore.append([ei.product_id, ei.model, ei.status])
        return False

    def delete_event(self, widget, event, data=None):
        # Change FALSE to TRUE and the main window will not be destroyed
        # with a "delete_event".
        return False

    def destroy(self, widget, data=None):
        try:
            self.eyetracker.StopTracking()
        except Exception, e:
            print e
        self.eyetracker = None
        self.calibplot.set_eyetracker(None)
        # self.trackstatus.set_eyetracker(None)
        self.browser.stop()
        self.browser = None

        self.control = None

        # self.ControlThread.stop.set()

        # Get active threads  
        self.mainloop_thread.stop()

        threads_list = threading.enumerate()
        print threads_list

        # Kill all the threads except MainThread
        try:
            for i in range(0, len(threads_list)):
                th = threads_list[i]
                if th.name != "MainThread":
                    # th.terminate()
                    th.stop.set()
        except Exception, e:
            print str(e)

        threads_list = threading.enumerate()
        print threads_list

        '''
        # Wait for the threads to end
        for i in range(1,len(threads_list)):
            th = threads_list[i]
            print th
            if th.name != "MainThread":
                th.join()
        '''

        gtk.main_quit()

    def main(self):
        # All PyGTK applications must have a gtk.main(). Control ends here
        # and waits for an event to occur (like a key press or mouse event).
        gtk.gdk.threads_init()
        gtk.main()
        self.mainloop_thread.stop()


# If the program is run directly or passed as an argument to the python
# interpreter then create a HelloWorld instance and show it
if __name__ == "__main__":
    ETCoord = BridgeETCoordClass()
    Coord = BridgeCoordClass()
    Conf = BridgeConfClass()
    trackstatus = TrackStatus(ETCoord)
    Bridge = BridgeClass()
    eb = EyetrackerBrowser(ETCoord, Coord, Conf, trackstatus, Bridge,Threading_Protocol)
    eb.main()

