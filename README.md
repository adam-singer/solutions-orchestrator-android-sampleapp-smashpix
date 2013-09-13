# Smashpix

## Copyright

Copyright 2013 Google Inc. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

[http://www.apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0)

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.


## Disclaimer

This sample application is not an official Google product.


## Summary
Smashpix is an image manipulation application that is built on Google's Cloud Platform. Smashpix combines several applications to showcase how developers can connect several components of the platform together.

1. Backend Server (Google App Engine + Google Cloud Storage)
2. Command line daemon (Google Compute Engine)
3. Mobile Application (Android)

The setup instructions in this README are the same as the ones you will find in the corresponding Google App Engine server code. You will need both packages for this sample to work.

Programming Languages:

* Java
* Python

Google Components:

* Google App Engine
* Google Cloud Endpoints
* Google Cloud Storage
* Android

## Download the sample code:

* [Smashpix sample application zip file](https://github.com/GoogleCloudPlatform/solutions-orchestrator-android-sampleapp-smashpix/archive/master.zip)

### Dependencies

* Make sure you have Java installed.
* Download and configure Eclipse.
* Download and configure the [Google App Engine Python SDK](https://developers.google.com/appengine/downloads#Google_App_Engine_SDK_for_Python)
* Download and configure the [Google Plugin for Eclipse for your IDE version](https://developers.google.com/eclipse/docs/getting_started)
* Download and configure the [Android SDK](http://developer.android.com/sdk/index.html)
* Download and configure the [Google Cloud Storage command line tool, gsutil](https://developers.google.com/storage/docs/gsutil)
* Download and configure the [Google Compute Engine command line tool, gcutil](https://developers.google.com/compute/docs/gcutil/)

## Creating a Google Cloud Platform project
1. Create a project using the [Google Cloud Console](https://cloud.google.com/console)
2. Enter a project name and project ID, [PROJECT\_ID]. The project ID will be your Google App Engine ID, [APPENGINE\_ID].
3. Select "Google Compute Engine" from the main project console. You will need to enable billing to use Google Compute Engine.
4. Select "APIs" from the main project console. Enable the following APIs.
    * Google Cloud Storage
    * Google Cloud Storage JSON API
    * TaskQueue API

### API Access
Create client IDs to allow authentication and authorization between components, [Using OAuth 2.0 to Access Google APIs](https://developers.google.com/accounts/docs/OAuth2).

#### Create a Client ID for web applications
1. Select your project in [https://code.google.com/apis/console/](https://code.google.com/apis/console/)
2. Select "API Access" (Left navigation)
3. Click the "Create another client ID" button
4. Under "Application type" > Select "Web application"
5. Under "Your site or hostname" > Enter site or hostname: [APPENGINE\_ID].appspot.com
6. Create client ID. This is the Client ID for your web application, [CLIENT\_ID\_WEB_APPLICATION]

#### Create a Service account
1. Select your project in [https://code.google.com/apis/console/](https://code.google.com/apis/console/)
2. Select "API Access" (Left navigation)
3. Click the "Create another client ID" button
4. Under "Application type" > Select "Service account"
5. Create client ID. This is the Service account, [SERVICE\_ACCOUNT]
7. Download private key and store it in a secure location. This is the service account private key file, [SERVICE\_ACCOUNT\_PRIVATE\_KEY]
    * Remember your private key's password.

#### Create a Client ID for installed applications

1. Generate a certificate fingerprint on your local machine.
  <pre>~$ keytool -exportcert -alias androiddebugkey -keystore ~/.android/debug.keystore | openssl sha1</pre>
2. Enter the keystore password: android
3. The returned value is the CERTIFICATE\_FINGERPRINT.
  <pre>(stdin)= [CERTIFICATE\_FINGERPRINT]</pre>
4. Select your project in [https://code.google.com/apis/console/](https://code.google.com/apis/console/)
5. Select "API Access" (Left navigation)
6. Click the "Create another client ID" button
7. Under "Application type" > Select "Installed applications"
8. Under "Installed application type" > Select "Android"
9. Enter package name: com.google.cloud.solutions.smashpix
10. Enter signing certificate fingerprint (SHA1): [CERTIFICATE\_FINGERPRINT]
11. Leave Deep Linking disabled.
12. Create client ID. This is the Client ID for your installed application, [CLIENT\_ID\_INSTALLED\_APPLICATION]


## Backend Server (Google App Engine + Google Cloud Storage)

### Dependencies

* Download the [Google Cloud Storage App Engine client](https://code.google.com/p/appengine-gcs-client/)

### Configuring the backend server (Google App Engine)

You should have downloaded the backend server sample code. Extract the files into a new directory, [BACKEND\_SERVER\_CODE].

1. Extract the Google Cloud Storage App Engine client dependency, <code>src/cloudstorage/</code>, folder into your backend server directory, [BACKEND\_SERVER\_CODE]/cloudstorage/
2. In the <code>app.yaml</code> file, replace [APPENGINE_ID] with your App Engine application ID
    <pre>application: [APPENGINE\_ID]</pre>
3. In the <code>queue.yaml</code> file, replace [SERVICE\_ACCOUNT] with the email address of the Service account
    <pre>queue:
    \- name: imagetasks
      ...
      acl: [SERVICE\_ACCOUNT]</pre>
4. In the <code>settings.cfg</code> file, replace the variable placeholders with your application variables
    * MAIN\_BUCKET: Primary Google Cloud Storage bucket to upload original images
    * BIT\_BUCKET: Google Cloud Storage bucket to store processed images
    * APP\_HOSTNAME: Full App Engine hostname, [APPENGINE\_ID].appspot.com
    * ALLOWED\_CLIENT\_IDS: Client IDs that are allowed to connect to service, [CLIENT\_ID\_INSTALLED\_APPLICATION]
    * CLIENT\_ID\_OF\_API\_SERVERS: Client IDs of the Cloud Endpoints server, [CLIENT\_ID\_WEB\_APPLICATION]
5. Upload the backend server to Google App Engine


### Configuring storage (Google Cloud Storage)

1. Obtain access credentials and create configuration file using the Service account, [SERVICE\_ACCOUNT]
    <pre>gsutil config -e</pre>
2. Create the primary bucket to upload original images, [BUCKET\_TO\_UPLOAD\_ORIGINAL\_IMAGES]
    <pre>~$ gsutil mb gs://[BUCKET\_TO\_UPLOAD\_ORIGINAL\_IMAGES]</pre>
3. Create the bucket to store processed images, [BUCKET\_TO\_STORE\_PROCESSED\_IMAGES]
    <pre>~$ gsutil mb gs://[BUCKET\_TO\_STORE\_PROCESSED\_IMAGES]</pre>
4. Configure Object Change Notification for the primary bucket to upload original images
    <pre>~$ gsutil notifyconfig watchbucket https://[APPENGINE\_ID].appspot.com/ocn \
        gs://[BUCKET\_TO\_UPLOAD\_ORIGINAL\_IMAGES]
    https://[APPENGINE\_ID].appspot.com/ocn ...
    Successfully created watch notification channel.
    Watch channel identifier: [OCN\_CHANNEL\_IDENTIFIER]
    Canonicalized resource identifier: [OCN\_RESOURCE\_IDENTIFIER]
    </pre>
5. Configure the default access controls (ACL) for both buckets
    <pre>~$ gsutil setdefacl public-read gs://[BUCKET\_TO\_UPLOAD\_ORIGINAL\_IMAGES]
    ~$ gsutil chdefacl -g AllUsers:FC gs://[BUCKET\_TO\_UPLOAD\_ORIGINAL\_IMAGES]
    ~$ gsutil setdefacl public-read gs://[BUCKET\_TO\_STORE\_PROCESSED\_IMAGES]
    ~$ gsutil chdefacl -g AllUsers:FC gs://[BUCKET\_TO\_STORE\_PROCESSED\_IMAGES]
    </pre>
6. Note: To remove Object Change Notifications
    <pre>~$ gsutil notifyconfig stopchannel [OCN_CHANNEL_IDENTIFIER] \
        [OCN_RESOURCE_IDENTIFIER]</pre>

### Testing the application
At this point, you should be able to upload images from the UI for testing purposes.

* Go to [APPENGINE\_ID].appspot.com
* On the top right, "Upload a new image"
* The UI should display an image with a second image "Image processing..."
    * Confirm the file upload in Google Cloud Storage
    * You should also see 1 task in the [App Engine console](appengine.google.com) > "Task Queues" > "imagetasks"
* To process the image, we will need to setup the Command line daemon to process image in the task queue.


## Command line daemon (Google Compute Engine)

Configure gcutil on the main system to connect your project.
    <pre>@main:~$ gcutil auth --project=[PROJECT\_ID]</pre>


### Setting up Google Compute Engine
1. Select "Google Compute Engine" from the main project console.
2. Create a "New Instance"
    * Name: smashpix-master
    * Machine Type: n1-standard-1
    * Boot Source: New presistent disk from image
    * Use default values for all other settings.
3. Go to the instance page after creation of the instance. Click "ssh" under "Equivalent REST or ssh" at the bottom of the page to obtain gcutil command line needed to SSH into the instance.
    <pre>@main:~$ gcutil --service_version="v1beta15" \
        --project="[PROJECT\_ID]" ssh --zone="[INSTANCE\_ZONE]" \
        "[INSTANCE\_NAME]"</pre>
4. SSH into the instance to set up the Command line daemon

### Setting up the Command line daemon
1. Copy the command line daemon files to the instance from your main system. "." represents the root of the home directory on the Google Compute Engine instance.
    <pre>@main:~$ gcutil --service_version="v1beta15" \
        --project="[PROJECT\_ID]" push --zone="[INSTANCE\_ZONE]" \
        "[INSTANCE\_NAME]" daemon/ .</pre>
2. Confirm that the files have been copied over
     <pre>@instance:~$ ls $HOME/daemon
compute\_engine\_daemon.py  image_processing.py  quotes.txt settings.py</pre>
3. Install command line daemon dependencies
    <pre>
    @instance:~$ sudo apt-get install python-pip python-openssl \
        python-dev
    @instance:~$ sudo apt-get install fonts-freefont-ttf libjpeg-dev \
        libpng-dev libgif-dev libtiff-dev libfreetype6-dev
    @instance:~$ sudo ln -s /usr/lib/x86\_64-linux-gnu/libjpeg.so /usr/lib
    @instance:~$ sudo ln -s /usr/lib/x86\_64-linux-gnu/libpng.so /usr/lib
    @instance:~$ sudo ln -s /usr/lib/x86\_64-linux-gnu/libtiff.so /usr/lib
    @instance:~$ sudo ln -s /usr/lib/x86\_64-linux-gnu/libz.so /usr/lib
    @instance:~$ sudo ln -s /usr/lib/x86\_64-linux-gnu/libfreetype.so /usr/lib
    # libfreetype6-dev must be installed before PIL.
    @instance:~$ sudo pip install PIL
    @instance:~$ sudo pip install google-api-python-client
    @instance:~$ sudo pip install gsutil
    </pre>
4. Copy private key over
    <pre>@main:~$ gcutil --service_version="v1beta15" \
        --project="[PROJECT\_ID]" push --zone="[INSTANCE\_ZONE]" \
        "smashpix-master" [SERVICE\_ACCOUNT\_PRIVATE\_KEY] ./.ssh/.
    </pre>
5. Configure settings file, <code>settings.py</code>
    * PROJECT\_ID: [PROJECT\_ID]
    * PROCESSED_IMG_BUCKET: Google Cloud Storage bucket to store processed images.
    * CREDENTIAL\_ACCOUNT_EMAIL: Service account email, [SERVICE\_ACCOUNT\_EMAIL]
    * PRIVATE\_KEY\_LOCATION: Service account private key, [SERVICE\_ACCOUNT\_PRIVATE\_KEY]
6. Run command line daemon
    <pre>python compute\_engine\_daemon.py &</pre>
7. Note: To add more quotes, add quotes to <code>quotes.txt</code>


### Testing the application
At this point, you should be able to view the processed image
* Go to [APPENGINE\_ID].appspot.com
* The processed image should be pixelized with a quote.


## Mobile Application (Android)

### Dependencies

* Download the [Apache HttpComponents Client](http://hc.apache.org/httpcomponents-client-ga/index.html)

### Setting up the Android project in Eclipse

You should have downloaded the mobile application sample code. Extract the files into a new directory, [MOBILE\_APP\_CODE].

1. Import the Android code into Eclipse.
    * File > New > Project...
    * Wizards > "Android Project from Existing Code"
    * Root Directory (Select folder with the mobile application code, [MOBILE\_APP\_CODE])
    * Projects to Import (Select project with the mobile application code)
2. Extract the Apache HttpComponents Client (HttpClient) file and copy the following jar files into your Android code library folder, <code>[MOBILE\_APP\_CODE]/libs/</code>.
    * <code>httpclient-[VERSION].jar</code>
    * <code>httpclient-cache-[VERSION].jar</code>
    * <code>httpcore-[VERSION].jar</code>
    * <code>httpmime-[VERSION].jar</code>
3. Generate Google Cloud Endpoints from the backend server (Google App Engine)
    * From the command line, go to the root directory of the backend server, <code>[BACKEND\_SERVER\_CODE]/</code>.
    * Create a temporary folder for the Cloud Endpoints file.
        <pre>~$ mkdir endpoints-lib/</pre>
    * Generate the Cloud Endpoints files for the Android application.
        <pre>~$ [APPENGINE\_PYTHON\_SDK]/endpointscfg.py get\_client\_lib java -o \
            endpoints-lib/. -f rest services.ImageApi</pre>
    * Extract <code>ImageApi.zip</code> and save it into <code>[BACKEND\_SERVER\_CODE]/endpoints-lib/image/libs/</code>
    * Copy the following jar files into your Android code library folder, <code>[MOBILE\_APP\_CODE]/libs/</code>.
        * <code>google-api-client-[VERSION].jar</code>
        * <code>google-api-client-android-[VERSION].jar</code>
        * <code>google-http-client-[VERSION].jar</code>
        * <code>google-http-client-android-[VERSION].jar</code>
        * <code>google-http-client-gson-[VERSION].jar</code>
        * <code>google-http-client-jackson-[VERSION].jar</code>
        * <code>google-http-client-jackson2-[VERSION].jar</code>
        * <code>google-oauth-client-[VERSION].jar</code>
        * <code>gson-[VERSION].jar</code>
        * <code>jackson-core-[VERSION].jar</code>
        * <code>jackson-core-asl-[VERSION].jar</code>
        * <code>jsr305-[VERSION].jar</code>
    * Extract <code>endpoints-lib/image/[APPENGINE_ID]-image-v[API_VERSION]-java-[VERSION]-rc-sources.jar</code> and copy the files into your source folder, <code>[MOBILE\_APP\_CODE]/src/com/appspot/[APPENGINE\_ID]/image/*</code>
4. Configure the Android code to connect to the endpoints backend server
    * Replace [CLIENT\_ID\_WEB\_APPLICATION] in <code>[MOBILE\_APP\_CODE]/src/com/google/cloud/smashpix/Constants.java</code>
    * Replace [APPENGINE\_ID] in <code>[MOBILE\_APP\_CODE]/src/com/google/cloud/smashpix/MainActivity.java</code>
    * Replace [APPENGINE\_ID] in <code>[MOBILE\_APP\_CODE]/src/com/google/cloud/smashpix/ImageRowActivity.java</code>
5. Copy the Google Play Service library
    * Browse to <code>[ANDROID\_SDK]/extras/google/google\_play\_services/libproject/google-play-services_lib/libs/</code>.
    * Copy <code>google-play-services.jar</code> into your Android code library folder, <code>[MOBILE\_APP\_CODE]/libs/</code>.
6. Make sure all code dependencies are resolved.
7. Run Android application.
LE\_APP\_CODE]/libs/</code>.
6. Make sure all code dependencies are resolved.
7. Run Android application.
