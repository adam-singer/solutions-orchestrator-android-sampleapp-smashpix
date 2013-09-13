# Copyright 2013 Google Inc. All Rights Reserved.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
# http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Bitified Image Entry Model and helper functions."""

import cgi

from google.appengine.ext import db

# Datetime string format
DATETIME_STRSAFE = '%Y-%m-%d %H:%M:%S'


class Bitdoc(db.Model):
  """Main Bitdoc model."""
  user = db.StringProperty(required=True)
  timestamp = db.DateTimeProperty(auto_now_add=True)
  image_link = db.StringProperty(required=True)
  file_name = db.StringProperty()
  image_8bit_link = db.StringProperty()
  timestamp_8bit = db.DateTimeProperty()

  @property
  def timestamp_strsafe(self):
    if self.timestamp:
      return self.timestamp.strftime(DATETIME_STRSAFE)
    return None

  @property
  def timestamp_8bit_strsafe(self):
    if self.timestamp_8bit:
      return self.timestamp_8bit.strftime(DATETIME_STRSAFE)
    return None

  @property
  def file_name_strsafe(self):
    """Replaces all '<', '>', and '&' chars with their HTML-safe versions."""
    if self.file_name:
      return cgi.escape(self.file_name)
    return None
