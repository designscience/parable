""" *****************************************************
This file defines classes used in the Parable effects sequencing
program used for the Shiva Vista Project, Burning Man 2007-2009.

Author: Stu D'Alessandro (stu@design-sci.com)

NOTES
* Set total_frames in TimeCode to a long.  Added long
handling in setTime().  Allows system clock to be used as an initializer.
7/13/2009

* Added start(), stop(), getNextByTime(), and the cleanup[] array to
allow a sequence to be played by an external loop and to be arbitrarily
stopped without leaving a cannon firing.

* Added perpetual sync ability, mostly in getNextByTime() (if beatnik
object passed).  7/24/2012

* Added TimeCode storing of float value (seconds) in attempt to improve
accuracy.  E.G. time basis is not float seconds with frames a by-product
instead of basis being frames with float seconds a by-product.  7/26/2012


Version 2.1

***************************************************** """

from __future__ import division
import parallel
import winsound
import operator
import time
import random
import os
import sys
import threading
import wx
import xml.etree.ElementTree as ET  # XML support
#import BTIC  # beat keeper class
from Queue import Queue

max_channels = 24  


#*********************** Channel ****************************
    
class ChannelMap(object):
    """ defines the mapping of one channel to another to account
        for hardware or input differences. Randomize() function
        swaps the channels around for run.  Reset() puts them back. """

    def __init__(self, num_channels=24):
        self.num_channels = num_channels
        self.map = [0] * num_channels
        self.current = [0] * num_channels
        # set up default
        self.clear()

    def addMapping(self, source_ch, dest_ch):
        """ Adds one channel mapping to the list """
        if source_ch < self.num_channels and source_ch > 0:
            self.map[source_ch - 1] = dest_ch
            self.reset()
            return True
        else:
            return False

    def reset(self):
        """ revert any temporary mapping to the set mapping """
        for i in range(self.num_channels):
            self.current[i] = self.map[i]

    def clear(self):
        """ clear out mapping and revert to a 1:default 1:1 mapping """
        for i in range(self.num_channels):
            self.map[i] = i + 1
            self.current[i] = i + 1

    def lookup(self, source_channel):
        """ lookup the source channel for this destination channel """
        if source_channel >= 0 and source_channel < self.num_channels:
            if source_channel == 0:
                return 0
            else:
                return self.current[source_channel - 1]
        else:
            return False


    def reverseLookup(self, dest_channel):
        """ lookup the source channel for this destination channel """
        result = 0
        for i in range(self.num_channels):
            if self.current[i] == dest_channel:
                result = i + 1
                break
        return result
    


#***************** TimeCode **************************

class TimeCode(object):
    """Stores a time code value in frames and formats it as SMPTE string"""
    version = 2.0

    def __init__(self,value=0) :
        self.total_frames = long(0)
        self.seconds = float(0.0)  # new 7/2012
        self.setTime(value)

    def __cmp__(self, other):
        """Comparison routine for cmp() BIF"""
        if isinstance(other, TimeCode):
            if self.total_frames != other.total_frames :
                if self.total_frames < other.total_frames :
                    return -1
                else :
                    return 1
            else :
                return 0
        elif isinstance(other, int) or isinstance(other, long):
            frames = long(other)
            if self.total_frames != frames :
                if self.total_frames < frames :
                    return -1
                else :
                    return 1
            else :
                return 0
        else:
            return False  # not a matching type

    def __str__(self):
        return(self.SMPTE())

    def __repr__(self):
        return(str(self.total_frames))

    def __add__(self, other):
        result = self.__class__(other)
        result.addTime(self.seconds)
        return(result)

    def __radd__(self, other):
        result = self.__class__(other)
        result.addTime(self.seconds)
        return(result)

    def __sub__(self, other):
        result = self.__class__(self.seconds)
        result.addTime(-other.seconds)
        return(result)

    def __mul__(self, other):
        result = self.__class__(self)
        if isinstance(other, TimeCode):
            result.setTime(self.seconds * other.seconds)
        else:
            # note - mulitplies by factor, not another time
            result.setTime(self.seconds * float(other))
        return(result)
        

    def setTime(self, timecode) :
        """Reads a SMPTE timecode string and sets the total_frames value"""
        if isinstance(timecode,str) :
            multipliers = [108000,1800,30,1]
            timecode = timecode.strip()
            split_tc = timecode.split(':')
            count = len(split_tc)
            index = 1
            self.total_frames = 0
                # parse string from the right-hand-side
            while count > 0 :
                try :
                    count -= 1
                    self.total_frames += int(split_tc[count]) * multipliers[4-index]
                    index += 1
                except :
                    print "There was an error in the timecode string.\nPlease use ':' to separate all fields"
                    self.total_frames = long(0)
                    break
            self.makeSeconds()
        elif isinstance(timecode,int) :
            self.total_frames = long(timecode)
            self.makeSeconds()
        elif isinstance(timecode,long) :
            self.total_frames = timecode
            self.makeSeconds()
        elif isinstance(timecode, float):  # float value assumed to be seconds!
            self.seconds = timecode
            self.makeFrames()
        elif isinstance(timecode, TimeCode):
            self.seconds = timecode.seconds
            self.makeFrames()
        else:
            print 'Time not set for new TimeCode instance; ' + str(type(timecode)) + ' passed'

    def getTime(self) :
        """Returns the timecode in frames (int)"""
        return self.total_frames

    def getSeconds(self) :
        """Returns time in seconds expressed as a float
            (converts frames to fractional seconds)"""
        return self.seconds

    def SMPTE(self):
        """Returns the timecode as a SMPTE string (""3:59:12:1"")"""
        multipliers = [108000,1800,30,1]
        index = 0
        # remainder = int(self.total_frames)
        remainder = int(self.getTime())
        result = ""
        while index < 4:
            value = divmod(remainder, multipliers[index])
            result += str(value[0])
            index += 1
            if index < 4:
                result += ":"
            remainder = value[1]
        return(result)

    def addTime(self, time_to_add):
        """Adds time (int or SMPTE string) to this timecode object"""
        # temp was previously based on total_frames
        temp = self.seconds
        self.setTime(time_to_add)
        self.seconds += temp
        self.makeFrames()

    # calculate frames value from seconds value
    def makeFrames(self):
        self.total_frames = long(round(self.seconds * 30.0))

    # calculate frames value from seconds value
    def makeSeconds(self):
        self.seconds = float(self.total_frames) / 30.0
        


#***************** ControlEvent **************************

