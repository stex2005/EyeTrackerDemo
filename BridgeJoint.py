# -*- coding: utf-8 -*-
from serial import *
import math
from numpy.linalg import inv
import math
import numpy
import serial
import threading, time
from BridgeConf import BridgeClass, BridgeConfClass, BridgeCoordClass

class Joint:
    def __init__(self, num, COM, Jmax, Jmin, Ratio, Offset, Target, Coord):
    #MGdef __init__(self, num, name, COM, Jmax, Jmin, Ratio, Offset, Target):
        self.num            = num
        self.CommPort       = ""
        self.Dmin           = 0.0     # min joint angular position
        self.Dmax           = 0.0     # max joint angular position
        self.Ratio          = Ratio   # reduction ratio 
        self.Offset         = Offset  # home (0 step) position (deg)
        self.StepDegrees    = 1.8     # degrees value of one step
        self.Target         = Target  # lo uso come target iniziale
        self.position       = 0       # posizione corrente
        self.connected      = 0
        self.porta          = serial.Serial()
        self.homed          = False
        self.Coord          = Coord

        self.SetPort(self.num, COM)
        self.SetRange(Jmax, Jmin)


    def SetPort(self, num, name):
        self.CommPort = name
        #print "Joint %d port set to %s" % (self.num, self.CommPort)

    def SetRange(self, dmin, dmax):
        if dmin > dmax:
            self.Dmin = dmax
            self.Dmax = dmin
        else:
            self.Dmin = dmin
            self.Dmax = dmax
            
        #print "Joint %d range: %d , %d" % (self.num, self.Dmin, self.Dmax)
    
    #function for check the controller response    
    def RplyCheck(self, sentcmd):

        stream = str()
        looppa = 1

        #print '@@@@@@@@@@@@@@@@ Rply check in'

#        while not stream.endswith("\r",stream):
        while looppa == 1:

            #wait for data in the RXbuffer
            while self.porta.inWaiting() < 1:
                time.sleep(0.01)
                
            #print '@@@@@@@@@@@@@@@@ Rply check out while loop'
            newchar = self.porta.read(1)

            if newchar == '\r':
                cmd_reply = stream + newchar
                looppa = 0
                #print '- Reply %s' % cmd_reply       
            else:
                stream += newchar                    
        
        # print 'reply:' + cmd_reply
        
 #       if cmd_reply == sentcmd:  #escludo il cancelletto dal confronto
        if cmd_reply == sentcmd[1 : ] :  #escludo il cancelletto dal confronto
            #print "Config sent correctly"
            return 1
        else:
            print "wrong reply to Config 1"             
            return 0
        
    #function for set up one or more parameters    
    def WriteCmd(self, command):

        ok_flag = True
        
        for cmd_el in command:
            
            try:
                self.porta.write(cmd_el)
                #print 'sent command: ' + cmd_el
                
                if self.RplyCheck(cmd_el) == 1:
                    ok_flag = True
                    #print 'Config sent correctly'
                else:
                    ok_flag = False
                    print 'wrong reply to Config 2'
            except:
                print 'Errore nell invio dei dati di configurazione'
                return False
                
        return ok_flag
                
    def ReadCmd(self, command):
        
        try:
            self.porta.write(command)
            #print 'parameter to read: ' + command
            
            stream = str()
            looppa = 1

#           while not stream.endswith("\r",stream):
            while looppa == 1:

                #wait for data in the RXbuffer
                while self.porta.inWaiting() < 1:
                    time.sleep(0.01)
                
                newchar = self.porta.read(1)

                if newchar == '\r':
                    cmd_reply = stream + newchar
                    looppa = 0               
                    #print cmd_reply      
                else:
                    stream += newchar                    
            #print 'reply:' + cmd_reply
            #cmd_reply = cmd_reply[1 : ] #ELIMINO CANCELLETTO DA RIMUOVERE!!!
            #print 'mod reply: ' + cmd_reply
            #print 'comm_t', command[1:len(command)-1]            
            #print 'reply_t', cmd_reply[ : len(command)-2]
            
            #command = command[1 : ]
