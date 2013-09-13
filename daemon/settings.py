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

"""GCE configuration settings file."""

PROJECT_ID = '[PROJECT_ID]'
QUEUE_NAME = 'imagetasks'

GOOGLE_STORAGE = 'gs'
# Do not include the "gs://" prefix to the bucket name.
PROCESSED_IMG_BUCKET = '[BUCKET_TO_STORE_PROCESSED_IMAGES]'

# Credentials information.
# ex. CREDENTIAL_ACCOUNT_EMAIL =
#                        '<SERVICE_ACCOUNT_ID>@developer.gserviceaccount.com'
CREDENTIAL_ACCOUNT_EMAIL = '[SERVICE_ACCOUNT]'
# ex. PRIVATE_KEY_LOCATION = '/home/[USERNAME]/.ssh/XXXX-privatekey.p12'
PRIVATE_KEY_LOCATION = '[SERVICE_ACCOUNT_PRIVATE_KEY]'

# List of quotes in a text file, each quote on a new-line.
QUOTES_FILE_LOCATION = 'quotes.txt'

## Task Queue Config options
# Number of tasks to lease in one cycle.
NUM_TASKS_TO_LEASE = 5
# Amount of time to lease a task for in seconds.
LEASE_TIME_SEC = 5

# Amount of time for daemon to sleep after having...
# - successfully chomped a task.
SLEEP_TIME_AFTER_TASKS_SEC = 1
# - found task queue empty.
SLEEP_TIME_AFTER_NO_TASKS_SEC = 4
# - been rate limitted.
SLEEP_TIME_RATE_LIMIT = 10

# Task queue reader Log filename
LOG_FILENAME = 'task-queue-reader.log'

## Image processing options
# Number of colors (bit-depth) for PIL image quantization.
BIT_DEPTH = 8
# Defines the thumbnail size reduction of an image,
# smaller numbers result in more pixellation.
THUMBNAIL_WIDTH = 64
# Defines the maximum width of the resulting processed image.
FINAL_WIDTH = 768

# True-Type Font file location used for quotes in processed images.
# To install FreeSans: sudo apt-get install fonts-freefont-ttf'
FONT_TTF = '/usr/share/fonts/truetype/freefont/FreeSans.ttf'
FONT_SIZE = 20

# Quote text color.
QUOTE_TEXT_COLOR = '#FFF'
# Quote background rectangle color.
QUOTE_BG_COLOR = '#000'

# Border depth and color
BORDER_EDGE_SIZE_PIXELS = 10
BORDER_COLOR = '#EEE'

## Heartbeat statistics web server information.
HEARTBEAT_ADDRESS = ''
HEARTBEAT_PORT = 9000
