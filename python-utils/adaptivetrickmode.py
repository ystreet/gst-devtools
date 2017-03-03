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
from gstgraph import LogFigure, LogGrapher, VDecLogData, ADecLogData, BaseSinkLogData, \
    AdaptiveDemuxData, Queue2LogData, DashDemuxData

# Example usage of the gstgraph API
#
# This example will live plot the gstdebug log provided in input.
#
# # GST_DEBUG=2,*adaptiv*:7,*dash*:7,*decoder:6,*sink:6 GST_DEBUG_FILE=/tmp/log <anygstapp>
# # python adaptivetrickmode.py /tmp/log
#

if __name__ == "__main__":
    # We want to extract data from various sources
    vdec = VDecLogData()
    adec = ADecLogData()
    sink = BaseSinkLogData()
    adapt = AdaptiveDemuxData()
    queue2 = Queue2LogData()
    dash = DashDemuxData()

    # Buffers being inputted, outputted and dropped in videodecoders
    vf = LogFigure("Video Decoder (Input/Output/Dropped)", [
                   vdec.chain.pts, vdec.chain.dts, vdec.push.pts, vdec.dropped.pts, vdec.qos_dropped.pts], main_key_split=False)
    vf3 = LogFigure("Audio Decoder", [adec.chain.pts, adec.push.pts])

    # Demo with all elements combined in one
    # vf4 = LogFigure("Decoder diff", [vdec.push.pts.diff(vdec.chain.dts)])

    # Demo with one figure per element
    vf5 = LogFigure("Sink split", [sink.qos.diff, sink.perform_qos.pt,
                                   sink.qos.diff.sliding_average(4)], main_key_split=True)
    vf6 = LogFigure("Sink split 2", [sink.qos.proportion], main_key_split=True)

    # adaptive demux test
    # vf6 = LogFigure("Adaptive Demux", [adapt.bitrate.bitrate])

    # QoS jitter observed (by sinks), should always be below 0.0
    # Corresponds to how "early" a frame arrived in the sink.
    # If above 0.0 it arrived after the target render time
    vf7 = LogFigure("Video QoS", [vdec.qos.jitter])

    # Concentrate in one single graph all positions we are interested in
    # * video sink : The position and when a buffer arrives in it
    # * adaptivedemux: The position of the current fragment and keyframe
    # * dashdemux: The target time (keyframe which will be next requested/downloaded)
    vf8 = LogFigure("Combined positions", [adapt.chainfirstbuf.pts, adapt.position.deadline,
                                           adapt.position.position, adapt.fragment_request_time.timestamp,
                                           sink.position.position, sink.chain.start,
                                           dash.advance_position.position, vdec.chain.pts,
                                           dash.target_time.target, dash.fragment_position.position])

    # Show the difference detected by adaptivedemux between current position
    # and downstream target position
    # vfu = LogFigure("Adaptive Demux diff", [dash.get_target_time.diff])

    # Observed bitrate per fragment/keyframe
    vfy = LogFigure("AdaptiveDemux (Observed bitrate)", [adapt.bitrate.bitrate,
                                                         adapt.bitrate.bitrate.sliding_average(3)])

    # Time taken to request and fully download keyframes
    # This will be used to figure out target time to download in trick modes
    # Also helps pointing out stray/persistent network behaviour
    vfx = LogFigure("AdaptiveDemux (Download time)", [adapt.request_latency.latency, adapt.request_latency.latency.sliding_average(8, margin=2.0),
                                                      dash.download_time.download_time, dash.download_time.average,
                                                      adapt.position.deadline.diff(adapt.position.position).sliding_average(16)])

    # Amount of data downloaded by adaptivedemux
    vfd = LogFigure("AdaptiveDemux (Amount downloaded)", [adapt.chain.size.cumulative()])

    vf9 = LogFigure("Queue2", [queue2.time_level.sink_time, queue2.time_level.src_time,
                               queue2.time_level.time_level], main_key_split=True)
    # Feed it, run it !
    grapher = LogGrapher([vf, vf3, vf5, vf6, vf7, vf8, vf9, vfx, vfy, vfd])

    print "Opening file for processing"
    # Use .analyze_file() if file won't grow
    grapher.plot_live_log(sys.argv[1])