#            if cmd_reply[ : 2] == command[1:3] :  #escludo il cancelletto dal confronto
            if cmd_reply[ : len(command)-2] == command[1:len(command)-1] :  #escludo il cancelletto dal confronto
                #if true, the controller response is relative to my query
                #so the value is after the header (and before the terminator)
                #value = int(cmd_reply[2: -1])
                #print 'valstring', cmd_reply[len(command)-2: -1]
                value = int(cmd_reply[len(command)-2: -1])
                #print 'val', value
                #print "Config sent correctly"
                return value
            else:
                print 'wrong reply to Read'           
                return 0
        except:
            print 'Errore lettura valore'
            return 0
            
                
    def OpenPort(self):
        try:
            self.porta.port     = self.CommPort
            self.porta.baudrate = 115200
            self.porta.parity   = serial.PARITY_NONE
            self.porta.stopbits = serial.STOPBITS_ONE
            self.porta.bytesize = serial.EIGHTBITS
            self.porta.timeout  = 0.1
            
            self.porta.open()
            self.porta.isOpen()

            self.porta.flush()
            self.porta.flushInput()
            self.porta.flushOutput()
            self.connected = 1

            return True
        except Exception, e:
            self.connected = 0
            return False

    def ClosePort(self):

        command = "#1S\r"  #stop the joint motor
        
        try:            
            self.porta.write(command)
            self.porta.flush()
        
            time.sleep(0.1)
            
            self.porta.flushInput()
            self.porta.flushOutput()
            self.porta.close()
            return True

        except:
            return False
    
    #send the target position to the controller (deg)
    def SetPositionDeg(self, p0deg):
        #check che sia nel range
        if p0deg >= self.Dmin and p0deg <= self.Dmax:
            p0step = self.deg2step(p0deg - self.Offset)
            
            #print 'p0step', p0step
            
            #leggo posizione attuale
            self.position = self.GetPositionDeg()

            #MGself.Coord.Jpos[self.num-1] = self.GetPositionDeg()
            #MGprint self.deg2step(self.position)
            
            if p0step == self.deg2step(self.position - self.Offset):
                #print'@@@@@@@@@@@@@@@@@already here'
                return True, self.position
            else:
                #print'@@@@@@@@@@@@@@@@@ invio cmd'
                #print 'p0step', p0step
                targetpos = "#1s%d\r" % p0step
                #print 'target', targetpos
                command = [targetpos, "#1A\r"]  #target position, start movement
                #return self.WriteCmd(command) ORIGINALE
                self.WriteCmd(command)
                return False, self.position
        else:
            #print 'out of range'
            return False, -1

    def SetMinSpeedHz(self, speed):

        if speed > 0:
            targetdirection = "#1d0\r" # Orario
        else:
            targetdirection = "#1d1\r" # Antiorario

        speed = abs(speed)

        #check che sia nel range
        if speed > 25 and speed <= 25000:
            targetspeed = "#1u%d\r" % speed
            command = [targetdirection, targetspeed]
            return self.WriteCmd(command)
        else:
            #print 'out of range'
            return False, -1

    def SetMaxSpeedHz(self, speed):

        if self.num == 3:
            speed = speed * -1            

        if speed == 0:
            speed = 1

       
        if speed > 0:
            targetdirection = "#1d0\r" # Orario
        else:
            targetdirection = "#1d1\r" # Antiorario

        speed = abs(speed)

        #check che sia nel range
        if speed >= 0 and speed <= 25000:
            targetspeed = "#1o%d\r" % speed
            command = [targetdirection, targetspeed]  #target position, start movement
            return self.WriteCmd(command)
        else:
            return False, -1

    def StartSpeed(self):
        command = ["#1D0\r", "#1D0\r"]
        self.WriteCmd(command)
        time.sleep(1)

        command = ["#1y10\r","#1A\r"]    #first record (homing) and start
        self.WriteCmd(command)

    def Stop(self):
        command = ["#1S\r","#1S\r"]
        self.WriteCmd(command)
        time.sleep(0.01)

    def Start(self):
        command = ["#1A\r"]
        self.WriteCmd(command)
        time.sleep(0.01)

    def HomingQuery(self):
        command = ["#1D0\r", "#1D0\r"]
        self.WriteCmd(command)
        time.sleep(1)

        self.ReadCmd("#1:is_referenced\r")

        if self.ReadCmd("#1:is_referenced\r") == 0: # first reference procedure

            print "Sono dentro all'if della prima reference procedure"

            command = ["#1y2\r","#1A\r"]    #second record (homing) and start
            self.WriteCmd(command)
            #time.sleep(20)
            #print 'homing command: ', self.ReadCmd("#1:is_referenced\r")
            self.ReadCmd("#1:is_referenced\r")

            while self.ReadCmd("#1:is_referenced\r") == 0:
                #command = ["#1Zy2\r"]
                print "Input reading: ", self.WriteCmd("#1Lh6\r")
                time.sleep(0.5)
            print "Input reading fine while: ", self.ReadCmd("#1:Capt_iAnalog\r")

        #else:
            # do referencing with the "new" profile
            # command = ["#1y2\r","#1A\r"]    #xxx record (homing) and start
            # self.WriteCmd(command)
            

    def DriveErrorClear(self):
        command = ["#1D0\r", "#1D0\r"]
        self.WriteCmd(command)
        #print 'DriveErrorClear'
    
    #read the actual position from the controller (deg)
    def GetPositionDeg(self):
        return self.step2deg(self.ReadCmd("#1I\r")) + self.Offset

    def GetPosition(self):
        return self.ReadCmd("#1I\r")
    
    #return the number of step, starting from degrees
    def deg2step(self,pdeg):
        return int(pdeg * self.Ratio / self.StepDegrees)
        
    #return the joint position (deg), starting from the encoder read
    def step2deg(self, pstep):
        return (pstep / (self.Ratio / self.StepDegrees))

    #read the actual position from the controller (deg)
    def SetPositionMode(self):
        command = ["#1y1\r", "#1p2\r"]

        while self.WriteCmd(command) == False:
            time.sleep(1)

    def MotorStart(self):
        command = ["#1A\r"]

        while self.WriteCmd(command) == False:
            time.sleep(1)



