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

"""Cloud Orchestration GAE App."""
from cStringIO import StringIO
from datetime import datetime
import json
import logging
import os

import jinja2
from PIL import Image
import webapp2
import yaml

import cloudstorage as gcs
from models import Bitdoc

from google.appengine.api import images
from google.appengine.api import taskqueue
from google.appengine.api import users
from google.appengine.ext import blobstore
from google.appengine.ext import db


# Set up the Jinja templating environment.
jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(
        os.path.dirname(__file__)))

# Load configuration options from settings.cfg file.
config = yaml.load(open('settings.cfg', 'r'))
MAIN_BUCKET = config['GCS']['MAIN_BUCKET']
BIT_BUCKET = config['GCS']['BIT_BUCKET']
TASKQUEUE = 'imagetasks'

# Get Task Queue.
processing_task_queue = taskqueue.Queue(TASKQUEUE)


#############
# Helper Functions
def GetGreeting(user, request):
  if user:
    return ('Logged in as %s. <a href="%s"'
            ' class="button">Log Out</a>') % (user.nickname(),
                                              users.create_logout_url('/'))
  else:
    return ('<a href="%s" class="button">'
            'Please log in.</a>' % users.create_login_url(request.uri))


def GetImageLinkFromBucket(bucket_name, object_name):
  # Get Image location in GCS.
  gcs_image_location = '/gs/%s/%s' % (bucket_name, object_name)
  logging.info('Trying to get image link for "%s"', gcs_image_location)
  blob_key = blobstore.create_gs_key(gcs_image_location)

  # Try to get public image URL for entry creation.
  try:
    image_link = images.get_serving_url(blob_key, secure_url=True)
    logging.info('Image link: %s', image_link)
    return image_link
  except images.ObjectNotFoundError:
    logging.error('Could not find image link for %s.',
                  gcs_image_location)
    return 'http://commondatastorage.googleapis.com/8bit-images%2Fnoimage.gif'
  except Exception, e:
    logging.error('Exception getting image link from bucket: %s', e)
    return ('http://commondatastorage.googleapis.com/8bit-images'
            '%2Fbucket_missing_image.png')


#############
# Request Handlers
class MainPage(webapp2.RequestHandler):
  """Main page and OCN handler."""

  def get(self):  # pylint: disable=g-bad-name
    """Returns front page list of bitdocs, only if logged in."""
    user = users.get_current_user()

    greeting = GetGreeting(user, self.request)

    bitdocs = []
    bitdocs = db.GqlQuery('SELECT * FROM Bitdoc ORDER BY timestamp '
                          'DESC LIMIT 100')

    template = jinja_environment.get_template('index.html')
    template_data = {
        'greeting': greeting,
        'bitdocs': bitdocs
    }

    self.response.write(template.render(template_data))


class UploadPage(webapp2.RequestHandler):
  """Upload page handles uploading new images to cloud storage."""

  def get(self):  # pylint: disable=g-bad-name
    """Returns basic upload form."""
    user = users.get_current_user()
    greeting = GetGreeting(user, self.request)
    upload_url = '/upload'

    template = jinja_environment.get_template('upload.html')
    template_data = {
        'greeting': greeting,
        'upload_url': upload_url
    }
    self.response.write(template.render(template_data))

  def post(self):  # pylint: disable=g-bad-name
    """Handles image upload form post."""
    file_img = self.request.get('file')
    if not file_img:
      logging.error('No image uploaded.')
      self.error(400)

    img_str = StringIO(file_img)
    contents = img_str.getvalue()
    try:
      img = Image.open(img_str)
    except IOError, e:
      logging.error('%s', e)
      self.error(404)

    logging.info('FORMAT: %s', img.format)
    if img.format == 'JPEG':
      content_type = 'image/jpeg'
    elif img.format == 'PNG':
      content_type = 'image/png'
    else:
      logging.error('Unknown format: %s', img.format)
      content_type = 'text/plain'

    image_name = self.request.params['file'].filename
    logging.info('Uploading file "%s"...', image_name)
    if image_name.find('.'):
      image_name = image_name[:image_name.find('.')]

    filename = '/%s/%s_%s' % (MAIN_BUCKET,
                              image_name,
                              datetime.strftime(datetime.now(),
                                                '%Y_%M_%d_%H_%M_%S_%s'))
    user = users.get_current_user()
    if user:
      owner = user.nickname()
    else:
      owner = 'Anonymous'

    # Create new image file
    gcs_file = gcs.open(filename,
                        'w',
                        content_type=content_type,
                        options={'x-goog-meta-owner': owner})

    gcs_file.write(contents)
    gcs_file.close()

    logging.info('Uploaded file %s as %s in the cloud.', image_name, filename)

    self.redirect('/')