class ControlEvent(object):
    """ Defines one Parable control action:
        time (actual of the action; TimeCode object),
        ref_time (original, unscaled timer),
        level (to combine multiple image planes),
        channel (device to control),
        action (on | off | trig),
        duration (only applies to ON actions; TimeCode object),
        scale_factor (float scaling used for current time value),
        value (from image greyscale or other input, for modulation) """
    # version = 1.1

    def __init__(self, initializer=None, **values): 
        """ __init__() takes an optional ControlEvent as an initializer """

        if isinstance(initializer, (ControlEvent, dict)):
            self.time = TimeCode(initializer.time.total_frames)
            self.ref_time = TimeCode(initializer.time.total_frames)
            self.level = initializer.level
            self.channel = initializer.channel
            self.action = initializer.action
            self.duration = TimeCode(int(initializer.duration.total_frames))
            self.value = initializer.value
            self.sequence = initializer.sequence
        elif isinstance(initializer, ET.Element):
            self.time = TimeCode(0)
            self.ref_time = TimeCode(0)
            self.level = 0
            self.channel = 0
            self.action = "off"
            self.duration = TimeCode(0)
            self.value = 0
            self.sequence = 0
            self.loadFromXML(initializer)
        else:
            # useless values to initialize the beastie
            self.time = TimeCode(0)
            self.ref_time = TimeCode(0)
            self.level = 0
            self.channel = 0
            self.action = "off"
            self.duration = TimeCode(0)
            self.value = 0
            self.sequence = 0

            if len(values) > 0:
                for k,v in values.items():
                    if k == "time":
                        self.time.setTime(v)
                        self.ref_time.setTime(v)
                    elif k == "level":
                        self.level = v
                    elif k == "channel":
                        self.channel = v
                    elif k == "action":
                        self.action = v
                    elif k == "duration":
                        self.duration.setTime(v);
                    elif k == "value":
                        self.value = v

        self.scale_factor = 1.0 #scaling in use


    def __cmp__(self, other):
        """ Compare time codes of events """
        if (isinstance(other, TimeCode)):
            return(self.time.__cmp__(other))
        elif isinstance(other, int) or isinstance(other, long) :
            result = self.time.total_frames - other.time.total_frames
            if (result > 0):
                result = 1
            elif (result < 0):
                result = -1
            return result
        else:  # incompatible data type
            return False


    def __str__(self):
        """ Returns ControlEvent settings as a string """
        result = "time=%s, level=%d, channel=%d, action=%s, dur=%d, val=%d, seq=%d" % \
                 (self.time, self.level, self.channel, self.action, self.duration.total_frames, self.value, self.sequence)
        return (result)

    __repr__ = __str__



    def getXML(self, indent=0):
        """Returns an XML element as a string; indent param inserts tabs"""
        ind1="    " * indent
        ind2="    " * (indent + 1)
        result = "%s<event>\n%s<time>%s</time>\n%s<level>%d</level>\n%s<channel>%d</channel>\n%s" \
                 "<action>%s</action>\n%s<duration>%s</duration>\n%s<value>%d</value>\n%s<sequence>%d</sequence>\n%s</event>" % \
                 (ind1, ind2, self.time.SMPTE(), ind2, self.level,  ind2, self.channel, ind2, self.action,  \
                  ind2, self.duration.SMPTE(), ind2, self.value, ind2, self.sequence, ind1)
        return(result)

    def setValues(self,frames=0,level=0,channel=0,action='off',duration=0,value=0,sequence=0):
        self.time=TimeCode(frames)
        self.ref_time=TimeCode(frames)
        self.level=level
        self.channel=channel
        self.action=action
        self.duration=TimeCode(duration)
        self.value=value
        self.value=sequence


    def translateLevel(self, newlevel = 0):
        """Changes the level for this item
        Use this function in preference to setting the level directly
        in case some rules are imposed in the future"""
        self.level = newlevel
        print "setting level to %d" % (newlevel)


    def translateChannel(self, newchannel = 0):
        """ Changes the channel for this item
            Use this function in preference to setting the level directly
            in case some rules are imposed in the future"""
        self.channel = newchannel
        print "setting channel to %d" % (newchannel)

    def setOffset(self, offsettime):
        """ changes the time of this event by adding offsettime to ref_time"""
        self.offset_time = TimeCode(offsettime)
        self.time = self.time + self.offset_time

    def getXMLElement(self, parent_node = None):
        """ returns an XML representation of this object as an xml.etree.Element object
            generally for use with ControlList.saveXML() """
        if parent_node != None:
            result = ET.SubElement(parent_node, "event")
        else:
            result = ET.Element("event")

        result.set("time", str(self.time.seconds))
        result.set("ref_time", str(self.ref_time.seconds))
        result.set("level", str(self.level))
        result.set("channel", str(self.channel))
        result.set("action", self.action)
        result.set("duration", str(self.duration.seconds))
        result.set("scale_factor", str(self.scale_factor))
        result.set("value", str(self.value))
        result.set("sequence", str(self.sequence))
        
        return result 
            
    def loadFromXML(self, xml_element):
        """ loads this object from an ElementTree.Element object """
        if isinstance(xml_element, ET.Element):
            self.time.setTime(float(xml_element.get("time", "0.0")))
            self.ref_time.setTime(float(xml_element.get("ref_time", "0.0")))
            self.level = int(xml_element.get("level", "0"))
            self.channel = int(xml_element.get("channel", "0"))
            self.action = xml_element.get("action", "off")
            self.duration.setTime(float(xml_element.get("duration", "0.0")))
            self.scale_factor = float(xml_element.get("scale_factor", "1.0"))
            self.value = int(xml_element.get("value", "0"))
            self.sequence = int(xml_element.get("sequence", "0"))
        else:
            print "loadFromXML is confused"
            
                      
                      

#***************** ControlList **************************

