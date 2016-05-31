#!/usr/bin/env python
# -*- coding: utf-8; mode: python; -*-
#
#  GStreamer Graph - Graph values from GStreamer debug logs
#
#  Copyright (C) 2016 Edward Hervey <edward@centricular.com>
#
#  This program is free software; you can redistribute it and/or modify it
#  under the terms of the GNU General Public License as published by the Free
#  Software Foundation; either version 2 of the License, or (at your option)
#  any later version.
#
#  This program is distributed in the hope that it will be useful, but WITHOUT
#  ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
#  FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
#  more details.
#
#  You should have received a copy of the GNU General Public License along with
#  this program.  If not, see <http://www.gnu.org/licenses/>.

"""GStreamer Debug Log grapher"""

import pylab
import sys
import numpy
import time

# Number of nanoseconds in a second
NS_PER_SECOND = 1000000000.0


def clocktime_to_float(valstr, defaultval=None):
    """Convert a string representing a GstClockTime or GstClockTimeDiff
    into the float equivalent in seconds.

    For the case of GST_CLOCK_TIME_NONE, the default value will be returned
    if specified, otherwise an exception will be raised
    """
    if "9:99:99" in valstr:
        if defaultval is None:
            raise Exception
        return defaultval
    h, m, d = valstr.split(':')
    s, ms = d.split('.')

    res = float(ms) / NS_PER_SECOND
    res += float(s)
    res += 60.0 * float(m)
    res += 3600.0 * float(h)

    if h.startswith('-'):
        res = -res
    return res


def pts_or_dts(ptsv, dtsv, default=0):
    """Given two string representations of PTS and DTS, will convert
    and return a tuple of the float equivalent in seconds.

    Handles the case where one or the other can be GST_CLOCK_TIME_NONE
    """
    try:
        pts = clocktime_to_float(ptsv)
    except:
        dts = clocktime_to_float(dtsv, default)
        pts = dts
        return (pts, dts)
    try:
        dts = clocktime_to_float(dtsv)
    except:
        dts = pts
    finally:
        return (pts, dts)


def movingaverage(interval, window_size):
    window = numpy.ones(int(window_size)) / float(window_size)
    return numpy.convolve(interval, window, 'same')


class LogDataEntry:
    """
    Base class for plottable entries. Doesn't contain the data.
    """

    def __init__(self, logger=None, entryname=None):
        self.__logger = logger
        self.__entryname = entryname
        print "Creating logger", self

    def get_loggers(self):
        return [self.__logger]

    def get_values(self, **kwargs):
        return self.__logger.get_values(self.__entryname, **kwargs)

    def get_walltime(self, **kwargs):
        return self.__logger.get_values("walltime", **kwargs)

    def get_label(self):
        return self.__logger.entries[self.__entryname]["description"]

    def get_linestyle(self):
        return self.__logger.entries[self.__entryname].get("linestyle", '-')

    def get_marker(self):
        return self.__logger.entries[self.__entryname].get("marker", '')

    def reset_updates(self):
        self.__logger.reset_updates()

    def has_updates(self):
        return self.__logger.has_updates()

    def get_key_values(self, keyname):
        return self.__logger.get_key_values(keyname)

    # Create other plots from this one
    def running_average(self, window):
        # Return RunningAverageLogDataEntry of this LogDataEntry
        return RunningAverageLogDataEntry(self, window)

    def sliding_average(self, window, margin=0.0):
        return SlidingAverageLogDataEntry(self, window, margin)

    def average(self):
        # Return AverageLogDataEntry of this LogDataEntry
        return AverageLogDataEntry(self)

    def derivate_time(self):
        # Returns the derivate over walltime of the value
        return DerivateTimeLogDataEntry(self)

    def diff_time(self):
        return DiffTimeLogDataEntry(self)

    def wall_diff(self):
        return WallDiffLogDataEntry(self)

    def cumulative(self):
        # Returns the accumulation of value over time
        return AccumulateLogDataEntry(self)

    def diff(self, to_compare):
        # Returns the difference with another entry
        return DiffLogDataEntry(self, to_compare)

    def __repr__(self):
        return "<%s from %s>" % (self.__entryname, self.__logger)


