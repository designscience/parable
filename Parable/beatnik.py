"""
Tap Beat Time Interface Class Version 1.0
Stu D'Alessandro

---Version Notes---
1.0 Release Version.

Beatnik is a tap beat class that accepts taps (mouse clicks or similar) and generates a
stable music beat that can be used to sunchronize a sequence to live music.  Beatnick is
designed to produce a stable accurate beat that can be quickly resampled to adjust to a
new beat or to bring the beat back in sync.

Beatnik is the successor to BTIC, written by Matt Kahler. BTIC worked but had isses with
drift (beat accuracy) and resynchsonizing would often result in a wildly off beat time
that was difficult to recover from.  Beanik maintains the same interface as BTIC with some
added methods.

Beatnik is a container class which contains an active tapBeat object and an optional
collecting tabBeat object.  The active tapBeat object is what a Beatnick onject delivers
it's current timing from.  If a new tap is offered a new tapBeat class object is created
to collect the taps and, when the beat is consistent enough, this is replaced as the active
tapBeat object.  

---Variable Notes---
fDL = FinishedDataList -- this is a simple float (double) timing value, in seconds, between beats.  

Version 1.01 - receives optional tap time in BeatRecorder()

"""

import time
import math

class TapBeat(object):
    def __init__(self):
        """ Initializes the tap beat  """
        self.taps_to_count = 12  # number of taps to incorporate into the calculation 
        self.taps = []
        self.index = 0
        self.period = 5.00      # arbitrary start value - will be overwritten

        self.ready = False      # indicates the timing is reasonably accurate
        self.locked = False     # no more taps accepted for this object

        self.start_time = 0.0   # reference start time
        self.invert_light = False   # 1 to invert, else 0

        self.toggle_test = 1000 # testing only
        self.cur_state = False

        self.default_light_time = 0.06  # SET default beat light time HERE
        self.light_time = 0.06  # time that the beat light is on in seconds
        
        time.time()             # start system time


    def tap(self, tapTime = None):
        """ Processes a tap and recalculated timing.
            Returns True if tap accepted, False if rejected (locked) """
        now = time.time() if tapTime == None else tapTime
        if (not self.locked and self.tapIsLegal(now)):
            # only collect the indicated amount of taps
            if (self.index >= self.taps_to_count):
                del self.taps[0]
                self.index = self.taps_to_count - 1

            self.taps.append(now)
            self.start_time = now  # use this as the new start time 
            self.index = self.index + 1
            print "INDEX: " + str(self.index)
            self.calcPeriod()
            return True
        else:
            return False
        

    def tapIsLegal(self, tapTime):
        """ filter out taps that are way out of time. Takes a current time value in seconds (float) """
        if self.index > 1:
            if (tapTime < (self.taps[self.index - 1] + (self.period * 1.5))) and \
               (tapTime > (self.taps[self.index - 1] + (self.period * 0.5))):
                return True
            else:
                print "TAP OUT OF RANGE."
                self.locked = True
                return False
        else:
            return True


    def calcPeriod(self):
        """ calculates the beat period """
        if (self.index > 1):
            self.period = (self.taps[self.index - 1] - self.taps[0]) / float(self.index - 1)
            if self.period < self.default_light_time / 3:
                self.light_time = self.period / 3
            else:
                self.light_time = self.default_light_time 
                
            # print "CALC PERIOD: " + str(self.taps[self.index - 1]) + " - " + str(self.taps[0]) + " / " + str(float(self.index - 1)) + " = " + str(self.period)

            #determine accuracy and set ready flag
            if self.index > 3:
                self.ready = True


    def nextBeatSecs(self):
        """ return a float, the number of seconds.ms until next beat """
        now = time.time()
        nextBeatTime = (math.ceil((now - self.start_time) / self.period) * self.period) + self.start_time
        return nextBeatTime - now


    def isReady(self):
        """ returns true if the tap beat may be used """
        return (self.ready)

    def isLocked(self):
        """ returns True if the tap bet is not accepting more taps """
        return (self.locked)

    def light(self):
        """ should the beat light be on or off? 1/10th second beat light assumed
            (old version toggled light every other beat) """
        if (self.index > 2):
            #return (math.ceil((time.time() - self.start_time) / self.period) % 2 != 0) ^ self.invert_light
            return ((time.time() - self.start_time) % self.period) > self.light_time            
        else:
            return False
        

    def setLightState(self, new_state):
        """ Sets the current state of the light (on or off).
            TYpically to sync with the light state of another TapBeat """
        cur_state = self.light()
        self.invert_light = cur_state != new_state
        

    def getPeriod(self):
        return self.period

    def setStartTime(self, new_start_time):
        """ used for aligning an existing tapBeat back to the start time """
        self.start_time = new_start_time

    def getCorrectedBeatTime(self, reference_beat_time):
        """ return beat time for this object that is closest to the passed
            reference_beat_time. Return passed beat time if this object is not ready """
        if self.ready:
            multi = (reference_beat_time - self.start_time) / self.period
            rem = multi - math.floor(multi)
            if rem > 0.5:
                return (math.ceil(multi) * self.period) + self.start_time
            else:
                return (math.floor(multi) * self.period) + self.start_time
        else:
            return reference_beat_time

                     
            