class ControlList(object):
    """Maintains a list of ControlEvents used to trigger event actions
    Items added to teh list are set to the default channel and level for
    this list, unless those are set to 0 (default)"""

    def __init__(self, initializer = None, level=0, channel=0, name=""):
        #set default channel and level and 'next' event
        self.deflevel = level
        self.defchannel = channel
        self.name = name

        self.next_event = 1000000  #arb large... for getNextByXXXX()
        self.eof = False

        self.start_time = TimeCode(0) #real (system) time start of sequence
        self.looping = False     # this is a looping sequence

        self.cur_state = [0] * (max_channels + 1)  #one entry for each channel
        self.cleanup = []  #array of ControlEvents to bring all channels to off

        self.scale_factor = 1.0  # for scaleOnNext()
        self.scale_pending = False  # for scaleOnNext()

        self.ref_beat_period = TimeCode(0)
        self.ref_first_beat = TimeCode(0)
        self.beat_period = TimeCode(0) # scaled version of ref_beat_period
        self.first_beat = TimeCode(0)  # scaled version of ref_first_beat

        self.sync_period = None  # period last used in scaleToBeat() - to maintain synch
        self.sync_object = None # reference to external beatnik object
        
        #initialize list with at least one event (to assert the level)
        if isinstance(initializer, ControlList):            
            self.events = []
            for ev in initializer.events:
                nextevent = ControlEvent(ev)
                self.events.append(nextevent)
        elif isinstance(initializer, str):  # XML file path
            self.events = []
            self.loadXML(initializer)
        else:
            event1 = ControlEvent(initializer)
            event1.level = level
            self.events = [event1]


    def __str__(self):
        result = ""
        for ev in self.events:
            result = result + ev.__str__() + "\n"
        return (result)


    def __add__(self, other):
        result = ControlList(self)
        if isinstance(other, ControlList):
            result.events += other.events
        elif isinstance(other, ControlEvent):
            self.addEvent(other)

    def __call__(self, out_queue, in_queue):
        print "entering thread"
        self.start()
        while self.atEnd() == False:
        #while 1:
            ev = self.getNextByTime()
            if isinstance(ev, ControlEvent):
                out_queue.put(ev)
                wx.WakeUpIdle()

            # read any sent commands
            while in_queue.empty() == False:
                cmd = in_queue.get()
                if cmd == "stop":
                    print "stopping"
                    self.stop()
                elif cmd == "start":
                    self.start()
                elif cmd == "die":
                    self.stop()
                    break
                else:
                    print "unknown cmd"
                    
        print "leaving thread"
                
            
    def addEvent(self, newEvent):
        """Adds one ControlEvent event to the list.  The level and channel of the
        event is translated unless it is already set to a non-zero value"""
        new1 = ControlEvent(newEvent) # create new event instance

        # Change channel of the new event unless already set
        if new1.channel == 0 and self.defchannel > 0:
            new1.translateChannel(self.defchannel)
        
        self.events.append(new1)
        return(new1)


    def sortEvents(self):
        """Sorts events in the list in time-order"""
        self.events.sort()


    def State(self, levelMap):
        onCount = len(levelMap)
        thisCount = 0
        for v in levelMap.itervalues():
            if v > 0:
                thisCount += 1
        
        return (thisCount >= onCount)


    def mapValue(self, valueMap):
        thisCount = 0
        for v in valueMap.itervalues():
            thisCount += v
        
        return (thisCount)


    # original version - see FAILED-1 for new version
    def offsetTime(self, offset):
        """Adds a time offset to the entire list, usually prior to
            overlaying in another list"""
        if isinstance(offset, TimeCode):
            frames = offset.total_frames
        else:
            frames = int(offset)
        
        for ev in self.events:
            ev.time.addTime(frames)

            
    # original version - see FAILED-1 for new version
    def setBaseTime(self, base_time=0):
        """ Sorts the list by time, sets the first event in this
            list to "base_time" and adjusts the time for all other
            items accordingly"""
        base = TimeCode(base_time)
        self.sortEvents()
        diff = base - self.events[0].time
        if diff.total_frames != 0:
            self.offsetTime(diff)

    
    def overlay(self, other_list, time_offset=0):
        """Overlays another list on this one. with an optional time offset"""
        # Create a unique instance of other_list
        other = ControlList(other_list)
        
        # Add time offset to other list
        ofs = TimeCode(time_offset)
        if (ofs.total_frames != 0):
            other.offsetTime(ofs.total_frames)
        
        if isinstance(other, ControlList):
            for ev in other.events:
                self.addEvent(ev)
        elif isinstance(other, ControlEvent):
            self.addEvent(other)
        else:
            print 'Overlay failed; illegal argument type'
        
        # Sort events in time order
        self.sortEvents()


    def append(self, other_list):
        """sorts this list then appends other_list by setting
            the base time of that list to the time of the last
            event in this list then overlaying the other_list."""
        if isinstance(other_list, ControlList):
            other = ControlList(other_list)
            self.sortEvents()
            start_time = self.events[len(self.events)-1].time
            ev = self.events[len(self.events)-1]
            self.overlay(other, ev.time.total_frames)
            return start_time
        else:
            print 'Unable to append other_list; \nIt is not a ControlList instance'
            return TimeCode(0)
        

    def getNextEvent(self):
        """ Returns the next event item in the list"""
        if (self.next_event < len(self.events)):
            self.next_event += 1
            return self.events[self.next_event - 1]
        else:
            return None


    def getFirstEvent(self):
        """ Retrieve the first event in this list"""
        self.next_event = 0
        if (self.next_event < len(self.events)):
            self.next_event += 1
            return self.events[self.next_event - 1]
        else:
            return None

    def getEventAtTime(self, target_time):
        """Returns the next event AFTER or ON target_time
            Resets the self.next_event index"""
        target = TimeCode(target_time)
        self.next_event = 0
        max_index = len(self.events)

        while (self.next_event < max_index and self.events[self.next_event].time.total_frames < target.total_frames):
            self.next_event += 1

        # Return the result
        if (self.next_event < max_index):
            return(self.events[self.next_event])
        else:
            return(None)

    def removeZeros(self):
        """ removes all channel 0 events (generally not
            a good idea - use for testing only)"""
        i = 0
        while i < len(self.events):
            if self.events[i].channel == 0:
                del self.events[i]
            else:
                i += 1


    def reconcile(self):
        """Sorts list and combines all levels to produce a list of all level 0
        (active control) events.  A ControlList must be reconciled before it can
        be used """
        levelMap = {} #dictionary to keep track of level in this file
        valueMap = {} #dictionary to keep track of pixel values (future)
        currentState = False #Assume an off state initially
        
        #First, create a new result list
        result = ControlList(initializer=self)
 
        #Sort all events (ControlEvents) in time order
        result.sortEvents()

        #Map all existing non-zero levels in this list to determine the number of levels
        for ev in result.events:
            if ev.level > 0 and ev.level not in levelMap:
                #Add this level to the map
                levelMap[ev.level] = 0

        #Start at the beginning and scan the list for non-level-0 events
        for ev in result.events:
            if ev.level > 0:
                # set "value" (future use)
                valueMap[ev.level] = ev.value
            
                #Save the state for this level to the levelMap
                if ev.action == "off":
                    levelMap[ev.level] = 0
                else:
                    levelMap[ev.level] = 1
                
                #Check for a change in state
                tempState = self.mapState(levelMap)
                
                if currentState != tempState:
                    #state has changed! Create a new level 0 event
                    currentState = tempState
                    newEv = ControlEvent()
                    newEv.setValues(level=0,frames=ev.time.total_frames,value=self.mapValue(valueMap),duration=0,channel=ev.channel)
                    if currentState:
                        newEv.action="on"
                    else:
                        newEv.action="off"
                    
                    #append the new event to this list (it's OK, it's level 0 and will be ignored)
                    result.events.append(newEv)
            
        # Now remove all non-level-0 events
        for i in range(len(result.events)):
            while i < len(result.events) and result.events[i].level > 0:
                del result.events[i]
        
        # re-sort the list
        result.sortEvents()
            
        # Filter for redundant events, minimums, and write duration to ON events
        # Normalize for time 0??  (don't allow negative times)
            
        return(result)


    def q_handler(queue):
        """ Handles an "interrupt" by the queue during execute(),
            overlays another list on this one and resets next_item
            to the current execution point"""
        pass


    def execute(self, valve_port, queue_obj=None):
        """Sends these commands in real time via a ValvePort instance"""
        if isinstance(valve_port, ValvePort):
            # Make sure everything is in order
            clr = self.reconcile()
            num_events = len(clr.events)
            
            # Get the current system time.
            start_time = time.time()

            # run until done
            now = TimeCode(0)
            ev = clr.getEventAtTime(0)
            run_it = False

            # danger Will Robinson...
            if queue_obj:
                force_run = True
            else:
                force_run = False
                
            print 'Running (' + str(self.numEvents()) + " events)..."
            
            while (force_run or isinstance(ev, ControlEvent)):
                while (isinstance(ev, ControlEvent) and ev.time <= now):
                    self.keepState(ev)  # keep cur_state up-to-date
                    if (valve_port.setEvent(ev)):
                        run_it = True
                    ev = clr.getNextEvent()

                # Send all changes to the channels and get the current time
                if run_it:
                    valve_port.execute()
                    run_it = False

                # Get the latest time relative to start_time
                now = TimeCode(time.time() - start_time)

                # Check for additions in the queue
                """
                if queue_obj:
                    li = queue_obj.get()
                    if isinstance(li, ControlList):
                        print '\noverlaying new list'
                        self.overlay(li, now)
                        ev = self.getEventAtTime(now) """
                
            print 'Done.'
        else:
            # No valid ValvePort instance passed
            print 'Unable to run this ControlList; invalid ValvePort instance'


    def numEvents(self):
        """ Returns the number of ControlEvents in this list"""
        return len(self.events)

    def scale(self, scale_factor):
        """ Scale the entire list times by a factor """
        self.scale_pending = False

        # reset start time
        now = TimeCode(time.time())
        seq_time = (now.seconds - self.start_time.seconds) * scale_factor # in seconds (float)
        now.addTime(0.0 - seq_time) # subtract seq_time
        self.start_time.setTime(now)

        # scale the list
        for ev in self.events:
            ev.time.setTime(ev.ref_time.seconds * scale_factor)

        self.beat_period.setTime(self.ref_beat_period.seconds * scale_factor)
        self.first_beat.setTime(self.ref_first_beat.seconds * scale_factor)
        



    def scaleToBeat(self, beatperiod, beatObject = None):
        """ calculates a scaling rate based on the target beat period
            then scales the sequence accordingly """
        if isinstance(beatperiod, TimeCode):
            period = beatperiod
            self.sync_period = beatperiod.getSeconds() 
        else:
            period = TimeCode(beatperiod)
            self.sync_period = beatperiod  # danger! assumes a float!

        self.sync_object = beatObject # object for perpetual resynching (optional)

        if self.ref_beat_period.total_frames > 0:
            scale_factor = period.seconds / self.ref_beat_period.seconds
            self.scale(scale_factor)

            
    def scaleOnNext(self, scale_factor):
        """ Save the scale factor and scale on next getNextByXXXX() call.
            Prevents conflicting scaling and sequence execution """
        self.scale_factor = scale_factor
        self.scale_pending = True

    def useCurrent(self):
        """ Updated 7/2012. The purpose is to make the sequence play at a default
            rate.  Previously, this was done by setting all the reference times to
            the current scaled time.  since the action is typically to speed up the
            sequence this is now done by simply setting scale_pending to True so that
            when re-run (such aa after a pickle save) the object will automatically
            scale to the saved scale_factor. """
        """
        for ev in self.events:
            ev.ref_time.setTime(ev.time)
        self.ref_beat_period.setTime(self.beat_period)
        self.ref_first_beat.setTime(self.first_beat)
        self.scale_factor = 1.0
        self.scale_pending = False
        """
        self.scale_pending = True
            

    def keepState(self, eventObj):
        """ maintains the cur_state array so the sequence can be
            stopped without having cannons firing """
        if eventObj.action == "on":
            self.cur_state[eventObj.channel] += 1
        elif eventObj.action == "off":
            self.cur_state[eventObj.channel] -= 1
            if self.cur_state[eventObj.channel] < 0:
                self.cur_state[eventObj.channel] = 0


    def start(self, starttime=None):
        """ Marks the start time of the sequence.  Call this before
            subsequent calls to getNextByTime() """
        if starttime == None:
            self.start_time.setTime(time.time())  # use system time
        else:
            self.start_time.setTime(starttime) # use passed time

        self.next_event = 0
        self.eof = False   # for end of sequence reporting in getNextByXXXX


    def stop(self):
        """ Stop() moves the next_event pointer past the end of the events list
            cleanup is done in the getNextEventByTime call """
        self.next_event = len(self.events) + 100
        

    def getNextByTime(self, timenow=None):
        """ Returns either an event to execute if it's due now or None if no events are due """
        #scale the sequence
        if self.scale_pending == True:
            self.scale(self.scale_factor)

        # check if we're at the end
        if self.next_event < len(self.events):
            # is the next item "due"?
            if timenow == None:
                now = TimeCode(time.time()) - self.start_time
            else:
                now = TimeCode(timenow) - self.start_time

            evnext = self.events[self.next_event]
            
            if evnext.time <= now:
                self.next_event += 1
                self.keepState(evnext)  #keep the cur_state array up to date

                # check for looping
                if self.looping == True and self.next_event == len(self.events):
                    #set the start to the end of the last loop 
                    newstart = TimeCode(self.start_time + evnext.time)

                    # perpetual resynching
                    if self.sync_object != None:
                        if self.sync_object.isSimilarTo(self.sync_period): # did timing on sync object change?
                            newstart.setTime(TimeCode(self.sync_object.getCorrectedBeatTime(newstart.getSeconds())))
                        else:
                            print "Dropping sync object - timing changed"
                            self.sync_object = None  # disengage from synch

                    self.start(newstart.seconds) # in any case, load new start time
                return evnext
            else:
                #print str(now) + ">>" + str(evnext.time) + " - " + str(self.next_event) + ":" + str(len(self.events))
                return False
        else:
            #at end of sequence... is there any cleanup needed?
            if sum(self.cur_state) == 0:            
                #report end of sequence
                try:
                    if self.eof == False:
                        self.eof = True
                        return True
                    else:
                        return False
                except:
                    print "NO EOF IN " + self.name
                    return False
            else:
                # return a cleanup event
                newEv = False
                for i in range(max_channels + 1):
                    if self.cur_state[i] > 0:
                        newEv = ControlEvent()
                        newEv.setValues(level=0,frames=0,value=0,duration=0,channel=i)
                        self.keepState(newEv)
                        self.cleanup.append(newEv)
                        break
                return newEv  # may be "False"
        

    def atEnd(self):
        """ Returns True if at end of sequence AND all cleanup done """
        if self.next_event < len(self.events) or sum(self.cur_state) > 0:
            return False
        else:
            return True
            
            
    def running(self):
        """ Returns True if not yet at end of sequence, else False
            Does not consider cleanup events "running" """
        if self.next_event < len(self.events):
            return True
        else:
            return False

    def stopSynching(self):
        """ stop synching with beat object. call when usebeat is off """
        self.sync_object = None

    def saveXML(self, file_path):
        """ Save and XML representation of this object """
        root = ET.Element("ControlList")

        root.set("deflevel", str(self.deflevel))
        root.set("defchannel", str(self.defchannel))
        root.set("name", str(self.name))
        root.set("looping", str("True" if self.looping else "False"))
        root.set("scale_factor", str(self.scale_factor))
        root.set("scale_pending", "True" if self.scale_pending else "False")
        root.set("ref_beat_period", str(self.ref_beat_period.seconds))
        root.set("ref_first_beat", str(self.ref_first_beat.seconds))
        root.set("beat_period", str(self.beat_period.seconds))
        root.set("first_beat", str(self.first_beat.seconds))
        root.set("version", "1.2")

        # load events
        events = ET.SubElement(root, "events")
        for ev in self.events:
            ev.getXMLElement(events)

        #save file
        tree = ET.ElementTree(root)
        tree.write(file_path)
                 

    def loadXML(self, file_path):
        """ reads a control list in from an XML file """
        try:
            tree = ET.parse(file_path)
        except Exception as e:
            # TODO: make below log to a logger file
            print "Not a valid ControlList XML file"
            return

        root = tree.getroot()
        self.deflevel = int(root.get("deflevel", 0))
        self.defchannel = int(root.get("defchannel", 0))
        self.name = root.get("name", "")
        self.looping = True if root.get("looping", "False") == "True" else False
        self.scale_factor = float(root.get("scale_factor"))
        self.scale_pending = True if root.get("scale_pending", "False") == "True" else False
        self.ref_beat_period.setTime(float(root.get("ref_beat_period", "0.0")))
        self.ref_first_beat.setTime(float(root.get("ref_first_beat")))
        self.beat_period.setTime(float(root.get("beat_period")))
        self.first_beat.setTime(float(root.get("first_beat")))

        
        # get events
        del self.events[:]  # clear any exiting events
        self.events = []

        events = root.find("events")
        if events != None:
            ev_list = events.findall("event")
            for ev in ev_list:
                self.events.append(ControlEvent(ev))
        
            