class UpdateWithBitifiedPic(webapp2.RequestHandler):
  """Handler for GCE callback with updated 8-bit image data."""

  def post(self):  # pylint: disable=g-bad-name
    """GCE callback."""
    logging.debug(
        '%s\n\n%s',
        '\n'.join(['%s: %s' % x for x in self.request.headers.iteritems()]),
        self.request.body)

    bitdoc_id = self.request.get('id')

    # Update existing Bitdoc with image link and timestamp.
    bitdoc = db.get(bitdoc_id)
    if not bitdoc:
      logging.error('No Bitdoc found for id: %s', bitdoc_id)
      self.error(404)

    status = self.request.get('status') == 'True'
    image_8bit_name = self.request.get('image_8bit_name')
    if status and image_8bit_name:
      bitdoc.image_8bit_link = GetImageLinkFromBucket(BIT_BUCKET,
                                                      image_8bit_name)
    else:
      bitdoc.image_8bit_link = ('http://commondatastorage.googleapis.com/'
                                '8bit-images%2Fbucket_missing_image.png')
    bitdoc.timestamp_8bit = datetime.now()
    bitdoc.put()

    logging.info('Successfully updated Bitdoc %s with link %s',
                 bitdoc_id, bitdoc.image_8bit_link)


class ObjectChangeNotification(webapp2.RequestHandler):
  """Object Change Notification (OCN) handler for cloud storage upload."""

  def post(self):  # pylint: disable=g-bad-name
    """Handles Object Change Notifications."""
    logging.debug(
        '%s\n\n%s',
        '\n'.join(['%s: %s' % x for x in self.request.headers.iteritems()]),
        self.request.body)

    resource_state = self.request.headers['X-Goog-Resource-State']

    if resource_state == 'sync':
      logging.info('Sync OCN message received.')
    elif resource_state == 'exists':
      logging.info('New file upload OCN message received.')
      data = json.loads(self.request.body)
      bucket = data['bucket']
      object_name = data['name']

      # Get Image location in GCS.
      gcs_image_location = '/gs/%s/%s' % (bucket, object_name)
      blob_key = blobstore.create_gs_key(gcs_image_location)

      # Try and get username from metadata.
      if data.has_key('metadata') and data['metadata'].has_key('owner'):
        owner = data['metadata']['owner']
      else:
        owner = data['owner']['entity']

      # Try to get public image URL for entry creation.
      image_link = None

      try:
        image_link = images.get_serving_url(blob_key, secure_url=True)
      except images.ObjectNotFoundError:
        logging.error('Could not find image link for %s.',
                      gcs_image_location)
      except images.TransformationError:
        logging.error('Could not convert link to image: %s.',
                      gcs_image_location)

      if image_link:
        bitdoc = Bitdoc(user=owner,
                        image_link=image_link,
                        file_name=object_name)

        logging.info('Creating Entry... %s - %s',
                     bitdoc.user,
                     bitdoc.image_link)

        # timestamp auto.

        bitdoc.put()

        # Add Task to pull queue.
        info = {'key': unicode(bitdoc.key()),
                'image_link': unicode(image_link)}

        processing_task_queue.add(taskqueue.Task(payload=json.dumps(info),
                                                 method='PULL'))


class Delete(webapp2.RequestHandler):
  """Bitdoc removal handler."""

  def post(self):  # pylint: disable=g-bad-name
    """Removes the bitdoc with given id."""
    bitdoc = db.get(self.request.get('id'))
    if bitdoc:
      bitdoc.delete()
    self.redirect('/')


class GetEntry(webapp2.RequestHandler):
  """Bitdoc single entry handler."""

  def get(self, key):  # pylint: disable=g-bad-name
    """Returns single entry in html or json format."""
    bitdoc = db.get(key)
    if not bitdoc:
      self.error(404)

    mode = self.request.get('mode')
    if mode == 'json':
      data = {
          'user': bitdoc.user,
          'timestamp': bitdoc.timestamp_strsafe,
          'image_link': bitdoc.image_link,
          'image_8bit_link': bitdoc.image_8bit_link,
          'timestamp_8bit': bitdoc.timestamp_8bit_strsafe,
          'key': str(bitdoc.key())
      }
      self.response.headers['Content-Type'] = 'application/json'
      self.response.write(data)
    else:
      # Get Logged in user data.
      user = users.get_current_user()
      greeting = GetGreeting(user, self.request)

      template = jinja_environment.get_template('single_entry.html')
      template_data = {
          'greeting': greeting,
          'bitdoc': bitdoc
      }

      self.response.write(template.render(template_data))


class GetImage(webapp2.RequestHandler):
  """Bitdoc single image handler."""

  def get(self, key):  # pylint: disable=g-bad-name
    """Returns processed or original image associated entry."""
    bitdoc = db.get(key)
    if not bitdoc:
      self.error(404)

    mode = self.request.get('mode')
    if mode == 'original':
      self.redirect(str(bitdoc.image_link))
    else:
      self.redirect(str(bitdoc.image_8bit_link))


application = webapp2.WSGIApplication([('/', MainPage),
                                       ('/ocn', ObjectChangeNotification),
                                       ('/delete', Delete),
                                       ('/get/image/(.*)', GetImage),
                                       ('/get/(.*)', GetEntry),
                                       ('/update', UpdateWithBitifiedPic),
                                       ('/upload', UploadPage)
                                      ],
                                      debug=True)