class Beatnik(object):
    def __init__(self):
        self.fDL = 0.500
        self.cur_state = False
        self.beat_light = 0

        # tap storage
        self.player = TapBeat()  # initial TapBeat obect
        self.collector = None  # 


    def __str__(self):
        return "BTIC Beat Keeper - period = " + str(self.fDL)
        
    def BeatRecorder(self, tap_time = None):
        """ record a tap into either the player TapBeat object or the
            collector TapBeat object, promoting the collector to the
            player when it's ready """
        if tap_time == None or tap_time == 0.0:
            now = time.time()
        else:                
            now = tap_time
            
        if self.collector == None:
            # if no collector object then tap the player
            if self.player.tap(now) == False:
                print "creating a collector"
                self.collector = TapBeat()
                self.collector.tap(now)
        else:
            # tap the collection object - move it to player?
            self.collector.tap(now)
            if self.collector.isReady():
                print "promoting collector"
                self.collector.setLightState(self.player.light())
                del self.player
                self.player = self.collector
                self.collector = None
            else:
                if self.collector.isLocked():
                    print "collctor NG - replacing collector"
                    self.collector = TapBeat()
                    self.collector.tap(now)
                    
        self.fDL = self.player.getPeriod() # update the period value


    def BeatLight(self):
        """ When called, will analyze if it's time to turn the light on, or time to turn the light off. """
        return self.player.light() if self.collector == None or not self.collector.isReady() else self.collector.light()
    

    def BeatLightToggle(self):
        """ Returns true ONLY if the state has changed """
        result = self.BeatLight() != self.cur_state            
        if result == True:
            self.cur_state = not self.cur_state
        return result


    def nextBeatTime(self):
        """ returns float, number of seconds.milliseconds until next beat """
        return self.player.nextBeatSecs() 


    def align(self, tap_time = None):
        """ realigns the player start time """
        if tap_time == None:
            now = time.time()
        else:
            now = tap_time
        if self.player.isReady():
            self.player.setStartTime(now)

    def isReady(self):
        """ returns true if player is ready """
        return self.player.isReady()

    def isSimilarTo(self, reference_beat_period):
        """ Returns True if player beat period is similar to passed beat period.
            Used to determine if sequence should use this beatnik to sync to """
        if self.player.isReady():
            ratio = reference_beat_period / self.player.getPeriod()
            return ratio < 1.25 and ratio > .75
        else:
            return False

    def getCorrectedBeatTime(self, reference_beat_time):
        """ Returns the beat time for this object that is closest to the
            passed reference beat time. Returns reference time back if this
            player object is not ready """
        return self.player.getCorrectedBeatTime(reference_beat_time)


    

    




        