#***************** ValvePort *****************************
    
class ValvePort(object):
    """Abstracts the interface between the ControlEvent class and the
       physical valve.  This may use a parallel port or it may use a
       serial port to intelligent controllers.  In general this should
       operate by passing ControlEvent instances to the execute() method,
       but manual controls are also provided"""

    def __init__(self, channels=24, channelsperbank=6):
        self.num_channels=channels
        self.channelsPerBank=channelsperbank
        self.channel_map = None

        #Create an arrary with the correct number of channels
        self.channels = [0] * self.num_channels

        #execstate stores the state of the valves since the last execute
        self.execstate = [0] * self.num_channels
        
        #Turn all channels off
        self.reset();

        #Set the exec state so the reset is performed
        for i in range(0, self.num_channels):
            self.execstate[i] = 1

    def setMap(self, channel_map=None):
        """ defines a channel map for remapping the output of this port """
        self.channel_map = channel_map


    def setChannel(self, channel, value):
        """Sets a channel to OFF (value=0) or ON (value=non-0).
           Increments a count with each "ON".  Decrements with
           each "OFF".  Use execute() to write the changes to the
           channels"""
        if self.channel_map != None:
            channel = self.channel_map.lookup(channel)

        if channel > 0 and channel <= self.num_channels:
            if value > 0:
                self.channels[channel-1] += 1
            else:
                self.channels[channel-1] -= 1 
                if self.channels[channel-1] < 0:
                    self.channels[channel-1] = 0
            return True
        else:
            return False


    def setEvent(self, event):
        """Set a channel by a ControlEvent event. Maintains
            a count which would """
        if isinstance(event, ControlEvent):
            if self.channel_map != None:
                channel = self.channel_map.lookup(event.channel)
            else:
                channel = event.channel

            if channel > 0 and channel <= self.num_channels:
                if event.action == "on":
                    self.channels[channel-1] += 1
                else:
                    self.channels[channel-1] -= 1
                    if self.channels[channel-1] < 0:
                        self.channels[channel-1] = 0
                return True
            else:
                return False


    def oneChannel(self, channel, value=1):
        """Sets ONE channel ON (default), all others off
           Use execute() to write the changes to the channels"""
        if self.channel_map != None:
            channel = self.channel_map.lookup(channel)

        #set all channels to OFF
        for i in range(0, self.num_channels):
            self.channels[i]=0

        # Set this channel to VALUE
        if channel > 0 or channel <= self.num_channels:
            self.channels[channel-1]=value
            return True
        else:
            return False


    def execute(self):
        """Write the current (internal) state of the channels
            to the output device.  Use setChannel() or
            setEvent() to update channel state before executing."""

        # update the exec state (after sending to output)
        for i in range(0, self.num_channels):
            self.execstate[i] = self.channels[i]


    def reset(self):
        """ Clears all channels and sends to the hardware"""
        #set all channels to OFF
        for i in range(0, self.num_channels):
            self.channels[i]=0

        self.execute()


    def all_on(self):
        """Sets all channels on and writes to the hardware"""
        #set all channels to ON
        for i in range(0, self.num_channels):
            self.channels[i]=1

        self.execute()


    def setChannelExec(self, channel, value):
        """Changes the state of one channel and sends the change
            immediately to the channel device"""
        if self.channel_map != None:
            channel = self.channel_map.lookup(channel)

        if (self.setChannel(channel, value)):
            self.execute()
            return True
        else:
            return False


    def setEventExec(self, event):
        """Changes the state of one channel and sends the change
            immediately to the channel device"""
        if(self.setEvent(event)):
            self.execute()
            return True
        else:
            return False


    def oneChannelExec(self, channel, value=1):
        """Changes the state of one channel clearing all others
            immediately to the channel device"""
        if self.channel_map != None:
            channel = self.channel_map.lookup(channel)

        if (self.oneChannel(channel, value)):
            self.execute()
            return True
        else:
            return False



