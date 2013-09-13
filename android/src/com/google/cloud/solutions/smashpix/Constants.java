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

import java.util.logging.Level;

/**
 * Application constants.
 */
public class Constants {
  // Application name.
  public static final String APP_NAME = "Smashpix";

  // Intent onActivityResult result codes.
  public static final int TAKE_PICTURE = 1;
  public static final int SELECT_PICTURE = 2;

  // Server Client ID for endpoints connection.
  private static final String API_KEY = "[ENTER YOUR CLIENT_ID_WEB_APPLICATION]";

  public static final Level LOGGING_LEVEL = Level.ALL;
}
