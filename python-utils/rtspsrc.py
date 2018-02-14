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
    Queue2LogData, RtpJitterBufferData, RtspInterleavedData, RtpSourceData, H264ParseData

# Example usage of the gstgraph API
#
# This example will live plot the gstdebug log provided in input.
#
# # GST_DEBUG=2,*rtspsrc*:7,*decoder:6,*sink:6 GST_DEBUG_FILE=/tmp/log <anygstapp>
# # python adaptivetrickmode.py /tmp/log
#

if __name__ == "__main__":
    # We want to extract data from various sources
    vdec = VDecLogData()
    sink = BaseSinkLogData()
    jbuf = RtpJitterBufferData()
    rtspsrc = RtspInterleavedData()
    rtp = RtpSourceData()
    h264 = H264ParseData()

    # Buffers being inputted, outputted and dropped in videodecoders
    vf1 = LogFigure("Video Decoder (Input/Output/Dropped)", [
                   vdec.chain.pts, vdec.chain.dts, vdec.push.pts, vdec.dropped.pts, vdec.qos_dropped.pts, vdec.amc_dropped.deadline], main_key_split=False)

    vf2 = LogFigure("rtpjitterbuffer packets", [
                   jbuf.in_packet.packet, jbuf.out_packet.packet], main_key_split=False)
    vf3 = LogFigure("rtpjitterbuffer packet times", [
                   jbuf.in_packet.time, jbuf.out_packet.pts], main_key_split=False)
    vf4 = LogFigure("rtpjitterbuffer packet spacing", [
                   jbuf.spacing.old, jbuf.spacing.new], main_key_split=False)

    # Demo with one figure per element
    vf5 = LogFigure("Sink split", [sink.qos.diff, sink.perform_qos.pt,
                                   sink.qos.diff.sliding_average(4)], main_key_split=True)
    vf6 = LogFigure("Sink split 2", [sink.qos.proportion], main_key_split=True)

    # QoS jitter observed (by sinks), should always be below 0.0
    # Corresponds to how "early" a frame arrived in the sink.
    # If above 0.0 it arrived after the target render time
    vf7 = LogFigure("Video QoS", [vdec.qos.jitter])

    vf8 = LogFigure("RtspSrc receival", [rtspsrc.data.size])

    vf9 = LogFigure("RtpSource jitter", [rtp.jitter.jitter])

    vf10 = LogFigure("RtpSource diff", [rtp.jitter.diff])

    vf11 = LogFigure("RtpSource rtptime", [rtp.jitter.rtptime])

    vf12 = LogFigure("H.264 slice type", [h264.slice.slice_type])

    # Feed it, run it !
    grapher = LogGrapher([vf1, vf2, vf3, vf4, vf5, vf6, vf7, vf8, vf9, vf10, vf11, vf12])

    print "Opening file for processing"
    # Use .analyze_file() if file won't grow
    grapher.plot_live_log(sys.argv[1])