#***************** ValvePort_GUI *************************
    
class ValvePort_GUI(ValvePort):
    """GUI display implementation of ValvePort class.  Displays the
    valve action as "lights" on a BitmapCanvas object """

    def __init__(self, channels=24, channelsperbank=6, canvas=None):
        ValvePort.__init__(self, channels, channelsperbank)
        self.canvas = canvas
        self.lights = [(0,0)] * channels
        for i in range(0, channels):
            self.lights[i] = (25 * 1, 0)

    def execute(self):
        """Display the output of the sequence on a bitmap canvase"""
        for i in range(0, self.num_channels):
            if self.execstate[i] != self.channels[i]:
                if self.channels[i] > 0:
                    self.canvas.fillColor=(255,20,20)
                else:
                    self.canvas.fillColor=(100,100,100)
                    
                self.canvas.drawEllipse(self.lights[i],(20,20))

        # set the exec state array
        ValvePort.execute(self)

    def set_light(self, channel, position):
        """channel number starting at 0; position is a typle of x,y"""
        #if self.channel_map != None:
        #    channel = self.channel_map.reverseLookup(channel)

        if channel <= self.num_channels and channel > 0:
            self.lights[channel - 1] = position        
       
        


#***************** ValvePort_Parallel *************************
    
class ValvePort_Parallel(ValvePort):
    """Parallel port implementation of ValvePort classe
        this was used in the original Parable versions """

    def __init__(self, channels=22, channelsperbank=6):
        try:
            self.py = parallel.Parallel()
        except:
            print "Unable to open parallel port"
            self.py = None
            
        ValvePort.__init__(self, channels, channelsperbank)
        """
        self.num_channels=channels;
        self.channelsPerBank=channelsperbank
        self.channels = [0] * self.num_channels
        self.reset();
        """

    """
    def setChannel(self, channel, value):
        #Sets a channel to OFF (value=0) or ON (value=non-0).
        #   Increments a count with each "ON".  Decrements with
        #   each "OFF".  Use execute() to write the changes to the
        #   channels
        if self.channel_map != None:
            channel = self.channel_map.lookup(channel)

        if channel > 0 and channel <= self.num_channels:
            if value > 0:
                self.channels[channel-1] += 1
            else:
                self.channels[channel-1] -= 1 
                if self.channels[channel-1] < 0:
                    self.channels[channel-1] = 0
            return True
        else:
            return False
    """

    """
    def setEvent(self, event):
        #Set a channel by a ControlEvent event. Maintains
        #    a count which would 
        if isinstance(event, ControlEvent):
            if self.channel_map != None:
                channel = self.channel_map.lookup(event.channel)
            else:
                channel = event.channel

            if channel > 0 and channel <= self.num_channels:
                if event.action == "on":
                    self.channels[channel-1] += 1 
                else:
                    self.channels[channel-1] -= 1 
                    if self.channels[channel-1] < 0:
                        self.channels[channel-1] = 0
                return True
            else:
                return False
    """
    """
    def oneChannel(self, channel, value=1):
        #Sets ONE channel ON (default), all others off
        #   Use execute() to write the changes to the channels
        if self.channel_map != None:
            channel = self.channel_map.lookup(channel)

        #set all channels to OFF
        for i in range(0, self.num_channels):
            self.channels[i]=0

        # Set this channel to VALUE
        if channel > 0 or channel <= self.num_channels:
            self.channels[channel-1]=value
            return True
        else:
            return False
    """

    def execute(self):
        """Write the current (internal) state of the channels
            to the channels themselves.  Use setChannel() or
            setEvent() to update channel state before sending
            to the ports."""
        data = 0
        base_channel = 0 # first channel for this bank
        
        #how many banks need to be updated?
        banks = self.num_channels // self.channelsPerBank
        for bk in range(0, banks):  # bank number, 0-based
            base_channel = self.channelsPerBank * bk
            data = 0

            # update each channel in the bank
            for ch in range (0, self.channelsPerBank):
                chnl = ch + base_channel # get channel number, 0-based
                if self.channels[chnl] > 0:
                    #Write a bit to data
                    data |= operator.lshift(1, ch)

            if (self.py != None):
                self.py.setData(data | (bk << 6))
                self.py.setDataStrobe(0)
                self.py.setDataStrobe(0)            
                self.py.setDataStrobe(1)
