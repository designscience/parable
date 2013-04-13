""" ************************************************************
Sequence Import Library for Parable Sequencing Program
Author: Stu D'Alessandro

Contains classes used to import sequences from graphic files and
other sources for use with the Parable program.

version 1.01 - added support for channel map passed to import functions
(this had been an unimplemented stub to-date)

************************************************************ """

from __future__ import division
import os, sys
import time
from PIL import Image
import parclasses


#*********************** GraphicImport ****************************
    
class GraphicImport(object):
    """ Imports a sequence from a graphic file """
    def __init__(self):
        object.__init__(self)
        pass

    def import_sequence(self, filename, numchannels, spacing, beattrackpos=250, channelmap=None, filtrobj=None):
        """ Opens a graphic file (jpg, gif) and imports a sequence.
            Returns a ControlList object
            filename: graphic file path
            numchannels: number of channels to import
            spacing: pixels between channels and first ch offset
            beattrackpos: horiz position of beat track (0 means no beat track)
            channelmap: channel mapping object
            filterobj: filter object (future) """

        result = parclasses.ControlList()
        ev = parclasses.ControlEvent()
        first_beat = False
        beat = False  # start with beat off
        beat_time = parclasses.TimeCode(0)
        beat_periods = []  # periods for averaging
        first_pos = int(spacing / 2)

        # open source image file  @@@ some error checking here @@@
        im = Image.open(filename)
        if im.format != "JPEG":
            print "Please use a JPG image file"
        else:
            print "Opening image for sequence import..."
            print "Width: " + str(im.size[0]) + "  Height: " + str(im.size[1])
            if channelmap != None:
                print "Using channel map"

            name = filename.rpartition('\\')[2]
            name = name.rpartition('.')[0]
            result.name = name

            state = [0] * numchannels  # current state of the channels

            # read grapic into a buffer
            buf = im.load()

            # display column, xposition and channel map (test)
            for colx in range(numchannels):
                if channelmap == None:
                    ch = colx + 1
                else:
                    ch = channelmap.lookup(colx + 1)
                print "colx:" + str(colx) + "  posx:" + str((colx + 1) * spacing) + "  ch:" + str(ch)

            # read in graphic lines
            start = parclasses.TimeCode(time.time())  # calc processing time
            for line in range(im.size[1]):
                for colx in range(numchannels):
                        if channelmap == None:
                            ch = colx
                        else:
                            ch = channelmap.lookup(colx + 1) - 1  #lookup then make 0-based
                            if ch < 0 or ch >= numchannels:
                                break
                        
                        val = buf[(colx + 1) * spacing, line] # first method
                        #val = buf[(ch * spacing) + first_pos, line]  # updated method
                        newval = int(val[0])
                        #print str(newval) + " ",  # warning slow!
                        #print str((ch + 1) * spacing) + " ",  # warning slow!
                        #print str(line) + " " + str(ch) + " | ", # warning slow!

                        # if the state has changed, create an event object
                        newstate = state[ch]
                        if newval > 153 and state[ch] == 0:
                            newstate = 1
                            newaction = "on"
                        elif newval < 118 and state[ch] == 1:
                            newstate = 0
                            newaction = "off"

                        if (state[ch] != newstate):                  
                            ev.setValues(line,0,ch+1,newaction,0,newval)
                            result.addEvent(ev)
                            state[ch] = newstate

                # read in beat track
                if beattrackpos > 0:
                    val = buf[beattrackpos, line]
                    newbeat = int(val[0]) > 153
                    if beat != newbeat:
                        beat = newbeat
                        if newbeat == True:
                            if first_beat == False:
                                first_beat = True
                                beat_time = parclasses.TimeCode(line)
                                result.first_beat = beat_time
                                result.ref_first_beat = parclasses.TimeCode(beat_time) # @@@ added contructor instead of reusing beat_time
                            else:
                                # Maintain running average
                                beat_periods.append(parclasses.TimeCode(line) - beat_time)
                                beat_time = parclasses.TimeCode(line)


            
            # calculate beat period
            if first_beat == True:
                print "Calculating beat..."
                avg_beat = 0
                for tc in beat_periods:
                    avg_beat += tc.total_frames

                if len(beat_periods) > 0:
                    avg_beat = avg_beat / len(beat_periods)
                beat_period = parclasses.TimeCode(long(avg_beat))
                
                # set current and reference beat periods
                result.beat_period = beat_period
                result.ref_beat_period = parclasses.TimeCode(beat_period) # @@@ added constructor instead of reusing beat period
                
                print "First Beat: "  + str(result.first_beat) + "  Beat Period: " + str(result.beat_period)
            else:
                print "No beat track found"

            # force an off condition at the end of the sequence
            #for i in range(numchannels):
            #    ev.setValues(im.size[1],0,i+1,"off",0,newval)
            #    result.addEvent(ev)

            # force a channel 0 event to mark the end of the sequence,
            ev.setValues(im.size[1] - 1,0,0,"off",0,newval)
            result.addEvent(ev)
            
            result.reconcile()

            # reference_beat_correction
            # the reference beat and the length of the sequence are calculated
            # separately, leading to some error. This calculates the whole
            # number of beats in the sequence and resets beat_period and
            # ref_beat_period to the appropriate value to make a whole number
            # of beats
            if result.ref_beat_period.total_frames > 0:
                seq_period = result.events[len(result.events) - 1].ref_time.seconds
                num_beats = round(seq_period / result.ref_beat_period.seconds)
                corrected_beat_period = seq_period / num_beats
                result.beat_period.setTime(corrected_beat_period)
                result.ref_beat_period.setTime(corrected_beat_period)
                print "** Seq period " + str(seq_period)
                print "** Num Beats  " + str(num_beats)
                print "** Corrected beat period" + str(corrected_beat_period)
            
            end =  parclasses.TimeCode(time.time())
            print "Processing time: " + str(end - start)

        return result

    
    def import_triple(self, filename, numchannels, spacing, beattrackpos=0, channelmap=None, filtrobj=None):
        """ Opens a graphic file (jpg, gif) and imports a sequence.
            Returns a ControlList object
            filename: graphic file path
            numchannels: number of total channels to import
            spacing: pixels between channels and first ch offset
            beattrackpos: horiz position of beat track (0 means no beat track)
            channelmap: channel mapping object
            filterobj: filter object (future) """

        result = parclasses.ControlList()
        ev = parclasses.ControlEvent()

        # open source image file  @@@ some error checking here @@@
        im = Image.open(filename)
        if im.format != "JPEG":
            print "Please use a JPG image file"
        else:
            print "Opening image for sequence import..."
            print "Width: " + str(im.size[0]) + "  Height: " + str(im.size[1])

            state = [0] * numchannels  # current state of the channels
            numchannels = int(numchannels / 3)

            # read grapic into a buffer
            buf = im.load()

            # read in graphic lines
            start = parclasses.TimeCode(time.time())  # calc processing time

            # import red channel (ch 1, 4, 7...)
            for line in range(im.size[1]):
                for chnl in range(numchannels):
                    for trip in range(3):
                        val = buf[(chnl + 1) * spacing, line]
                        ch = chnl + trip
                        newval = val[trip]
                        
                        # if the state has changed, create an event object
                        newstate = state[ch]
                        if newval > 153 and state[ch] == 0:
                            newstate = 1
                            newaction = "on"
                        elif newval < 118 and state[ch] == 1:
                            newstate = 0
                            newaction = "off"

                        if (state[ch] != newstate):                  
                            ev.setValues(line,0,ch+1,newaction,0,newval)
                            result.addEvent(ev)
                            state[ch] = newstate
                            
            result.reconcile()
            end =  parclasses.TimeCode(time.time())
            print "Processing time: " + str(end - start)

        return result

    
        
                        
