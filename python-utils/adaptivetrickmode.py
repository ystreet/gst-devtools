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

if __name__ == "__main__":
    # We want to extract data from various sources
    vdec = VDecLogData()
    adec = ADecLogData()
    sink = BaseSinkLogData()
    adapt = AdaptiveDemuxData()
    queue2 = Queue2LogData()
    dash = DashDemuxData()

    # And we want to have a figure with those input pts/dts
    vf = LogFigure("Video Decoder", [
                   vdec.chain.pts, vdec.chain.dts, vdec.push.pts, vdec.dropped.pts, vdec.qos_dropped.pts], main_key_split=False)
    vf3 = LogFigure("Audio Decoder", [adec.chain.pts, adec.push.pts])
    vf2 = LogFigure("VDec", [vdec.chain.size, vdec.chain.size.running_average(
        10), vdec.chain.size.average()])

    # Demo with all elements combined in one
    # vf4 = LogFigure("Decoder diff", [vdec.push.pts.diff(vdec.chain.dts)])

    # Demo with one figure per element
    vf5 = LogFigure("Sink split", [sink.qos.diff, sink.perform_qos.pt,
                                   sink.qos.diff.sliding_average(4)], main_key_split=True)
    vf6 = LogFigure("Sink split 2", [sink.qos.proportion], main_key_split=True)

    # adaptive demux test
    # vf6 = LogFigure("Adaptive Demux", [adapt.bitrate.bitrate])

    vf7 = LogFigure("VDEC QoS", [vdec.qos.jitter])

    vfz = LogFigure("Sink rate", [sink.chain.start.derivate_time()])

    vf8 = LogFigure("Adaptive Demux position", [adapt.chainfirstbuf.pts, adapt.position.deadline,
                                                adapt.position.position, adapt.fragment_request_time.timestamp,
                                                sink.position.position, sink.chain.start,
                                                dash.advance_position.position, vdec.chain.pts,
                                                dash.target_time.target, dash.fragment_position.position])

    vfu = LogFigure("Adaptive Demux diff", [dash.get_target_time.diff])

    vfy = LogFigure("Adaptive Demux bitrate", [adapt.bitrate.bitrate,
                                               adapt.bitrate.bitrate.sliding_average(3)])

    vfx = LogFigure("Adaptive Demux latencies", [adapt.request_latency.latency, adapt.request_latency.latency.sliding_average(8, margin=2.0),
                                                 dash.download_time.download_time, dash.download_time.average,
                                                 adapt.position.deadline.diff(adapt.position.position).sliding_average(16)])

    vfd = LogFigure("Adaptive download", [adapt.chain.size.cumulative()])

    vf9 = LogFigure("Queue2", [queue2.time_level.sink_time, queue2.time_level.src_time,
                               queue2.time_level.time_level], main_key_split=True)
    # Demo with one sub-figure per element

    # Feed it, run it !
    grapher = LogGrapher([vf, vf2, vf3, vf5, vf6, vf7, vf8, vf9, vfx, vfy, vfd, vfu, vfz])

    print "Opening file for processing"
    grapher.analyze_file(sys.argv[1])
