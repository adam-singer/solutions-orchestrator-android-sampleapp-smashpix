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

"""Cloud Orchestration GCE daemon."""
import base64
from BaseHTTPServer import BaseHTTPRequestHandler
from BaseHTTPServer import HTTPServer
from datetime import datetime
from httplib import BadStatusLine
import json
import logging
import os
import socket
import thread
import threading
from time import sleep
from time import time
from urllib import urlencode
import urllib2

from apiclient.discovery import build
from apiclient.errors import HttpError
import boto
import httplib2
from oauth2client.client import SignedJwtAssertionCredentials

from image_processing import ConvertToBitifiedImage
import settings


# Logging
logging.basicConfig(filename=settings.LOG_FILENAME, level=logging.INFO)

# Task function response codes
TASK_PASS = 1
TASK_FAIL = 2
NO_TASKS = 3
TASK_RATE_LIMITTED = 4  # HttpErro(403) RateLimit error returned.

# Authorization
http = SignedJwtAssertionCredentials(
    settings.CREDENTIAL_ACCOUNT_EMAIL,
    file(settings.PRIVATE_KEY_LOCATION, 'rb').read(),
    scope='https://www.googleapis.com/auth/taskqueue')
http = http.authorize(httplib2.Http())
task_api = build('taskqueue', 'v1beta2', http=http)

DATETIME_STRSAFE = '%Y-%m-%d %H:%M:%S'

# Heartbeat monitor statistics
# NOTE: numTasksProcessedLastMin is the total number of tasks processed in
#       the previous minute which ended prior to the current time, from
#       0 seconds to 60 seconds.
#
#       0      1      2      3  Minutes
#       |      |      |  V   |
#               \----/   ^ Polled
#                 ^The previous minute numTasksProcessedLastMin
STATS = {
    'numTasksProcessing': 0,
    'numTasksProcessedLastMin': 0,
    'lastLeasedDate': None
}
# Tracks number of tasks complete in last minute, reset at at the end of the
# minute.
task_complete_counter = 0


#########
# Taskqueue manipulation
def GetTasks():
  """Pull next set of tasks off the queue."""

  try:
    tasks = task_api.tasks().lease(leaseSecs=settings.LEASE_TIME_SEC,
                                   taskqueue=settings.QUEUE_NAME,
                                   project='s~'+settings.PROJECT_ID,
                                   numTasks=settings.NUM_TASKS_TO_LEASE)
    tasks = tasks.execute().get('items', [])
    if tasks:

      # Update Stats.
      STATS['numTasksProcessing'] += len(tasks)
      STATS['lastLeasedDate'] = datetime.now().strftime(DATETIME_STRSAFE)
    return TASK_PASS, tasks
  except HttpError, http_error:
    logging.error('HttpError %s: \'%s\'',
                  http_error.resp.status,
                  http_error.resp.reason)
    # Check for Rate-limit error.
    if (http_error.resp.status == 403 and
        (http_error.resp.reason == 'rateLimitExceeded' or
         http_error.resp.reason == 'Rate Limit Exceeded' or
         http_error.resp.reason == 'userRateLimitExceeded' or
         http_error.resp.reason == 'User Rate Limit Exceeded')):
      return TASK_RATE_LIMITTED, None
    else:
      return TASK_FAIL, None
  except BadStatusLine, e:
    logging.error('BadStatusLine while trying to lease tasks: %s', e)
    return TASK_FAIL, None
  except socket.error, e:
    logging.error('Socket error: %s', e)
    return TASK_FAIL, None
  except IOError, e:
    logging.error('IO error: %s', e)
    return TASK_FAIL, None
  except Exception, e:
    logging.error('Exception %s/%s', type(e), e)
    return TASK_FAIL, None


def DeleteTask(task):
  """Delete the given task from the queue."""

  try:
    task_api.tasks().delete(project='s~'+settings.PROJECT_ID,
                            taskqueue=settings.QUEUE_NAME,
                            task=task['id']).execute()
    # Update Stats. (Decrement to zero)
    STATS['numTasksProcessing'] = max(0, STATS['numTasksProcessing'] - 1)
    return True
  except HttpError, http_error:
    logging.error('Error deleting task %s from taskqueue: %s',
                  task['id'],
                  http_error)
    return False
  except Exception, e:
    logging.error('Error deleting task: %s', e)
    return False


def DoTask(task):
  """Load, process and upload task image and return processed image link."""

  payload = json.loads(base64.b64decode(task['payloadBase64']))

  # Load Image from URL
  url = payload['image_link']

  # Save image temporarily for upload with timestamp as name
  filename = '%s_%s' % (url[url.rfind('/')+1:],
                        datetime.strftime(datetime.now(),
                                          '%Y_%M_%d_%H_%M_%S_%s'))

  filepath = os.path.join('/tmp', filename)

  # Save image to temporary file
  try:
    image_request = urllib2.urlopen(url)
    with open(filepath, 'wb') as file_handle:
      file_handle.write(image_request.read())
  except urllib2.HTTPError, e:
    logging.error('Error loading image link %s : %s', url, e)
    return False

  # Generate Bitified image from given image.
  try:
    processed_image = ConvertToBitifiedImage(filepath)
  except IOError, e:
    logging.error('Error processing image for %s : %s', url, e)
    return False

  filepath_processed_image = filepath+'.png'

  try:
    processed_image.save(filepath_processed_image)
  except IOError, e:
    logging.error('Error saving processed image for %s : %s', url, e)
    return False

  # Upload processed image to bitified image cloud bucket
  contents = file(filepath_processed_image, 'r')
  uri = boto.storage_uri(settings.PROCESSED_IMG_BUCKET + '/' + filename,
                         settings.GOOGLE_STORAGE)
  uri.new_key().set_contents_from_file(contents)

  contents.close()

  # Remove temporary image
  os.remove(filepath)

  logging.info('%s - Successfully created "%s/%s"\n',
               datetime.now(),
               uri.bucket_name,
               uri.object_name)

  return uri.object_name


