/* GStreamer
 *
 * Copyright (C) 2013 Thibault Saunier <thibault.saunier@collabora.com>
 *
 * gst-validate-utils.h - Some utility functions
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Library General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Library General Public License for more details.
 *
 * You should have received a copy of the GNU Library General Public
 * License along with this library; if not, write to the
 * Free Software Foundation, Inc., 59 Temple Place - Suite 330,
 * Boston, MA 02111-1307, USA.
 */

#ifndef EXPRESSION_PARSER_H
#define EXPRESSION_PARSER_H

#include<setjmp.h>
#include<stdlib.h>
#include<glib.h>
#include<gio/gio.h>
#include <gst/gst.h>
#include "gst-validate-scenario.h"
#include "gst-validate-reporter.h"

typedef int (*GstValidateParseVariableFunc) (const gchar *name,
    double *value, gpointer user_data);

GST_EXPORT
gdouble gst_validate_utils_parse_expression (const gchar *expr,
                                             GstValidateParseVariableFunc variable_func,
                                             gpointer user_data,
                                             gchar **error);
GST_EXPORT
guint gst_validate_utils_flags_from_str     (GType type, const gchar * str_flags);
GST_EXPORT
gboolean gst_validate_utils_enum_from_str   (GType type,
                                             const gchar * str_enum,
                                             guint * enum_value);

GST_EXPORT
GList * gst_validate_utils_structs_parse_from_filename         (const gchar * scenario_file);
GST_EXPORT
GList * gst_validate_structs_parse_from_gfile            (GFile * scenario_file);

GST_EXPORT
gboolean gst_validate_element_has_klass (GstElement * element, const gchar * klass);
GST_EXPORT
gboolean gst_validate_utils_get_clocktime (GstStructure *structure, const gchar * name,
        GstClockTime * retval);

GST_EXPORT
GstValidateActionReturn gst_validate_object_set_property (GstValidateReporter * reporter,
                                                          GObject * object,
                                                          const gchar * property,
                                                          const GValue * value,
                                                          gboolean optional);

#endif
