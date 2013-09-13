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

import com.google.api.client.extensions.android.http.AndroidHttp;
import com.google.api.client.googleapis.extensions.android.gms.auth.GoogleAccountCredential;
import com.google.api.client.json.gson.GsonFactory;

import android.accounts.Account;
import android.accounts.AccountManager;
import android.app.Activity;
import android.app.AlertDialog;
import android.app.ProgressDialog;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.pm.ActivityInfo;
import android.content.res.Configuration;
import android.database.Cursor;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.net.Uri;
import android.os.AsyncTask;
import android.os.Bundle;
import android.os.Environment;
import android.provider.MediaStore;
import android.util.Log;
import android.view.Menu;
import android.view.MenuItem;
import android.view.View;
import android.widget.ListView;

import com.appspot.[ENTER YOUR APPENGINE_ID].image.Image;
import com.appspot.[ENTER YOUR APPENGINE_ID].image.model.ServicesListImage;
import com.appspot.[ENTER YOUR APPENGINE_ID].image.model.ServicesListImagesResponse;
import com.appspot.[ENTER YOUR APPENGINE_ID].image.model.ServicesStorageSignedUrlRequest;
import com.appspot.[ENTER YOUR APPENGINE_ID].image.model.ServicesStorageSignedUrlResponse;

import org.apache.http.HttpResponse;
import org.apache.http.client.ClientProtocolException;
import org.apache.http.client.HttpClient;
import org.apache.http.client.methods.HttpPost;
import org.apache.http.entity.mime.HttpMultipartMode;
import org.apache.http.entity.mime.MultipartEntity;
import org.apache.http.entity.mime.content.FileBody;
import org.apache.http.entity.mime.content.StringBody;
import org.apache.http.impl.client.DefaultHttpClient;

import java.io.File;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.UnsupportedEncodingException;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.logging.Logger;

/**
 * This is the Main application Activity.
 */
public class MainActivity extends Activity {
  ListView imagesList;

  Image service;
  GoogleAccountCredential credential;

  private static File imageStoragePath;
  private static File imageStorageDirectory;
  private static String accountName;

  private static final String PICASA_URI_PREFIX = "/picasa/item/";
  private static final String PICASA_FILENAME_PREFIX = "picasa_item_";
  private static final String CAMERA_FILENAME_PREFIX = "IMG_";
  private static final String PNG_EXTENSION = ".png";
  private static final String JPEG_EXTENSION = ".jpg";

  private static final String LOGGER_NAME = "com.google.api.client";
  private static final String ACCOUNT_TYPE = "com.google";
  private static final String AUDIENCE_NAMESPACE = "server:client_id:";

  private static final String DATETIME_FORMAT = "yyyyMMdd_HHmmss";

  private static final String INTENT_IMAGE_PICK_FILTER = "image/*";
  private static final String IMAGE_CAPTURE_INTENT = "android.media.action.IMAGE_CAPTURE";
  private static final Integer BITMAP_QUALITY = 100;

  private static final Integer IMAGE_LOAD_LIMIT = 25;
  private static final Integer IMAGE_LOAD_OFFSET = 0;

  /*  Activity methods  */
  @Override
  protected void onCreate(Bundle savedInstanceState) {
    super.onCreate(savedInstanceState);
    setContentView(R.layout.activity_main);

    createImageStorageDirectory();
    setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_PORTRAIT);
    Logger.getLogger(LOGGER_NAME).setLevel(Constants.LOGGING_LEVEL);

    AccountManager accountManager = AccountManager.get(this);
    Account[] accounts = accountManager.getAccountsByType(ACCOUNT_TYPE);
    accountName = accounts[0].name;

    credential =
        GoogleAccountCredential.usingAudience(this, AUDIENCE_NAMESPACE + Constants.WEB_CLIENT_ID);
    credential.setSelectedAccountName(accountName);
    Image.Builder builder = new Image.Builder(
      AndroidHttp.newCompatibleTransport(),
      new GsonFactory(),
      credential);
    builder.setApplicationName(Constants.APP_NAME);
    service = builder.build();

