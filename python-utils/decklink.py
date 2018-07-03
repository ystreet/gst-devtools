#!/usr/bin/env python
# -*- coding: utf-8; mode: python; -*-
#
#  GStreamer Graph - Example usage (debugging adaptive demuxer trick mode)
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

import sys
from gstgraph import LogFigure, LogGrapher, BaseSinkLogData, DeckLinkVideoSinkLogData

# Example usage of the gstgraph API
#
# This example will live plot the gstdebug log provided in input.
#
# # GST_DEBUG=2,*rtspsrc*:7,*decoder:6,*sink:6 GST_DEBUG_FILE=/tmp/log <anygstapp>
# # python adaptivetrickmode.py /tmp/log
#

if __name__ == "__main__":
    sink = BaseSinkLogData()
    decklinkvideosink = DeckLinkVideoSinkLogData()

    # Buffers being inputted, outputted and dropped in videodecoders

    vf1 = LogFigure("decklink completion", [decklinkvideosink.completion.completed, decklinkvideosink.completion.dropped, decklinkvideosink.completion.flushed, decklinkvideosink.completion.late], main_key_split=False)
    vf2 = LogFigure("decklink scheduling", [decklinkvideosink.scheduling.position, decklinkvideosink.scheduling.duration], main_key_split=False)

    vf3 = LogFigure("decklink clock_skew", [decklinkvideosink.clock_skew.upstream, decklinkvideosink.clock_skew.result, decklinkvideosink.clock_skew.internal, decklinkvideosink.clock_skew.external, decklinkvideosink.clock_skew.rate], main_key_split=False)

    # Demo with one figure per element
    vf4 = LogFigure("Sink split", [sink.qos.diff, sink.perform_qos.pt,
                                   sink.qos.diff.sliding_average(4)], main_key_split=True)
    vf5 = LogFigure("Sink split 2", [sink.qos.proportion], main_key_split=True)

    # QoS jitter observed (by sinks), should always be below 0.0
    # Corresponds to how "early" a frame arrived in the sink.
    # If above 0.0 it arrived after the target render time

    # Feed it, run it !
    grapher = LogGrapher([vf1, vf2, vf3, vf4, vf5])

    print "Opening file for processing"
    # Use .analyze_file() if file won't grow
    grapher.plot_live_log(sys.argv[1])
