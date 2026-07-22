#!/usr/bin/env python3
"""
main.py

Simple photobooth application.

Workflow
--------
1. Display a fullscreen mirrored webcam preview.
2. Wait for the user to press "P".
3. Display a live countdown (3, 2, 1).
4. Capture the image.
5. Display the captured image for three seconds.
6. Print the image.
7. Return to the mirrored preview.

This file intentionally contains almost no image-processing code.
Everything is delegated to photobooth_utils.py.
"""

import os
import time
import logging

import cv2

from photobooth_utils import (
    get_display_resolution,
    setup_fullscreen_window,
    open_camera,
    crop_and_resize,
    draw_countdown,
    save_photo,
    print_photo,
    flash_screen,
    frame_photo,
    rotate_screen,
    hide_mouse
)


##############################################################################
# Configuration
##############################################################################

WINDOW_NAME = "Photobooth"

CAMERA_INDEX = 0

COUNTDOWN_SECONDS = 10

PHOTO_DISPLAY_SECONDS = 3

PHOTO_DIRECTORY = "photos"


ROTATION = "left"        # or "left", "right", "flip", "normal"
HIDE_MOUSE = True

##############################################################################
# Logging
##############################################################################

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
)


##############################################################################
# Main
##############################################################################

def main():
    """
    Runs the photobooth forever.
    """

    logging.info("Starting photobooth.")

    os.makedirs(PHOTO_DIRECTORY, exist_ok=True)

    screen_width, screen_height = get_display_resolution()

    logging.info(
        "Detected monitor resolution: %d x %d",
        screen_width,
        screen_height,
    )

    setup_fullscreen_window(WINDOW_NAME)

    camera = open_camera(CAMERA_INDEX)

    if ROTATION is not None:
        rotate_screen(ROTATION)

    if HIDE_MOUSE:
        hide_mouse()

    while True:

        ######################################################################
        # Live mirror mode
        ######################################################################

        while True:

            success, frame = camera.read()

            if not success:
                logging.warning("Failed to read webcam frame.")
                continue

            frame = cv2.flip(frame, 1)

            frame = crop_and_resize(
                frame,
                screen_width,
                screen_height,
            )

            cv2.imshow(WINDOW_NAME, frame)

            key = cv2.waitKey(1) & 0xFF

            #
            # Press P to take a photo.
            #
            if key == ord("p"):
                break

            #
            # ESC exits during development.
            #
            if key == 27:
                camera.release()
                cv2.destroyAllWindows()
                return

        ######################################################################
        # Countdown
        ######################################################################

        logging.info("Countdown started.")

        captured = None

        for seconds_remaining in range(COUNTDOWN_SECONDS, 0, -1):

            start = time.time()

            while time.time() - start < 1.0:

                success, frame = camera.read()

                if not success:
                    continue

                frame = cv2.flip(frame, 1)

                frame = crop_and_resize(
                    frame,
                    screen_width,
                    screen_height,
                )

                frame = draw_countdown(
                    frame,
                    seconds_remaining,
                )

                cv2.imshow(WINDOW_NAME, frame)

                cv2.waitKey(1)

        ######################################################################
        # Capture image
        ######################################################################

        #
        # Flush a few frames so we capture the newest image.
        #
        for _ in range(5):
            camera.read()

        success, captured = camera.read()

        if not success:
            logging.warning("Failed to capture image.")
            continue

        captured = cv2.flip(captured, 1)

        captured = crop_and_resize(
            captured,
            screen_width,
            screen_height,
        )





        ##########################################################################
        # Flash + Display image
        ##########################################################################

        flash_screen(
            WINDOW_NAME,
            screen_width,
            screen_height,
        )

        display_image = frame_photo(
            captured,
            screen_width,
            screen_height,
        )

        logging.info("Displaying captured image.")

        cv2.imshow(
            WINDOW_NAME,
            display_image,
        )

        cv2.waitKey(PHOTO_DISPLAY_SECONDS * 1000)

        ######################################################################
        # Save image
        ######################################################################

        filename = save_photo(
            captured,
            PHOTO_DIRECTORY,
        )

        logging.info("Saved %s", filename)

        ######################################################################
        # Print image
        ######################################################################

        try:
            print_photo(filename)
            logging.info("Print complete.")

        except Exception as exc:

            #
            # Don't let printer failures kill the booth.
            #
            logging.exception(exc)

        ######################################################################
        # Back to live preview
        ######################################################################

        logging.info("Returning to mirror mode.")


##############################################################################
# Entry point
##############################################################################

if __name__ == "__main__":
    main()