class ProxyLogDataEntry(LogDataEntry):

    def __init__(self, other, *args, **kwargs):
        self.other = other
        LogDataEntry.__init__(self, *args, **kwargs)

    def __getattr__(self, name):
        return self.other.__getattr__(name)

    def get_loggers(self):
        return self.other.get_loggers()

    def has_updates(self):
        return self.other.has_updates()

    def reset_updates(self):
        self.other.reset_updates()

    def get_walltime(self, **kwargs):
        return self.other.get_walltime(**kwargs)

    def get_values(self, **kwargs):
        return self.other.get_values(**kwargs)

    def get_key_values(self, keyname):
        return self.other.get_key_values(keyname)

    def get_linestyle(self):
        return self.other.get_linestyle()

    def get_marker(self):
        return self.other.get_marker()

    def __repr__(self):
        return "<%s for %r>" % (self.__class__.__name__, self.other)


class AverageLogDataEntry(ProxyLogDataEntry):

    def get_label(self):
        return "average() %s" % self.other.get_label()

    def get_walltime(self, **kwargs):
        v = self.other.get_walltime(**kwargs)
        if len(v) > 1:
            return [v[0], v[-1]]
        return []

    def get_values(self, **kwargs):
        oval = self.other.get_values(**kwargs)
        if len(oval):
            s = sum(oval) / len(oval)
            return [s, s]
        return []


class RunningAverageLogDataEntry(ProxyLogDataEntry):

    def __init__(self, other, windowsize, *args, **kwargs):
        self.windowsize = windowsize
        ProxyLogDataEntry.__init__(self, other, *args, **kwargs)

    def get_label(self):
        return "avg(%d) %s" % (self.windowsize, self.other.get_label())

    def get_walltime(self, **kwargs):
        v = self.other.get_walltime(**kwargs)
        if len(v) > self.windowsize:
            return v[self.windowsize / 2: - (self.windowsize / 2)]
        return []

    def get_values(self, **kwargs):
        v = self.other.get_values(**kwargs)
        if len(v) > self.windowsize:
            return movingaverage(v, self.windowsize)[self.windowsize / 2: - (self.windowsize / 2)]
        return []


class SlidingAverageLogDataEntry(ProxyLogDataEntry):

    def __init__(self, other, windowsize, margin, *args, **kwargs):
        self.windowsize = windowsize
        # value gets resetted if difference between new and average exceeds
        # the margin percentage
        self.margin = margin
        ProxyLogDataEntry.__init__(self, other, *args, **kwargs)

    def get_label(self):
        return "avgslide(%d) %s" % (self.windowsize, self.other.get_label())

    def get_walltime(self, **kwargs):
        w = self.other.get_walltime(**kwargs)
        if len(w) < self.windowsize:
            return []
        return w

    def get_values(self, **kwargs):
        v = self.other.get_values(**kwargs)
        if len(v) < self.windowsize:
            return []
        r = [v[0]]
        for i in range(1, len(v)):
            # if the new value differs from the current average by more
            # than the threshold, use it
            if self.margin > 0.0:
                vd = abs(r[-1] - v[i])
                if vd >= self.margin * r[-1] or vd >= self.margin * v[i]:
                    up = v[i]
                else:
                    up = (v[i] + (r[-1] * (self.windowsize - 1))) / \
                        self.windowsize
            else:
                up = (v[i] + (r[-1] * (self.windowsize - 1))) / self.windowsize
            r.append(up)
        return r


class DiffTimeLogDataEntry(ProxyLogDataEntry):
    # values over derivate of walltime: vals / d(walltime)
    # Use this for bitrate calculation for example

    def __init__(self, other, other_key="walltime", *args, **kwargs):
        self.__other_key = other_key
        ProxyLogDataEntry.__init__(self, other, *args, **kwargs)

    def get_label(self):
        return "%s / d(time)" % self.other.get_label()

    def get_walltime(self, **kwargs):
        return self.other.get_walltime(**kwargs)[1:]

    def get_values(self, **kwargs):
        return self.other.get_values(**kwargs)[1:] / numpy.diff(self.other.get_walltime(**kwargs))


class DerivateTimeLogDataEntry(ProxyLogDataEntry):
    # Derivate of values over walltime: d(vals) / d(walltime)

    def __init__(self, other):
        ProxyLogDataEntry.__init__(self, other)

    def get_label(self):
        return "d(values)/d(time) %s" % self.other.get_label()

    def get_walltime(self, **kwargs):
        return self.other.get_walltime(**kwargs)[1:]

    def get_values(self, **kwargs):
        return numpy.diff(self.other.get_values(**kwargs)) / numpy.diff(self.other.get_walltime(**kwargs))