class Thread_JointInitClass(threading.Thread):

    def __init__(self, Jj):

        threading.Thread.__init__(self)
        self.stop           = threading.Event()
        self.running        = False
        self.Jn             = Jj
        #self.finalpos       = fpos
        #self.conf           = conf
        
    def run(self):
        
        #global p0,q0, joint_update
        self.running = True
        #print self.lockingThread, self.Jn.num
        
        #MGif self.lockingThread == 1:
            # Get lock to synchronize threads
            #MGlock.acquire()
            
        self.Jn.HomingQuery()

        print 'J%d - Homing done!' % self.Jn.num

        
        command = ["#1D0\r", "#1D0\r"]
        self.Jn.WriteCmd(command)
        time.sleep(0.5)

        
        homing_position = self.Jn.GetPositionDeg()
        print 'J%d - Homing position (deg: %d | step: %d):' % (self.Jn.num, homing_position, self.Jn.deg2step(homing_position))
        
        time.sleep(0.5)
        
        #mando al controller le seguenti impostazioni
        command = ["#1y1\r", "#1p2\r"]  #record 2, absolute position
        
        while self.Jn.WriteCmd(command) == False:
            time.sleep(1)
        
        time.sleep(0.1)
        
        self.Jn.SetPositionDeg(self.Jn.Target)   #position setpoint -> ho cambiato in Target che era campo esistente
        
        while abs(self.Jn.GetPositionDeg()-self.Jn.Target) > 2.0:
            print '**** Sto andando a target position, J%d - %d' % (self.Jn.num, self.Jn.GetPositionDeg())
            time.sleep(1)
            #self.Jn.SetPositionDeg(self.Jn.Target)
            
        print 'J%d - In position (%f)' % (self.Jn.num, self.Jn.GetPositionDeg())
        #flag che indica la corretta inizzializzazione del joint
        
        self.Jn.homed = True

        print ' J%d - target position (%f)' % (self.Jn.num, self.Jn.Target)
        
        #time.sleep(1)
        #MGif self.lockingThread == 1:
            # Free lock to release next thread
            #MGlock.release()                
                                         
    def terminate(self):
        
        # Kill the thread
        self.stop.set()
        self.running = False
    
