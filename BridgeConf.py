# -*- coding: utf-8 -*-
import ConfigParser
import math
import numpy

class BridgeCoordClass:
    def __init__(self):
        self.p0                         = [0]*4
        self.p0_check                   = [0]*4
        self.EndEff0                    = numpy.array([0.0, 0.0, 0.0, 0.0])
        self.Elbow                      = numpy.array([0.0, 0.0, 0.0])
        self.joint_update               = False
        self.Jupdate                    = [False, False, False, False, False]
        self.SavePos                    = [False, False, False, False, False]
        self.GoToSavedPos               = [False, False, False, False, False]
        self.GoToSavedPosMainTrigger    = False
        self.SavePosMainTrigger         = False
        self.FirstStart                 = [True, True, True, True, True]
        self.Jpos                       = [0]*5
        self.JposPrec                   = [0]*5
        self.Jdes                       = [0]*5
        self.change_dir_count           = [0]*5
        self.Jv                         = [0]*5
        self.Jdebug                     = []
        self.SavedPos                   = [0]*5
        self.VocalCtrlPos               = None

        # self.TargetPos    = [0.27, 0.2, -0.1]
        # self.TargetPos    = [0.3, 0.1, 0.15]
        self.TargetPos    = [0.3, -0.15, 0.2]
        # self.TargetPos    = [0.25, 0.2, -0.15]
        # self.TargetPos    = [0.3, -0.15, -0.1]


class BridgeClass:
    def __init__(self):
        self.J              = [None] * 5
        self.InitThread     = [None] * 5
        self.UpdateThread   = [None] * 5
        self.ControlThread  = None

class SerialClass:
    def __init__(self):
        self.COM            = [None] * 5
        self.Connected      = [False] * 5
        self.Enabled        = False


class PyGameConfClass:
    def __init__(self):

        self.size   = self.width, self.height = 320, 240
        self.color  = 0, 0, 0
        self.period = 0.05