class WallDiffLogDataEntry(ProxyLogDataEntry):
    # Difference from previous value in walltime

    def __init__(self, other, *args, **kwargs):
        ProxyLogDataEntry.__init__(self, other, *args, **kwargs)

    def get_label(self):
        return "d(walltime) %s" % self.other.get_label()

    def get_walltime(self, **kwargs):
        return self.other.get_walltime(**kwargs)[1:]

    def get_values(self, **kwargs):
        return 1.0 / numpy.ediff1d(self.other.get_values(**kwargs))


class AccumulateLogDataEntry(ProxyLogDataEntry):

    def get_label(self):
        return "cumulative of %s" % self.other.get_label()

    def get_values(self, **kwargs):
        return numpy.cumsum(self.other.get_values(**kwargs))


class DiffLogDataEntry(ProxyLogDataEntry):
    # Computes the difference between two fields over time
    # Useful to calculate for example latency

    def __init__(self, other, to_compare, *args, **kwargs):
        self.to_compare = to_compare
        ProxyLogDataEntry.__init__(self, other, *args, **kwargs)

    def get_loggers(self):
        r = self.other.get_loggers()
        t = self.to_compare.get_loggers()
        for i in t:
            if i not in r:
                r.append(i)
        return r

    def get_label(self):
        return "diff: %s vs %s" % (self.other.get_label(), self.to_compare.get_label())

    def get_walltime(self, **kwargs):
        wt1 = self.other.get_walltime(**kwargs)
        wt2 = self.to_compare.get_walltime(**kwargs)
        wt1.extend(wt2)
        wt1.sort()
        return wt1

    def get_values(self, **kwargs):
        wt1 = self.other.get_walltime(**kwargs)
        v1 = self.other.get_values(**kwargs)
        wt2 = self.to_compare.get_walltime(**kwargs)
        v2 = self.to_compare.get_values(**kwargs)
        f = [0]
        idx1 = 0
        len1 = len(wt1)
        for idx2 in range(len(wt2)):
            a2 = wt2[idx2]
            b2 = v2[idx2]
            # Go over all values of the second range and subtract from
            # values of the first range which are located before a2
            while idx1 < len1 and wt1[idx1] < a2:
                # print "Comparing wt", wt1[idx1], a2, "values", v1[idx1], b2
                f.append(b2 - v1[idx1])
                idx1 += 1
            if idx1 < len1:
                f.append(b2 - v1[idx1])
        return f


class LogData:
    """
    Base class for logging data
    """
    # base class for log data
    # This tracks one or more LogDataEntry that come from one or more log line

    # has_strings : List of strings the line must contain
    has_strings = []
    # without_strings : List of strings the line must *not* contain
    without_strings = []

    # FIXME : How to handle multiple instances ?
    # Maybe have a way to specify where the instance ID is located in the
    # string to automatically create the different instances
    # note : by instance ID, we mean more than just the element name (ex:
    # multiqueue single queue entries)
    elements = []
    element_locator = None

    # The entries provided by this Logger
    # key : entry name
    # value : dictionnary
    #     'name' : name of the entry
    #     'description' : description of the entry, used for display
    # walltime and element are already taken care of by the base class
    entries = {}

    def __init__(self):
        # sorted list of all values
        self.__entries = []
        self.__updated = False

    def analyze_line(self, line):
        if self.__matches(line):
            ls = line.split()
            wt = clocktime_to_float(ls[0])
            if self.element_locator is not None:
                element = ls[self.element_locator].split(
                    ':<')[-1].split('>')[0]
                try:
                    self.process(ls, walltime=wt, element=element)
                except:
                    print "EXCEPTION HANDLING LINE", line
                    print "FROM", self
                    raise Exception
            else:
                self.process(ls, walltime=wt)
            return True
        return False

    def append(self, **kwargs):
        """Append all values. To be used by subclasses"""
        # FIXME : yes, it's totally not efficient
        self.__entries.append(kwargs)
        self.__updated = True

    def reset_updates(self, updated=False):
        self.__updated = updated

    def has_updates(self):
        return self.__updated

    def get_key_values(self, keyname):
        """Returns the list of unique values for keyname"""
        # FIXME : Implement a cache invalidate by __updated
        r = []
        for e in self.__entries:
            if keyname in e and not e[keyname] in r:
                r.append(e[keyname])
        return r

    def __getattr__(self, name):
        # Allows getting accessor to entries
        if name in self.entries:
            return LogDataEntry(self, name)
        raise AttributeError("Unknown attribute %s" % name)

    def get_values(self, entryname, **kwargs):
        r = []

        for e in self.__entries:
            if entryname in e:
                has_all = True
                # filter by other kwargs if present and applicable
                for k, v in kwargs.iteritems():
                    if k in e and e[k] != v:
                        has_all = False
                if has_all:
                    r.append(e[entryname])
        # return numpy.array(r)
        return r

    def process(self, ls, **kwargs):
        """
        Extract values of the given line
        ls: array of elements from the line (space separated)
        kwargs: other values to be stored

        Implementations shall extract the values and then call
        the append method with:
        * <entryname>=<entryvalue>
        * and terminated with **kwargs
        """
        raise NotImplemented

    def __matches(self, line):
        if self.has_strings == [] and self.without_strings == []:
            raise NotImplemented
        for i in self.has_strings:
            if i not in line:
                return False
        for i in self.without_strings:
            if i in line:
                return False
        return True