class Thread_JointUpdateClassOld(threading.Thread):
    def __init__(self, Jj, Conf, Coord):

        threading.Thread.__init__(self)
        self.stop           = threading.Event()
        self.running        = False
        self.Jn             = Jj
        self.Conf           = Conf
        self.Coord          = Coord
        #self.period         = 0.1
        self.FirstStart     = True
        
    def run(self):
        self.running   = True
        self.ret       = False


        command = ["#1y3\r", "#1p2\r"]  #record 3, absolute position

        while self.Jn.WriteCmd(command) == False:
            time.sleep(1)

        
        while self.running and self.Conf.CtrlRunning:
            # measure process time
            #t0 = time.clock()

            if self.Coord.Jupdate[self.Jn.num-1] and not self.Coord.GoToSavedPos[self.Jn.num-1]:
                #print 'J%d Update' % self.Jn.num
                self.ret, self.Coord.Jpos[self.Jn.num-1] = self.Jn.SetPositionDeg(self.Coord.Jdes[self.Jn.num-1])
                self.Coord.Jupdate[self.Jn.num-1] = False

                #self.Coord.Jpos[self.Jn.num-1] = self.Jn.GetPositionDeg()

                '''
                if self.FirstStart:
                    print 'J%d Update' % self.Jn.num
                    self.ret, self.Coord.Jpos[self.Jn.num-1] = self.Jn.SetPositionDeg(self.Coord.Jdes[self.Jn.num-1])
                    self.FirstStart = False


                
                #if self.Jn.SetPositionDeg(10):
                self.ret, self.Coord.Jpos[self.Jn.num-1] = self.Jn.SetPositionDeg(self.Coord.Jdes[self.Jn.num-1])
                if self.ret:   #position setpoint
                    # print 'Joint %d in position' % self.Jn.num
                    self.Coord.Jupdate[self.Jn.num-1] = False
                    self.FirstStart = True
                    #print 'Set J', self.Jn.num, ' PosDeg OK', p0[self.Jn.num-1]
                '''
            elif self.Coord.GoToSavedPos[self.Jn.num-1]:
                self.ret, self.Coord.Jpos[self.Jn.num-1] = self.Jn.SetPositionDeg(self.Coord.SavedPos[self.Jn.num-1])

                if abs(self.Coord.Jpos[self.Jn.num-1] - self.Coord.SavedPos[self.Jn.num-1]) < 1:
                   self.ret = True
 
                if self.ret:
                    print '################################ STO ARRIVATO J%d' % self.Jn.num
                    self.Coord.GoToSavedPos[self.Jn.num-1] = False
            else:
                self.Coord.Jpos[self.Jn.num-1] = self.Jn.GetPositionDeg()

                if self.Coord.SavePos[self.Jn.num-1]:
                    self.Coord.SavePos[self.Jn.num-1] = False
                    self.Coord.SavedPos[self.Jn.num-1] = self.Coord.Jpos[self.Jn.num-1]

                    print ' + J%d - Jpos saved: %f' % (self.Jn.num, self.Coord.Jpos[self.Jn.num-1])

                time.sleep(0.001)

        print '@@@@@@@@@@@@@ J%d  update thread exit' % self.Jn.num

    def terminate(self):
        
        #close the serial port
        try:
            Jn.ClosePort()
        except:
            print 'Errore chiusura porta seriale'

        
        # Kill the thread
        self.stop.set()
        self.running = False


