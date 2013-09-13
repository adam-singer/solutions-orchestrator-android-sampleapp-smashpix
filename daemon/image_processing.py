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

"""Image processing function used by GCE daemon."""

from random import choice

import Image
import ImageDraw
import ImageFilter
import ImageFont
import ImageOps

import settings

# Load stripped quotes from file
quotes = [quote.strip() for quote in open(settings.QUOTES_FILE_LOCATION,
                                          'r').readlines()]

# Set quote font
FONT = ImageFont.truetype(settings.FONT_TTF, settings.FONT_SIZE)


def ConvertToBitifiedImage(file_location,
                           thumbnail_width=settings.THUMBNAIL_WIDTH,
                           final_width=settings.FINAL_WIDTH,
                           bit_depth=settings.BIT_DEPTH):
  """Loads image from filename, generates bitified Image and returns it."""
  # Load image from file location
  image = Image.open(file_location).convert('RGB')

  # If image is JPG/GIF perform extra processing to image
  if image.format == 'JPG':
    image = ImageOps.autocontrast(image)
  elif image.format == 'GIF':
    # Need to equalize to change gif to something that can be converted.
    image = ImageOps.equalize(image)

  # Blur image and reduce number of colors to bit_depth
  image = image.convert('P',
                        palette=Image.ADAPTIVE,
                        colors=bit_depth).convert('RGB')

  processed_image = image.copy()

  # Keep only most common color in large area
  processed_image = processed_image.filter(ImageFilter.BLUR)

  # Low-pass filter
  for x in xrange(processed_image.size[0]):
    for y in xrange(processed_image.size[1]):
      r, g, b = processed_image.getpixel((x, y))
      if r < 50 and g < 50 and b < 50:
        processed_image.putpixel((x, y), (0, 0, 0))
      else:
        processed_image.putpixel((x, y), (r, g, b))

  # Set final width to at most final_width
  width, height = processed_image.size
  final_width = min(width, final_width)

  # Add border to image before shrinking
  processed_image = AddBorderToImage(processed_image)

  thumbnail_size = thumbnail_width, thumbnail_width * height/width
  final_size = final_width, final_width * height/width
  # Shrink image while keeping aspect ratio
  processed_image.thumbnail(thumbnail_size, Image.ADAPTIVE)
  # Resize back, resulting in pixelized image
  processed_image = processed_image.resize(final_size, Image.NEAREST)
  # Back to RGB format
  processed_image = processed_image.convert('RGB',
                                            palette=Image.ADAPTIVE,
                                            colors=bit_depth)

  # Add a random quote to the image
  processed_image = AddRandomTextToImage(processed_image)

  return processed_image


def GetImageWrappedText(img_width, draw, text, font):
  """Returns a list of sentence segments that will fit within an image."""
  words = text.split(' ')
  msg = []
  sentence = ''
  words.reverse()
  while words:
    w = draw.textsize(sentence + words[-1], font=font)[0]
    if w >= img_width-20:
      msg.append(sentence)
      sentence = ''
    if sentence:
      sentence += ' '
    sentence += words.pop()
  if sentence:
    msg.append(sentence)
  return msg


def AddTextToImage(image, text):
  """Adds text along the bottom of the image, meme style."""
  draw = ImageDraw.Draw(image)
  width, height = image.size
  lines = GetImageWrappedText(width, draw, text, FONT)
  text_width, text_height = draw.textsize('A', font=FONT)
  start_height_offset = max(10, text_height * len(lines))

  image = DrawBlurredRectangle(image,
                               [0, height-10,
                                width,
                                height-start_height_offset-10])

  # image is changed, re-set draw.
  draw = ImageDraw.Draw(image)

  for line in lines:
    text_width, text_height = draw.textsize(line, font=FONT)
    draw.text(((width-text_width)/2, height-start_height_offset-10), line,
              font=FONT,
              fill=settings.QUOTE_TEXT_COLOR)
    start_height_offset -= text_height
  return image


def AddRandomTextToImage(image):
  """Adds text along the bottom of the image, meme style."""
  return AddTextToImage(image, choice(quotes))


def AddBorderToImage(image,
                     edge_size_px=settings.BORDER_EDGE_SIZE_PIXELS,
                     color=settings.BORDER_COLOR):
  """Adds a border around a given image with given fill color."""
  draw = ImageDraw.Draw(image)
  width, height = image.size
  # Top across
  draw.rectangle([(0, 0), (width, edge_size_px)], fill=color)
  # Bottom across
  draw.rectangle([(0, height-edge_size_px), (width, height)], fill=color)
  # Left side
  draw.rectangle([(0, 0), (edge_size_px, height)], fill=color)
  # Right
  draw.rectangle([(width-edge_size_px, 0), (width, height)], fill=color)
  return image


def DrawBlurredRectangle(image, bbox, alpha=0.6):
  """Blends a rectangle into the image with given alpha."""
  # Blend image
  other = image.copy()
  # other = Image.new(image.mode, image.size)

  draw = ImageDraw.Draw(other)
  # Draw rectangle before text
  draw.rectangle([(bbox[0], bbox[1]), (bbox[2], bbox[3])],
                 fill=settings.QUOTE_BG_COLOR)

  # other = other.filter(ImageFilter.BLUR)

  return Image.blend(image, other, alpha)