class VDecInLogData(LogData):
    has_strings = ["gst_video_decoder_chain", "PTS"]
    without_strings = ["reverse"]

    entries = {
        'pts': {'description': "Input PTS", 'marker': "x"},
        'dts': {'description': "Input DTS", 'marker': "x"},
        'size': {'description': "Input buffer size",
                 'unit': "bytes"}
    }

    # FIXME : Handle this. We need a system for "last" observed values
    vdecinsstart = []
    vdecinsstop = []

    element_locator = -10

    def process(self, ls, **kwargs):
        pts, dts = pts_or_dts(ls[-7][:-1], ls[-5])
        sz = int(ls[-1])
        self.append(pts=pts, dts=dts, size=sz, **kwargs)


class VDecDropQosLogData(LogData):
    has_strings = ["gst_video_decoder_clip_and_push", "Dropping frame"]
    entries = {
        'pts': {'description': "Dropped PTS (QoS)",
                'marker': 'o',
                'linestyle': ''}
    }
    element_locator = -9

    def process(self, ls, **kwargs):
        self.append(pts=clocktime_to_float(ls[-3][6:]), **kwargs)


class VDecDropLogData(LogData):
    has_strings = ["gst_video_decoder_clip_and_push", "dropping buffer"]
    entries = {
        'pts': {'description': "Dropped PTS",
                'marker': 'o',
                'linestyle': ''}
    }
    element_locator = -13

    def process(self, ls, **kwargs):
        self.append(pts=clocktime_to_float(ls[-8]), **kwargs)


class VDecOutLogData(LogData):
    has_strings = ["gst_video_decoder_clip_and_push_buf", "pushing buffer "]

    entries = {
        'pts': {'description': "Output PTS", 'marker': 'x'},
        'size': {'description': "Output buffer size"},
        'duration': {'description': "Output buffer duration"}
    }
    element_locator = -11

    def process(self, ls, **kwargs):
        self.append(pts=clocktime_to_float(ls[-3][:-1]),
                    duration=clocktime_to_float(ls[-1], 0),
                    size=int(ls[-5][:-1]),
                    **kwargs)


class VDecQosData(LogData):
    has_strings = ["gst_video_decoder_src_event_default", "got QoS"]

    entries = {
        'runtime': {'description': 'QoS runtime'},
        'jitter': {'description': 'QoS Jitter'},
        'rate': {'description': 'QoS rate'}
    }
    element_locator = -6

    def process(self, ls, **kwargs):
        rt = clocktime_to_float(ls[-3][:-1])
        jit = clocktime_to_float(ls[-2][:-1])
        rate = float(ls[-1])
        self.append(runtime=rt, jitter=jit, rate=rate, **kwargs)


class MultiLogData(LogData):
    # Base Class for aggregating multiple LogData together
    # Useful for example for LogData coming from one element for example

    # Subentries
    # key: 'entry name'
    # value: LogData
    subentries = {}

    def __init__(self):
        if self.subentries == []:
            raise Exception
        self.__childs = []
        for k, v in self.subentries.iteritems():
            self.__childs.append(v)

    def analyze_line(self, line):
        for c in self.__childs:
            if c.analyze_line(line):
                return True

    def reset_updates(self):
        for c in self.__childs:
            c.reset_updates()

    def __getattr__(self, name):
        if name in self.subentries:
            return self.subentries[name]
        raise AttributeError("Unknown attribute %s" % name)