#               print 'Data written: %2.2X' % (data | (bk << 7))
        
        #FUTURE: update the prev_channels array to keep track of changes

    """
    def reset(self):
        #Clears all channels and sends to the hardware
        #set all channels to OFF
        for i in range(0, self.num_channels):
            self.channels[i]=0

        self.execute()
    """

    """
    def all_on(self):
        #Sets all channels on and writes to the hardware
        #set all channels to ON
        for i in range(0, self.num_channels):
            self.channels[i]=1

        self.execute()
    """
    """
    def setChannelExec(self, channel, value):
        #Changes the state of one channel and sends the change
        #   immediately to the channel device
        if (self.setChannel(channel, value)):
            self.execute()
            return True
        else:
            return False
    """
    """
    def setEventExec(self, event):
        #Changes the state of one channel and sends the change
        #    immediately to the channel device
        if(self.setEvent(event)):
            self.execute()
            return True
        else:
            return False
    """
    """
    def oneChannelExec(self, channel, value=1):
        #Changes the state of one channel clearing all others
        #    immediately to the channel device
        if (self.oneChannel(channel, value)):
            self.execute()
            return True
        else:
            return False
    """



#***************** ValvePort_Beep *************************
class ValvePort_Beep(ValvePort):
    def __init__(self, channels=24, channelsperbank=6):
        self.mute = False  # don't produce an output
        ValvePort.__init__(self, channels, channelsperbank)
        
                 
    def execute(self):
        """Display the output of the sequence on a bitmap canvase"""
        if self.mute == False:
            for i in range(0, self.num_channels):
                if self.execstate[i] != self.channels[i]:
                    if self.channels[i] > 0:
                        winsound.Beep(440, 1)

        # set the exec state array
        ValvePort.execute(self)



#*********************** ValvePortBank ****************************
    
class ValvePortBank(ValvePort):
    """ This is a container class for one or more ValvePort instances.
        This allows multiple outputs to be written the sequence.  It
        masquerades as a single ValvePort since that's how it's intended
        to work """

    def __init__(self, channels=22, channelsperbank=6):
        self.numports = 0
        self.ports = []

    def addPort(self, port):
        """ Add a ValvePort object to the list """
        if isinstance(port, ValvePort):
            self.ports.append(port)
            self.numports += 1

    def setChannel(self, channel, value):
        """Sets a channel to OFF (value=0) or ON (value=non-0).
           Increments a count with each "ON".  Decrements with
           each "OFF".  Use execute() to write the changes to the
           channels"""
        for i in range(self.numports):
            self.ports[i].setEvent(channel, value)
        return True

    def setEvent(self, event):
        for i in range(self.numports):
            self.ports[i].setEvent(event)
        return True

    def oneChannel(self, channel, value=1):
        """Sets ONE channel ON (default), all others off
           Use execute() to write the changes to the channels"""
        for i in range(self.numports):
            self.ports[i].oneChannel(channel, value)
        return True

    def execute(self):
        """ executes all ports in the bank """
        for i in range(self.numports):
            self.ports[i].execute()

    def reset(self):
        """ Clears all channels and sends to the hardware"""
        for i in range(self.numports):
            self.ports[i].reset()

    def all_on(self):
        """Sets all channels on and writes to the hardware"""
        for i in range(self.numports):
            self.ports[i].all_on()

    def setChannelExec(self, channel, value):
        """Changes the state of one channel and sends the change
            immediately to the channel device"""
        for i in range(self.numports):
            self.ports[i].oneChannelExec(channel, value)
        return True

    def setEventExec(self, event):
        """Changes the state of one channel and sends the change
            immediately to the channel device"""
        for i in range(self.numports):
            self.ports[i].setEventExec(event)
        return True

    def oneChannelExec(self, channel, value=1):
        """Changes the state of one channel clearing all others
            immediately to the channel device"""
        for i in range(self.numports):
            self.ports[i].oneChannelExec(channel, value)
        return True





#********************************************************
# These are functions used for testing and running shows
#********************************************************

def kill():
    vp = ValvePort(channels=12)
    vp.reset()    


def run(control_list, vp=None):
    """Runs a control list in real time,
        sending commands to the port hardware"""
#    print control_list
    if vp == None:
        vp = ValvePort(channels=12)

    try:
        control_list.execute(vp)
    except:
        vp.reset()
        print 'Reset on exception.'
    vp.reset()
    return None


def rsweep(step_period, pulse_duration):
    """ Creates and runs a left-to-right monotonic sweep"""
    cl = ControlList()
    ev_time = TimeCode(0)
    duration = TimeCode(pulse_duration)
    period = TimeCode(step_period)
    
    for i in range(1, 13):
        ev = ControlEvent(channel=i, action='on', time=ev_time, duration=0, \
                         value=1, level=0)
        cl.addEvent(ev)
        ev.time.addTime(duration)
        ev.action='off'
        cl.addEvent(ev)

        ev_time.addTime(period)
        
    cl.sortEvents()
    return (cl)


def lsweep(step_period, pulse_duration):
    """ Creates and runs a left-to-right monotonic sweep"""
    cl = ControlList()
    ev_time = TimeCode(0)
    duration = TimeCode(pulse_duration)
    period = TimeCode(step_period)
    
    for i in range(1, 13):
        ev = ControlEvent(channel=13-i, action='on', time=ev_time, duration=0, \
                         value=1, level=0)

        # Append ON and OFF events
        cl.addEvent(ev)
        ev.time.addTime(duration)
        ev.action='off'
        cl.addEvent(ev)
        
        ev_time.addTime(period)

    cl.sortEvents()
    return (cl)