class BridgeConfClass:
    def __init__(self):
        self.version     = '1.0'
        self.verbose     = True
        self.conf_file   = 'Conf.ini'

        self.PyGameConf  = PyGameConfClass()
        self.serial      = SerialClass()

        self.Jmin        = [0]*5
        self.Jmax        = [0]*5
        self.COM         = ['']*5
        self.Ratio       = [0]*5
        self.Offset      = [0]*5
        self.Target      = [0]*5

        self.CtrlEnable  = False
        self.InitEnable  = False
        self.InitDone    = False
        self.FirstStart  = True

        self.CtrlThreadPeriod = 0.1

        self.PatientLoaded  = False
        self.PatientFile    = ''

        self.CtrlInput      = 'ET'
        self.CtrlEnable     = True


        # Parameters
        self.toll        = 1e-4 # tolleranza sull'errore cartesiano nella cinematica inversa
        self.Rjoint2     = float(8) / 100 #0.08 -> raggio del terzo giunto [m]
        self.deq         = 10*math.pi/180 #intervallo delta q in cui eseguire la rampa del peso di giunto da 1 a 0; se sono deq vicino al limite di giunto scalo il peso da 1 a 0
        self.alpha       = 1
        self.l1          = 0.13
        self.l2          = 0.1186
        self.l3          = 0.2060
        self.l           = self.l1+self.l2+self.l3
        self.s           = 0.01 # max velocità lungo le 3 direzioni cartesiane [Hz -> steps/sec]
        self.ctrl_t      = 0.1 # [s] durata del ciclo di controllo -> 10 Hz
        self.eps         = 0.1
        self.wq0s        = 0.2 # minimo valore per il peso del giunto --> massimo valore 1
        self.it_max      = 1000 # massimo numero di iterazioni 
        self.co          = 0.4
        self.n_discr     = 100 #numero discretizzazioni nelle varie dimensioni del WS
        self.MaxDegDispl = 5 # °

        self.w_plot_joy  = 0
        self.h_plot_joy  = 0

    def ReadPatientFile (self, filename):
        try:
            Config = ConfigParser.ConfigParser()
            Config.read(filename)
            section = Config.sections()

            self.Jmin[0]        = int(Config.get(section[0],"J1_min"))
            self.Jmin[1]        = int(Config.get(section[0],"J2_min"))
            self.Jmin[2]        = int(Config.get(section[0],"J3_min"))
            self.Jmin[3]        = int(Config.get(section[0],"J4_min"))
            self.Jmin[4]        = int(Config.get(section[0],"J5_min"))

            self.Jmax[0]        = int(Config.get(section[0],"J1_max"))
            self.Jmax[1]        = int(Config.get(section[0],"J2_max"))
            self.Jmax[2]        = int(Config.get(section[0],"J3_max"))
            self.Jmax[3]        = int(Config.get(section[0],"J4_max"))
            self.Jmax[4]        = int(Config.get(section[0],"J5_max"))

            self.Ratio[0]        = float(Config.get(section[0],"M1_ratio"))
            self.Ratio[1]        = float(Config.get(section[0],"M2_ratio"))
            self.Ratio[2]        = float(Config.get(section[0],"M3_ratio"))
            self.Ratio[3]        = float(Config.get(section[0],"M4_ratio"))
            self.Ratio[4]        = float(Config.get(section[0],"M5_ratio"))

            self.Offset[0]       = float(Config.get(section[0],"M1_offset"))
            self.Offset[1]       = float(Config.get(section[0],"M2_offset"))
            self.Offset[2]       = float(Config.get(section[0],"M3_offset"))
            self.Offset[3]       = float(Config.get(section[0],"M4_offset"))
            self.Offset[4]       = float(Config.get(section[0],"M5_offset"))

            self.Target[0]       = float(Config.get(section[0],"M1_target"))
            self.Target[1]       = float(Config.get(section[0],"M2_target"))
            self.Target[2]       = float(Config.get(section[0],"M3_target"))
            self.Target[3]       = float(Config.get(section[0],"M4_target"))
            self.Target[4]       = float(Config.get(section[0],"M5_target"))

            self.PatientFile     = filename

            return True

        except Exception, e:
            print '# Error: ReadPatientFile failed | ' + str(e)
            # Read conf failed -> create a new configuration file
            return False


    def WriteConfFile(self):

        Config = ConfigParser.ConfigParser()
        Config.optionxform = str
        section = 'BRIDGE'
        Config.add_section(section)

        Config.set(section, 'COM_M1', self.serial.COM[0])
        Config.set(section, 'COM_M2', self.serial.COM[1])
        Config.set(section, 'COM_M3', self.serial.COM[2])
        Config.set(section, 'COM_M4', self.serial.COM[3])
        Config.set(section, 'COM_M5', self.serial.COM[4])

        cfgfile = open(self.conf_file,'w')
        Config.write(cfgfile)
        cfgfile.close()

    def WritePatientFile(self, filename):

        Config = ConfigParser.ConfigParser()
        Config.optionxform = str
        section = 'BRIDGE-PATIENT'
        Config.add_section(section)

        Config.set(section, 'J1_min', self.Jmin[0])
        Config.set(section, 'J2_min', self.Jmin[1])
        Config.set(section, 'J3_min', self.Jmin[2])
        Config.set(section, 'J4_min', self.Jmin[3])
        Config.set(section, 'J5_min', self.Jmin[4])

        Config.set(section, 'J1_max', self.Jmax[0])
        Config.set(section, 'J2_max', self.Jmax[1])
        Config.set(section, 'J3_max', self.Jmax[2])
        Config.set(section, 'J4_max', self.Jmax[3])
        Config.set(section, 'J5_max', self.Jmax[4])

        Config.set(section, 'M1_ratio', self.Ratio[0])
        Config.set(section, 'M2_ratio', self.Ratio[1])
        Config.set(section, 'M3_ratio', self.Ratio[2])
        Config.set(section, 'M4_ratio', self.Ratio[3])
        Config.set(section, 'M5_ratio', self.Ratio[4])

        Config.set(section, 'M1_offset', self.Offset[0])
        Config.set(section, 'M2_offset', self.Offset[1])
        Config.set(section, 'M3_offset', self.Offset[2])
        Config.set(section, 'M4_offset', self.Offset[3])
        Config.set(section, 'M5_offset', self.Offset[4])

        Config.set(section, 'M1_target', self.Target[0])
        Config.set(section, 'M2_target', self.Target[1])
        Config.set(section, 'M3_target', self.Target[2])
        Config.set(section, 'M4_target', self.Target[3])
        Config.set(section, 'M5_target', self.Target[4])

        cfgfile = open(filename,'w')
        Config.write(cfgfile)
        cfgfile.close()