class VDecLogData(MultiLogData):
    # Group all LogData from video decoders
    subentries = {
        'chain': VDecInLogData(),
        'push': VDecOutLogData(),
        'qos': VDecQosData(),
        'dropped': VDecDropLogData(),
        'qos_dropped': VDecDropQosLogData()
    }


class Queue2ChainLogData(LogData):
    has_strings = ["gst_queue2_chain", "received buffer"]
    element_locator = -11
    entries = {
        'size': {'description': "Input buffer size"},
        'pts': {'description': "Input buffer PTS"},
        'duration': {'description': "Input buffer duration"}
    }

    def process(self, ls, **kwargs):
        pts = clocktime_to_float(ls[-3][:-1], 0)
        sz = int(ls[-5][:-1])
        dur = clocktime_to_float(ls[-1], 0)
        self.append(pts=pts, size=sz, duration=dur, **kwargs)


class Queue2InputRate(LogData):
    has_strings = ["update_in_rates"]
    without_strings = ["global period"]
    element_locator = -6
    entries = {
        'rate': {'description': "Average input rate"}
    }

    def process(self, ls, **kwargs):
        rate = float(ls[-3][:-1])
        self.append(rate=rate, **kwargs)


class Queue2TimeLevel(LogData):
    has_strings = ["update_time_level", "gstqueue2.c"]
    entries = {
        'sink_time': {"description": "Incoming time"},
        'src_time': {"description": "Outgoing time"},
        'time_level': {"description": "Time level"}
    }
    element_locator = -5

    def process(self, ls, **kwargs):
        sink = clocktime_to_float(ls[-3][:-1], 0)
        src = clocktime_to_float(ls[-1], 0)
        self.append(sink_time=sink, src_time=src,
                    time_level=sink - src,
                    **kwargs)


class Queue2LogData(MultiLogData):
    subentries = {
        'chain': Queue2ChainLogData(),
        'input_rate': Queue2InputRate(),
        'time_level': Queue2TimeLevel()
    }


class ADecInLogData(LogData):
    has_strings = ["audio_decoder_chain", "received buffer"]

    entries = {
        'pts': {'description': "Input PTS"},
        'size': {'description': "Input buffer size"},
        'duration': {'description': "Input buffer duration"}
    }
    element_locator = -11

    def process(self, ls, **kwargs):
        pts = clocktime_to_float(ls[-3][:-1], 0)
        sz = int(ls[-6])
        dur = clocktime_to_float(ls[-1], 0)
        self.append(pts=pts, size=sz, duration=dur, **kwargs)


class ADecOutLogData(LogData):
    has_strings = ["gst_audio_decoder_push_forward", "pushing buffer of size"]

    entries = {
        'pts': {'description': "Output PTS"},
        'size': {'description': "Output buffer size"}
    }

    def process(self, ls, **kwargs):
        pts = clocktime_to_float(ls[-3][:-1])
        sz = int(ls[-6])
        self.append(pts=pts, size=sz, **kwargs)


class ADecLogData(MultiLogData):
    subentries = {
        'chain': ADecInLogData(),
        'push': ADecOutLogData()
    }


class BaseSinkChainLogData(LogData):
    has_strings = ["gst_base_sink_chain_unlocked", "got times"]
    entries = {
        'start': {'description': "Input buffer start time",
                  'marker': 'x'},
        'stop': {'description': "Input buffer stop time"}
    }
    element_locator = -7

    def process(self, ls, **kwargs):
        start = clocktime_to_float(ls[-3][:-1])
        stop = clocktime_to_float(ls[-1], start)
        self.append(start=start, stop=stop, **kwargs)


class BaseSinkPerformQosLogData(LogData):
    has_strings = ["gst_base_sink_perform_qos", "entered", "pt", "jitter"]
    entries = {
        'pt': {'description': "Processing Time"}
    }
    element_locator = -14

    def process(self, ls, **kwargs):
        self.append(pt=clocktime_to_float(ls[-4][:-1], 0), **kwargs)


class BaseSinkQosLogData(LogData):
    has_strings = ["base_sink_send_qos"]
    entries = {
        'proportion': {'description': "Proportion",
                       'marker': 'o'},
        'diff': {'description': "Jitter"},
        'timestamp': {'description': "Timestamp"}
    }
    element_locator = -10

    def process(self, ls, **kwargs):
        self.append(proportion=float(ls[-5][:-1]), diff=float(ls[-3][:-1]) / 1000000000.0,
                    timestamp=clocktime_to_float(ls[-1], 0), **kwargs)


