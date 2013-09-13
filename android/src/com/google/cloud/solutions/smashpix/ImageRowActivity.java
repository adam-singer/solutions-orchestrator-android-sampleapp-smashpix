/*
 * Copyright 2013 Google Inc. All Rights Reserved.
 * 
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 * 
 * http://www.apache.org/licenses/LICENSE-2.0
 * 
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
*/

package com.google.cloud.solutions.smashpix;

import android.content.Context;
import android.content.res.Resources;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Typeface;
import android.os.AsyncTask;
import android.util.DisplayMetrics;
import android.util.Log;
import android.view.LayoutInflater;
import android.view.View;
import android.view.View.OnClickListener;
import android.view.ViewGroup;
import android.widget.BaseAdapter;
import android.widget.ImageView;
import android.widget.ImageView.ScaleType;
import android.widget.TextView;

import com.appspot.[ENTER YOUR APPENGINE_ID].image.model.ServicesListImage;

import java.io.InputStream;
import java.net.URL;
import java.util.ArrayList;

/**
 * This Activity renders each image row into the main ListView.
 */
public class ImageRowActivity extends BaseAdapter {
  private final ArrayList pictureArrayList;
  private final DisplayMetrics displayMetrics;
  private final LayoutInflater layoutInflater;
  private final Resources getResources;

  private static class PictureListRow {
    ImageView pictureImageView;
    TextView pictureTextView;
  }

  public ImageRowActivity(Context context, ArrayList pictureArrayList) {
    this.pictureArrayList = pictureArrayList;
    this.getResources = context.getResources();
    this.displayMetrics = this.getResources.getDisplayMetrics();
    this.layoutInflater = LayoutInflater.from(context);
  }

  @Override
  public View getView(int position, View convertView, ViewGroup parent) {
    final PictureListRow pictureRow;
    if (convertView == null) {
      convertView = this.layoutInflater.inflate(R.layout.image_row, null);

      pictureRow = new PictureListRow();
      pictureRow.pictureImageView = (ImageView) convertView.findViewById(R.id.picture);
      pictureRow.pictureTextView = (TextView) convertView.findViewById(R.id.pictureInfo);

      convertView.setTag(pictureRow);
    } else {
      pictureRow = (PictureListRow) convertView.getTag();
    }

    final ServicesListImage image = (ServicesListImage) pictureArrayList.get(position);

    if (image.getImage8bitLink() != null) {
      new DownloadImageTask(pictureRow.pictureImageView).execute(image.getImage8bitLink());
      pictureRow.pictureImageView.setTag(image.getImage8bitLink());
      pictureRow.pictureImageView.setScaleType(ScaleType.FIT_CENTER);
      pictureRow.pictureImageView.setOnClickListener(new OnClickListener() {
        @Override
        public void onClick(View v) {
          // Toggle between original and processed image.
          if (pictureRow.pictureImageView.getTag() == image.getImage8bitLink()) {
            pictureRow.pictureImageView.setTag(image.getImageLink());
          } else  {
            pictureRow.pictureImageView.setTag(image.getImage8bitLink());
          }
          new DownloadImageTask(pictureRow.pictureImageView).execute(
              pictureRow.pictureImageView.getTag().toString());
        }
      });
      pictureRow.pictureTextView.setTypeface(null, Typeface.BOLD);
      pictureRow.pictureTextView.setText(image.getUser() + ": " + image.getTimestamp());
    } else {
      // Load original image if processed image not found.
      new DownloadImageTask(pictureRow.pictureImageView).execute(image.getImageLink());
      pictureRow.pictureImageView.setTag(image.getImageLink());
      pictureRow.pictureTextView.setText(this.getResources.getString(R.string.processing_picture));
    }
    return convertView;
  }

  @Override
  public Object getItem(int position) {
    return pictureArrayList.get(position);
  }

  @Override
  public long getItemId(int position) {
    return position;
  }

  @Override
  public int getCount() {
    return pictureArrayList.size();
  }

  // Download images asynchronously for each image row.
  private class DownloadImageTask extends AsyncTask<String, Void, Bitmap> {
    private final ImageView downloadedPictureImageView;

    public DownloadImageTask(ImageView downloadedPictureImageView) {
      this.downloadedPictureImageView = downloadedPictureImageView;
    }

    @Override
    protected Bitmap doInBackground(String... urls) {
      String pictureUrl = urls[0];
      Bitmap pictureBitmap = null;
      try {
        InputStream inputStream = new URL(pictureUrl).openStream();
        pictureBitmap = BitmapFactory.decodeStream(inputStream);
        return pictureBitmap;
      } catch (Exception e) {
        Log.e(Constants.APP_NAME, "Image Download Error.");
      }
      return null;
    }

    @Override
    protected void onPostExecute(Bitmap response) {
      downloadedPictureImageView.setImageBitmap(response);
      if (response != null) {
        downloadedPictureImageView.getLayoutParams().height =
            response.getHeight() * (displayMetrics.densityDpi / DisplayMetrics.DENSITY_DEFAULT);
      }
    }
  }
}