class TaskThread(threading.Thread):
  def __init__(self, task):
    threading.Thread.__init__(self)
    self.task = task
    self.status = TASK_PASS

  def run(self):
    """Process the single task, ping GAE app, and delete task from queue."""
    task = self.task
    # Perform image processing for Task
    time_task_start = time()
    processed_image_name = DoTask(task)
    time_task = time()-time_task_start
    if processed_image_name:
      logging.info('Task successful: %g seconds', time_task)
      individual_task_status = True
    else:
      logging.error('Task failed: %g seconds', time_task)
      individual_task_status = False
      processed_image_name = ''

    # GAE Notification
    data = dict(status=individual_task_status,
                image_8bit_name=processed_image_name)
    resp, content = SendUpdatedMetadataToApp(task, data)

    if resp['status'] == '200':
      logging.info('Successfully sent metadata to App.')
    else:
      logging.error('Unexpected Google App Engine Response: %s, %s',
                    resp,
                    content)
      self.status = TASK_FAIL


def DoTaskBatch():
  """Check for tasks, do tasks, store stats, rinse and repeat."""
  global task_complete_counter
  tasks_query_status, tasks = GetTasks()
  if tasks_query_status == TASK_PASS:
    if not tasks:
      logging.debug('No tasks in queue.')
      return NO_TASKS

    logging.info('Recieved %g tasks.', len(tasks))
    # Initial status is all passed.
    aggregate_task_status = TASK_PASS

    # For each task, create a a new thread, start it and add it to a
    # list of threads.
    threads = []
    for task in tasks:
      task_thread = TaskThread(task)
      task_thread.start()
      threads.append(task_thread)

    # Wait for all the threads to complete.
    for task_thread in threads:
      task_thread.join()

    # Delete all the tasks processed.
    for task in tasks:
      # Delete Task
      if DeleteTask(task):
        logging.info('Deleted task.')
      else:
        aggregate_task_status = TASK_FAIL

      # Increment task counter
      task_complete_counter += 1

    # Aggregate end status of all the task threads.
    for task_thread in threads:
      if task_thread.status == TASK_FAIL:
        aggregate_task_status = TASK_FAIL

    return aggregate_task_status
  elif tasks_query_status == TASK_FAIL:
    logging.error('Task Batch Failed.')
    return TASK_FAIL
  else:
    return tasks_query_status


def SendUpdatedMetadataToApp(task, data):
  """Does http post to GAE app with the task and it's metadata."""
  payload = json.loads(base64.b64decode(task['payloadBase64']))

  # Add key to the data sent.
  data['id'] = payload['key']
  url = 'https://%s.appspot.com/update' % settings.PROJECT_ID
  return httplib2.Http().request(url,
                                 'POST',
                                 urlencode(data))


#########
# Heartbeat server
def HeartbeatServe():
  """Run a basic HTTP server providing heartbeat statistics."""
  server = None
  try:
    server = HTTPServer((settings.HEARTBEAT_ADDRESS,
                         settings.HEARTBEAT_PORT),
                        HeartbeatHandler)
    server.serve_forever()
  except socket.error, e:
    logging.error('Could not start up Heartbeat server thread: %s', e)
  finally:
    if server:
      server.socket.close()


class HeartbeatHandler(BaseHTTPRequestHandler):
  """Heartbeat GCE Statistics Handler."""

  def do_GET(self):  # pylint: disable=g-bad-name
    self.send_response(200)
    self.send_header('Content-type', 'application/json')
    self.end_headers()

    # Return Heartbeat statistics
    self.wfile.write(json.dumps(STATS))
    return


#########
# Main Logic
def main():
  global task_complete_counter
  t_start = datetime.now()

  # Tasks per minute counter, reset every minute
  t_tasks_per_min = time()
  task_complete_counter = 0

  while True:
    logging.debug('Current Time: %s (Since start: %s)',
                  datetime.now(),
                  datetime.now() - t_start)

    # If a minute has gone by.
    if time() - t_tasks_per_min >= 60:
      logging.info('Number of tasks completed in last minute: %g',
                   task_complete_counter)
      STATS['numTasksProcessedLastMin'] = task_complete_counter
      task_complete_counter = 0
      t_tasks_per_min = time()

    # Initialize number of tasks complete in one cycle
    result = DoTaskBatch()
    if result == TASK_PASS:
      logging.debug('Sleeping for %g seconds...',
                    settings.SLEEP_TIME_AFTER_TASKS_SEC)
      sleep(settings.SLEEP_TIME_AFTER_TASKS_SEC)
    elif result == NO_TASKS:
      logging.debug('Sleeping for %g seconds...',
                    settings.SLEEP_TIME_AFTER_NO_TASKS_SEC)
      sleep(settings.SLEEP_TIME_AFTER_NO_TASKS_SEC)
    elif result == TASK_RATE_LIMITTED:
      logging.debug('Sleeping for %g seconds...',
                    settings.SLEEP_TIME_RATE_LIMIT)
      sleep(settings.SLEEP_TIME_RATE_LIMIT)
    else:
      logging.debug('Task failed. Sleeping for %g seconds...',
                    settings.SLEEP_TIME_AFTER_NO_TASKS_SEC)
      sleep(settings.SLEEP_TIME_AFTER_NO_TASKS_SEC)


if __name__ == '__main__':
  # Start heartbeat poll handler in separate thread.
  thread.start_new_thread(HeartbeatServe, ())

  # Start main task-queue chomping daemon
  main()