class BaseSinkQueryPosition(LogData):
    has_strings = ["gst_base_sink_get_position", "res:"]
    entries = {'position': {'description': "Current position"}}
    element_locator = -5

    def process(self, ls, **kwargs):
        self.append(position=clocktime_to_float(ls[-1], 0), **kwargs)


class BaseSinkLogData(MultiLogData):
    # FIXME : Add a method to compute seeking delays based on moment:
    # 1) the seek event was sent
    # 2) the seek event was returned
    # 3) the corresponding segment was received
    # 4) the first buffer was received (i.e. pre-roll was effective)
    subentries = {
        'chain': BaseSinkChainLogData(),
        'qos': BaseSinkQosLogData(),
        'perform_qos': BaseSinkPerformQosLogData(),
        'position': BaseSinkQueryPosition()
    }


class AdaptiveDemuxChainData(LogData):
    has_strings = ["adaptivedemux.c", "_src_chain", "Received buffer of size"]
    entries = {
        'size': {'description': "Downloaded buffer size"}
    }
    element_locator = -6

    def process(self, ls, **kwargs):
        self.append(size=int(ls[-1]), **kwargs)


class AdaptiveDemuxChainFirstBufferData(LogData):
    has_strings = ["adaptivedemux.c", "_src_chain", "set fragment pts"]
    entries = {
        'pts': {'description': "PTS of initial buffer",
                'marker': 'x'}
    }
    element_locator = -4

    def process(self, ls, **kwargs):
        self.append(pts=clocktime_to_float(ls[-1].split('=')[-1], 0), **kwargs)


class AdaptiveDemuxBitrateSingleData(LogData):
    has_strings = ["gst_adaptive_demux_stream_update_current_bitrate",
                   "last fragment bitrate was"]
    entries = {'bitrate': {'description': "Last fragment bitrate"}}

    def process(self, ls, **kwargs):
        self.append(bitrate=int(ls[-1]), **kwargs)


class AdaptiveDemuxPosition(LogData):
    has_strings = ["demux_stream_advance_fragment",
                   "segment_timestamp", "earliest_position"]
    entries = {'position': {'description': "Fragment position",
                            'marker': 'x'},
               'deadline': {'description': "QoS deadline (corrected)"}
               }
    element_locator = -3

    def process(self, ls, **kwargs):
        self.append(position=clocktime_to_float(ls[-2][18:]),
                    deadline=clocktime_to_float(ls[-1][18:]),
                    **kwargs)


class AdaptiveDemuxDeadline(LogData):
    has_strings = ["gst_adaptive_demux_src_event", "deadline", "proportion"]
    entries = {'deadline': {'description': "QoS Deadline"}}

    def process(self, ls, **kwargs):
        self.append(deadline=clocktime_to_float(ls[-2]), **kwargs)


class AdaptiveDemuxStreamDeadline(LogData):
    has_strings = ["gst_adaptive_demux_src_event", "Earliest stream time"]
    entries = {'deadline': {'description': "QoS Stream Deadline"}}

    def process(self, ls, **kwargs):
        self.append(deadline=clocktime_to_float(ls[-1]), **kwargs)


class AdaptiveDemuxFragmentRequestTime(LogData):
    has_strings = ["gst_adaptive_demux_stream_download_fragment",
                   "Requested fragment timestamp"]
    entries = {'timestamp': {'description': "Requested Timestamp"}}
    element_locator = -5

    def process(self, ls, **kwargs):
        if "99:99:99.999999999" not in ls[-1]:
            self.append(timestamp=clocktime_to_float(ls[-1]), **kwargs)


class AdaptiveDemuxRequestLatency(LogData):
    has_strings = ["gstadaptivedemux.c", "_src_chain", "Request latency"]
    entries = {'latency': {'description': "Request Latency"}}

    def process(self, ls, **kwargs):
        self.append(latency=clocktime_to_float(ls[-1]), **kwargs)


class AdaptiveDemuxData(MultiLogData):
    subentries = {
        'chain': AdaptiveDemuxChainData(),
        'chainfirstbuf': AdaptiveDemuxChainFirstBufferData(),
        'bitrate': AdaptiveDemuxBitrateSingleData(),
        'position': AdaptiveDemuxPosition(),
        'deadline': AdaptiveDemuxDeadline(),
        'stream_deadline': AdaptiveDemuxStreamDeadline(),
        'request_latency': AdaptiveDemuxRequestLatency(),
        'fragment_request_time': AdaptiveDemuxFragmentRequestTime()
    }