def pause(duration=30):
    """ Creates a pause in which all channels are off for duration """
    cl = ControlList()
    dur = TimeCode(duration)
    ev = ControlEvent(channel=0, action='off', time=0, duration=0, \
                     value=1, level=0)    
    for i in range(1, 13):
        ev.channel = i
        cl.addEvent(ev)

    # Add dummy placekeeper event (NOOP) 
    ev.channel=0
    ev.time.setTime(dur)
    cl.addEvent(ev)

    cl.sortEvents()
    return (cl)


def beep(chanl, duration=12, pause=0, start_time=0, level=0, sequence=0):
    """ Opens one channel for duration """
    cl = ControlList()
    start = TimeCode(start_time)
    end = TimeCode(start_time + duration)
    paus = TimeCode(pause)

    # Add ON event
    ev = ControlEvent(channel=chanl, action='on', time=start, duration=duration, \
                     value=1, level=level, sequence=sequence)    
    cl.addEvent(ev)

    # Add OFF event
    ev.action='off'
    ev.time.setTime(end)
    cl.addEvent(ev)

    # Add pause events if pause is set
    if paus.total_frames > 0:
        ev.channel = 0
        cl.addEvent(ev)
        ev.time = TimeCode(end.total_frames + paus.total_frames)
        cl.addEvent(ev)
    
    cl.sortEvents()
    return (cl)


def rand_beep(duration=1, pause=0, start_time=0, level=0, sequence=0):
    ch = random.randint(1, 12)
    return(beep(ch, duration, pause, start_time, level, sequence))


def bang(duration=12):
    """ Opens all channels simultaneously for duration """
    cl = ControlList()
    zero = TimeCode(0)
    dur = TimeCode(duration)

    # Add ON events
    ev = ControlEvent(channel=0, action='on', time=0, duration=0, \
                     value=1, level=0)    
    for i in range(1, 13):
        ev.channel = i
        cl.addEvent(ev)

    # Add OFF events
    ev.action='off'
    ev.time.setTime(dur)

    for i in range(1, 13):
        ev.channel = i
        cl.addEvent(ev)
    
    cl.sortEvents()
    return (cl)


def whizbang(stage_right=False):
    """ Makes a right-to-left sweep, then BANG BANG BANG BANG! """
    # Bang:
    cl1 = bang(4)
    cl1.append(pause(5))
    # Whiz:
    if stage_right:
        cl = rsweep(3, 8)
    else:
        cl = lsweep(3, 8)
        
    cl.append(pause(13))
    # Whiz + four bangs:
    cl.append(cl1)
    cl.append(cl1)
    cl.append(cl1)
    cl.append(cl1)

    cl.sortEvents()
    return(cl)


def fourbang(level=0, sequence=0):
    """ For random bangs in quick succession"""

    cl = ControlList()
    ev = ControlEvent(channel=0, action='on', time=0, duration=0, \
                     value=1, level=level, sequence=sequence)    

    # Add four 
    for i in range(4):
        ch = random.randint(1, 12)
        li = beep(ch, 2, 1, level=level, sequence=sequence)
        cl.append(li)
        
    cl.sortEvents()
    return (cl)
        

def foursweep(level=0, sequence=0):
    """ A sweep of four beeps in quick succession starting at a random point"""
    cl = ControlList()

    # Pick a starting point and direction (increment value)
    incr = random.choice((-1, 1))
    start = random.randint(1, 12)
    if (incr < 0 and start < 4):
        incr = 1
    elif (incr > 0 and start > 9):
        incr = -1
    
    # set up first ControlEvent
    ch = start
    
    # Add four 
    for i in range(4):
        li = beep(ch, 2, 1, level=level, sequence=sequence)
        cl.append(li)
        ch += incr
        
    cl.sortEvents()
    return (cl)
        

def w(num_channels=12, level=0, sequence=0):
    """Two alternating sweeps from the center out"""
    cl = ControlList()
    beep_length = 3  # how long the beep lasts (frames)
    beep_period = 2  # how long between channels (frames)
    beep_time = 0
    
    left = num_channels // 2
    if num_channels % 2 == 0:
        # no middle channel
        middle = 0
        right = left + 1
    else:
        # middle channel
        middle = num_channels / 2
        right = left + 2

    # add middle channel
    if (middle > 0):
        li = beep(middle, duration=beep_length, start_time=beep_time)
        beep_time += beep_period
        cl.append(li)

    # add sequences
    while left > 0:
        li = beep(left, duration=beep_length, start_time=beep_time)
        cl.append(li)
        li = beep(right, duration=beep_length, start_time=beep_time)
        cl.append(li)
        
        beep_time += beep_period
        left -= 1
        right += 1

    # sort and finish
    cl.sortEvents()
    return (cl)

    

def v(num_channels=12, dur=4, per=2, level=0, sequence=0):
    """Two concurrent sweeps from the center out"""
    cl = ControlList()
    beep_length = dur  # how long the beep lasts (frames)
    beep_period = per  # how long between channels (frames)
    beep_time = 0
    
    left = num_channels // 2
    if num_channels % 2 == 0:
        # no middle channel
        middle = 0
        right = left + 1
    else:
        # middle channel
        middle = num_channels / 2
        right = left + 2

    # add middle channel
    if (middle > 0):
        li = beep(middle, duration=beep_length, start_time=beep_time, level=level, sequence=sequence)
        beep_time += beep_period
        cl.overlay(li)

    # add sequences
    while left > 0:
        li = beep(left, duration=beep_length, start_time=beep_time, level=level, sequence=sequence)
        cl.overlay(li)
        li = beep(right, duration=beep_length, start_time=beep_time, level=level, sequence=sequence)
        cl.overlay(li)
        
        beep_time += beep_period
        left -= 1
        right += 1

    # sort and finish
    cl.sortEvents()
    return (cl)


def swing():
    cl = lsweep(3, 2)
    cl.append(rsweep(3, 2))
    cl.append(pause(10))
    cl.append(bang(8))
    return(cl)


def randy(iterations, num_channels=12, beep_dur=3, per=2, level=0, sequence=0):
    """randomly fires the cannons"""
    cl = ControlList()
    start = 0
    for i in range(0, iterations):
        ch = random.randint(1, num_channels)
        ev = beep(ch, duration=beep_dur, start_time=start, level=level)
        cl.overlay(ev)
        start += random.randint(0, per)

    cl.sortEvents()
    return(cl)


def flying_v(iterations):
    """Combines V with randy"""
    cl = randy(iterations, level=1)
    cl.overlay(v(dur=200, per=30, level=2))
    return(cl.reconcile())


def los_endos():
    cl = rsweep(2, 2)
    cl.append(lsweep(2,2))
    cl.overlay(w(), TimeCode(0))
    point = cl.append(v())
#    print "Point: %s" % point.__str__()
#    li = randy(200)
#    li.offsetTime(point.total_frames + 8)
#    cl.overlay(li)
    cl.overlay(randy(200), point.total_frames + 8)
    cl.overlay(v(dur=10, per=2), point.total_frames + 90)