    listImages();
  }

  @Override
  public void onConfigurationChanged(Configuration newConfig) {
    super.onConfigurationChanged(newConfig);
  }

  @Override
  public boolean onCreateOptionsMenu(Menu menu) {
    getMenuInflater().inflate(R.menu.main, menu);
    return true;
  }

  @Override
  public boolean onOptionsItemSelected(MenuItem item) {
    switch (item.getItemId()) {
      case R.id.actionBarRefresh:
        listImages();
        break;
      case R.id.actionBarPicture:
        getPicture();
        break;
      case R.id.actionBarCamera:
        takePicture();
        break;
    }
    return true;
  }

  @Override
  protected void onActivityResult(int requestCode, int resultCode, Intent data) {
    super.onActivityResult(requestCode, resultCode, data);
    if (resultCode == Activity.RESULT_OK) {
      if (requestCode == Constants.TAKE_PICTURE) {
        new UploadImageTask(this).execute();
      } else if (requestCode == Constants.SELECT_PICTURE) {
        if (data.getData().getPath().startsWith(PICASA_URI_PREFIX))  {
          new DownloadGooglePhotoTask(this).execute(data.getData());
        } else  {
          imageStoragePath = new File(getPathFromData(data.getData()));
          new UploadImageTask(this).execute();
        }
      }
    }
  }

  public String getPathFromData(Uri uri) {
    try {
      String[] filePathData = {MediaStore.Images.Media.DATA};
      Cursor cursor = getContentResolver().query(uri, filePathData, null, null, null);
      cursor.moveToFirst();
      int dataColumnIndex = cursor.getColumnIndex(MediaStore.Images.Media.DATA);
      String picturePath = cursor.getString(dataColumnIndex);
      cursor.close();
      return picturePath;
    } catch (Exception e) {
      Log.e(Constants.APP_NAME, e.getMessage());
    }
    return uri.getPath();
  }

  /**
   * Gets current list of images from server.
   */
  private void listImages() {
    new ListImageTask(this).execute(IMAGE_LOAD_LIMIT, IMAGE_LOAD_OFFSET);
  }

  /**
   * Creates a local directory to store application images.
   */
  private void createImageStorageDirectory() {
    String externalStorageDirectory = Environment.getExternalStorageDirectory().getAbsolutePath();
    imageStorageDirectory = new File(externalStorageDirectory, Constants.APP_NAME);
    if (!imageStorageDirectory.exists())   {
      imageStorageDirectory.mkdirs();
    }
  }

  /**
   * Takes a picture and stores the image locally.
   */
  public void takePicture()  {
    String timeStamp = new SimpleDateFormat(DATETIME_FORMAT).format(new Date());
    String imageFileName = CAMERA_FILENAME_PREFIX + timeStamp + JPEG_EXTENSION;
    imageStoragePath = new File(imageStorageDirectory, imageFileName);
    Uri imageStorageUri = Uri.fromFile(imageStoragePath);

    Intent intent = new Intent(IMAGE_CAPTURE_INTENT);
    intent.putExtra(MediaStore.EXTRA_OUTPUT, imageStorageUri);
    startActivityForResult(intent, Constants.TAKE_PICTURE);
  }

  /**
   * Gets a picture from the built in image gallery.
   */
  public void getPicture()  {
    Intent intent = new Intent(Intent.ACTION_PICK,
        android.provider.MediaStore.Images.Media.EXTERNAL_CONTENT_URI);
    intent.setType(INTENT_IMAGE_PICK_FILTER);
    startActivityForResult(Intent.createChooser(intent,
        getResources().getString(R.string.select_image)), Constants.SELECT_PICTURE);
  }

  /**
   * Gets signed URL parameters to upload image to Google Cloud Storage.
   *
   * @param imageStoragePath the image storage path.
   * @return {@link ServicesStorageSignedUrlResponse}.
   */
  public ServicesStorageSignedUrlResponse getSignedUrlParams(File imageStoragePath){
    try {
      ServicesStorageSignedUrlRequest request = new ServicesStorageSignedUrlRequest();
      if (imageStoragePath == null)  {
        Log.d(Constants.APP_NAME, "Broken image path");
        return null;
      }
      request.setFilename(imageStoragePath.getName());
      request.setOwner(accountName);
      return service.upload().storagesignedurl(request).execute();
    } catch (IOException e) {
      Log.d(Constants.APP_NAME, "Unable to get signed url credentials.");
    }
    return null;
  }

  public void notifyDialog(Activity activity, String dialogTitle, String dialogMessage){
    new AlertDialog.Builder(activity)
      .setTitle(dialogTitle)
      .setMessage(dialogMessage)
      .setPositiveButton(getResources().getString(R.string.ok),
          new DialogInterface.OnClickListener() {
            public void onClick(DialogInterface dialog, int which) {
              dialog.dismiss();
            }
          })
      .show();
  }

  /**
   * Uploads the image to Google Cloud Storage.
   */
  public Boolean uploadToCloudStorage(ServicesStorageSignedUrlResponse signedUrlParams,
    File localImageStoragePath){
    if (!signedUrlParams.isEmpty() && localImageStoragePath.exists())  {
      FileBody binary = new FileBody(localImageStoragePath);
      HttpClient httpClient = new DefaultHttpClient();
      HttpPost httpPost = new HttpPost(signedUrlParams.getFormAction());
      MultipartEntity entity = new MultipartEntity(HttpMultipartMode.BROWSER_COMPATIBLE);
      try {
        entity.addPart("bucket", new StringBody(signedUrlParams.getBucket()));
        entity.addPart("key", new StringBody(signedUrlParams.getFilename()));
        entity.addPart("policy", new StringBody(signedUrlParams.getPolicy()));
        entity.addPart("signature", new StringBody(signedUrlParams.getSignature()));
        entity.addPart("x-goog-meta-owner", new StringBody(accountName));
        entity.addPart("GoogleAccessId", new StringBody(signedUrlParams.getGoogleAccessId()));
        entity.addPart("file", binary);
      } catch (UnsupportedEncodingException e) {
        Log.e(Constants.APP_NAME, e.getMessage());
        return false;
      }

      httpPost.setEntity(entity);
      HttpResponse httpResponse;
      try {
        httpResponse = httpClient.execute(httpPost);
        if (httpResponse.getStatusLine().getStatusCode() == 204) {
          Log.i(Constants.APP_NAME, "Image Uploaded");
          return true;
        }
      } catch (ClientProtocolException e) {
          Log.e(Constants.APP_NAME, e.getMessage());
      } catch (IOException e) {
          Log.e(Constants.APP_NAME, e.getMessage());
      }
    }
    Log.e(Constants.APP_NAME, "Image Upload Failed");
    return false;
  }

  /*
   * AsyncTasks.
   */

  // Uploads an image asynchronously from the client to Google Cloud Storage.
  private class UploadImageTask extends AsyncTask<Void, Void, Boolean> {
    private final Activity activity;
    private final ProgressDialog uploadingDialog;
    private final ListView listView;

    public UploadImageTask(Activity activity) {
      this.activity = activity;
      this.listView = (ListView) findViewById(R.id.imagesList);
      this.listView.setVisibility(View.INVISIBLE);
      this.uploadingDialog =
        ProgressDialog.show(this.activity, getResources().getString(R.string.uploading),
            getResources().getString(R.string.send_for_processing, true));
    }

    @Override
    protected Boolean doInBackground(Void... unused) {
      // Get signed URL parameters to post image to Google Cloud Storage.
      ServicesStorageSignedUrlResponse signedUrlParams = getSignedUrlParams(imageStoragePath);
      if (signedUrlParams != null && !signedUrlParams.isEmpty() && imageStoragePath.exists())   {
        return uploadToCloudStorage(signedUrlParams, imageStoragePath);
      }
      return false;
    }

    @Override
    protected void onPostExecute(Boolean results) {
      this.uploadingDialog.dismiss();
      if (!results)  {
        notifyDialog(this.activity, getResources().getString(R.string.upload_error),
            getResources().getString(R.string.upload_error_notice));
      }
      this.listView.setVisibility(View.VISIBLE);
    }
  }

  // Requests list of images asynchronously from the server to display to the main image stream.
  private class ListImageTask extends AsyncTask<Integer, Void, ServicesListImagesResponse>{
    private final Activity activity;
    private final ProgressDialog loadingDialog;

    public ListImageTask(Activity activity) {
      this.activity = activity;
      this.loadingDialog = ProgressDialog.show(this.activity,
          getResources().getString(R.string.loading),
          getResources().getString(R.string.loading_pictures),
          true);
    }

    @Override
    protected ServicesListImagesResponse doInBackground(Integer... params) {
      ServicesListImagesResponse imageListResponse = null;
      if (params.length == 2)  {
        try {
          imageListResponse = service.list().images().setLimit((long) params[0]).
              setOffset((long) params[1]).execute();
        } catch (IOException e) {
          Log.e(Constants.APP_NAME, "Unable to connect to server.");
        }
      } else {
        Log.e(Constants.APP_NAME, "Missing offset and limit request parameters.");
      }
      return imageListResponse;
    }

    @Override
    protected void onPostExecute(ServicesListImagesResponse imageListResponse) {
      ArrayList<ServicesListImage> imageList = new ArrayList<ServicesListImage>();
      if (imageListResponse == null) {
        notifyDialog(this.activity, getResources().getString(R.string.connection_error),
            getResources().getString(R.string.unable_to_connect));
      } else if (imageListResponse.getImages().isEmpty()) {
        notifyDialog(this.activity, getResources().getString(R.string.empty_list),
            getResources().getString(R.string.empty_image_list));
      } else {
        for (ServicesListImage image : imageListResponse.getImages()) {
          imageList.add(image);
        }
      }
      ListView imageListView = (ListView) findViewById(R.id.imagesList);
      imageListView.setAdapter(new ImageRowActivity(this.activity, imageList));
      this.loadingDialog.dismiss();
    }
  }

  // Downloads an images from Google Photos asynchronously.
  private class DownloadGooglePhotoTask extends AsyncTask<Uri, Void, Void>{
    private final Activity activity;
    private final ProgressDialog loadingDialog;

    public DownloadGooglePhotoTask(Activity activity) {
      this.activity = activity;
      ListView imageListView = (ListView) findViewById(R.id.imagesList);
      imageListView.setVisibility(View.INVISIBLE);
      this.loadingDialog = ProgressDialog.show(this.activity,
          getResources().getString(R.string.loading),
          getResources().getString(R.string.loading_google_photos),
          true);
    }

    @Override
    protected Void doInBackground(Uri... params) {
      BitmapFactory.Options options = new BitmapFactory.Options();
      try {
        final InputStream inputStream =
          getApplicationContext().getContentResolver().openInputStream(params[0]);
        final Bitmap bitmap = BitmapFactory.decodeStream(inputStream, null, options);

        String imageFileName =
            params[0].getPath().replace(PICASA_URI_PREFIX, PICASA_FILENAME_PREFIX) + PNG_EXTENSION;
        imageStoragePath = new File(imageStorageDirectory, imageFileName);
        FileOutputStream outStream = new FileOutputStream(imageStoragePath);
        bitmap.compress(Bitmap.CompressFormat.PNG, BITMAP_QUALITY, outStream);
        outStream.flush();
        outStream.close();
        inputStream.close();
      } catch (FileNotFoundException e) {
        Log.e(Constants.APP_NAME, e.getMessage());
      } catch (IOException e) {
        Log.e(Constants.APP_NAME, e.getMessage());
      }
      return null;
    }

    @Override
    protected void onPostExecute(Void unused) {
      this.loadingDialog.dismiss();
      new UploadImageTask(this.activity).execute();
    }
  }
}