class DashDemuxDownloadTime(LogData):
    has_strings = ["gstdashdemux.c", "advance_fragment", "Download time"]
    entries = {'download_time': {'description': "Keyframe download time",
                                 'marker': "o"},
               'average': {'description': "Average Keyframe download time"}}
    element_locator = -5

    def process(self, ls, **kwargs):
        self.append(download_time=clocktime_to_float(ls[-3]),
                    average=clocktime_to_float(ls[-1]),
                    **kwargs)


class DashDemuxAdvancePosition(LogData):
    has_strings = ["gstdashdemux.c",
                   "dash_demux_stream_advance_fragment", "Actual position"]
    entries = {'position': {'description': "position"}}
    element_locator = -4

    def process(self, ls, **kwargs):
        self.append(position=clocktime_to_float(ls[-1]),
                    **kwargs)


class DashDemuxFragmentPosition(LogData):
    has_strings = ["gstdashdemux.c", "update_fragment_info", "Actual position"]
    entries = {'position': {'description': "Fragment position",
                            'linestyle': "--",
                            'marker': "o"}}
    element_locator = -4

    def process(self, ls, **kwargs):
        self.append(position=clocktime_to_float(ls[-1]),
                    **kwargs)


class DashDemuxAdvanceTargetTime(LogData):
    has_strings = ["gstdashdemux.c",
                   "dash_demux_stream_advance_fragment", "target_time"]
    entries = {'target': {'description': "Target timestamp"}}
    element_locator = -3

    def process(self, ls, **kwargs):
        self.append(target=clocktime_to_float(ls[-1], 0),
                    **kwargs)


class DashDemuxTargetTime(LogData):
    has_strings = ["gstdashdemux.c",
                   "get_target_time", "diff", "average_download"]
    element_locator = -7
    entries = {
        "diff": {"description": "difference vs qos time"}
    }

    def process(self, ls, **kwargs):
        self.append(diff=clocktime_to_float(ls[-3]), **kwargs)


class DashDemuxData(MultiLogData):
    subentries = {
        'download_time': DashDemuxDownloadTime(),
        'advance_position': DashDemuxAdvancePosition(),
        'target_time': DashDemuxAdvanceTargetTime(),
        'get_target_time': DashDemuxTargetTime(),
        'fragment_position': DashDemuxFragmentPosition()
    }


