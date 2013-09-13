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

"""Endpoints services library."""
import base64
from datetime import datetime
from datetime import timedelta
import json

from protorpc import messages
from protorpc import remote
import yaml

from models import Bitdoc

from google.appengine.api import app_identity
from google.appengine.ext import endpoints

# Load config options from settings.cfg
config = yaml.load(open('settings.cfg', 'r'))

# Required when generating endpoints library from the command line.
APP_HOSTNAME = config['ENDPOINTS']['APP_HOSTNAME']

# Client ID(s) that are allowed to connect to the API server.
ALLOWED_CLIENT_IDS = [endpoints.API_EXPLORER_CLIENT_ID]
ALLOWED_CLIENT_IDS.extend(config['ENDPOINTS']['ALLOWED_CLIENT_IDS'])

# Client ID(s) of the API server.
AUDIENCE = config['ENDPOINTS']['AUDIENCE']

GCS_API_URL = 'https://%s.commondatastorage.googleapis.com'
GCS_BUCKET = config['GCS']['MAIN_BUCKET']


class ListImagesRequest(messages.Message):
  """List images message request."""
  limit = messages.IntegerField(1, default=10)
  offset = messages.IntegerField(2, default=0)


class ListImage(messages.Message):
  """Single image message."""
  user = messages.StringField(1)
  timestamp = messages.StringField(2)
  image_link = messages.StringField(3)
  image_8bit_link = messages.StringField(4)
  timestamp_8bit = messages.StringField(5)
  key = messages.StringField(6)


class ListImagesResponse(messages.Message):
  """Multiple image message response."""
  images = messages.MessageField(ListImage, 1, repeated=True)


class StorageSignedUrlRequest(messages.Message):
  """Cloud Storage Signed URL message request."""
  filename = messages.StringField(1)
  owner = messages.StringField(2)


class StorageSignedUrlResponse(messages.Message):
  """Cloud Storage Signed URL message response."""
  form_action = messages.StringField(1)
  bucket = messages.StringField(2)
  policy = messages.StringField(3)
  signature = messages.StringField(4)
  google_access_id = messages.StringField(5)
  filename = messages.StringField(6)


def GetEndpointsAuthUser():
  """Requires RPC service to authenticate. Returns authenticated user."""
  if endpoints.get_current_user() is None:
    raise endpoints.UnauthorizedException('Invalid token.')
  return endpoints.get_current_user()


# pylint: disable=undefined-variable
@endpoints.api(name='image', version='v1.0', description='Image API',
               allowed_client_ids=ALLOWED_CLIENT_IDS,
               audiences=AUDIENCE,
               hostname=APP_HOSTNAME)
class ImageApi(remote.Service):
  """Receipt RPC service to exchange messages."""

  @endpoints.method(ListImagesRequest, ListImagesResponse,
                    path='ListImages', http_method='GET', name='list.images')
  def ListImages(self, request):
    """Returns list of images to the client."""
    GetEndpointsAuthUser()

    images = []
    query = Bitdoc.all().order('-timestamp')
    for item in query.fetch(limit=request.limit, offset=request.offset):
      images.append(
          ListImage(
              user=item.user,
              timestamp=item.timestamp_strsafe,
              image_link=item.image_link,
              image_8bit_link=item.image_8bit_link,
              timestamp_8bit=item.timestamp_8bit_strsafe,
              key=str(item.key())
          )
      )
    return ListImagesResponse(images=images)

  @endpoints.method(StorageSignedUrlRequest, StorageSignedUrlResponse,
                    path='GenerateStorageSignedUrl',
                    http_method='POST',
                    name='upload.storage_signed_url')
  def GenerateStorageSignedUrl(self, request):
    """Generates signed url for Cloud Storage."""
    GetEndpointsAuthUser()

    if not request.filename:
      raise endpoints.BadRequestException('Missing request field "filename".')
    if not request.owner:
      raise endpoints.BadRequestException('Missing request field "owner".')

    expires = '%sZ' % (datetime.utcnow() + timedelta(hours=1)).isoformat()[:19]
    policy = base64.b64encode(json.dumps({
        'expiration': expires,
        'conditions': [
            ['eq', '$bucket', GCS_BUCKET],
            ['eq', '$key', request.filename],
            ['eq', '$x-goog-meta-owner', request.owner],
        ],
    }))
    signature = base64.b64encode(app_identity.sign_blob(policy)[1])

    return StorageSignedUrlResponse(
        form_action=GCS_API_URL % GCS_BUCKET,
        bucket=GCS_BUCKET,
        policy=policy,
        signature=signature,
        google_access_id=app_identity.get_service_account_name(),
        filename=request.filename
    )


server = endpoints.api_server(
    [
        ImageApi
    ],
    restricted=False
)