class Thread_JointUpdateClass(threading.Thread):
    def __init__(self, Jj, Conf, Coord):

        threading.Thread.__init__(self)
        self.stop           = threading.Event()
        self.running        = False
        self.Jn             = Jj
        self.Conf           = Conf
        self.Coord          = Coord
        self.FirstStart     = True
        self.Period         = 0.1
        self.StopPosition   = None
        
    def run(self):
        self.running   = True
        self.ret       = False
        
        command = ["#1y10\r", "#1o1\r", "#1A\r"]

        while self.Jn.WriteCmd(command) == False:
            time.sleep(1)

        self.Coord.Jpos[self.Jn.num-1] = self.Jn.GetPositionDeg()
        
        while self.running:

            # measure process time
            t0 = time.clock()

            if self.Conf.CtrlEnable:

                if self.Coord.GoToSavedPos[self.Jn.num-1]:

                    if self.Coord.FirstStart[self.Jn.num-1]:

                        command = ["#1S\r", "#1y1\r", "#1p2\r"]

                        while self.Jn.WriteCmd(command) == False:
                            time.sleep(1)

                        self.Coord.FirstStart[self.Jn.num-1] = False

                    self.ret, self.Coord.Jpos[self.Jn.num-1] = self.Jn.SetPositionDeg(self.Coord.SavedPos[self.Jn.num-1])

                    if abs(self.Coord.Jpos[self.Jn.num-1] - self.Coord.SavedPos[self.Jn.num-1]) < 1:
                       self.ret = True

                    if self.ret:
                        print '################################ STO ARRIVATO J%d' % self.Jn.num
                        self.Coord.GoToSavedPos[self.Jn.num-1] = False

                else:
                    '''
                    if self.Jn.num == 1:
                        print 'YEEEEEEEEEE 2'
                    '''

                    if self.Coord.FirstStart[self.Jn.num-1]:
                        print '* JointUpdate %d: first start speed control' % self.Jn.num

                        command = ["#1S\r", "#1y10\r", "#1o1\r", "#1A\r"]

                        while self.Jn.WriteCmd(command) == False:
                            time.sleep(1)

                        self.Coord.FirstStart[self.Jn.num-1] = False

                    #print 'JointUpdate %d | speed %d' % (self.Jn.num, self.Coord.Jv[self.Jn.num-1])

                    # Set speed
                    self.Jn.SetMaxSpeedHz(self.Coord.Jv[self.Jn.num-1])

                    # Get position
                    self.Coord.Jpos[self.Jn.num-1] = self.Jn.GetPositionDeg()

                    if self.Coord.SavePos[self.Jn.num-1]:
                        print '@@@@@@@@     JointUpdate %d | saving pos %d' % (self.Jn.num, self.Coord.Jpos[self.Jn.num-1])
                        self.Coord.SavePos[self.Jn.num-1] = False
                        self.Coord.SavedPos[self.Jn.num-1] = self.Coord.Jpos[self.Jn.num-1]
            else:

                if self.Coord.FirstStart[self.Jn.num-1]:
                    print '* JointUpdate %d: first start position control' % self.Jn.num

                    command = ["#1S\r", "#1y1\r", "#1p2\r"]

                    while self.Jn.WriteCmd(command) == False:
                        time.sleep(1)

                    # Disable flag
                    self.Coord.FirstStart[self.Jn.num-1] = False

                    # Get current position
                    self.StopPosition = self.Jn.GetPositionDeg()

                self.ret, self.Coord.Jpos[self.Jn.num-1] = self.Jn.SetPositionDeg(self.StopPosition)

            elapsed_time = time.clock() - t0

            if elapsed_time > self.Period:
                print ' - JointUpdate %d: overrun' % self.Jn.num

                elapsed_time = self.Period

            time.sleep(0.1- elapsed_time)


        print ' - JointUpdate %d: thread exit' % self.Jn.num

    def terminate(self):
        
        #close the serial port
        try:
            Jn.ClosePort()
        except:
            print 'Errore chiusura porta seriale'

        
        # Kill the thread
        self.stop.set()
        self.running = False