class LogFigure:
    # base class for figures combining information from multiple extractors
    # Can produce one or more figure, with one or more subfigures within
    name = None
    xlabel = "Wall Time (seconds)"
    ylabel = "Value (seconds)"

    plots = []

    # The pylab plots. Store per figure ?
    # __plots = {}

    def __init__(self, name, datapoints=[], main_key="element", main_key_split=False, *args, **kwargs):
        """
        name: name of the figure
        datapoints: a list of LogDataEntry to plot
        main_key: The main key used to separate entries
        main_key_split: If True, different figures will be done for each different 'main_key',
                        else they will be plotted on the same figure
        """
        self.name = name
        self.datapoints = datapoints
        self.main_key = main_key
        self.main_key_split = main_key_split
        # The pylab figures
        # key : main_key
        # value : { "figure" : Figure, "axes" : Axes, "plots" : {plots} }
        self.__figures = {}

    def __repr__(self):
        return "<Figure '%s'>" % self.name

    def __draw_single_figure(self, name, filter_dict=None, key_values=None):
        # name : Name to use for the figure
        # filter_dict : filte dictionnary to get the values from
        # key_values : list of main key values to iterate over for each data
        # point
        res = {}
        # create figure
        res["figure"] = pylab.figure(name)
        # set labels
        # FIXME : Use information from datapoints
        pylab.xlabel(self.xlabel)
        pylab.ylabel(self.ylabel)
        res["plots"] = {}
        if filter_dict is None:
            filter_dict = {}
        # print "FILTER", filter_dict
        # print "KEY VALUES", key_values, name
        # FIXME : Handle subplots
        for p in self.datapoints:
            # print "KEY", key_values
            if key_values is not None:
                # print "GAAAH"
                for k in key_values:
                    d = filter_dict
                    d[self.main_key] = k
                    wt = p.get_walltime(**d)
                    v = p.get_values(**d)
                    if wt != []:
                        print "plotting", p.get_label(), k
                        # print v
                        res["plots"][(p, k)] = pylab.plot(wt, v, label="%s %s" % (p.get_label(), k),
                                                          marker=p.get_marker(),
                                                          linestyle=p.get_linestyle())[0]
            else:
                # print "BOPOH", filter_dict, p
                wt = p.get_walltime(**filter_dict)
                v = p.get_values(**filter_dict)
                if v != []:
                    # print v
                    print "plotting", p.get_label(), "GLOBAL"
                    res["plots"][p] = pylab.plot(wt, v,
                                                 label=p.get_label(),
                                                 marker=p.get_marker(),
                                                 linestyle=p.get_linestyle())[0]
        pylab.legend(loc=0)
        pylab.grid(True)
        pylab.draw()
        res["axes"] = res["figure"].get_axes()[0]
        return res

    def __update_single_figure(self, fig, filter_dict={}, key_values=[]):
        any_updated = False
        for p in self.datapoints:
            if p.has_updates():
                if key_values is not []:
                    for k in key_values:
                        d = filter_dict
                        d[self.main_key] = k
                        print "Updating plots for", p, k
                        pl = fig["plots"][(p, k)]
                        pl.set_xdata(p.get_walltime(**d))
                        pl.set_ydata(p.get_values(**d))
                        any_updated = True
                else:
                    print "Updating plots for", p
                    pl = fig["plots"][p]
                    pl.set_xdata(p.get_walltime(**filter_dict))
                    pl.set_ydata(p.get_values(**filter_dict))
                    any_updated = True
        if any_updated:
            fig["axes"].relim()
            fig["axes"].autoscale_view(True, True, True)
            pylab.draw()
            # micro-pause to get the image to be re-drawn
            pylab.pause(0.1)

    def draw(self):
        # Several cases:
        # Single picture, single plot, no main keys
        # Single picture, single plot, multiple values with main keys
        #           Some values might have keys, some other not
        #
        # No need to draw until we have any updates
        have_any_updates = False
        for d in self.datapoints:
            if d.has_updates():
                have_any_updates = True
                break
        if not have_any_updates:
            return

        # figure out available keys from datapoints
        keyval = []
        for d in self.datapoints:
            keyval.extend(d.get_key_values(self.main_key))
        keyval = list(set(keyval))
        if keyval == []:
            if "main" not in self.__figures:
                self.__figures["main"] = self.__draw_single_figure(self.name)
            else:
                self.__update_single_figure("main")
            return
        if self.main_key_split:
            # we draw a different figure per main_key
            for key in keyval:
                d = {self.main_key: key}
                if key not in self.__figures:
                    self.__figures[key] = self.__draw_single_figure(
                        "%s %s" % (self.name, key), filter_dict=d)
                else:
                    self.__update_single_figure(key, filter_dict=d)
        else:
            # we draw everything in one figure
            if "main" not in self.__figures:
                self.__figures["main"] = self.__draw_single_figure(
                    self.name, key_values=keyval)
            else:
                self.__update_single_figure("main", key_values=keyval)
        return

    def reinit_update(self):
        # call this once all draw have been done to reset
        # the timedata observations
        for p in self.datapoints:
            p.reset_updates()


class LogGrapher:
    # list of logdata extracters to use
    extracters = []
    figures = []

    def __init__(self, figures=[]):
        # We want the pylab interactive mode
        pylab.ion()
        self.figures = figures

        self.extracters = []
        # Go over each figure and get all the extracters we need
        for f in figures:
            for d in f.datapoints:
                r = d.get_loggers()
                for i in r:
                    if i not in self.extracters:
                        self.extracters.append(i)

    def analyze_line(self, line):
        if '\r' in line[:-1]:
            line = line.split('\r')[-1]
        # find which logdata can analyze this
        for e in self.extracters:
            if e.analyze_line(line):
                return

    def update_graphs(self):
        # Go over each figure and see if we have something to update
        for f in self.figures:
            f.draw()
        for f in self.figures:
            f.reinit_update()
        # update every second
        pylab.pause(1)

    def analyze_file(self, filename):
        f = open(filename)
        for l in f.readlines():
            self.analyze_line(l)
        self.update_graphs()
        while True:
            pylab.pause(1)

    def plot_live_log(self, filename):
        f = open(filename)

        # we analyze all lines. If we get an empty line, that means we have reached the
        # last line. Pause and retry a few seconds later
        while True:
            l = f.readline()
            if l == '':
                self.update_graphs()
                # if no new line, wait for a second for the log file to grow
                # again
                print "Checking for new content in", filename
            else:
                # analyze the line
                self.analyze_line(l)