#    cl.overlay(foursweep(), TimeCode(45))
#    cl.overlay(foursweep(), TimeCode(60))
    cl.append(pause(90))
    cl.append(bang(10))
    cl.append(pause(4))
    cl.append(bang(10))
    cl.append(pause(4))
    cl.append(bang(10))
    cl.append(pause(4))
    cl.append(bang(10))
    return(cl)

def pair1():
    cl = beep(1, 2)
    cl.overlay(beep(3, 2))
    return(cl)

def pair2():
    cl = beep(3, 2)
    cl.overlay(beep(5, 2))
    return(cl)

def pair3():
    cl = beep(5, 2)
    cl.overlay(beep(7, 2))
    return(cl)

def pair4():
    cl = beep(7, 2)
    cl.overlay(beep(9, 2))
    return(cl)

def pair5():
    cl = beep(9, 2)
    cl.overlay(beep(11, 2))
    return(cl)

def spiral(iterations=0, channels=12, dur=2, start_per=12, end_per=1, accel=1):
    ch = channels
    num_loops = iterations
    period = start_per
    
    if num_loops == 0:
        num_loops = (start_per - end_per) // accel
    
    cl = beep(ch, dur, period)
    for i in range(1, num_loops - 1):
        ch -= 1
        if ch <= 0:
            ch = channels

        period -= accel
        if period < end_per:
            period = end_per
            
        cl.append(beep(ch, dur, period))

    return(cl)


def blow():
    cl = bang(5400)
    return(cl)


def runit():
    for i in range(1, 1000):
        v.all_on()
        v.reset()



def go(vp, queue_obj):
    print 'ENTERING GO\n'
    cl = ControlList()

    cl.execute(vp, queue_obj)
    print '\nLEAVING GO\n'
    return None


def new_main():
    running = True
    q = Queue(32)
    vp = ValvePort(channels=12)

#    print 'Preparing lists...'
#    clV = v()
#    clW = w()
#    clFLYINGV = flying_v(200)
#    clRANDY = randy(300)
#    clBANG = bang(10)
#    clLSWEEP = lsweep(2, 3)
#    clRSWEEP = rsweep(2, 3)
#    clLSWEEP2 = lsweep(1, 3)
#    clRSWEEP2 = rsweep(1, 3)
#    clWHIZBANG = whizbang()
#    clPAIR1 = pair1()
#    clPAIR2 = pair2()
#    clPAIR3 = pair3()
#    clPAIR4 = pair4()
#     clPAIR5 = pair5()
   
    # start playback thread
    th = threading.Thread(target=go, args=(vp, q,))
    th.setDaemon(True)
    th.start()

    while running:
        seq = raw_input('sequence: ')
        if seq == 'x':
            running = False
        else:
            if seq == "v":
                q.put(clV)
            elif seq == "f":
                run(foursweep())
            elif seq == "1":
                run(clPAIR1)
            elif seq == "2":
                run(clPAIR2)
            elif seq == "3":
                run(clPAIR3)
            elif seq == "4":
                run(clPAIR4)
            elif seq == "5":
                run(clPAIR5)
            elif seq == "fb":
                run(fourbang())
            elif seq == "w":
                q.put(clW)
            elif seq == ".":
                run(rand_beep(2))
            elif seq == "fv":
                q.put(clFLYINGV)
            elif seq == "r":
                q.put(clRANDY)
            elif seq == " ":
                q.put(clBANG)
            elif seq == "<":
                q.put(clLSWEEP)
            elif seq == ">":
                q.put(clRSWEEP)
            elif seq == "<<":
                q.put(clLSWEEP2)
            elif seq == ">>":
                q.put(clRSWEEP2)
            elif seq == "wb":
                q.put(clWHIZBANG)
            elif seq == "x":
                running = False
                print 'Terminated'
            else:
                print 'Unknown sequence use v w . fv ? < >' 

    print '\nwaiting for thread to finish'
    th.join()
    print 'Done'
    return None
    
    
    

def main():
    vp = ValvePort(channels=12)

#    print 'Preparing lists...'
#    clV = v()
#    clFOURSWEEP = foursweep()
#    clFOURBANG = fourbang()
#    clW = w()
#    clRANDBEEP = rand_beep(2)
#    clFLYINGV = flying_v(200)
#    clRANDY = randy(300)
#    clBANG = bang(10)
#    clLSWEEP = lsweep(3, 3)
#    clRSWEEP = rsweep(3, 3)
#    clLSWEEP2 = lsweep(1, 2)
#    clRSWEEP2 = rsweep(1, 2)
#    clWHIZBANG = whizbang()
#    clWHIZBANGR = whizbang(True)
#    clBLOW = blow()
#    clLOSENDOS = los_endos()
#    clPAIR1 = pair1()
#    clPAIR2 = pair2()
#    clPAIR3 = pair3()
#    clPAIR4 = pair4()
#    clPAIR5 = pair5()
#    clSPIRAL = spiral(120)
#    clSWING = swing()

   
    running = True
    while running:
        seq = raw_input("sequence: ")
        if seq == "v":
            run(clV, vp)
        elif seq == "f":
            run(foursweep(), vp)
        elif seq == "fb":
            run(fourbang(), vp)
        elif seq == "1":
            run(clPAIR1)
        elif seq == "2":
            run(clPAIR2)
        elif seq == "3":
            run(clPAIR3)
        elif seq == "4":
            run(clPAIR4)
        elif seq == "5":
            run(clPAIR5)
        elif seq == "w":
            run(clW, vp)
        elif seq == ".":
            run(rand_beep(2), vp)
        elif seq == "fv":
            run(clFLYINGV, vp)
        elif seq == "r":
            run(clRANDY, vp)
        elif seq == "s":
            run(clSPIRAL, vp)
        elif seq == " ":
            run(clBANG, vp)
        elif seq == "r":
            run(randy(50, beep_dur=1), vp)
        elif seq == "<":
            run(clLSWEEP, vp)
        elif seq == ">":
            run(clRSWEEP, vp)
        elif seq == "<<":
            run(clLSWEEP2, vp)
        elif seq == ">>":
            run(clRSWEEP2, vp)
        elif seq == "wb":
            run(clWHIZBANG, vp)
        elif seq == "wbl" or seq == "wbr":
            run(clWHIZBANGR, vp)
        elif seq == "le":
            run(clLOSENDOS, vp)
        elif seq == "blow":
            run(clBLOW, vp)
        elif seq == "sw":
            run(clSWING, vp)
        elif seq == "xx":
            running = False
            print 'Terminated'
        else:
            print 'Unknown sequence use v f fb w . <sp> fv ? < > << >> 1-5  '
            
    

cl1 = ControlList()
cl1.addEvent(ControlEvent(channel=1,value=1,level=1,time=6,action="off"))
cl1.addEvent(ControlEvent(channel=1,value=1,level=2,time=5,action="on"))
cl1.addEvent(ControlEvent(channel=1,value=1,level=1,time=4,action="on"))

if __name__ == "main":
    main()


            
# Initializing a ControlList with another ControlList does not work
# Make sure to preserve all channel-0 as these may be time-keeper NOOPs
# Adding TimeCode objects does not return a TimeCode object (doesn't work)
# overlay() sorts list each time.  May not be wanted always
# first event played back (usually ch0) does not clear out - maybe it's getting a count > 1
# make control list a proper iterator

