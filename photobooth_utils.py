#!/usr/bin/env python3
"""
photobooth_utils.py

Utility functions for the photobooth.

All image processing, display setup and printing lives here so that
main.py only contains the application state machine.
"""

import datetime
import numpy as np
import os
import platform
import re
import subprocess
import time

import cv2


##############################################################################
# Display
##############################################################################
def get_display_resolution():
    """
    Returns (width, height) of the primary display.
    """

    system = platform.system()

    #
    # macOS
    #
    if system == "Darwin":

        output = subprocess.check_output(
            ["system_profiler", "SPDisplaysDataType"],
            text=True,
        )

        match = re.search(r"Resolution:\s+(\d+)\s+x\s+(\d+)", output)

        if match is None:
            raise RuntimeError("Could not determine monitor resolution.")

        width, height = map(int, match.groups())

        return width, height

    #
    # Linux (Ubuntu)
    #
    elif system == "Linux":

        env = os.environ.copy()
        env["DISPLAY"] = ":0"

        output = subprocess.check_output(
            ["xrandr"],
            env=env,
            text=True,
        )

        match = re.search(r"current\s+(\d+)\s+x\s+(\d+)", output)

        if match is None:
            raise RuntimeError("Could not determine monitor resolution.")

        width, height = map(int, match.groups())

        return width, height

    else:
        raise RuntimeError(f"Unsupported operating system: {system}")


def setup_fullscreen_window(window_name):
    """
    Creates a fullscreen OpenCV window.
    """

    os.environ["DISPLAY"] = ":0"
    os.environ["QT_QPA_PLATFORM"] = "xcb"
    os.environ["GDK_BACKEND"] = "x11"

    time.sleep(2)

    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    cv2.setWindowProperty(
        window_name,
        cv2.WND_PROP_FULLSCREEN,
        cv2.WINDOW_FULLSCREEN,
    )


##############################################################################
# Camera
##############################################################################

def open_camera(camera_index=0):
    """
    Opens the webcam.

    On Linux, uses the V4L2 backend.
    On macOS, uses the default AVFoundation backend.
    """

    if platform.system() == "Linux":
        camera = cv2.VideoCapture(camera_index, cv2.CAP_V4L2)

    else:
        # macOS uses AVFoundation automatically.
        camera = cv2.VideoCapture(camera_index)

        # If camera 0 doesn't exist, try the built-in camera.
        if not camera.isOpened():
            camera.release()
            camera = cv2.VideoCapture(1)

    if not camera.isOpened():
        raise RuntimeError("Could not open webcam.")

    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

    return camera


##############################################################################
# Image Processing
##############################################################################

def crop_and_resize(frame, output_width, output_height):
    """
    Center-crops an image to match the monitor aspect ratio
    then resizes to the monitor resolution.
    """

    frame_height, frame_width = frame.shape[:2]

    target_ratio = output_width / output_height
    frame_ratio = frame_width / frame_height

    #
    # Too wide.
    #
    if frame_ratio > target_ratio:

        new_width = int(frame_height * target_ratio)

        x0 = (frame_width - new_width) // 2

        frame = frame[:, x0:x0 + new_width]

    #
    # Too tall.
    #
    else:

        new_height = int(frame_width / target_ratio)

        y0 = (frame_height - new_height) // 2

        frame = frame[y0:y0 + new_height, :]

    frame = cv2.resize(
        frame,
        (output_width, output_height),
        interpolation=cv2.INTER_LINEAR,
    )

    return frame


##############################################################################
# Countdown Overlay
##############################################################################

def draw_countdown(frame, number):
    """
    Draws a large countdown number in the middle of the screen.
    """

    image = frame.copy()

    text = str(number)

    font = cv2.FONT_HERSHEY_SIMPLEX

    scale = 8

    thickness = 12

    text_size, _ = cv2.getTextSize(
        text,
        font,
        scale,
        thickness,
    )

    x = (image.shape[1] - text_size[0]) // 2

    y = (image.shape[0] + text_size[1]) // 2

    #
    # Black outline.
    #
    cv2.putText(
        image,
        text,
        (x, y),
        font,
        scale,
        (0, 0, 0),
        thickness + 8,
        cv2.LINE_AA,
    )

    #
    # White text.
    #
    cv2.putText(
        image,
        text,
        (x, y),
        font,
        scale,
        (255, 255, 255),
        thickness,
        cv2.LINE_AA,
    )

    return image


##############################################################################
# Saving
##############################################################################

def save_photo(image, directory):
    """
    Saves a JPEG to disk.

    Returns
    -------
    str
        Full path to image.
    """

    timestamp = datetime.datetime.now().strftime(
        "%Y-%m-%d_%H-%M-%S"
    )

    filename = os.path.join(
        directory,
        f"{timestamp}.jpg",
    )

    cv2.imwrite(
        filename,
        image,
    )

    return filename


##############################################################################
# Printing
##############################################################################

def print_photo(filename, printer_name=None):
    """
    Prints an image using CUPS.

    Assumes the printer has already been configured with the
    zj-58 driver.

    Parameters
    ----------
    filename : str

    printer_name : str or None
        If None, uses the system default printer.
    """

    command = ["lp"]

    if printer_name is not None:
        command.extend(
            [
                "-d",
                printer_name,
            ]
        )

    command.append(filename)

    subprocess.run(
        command,
        check=True,
    )



def flash_screen(window_name, width, height, duration=0.15):
    """
    Displays a brief white flash.
    """

    flash = np.full(
        (height, width, 3),
        255,
        dtype=np.uint8,
    )

    cv2.imshow(window_name, flash)
    cv2.waitKey(int(duration * 1000))
def frame_photo(
    image,
    screen_width,
    screen_height,
    scale=0.82,
    border=25,
    shadow_offset=10,
):
    """
    Places the captured image on a black background with
    a white border and subtle drop shadow.
    """

    import numpy as np
    import cv2

    #
    # Resize photo.
    #
    new_width = int(screen_width * scale)
    new_height = int(screen_height * scale)

    photo = cv2.resize(
        image,
        (new_width, new_height),
        interpolation=cv2.INTER_AREA,
    )

    #
    # White border.
    #
    photo = cv2.copyMakeBorder(
        photo,
        border,
        border,
        border,
        border,
        cv2.BORDER_CONSTANT,
        value=(255, 255, 255),
    )

    #
    # Thin black outline.
    #
    cv2.rectangle(
        photo,
        (0, 0),
        (photo.shape[1] - 1, photo.shape[0] - 1),
        (0, 0, 0),
        2,
    )

    #
    # Black background.
    #
    canvas = np.zeros(
        (screen_height, screen_width, 3),
        dtype=np.uint8,
    )

    x = (screen_width - photo.shape[1]) // 2
    y = (screen_height - photo.shape[0]) // 2

    #
    # Drop shadow.
    #
    sx = x + shadow_offset
    sy = y + shadow_offset

    canvas[
        sy:sy + photo.shape[0],
        sx:sx + photo.shape[1],
    ] = (40, 40, 40)

    #
    # Photo.
    #
    canvas[
        y:y + photo.shape[0],
        x:x + photo.shape[1],
    ] = photo

    return canvas