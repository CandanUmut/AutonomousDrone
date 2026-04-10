"""
ArUco marker detector for precision landing.

Provides:
    ArucoDetector — single marker pose estimation from a camera image.

This module is used by the MAVSDK companion stack when ROS 2 is not available.
For the ROS 2 simulation stack, precision_landing_node.py contains an
equivalent implementation using cv_bridge.

Requirements:
    opencv-contrib-python >= 4.7  (for cv2.aruco)
    numpy

Usage:
    detector = ArucoDetector(marker_id=0, marker_size_m=0.5)
    result = detector.detect(image_bgr, camera_matrix, dist_coeffs)
    if result is not None:
        x_err, y_err, z_dist = result
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import cv2
import cv2.aruco as aruco
import numpy as np

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MarkerPose:
    """Pose of the ArUco marker relative to the camera."""

    x_m: float   # Lateral offset (camera frame +X = right)
    y_m: float   # Longitudinal offset (camera frame +Y = down in image)
    z_m: float   # Distance from camera to marker
    # Body-frame offsets (positive = need to move this way to centre)
    body_x_err: float  # Forward error (drone must move forward by this)
    body_y_err: float  # Lateral error  (drone must move right by this)


class ArucoDetector:
    """
    Detects a single ArUco marker and estimates its 3-D pose.

    Parameters
    ----------
    marker_id : int
        ArUco marker ID to track (from DICT_4X4_50 by default).
    marker_size_m : float
        Physical side length of the printed marker in metres.
    aruco_dict_type : int
        cv2.aruco dictionary constant. Default: DICT_4X4_50.
    camera_offset_x : float
        Camera mounting offset from drone CG in body +X direction (metres).
    camera_offset_y : float
        Camera mounting offset from drone CG in body +Y direction (metres).
    """

    def __init__(
        self,
        marker_id: int = 0,
        marker_size_m: float = 0.5,
        aruco_dict_type: int = aruco.DICT_4X4_50,
        camera_offset_x: float = 0.0,
        camera_offset_y: float = 0.0,
    ) -> None:
        self._marker_id = marker_id
        self._marker_size = marker_size_m
        self._cam_offset_x = camera_offset_x
        self._cam_offset_y = camera_offset_y

        aruco_dict = aruco.getPredefinedDictionary(aruco_dict_type)
        aruco_params = aruco.DetectorParameters()
        self._detector = aruco.ArucoDetector(aruco_dict, aruco_params)

    def detect(
        self,
        image_bgr: np.ndarray,
        camera_matrix: np.ndarray,
        dist_coeffs: np.ndarray,
    ) -> MarkerPose | None:
        """
        Detect the target marker and return its pose, or None if not found.

        Args:
            image_bgr:      OpenCV BGR image (HxWx3 uint8).
            camera_matrix:  3×3 intrinsic matrix.
            dist_coeffs:    Distortion coefficients (1×4, 1×5, or 1×8).

        Returns:
            MarkerPose with body-frame error vectors, or None.
        """
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = self._detector.detectMarkers(gray)

        if ids is None:
            return None

        flat_ids = ids.flatten()
        if self._marker_id not in flat_ids:
            return None

        idx = int(np.where(flat_ids == self._marker_id)[0][0])
        target_corners = corners[idx]

        rvec, tvec, _ = aruco.estimatePoseSingleMarkers(
            target_corners, self._marker_size, camera_matrix, dist_coeffs
        )

        tx, ty, tz = (
            float(tvec[0][0][0]),
            float(tvec[0][0][1]),
            float(tvec[0][0][2]),
        )

        # For a downward-facing camera (pointing nadir):
        #   camera +X  → body +Y (right)
        #   camera +Y  → body -X (backward in image top-down view)
        #   camera +Z  → body -Z (down, toward marker)
        # Error = how far the drone must move to centre over marker:
        body_x_err = -ty - self._cam_offset_x   # forward
        body_y_err = tx - self._cam_offset_y    # lateral

        return MarkerPose(
            x_m=tx,
            y_m=ty,
            z_m=tz,
            body_x_err=body_x_err,
            body_y_err=body_y_err,
        )

    # ------------------------------------------------------------------
    @staticmethod
    def build_camera_matrix(
        fx: float, fy: float, cx: float, cy: float
    ) -> np.ndarray:
        """Convenience builder for the camera intrinsic matrix."""
        return np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]], dtype=float)

    @staticmethod
    def generate_marker_png(marker_id: int, size_px: int = 256) -> np.ndarray:
        """
        Generate a printable ArUco marker image.

        Returns an HxW uint8 grayscale image suitable for saving with
        cv2.imwrite(). Print at 5×5 cm → use a ruler to verify exact size.
        """
        aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
        marker_img = aruco.generateImageMarker(aruco_dict, marker_id, size_px)
        return marker_img

    @staticmethod
    def draw_pose_axes(
        image_bgr: np.ndarray,
        camera_matrix: np.ndarray,
        dist_coeffs: np.ndarray,
        rvec: np.ndarray,
        tvec: np.ndarray,
        length: float = 0.1,
    ) -> np.ndarray:
        """Draw XYZ pose axes on the image for visual debugging."""
        cv2.drawFrameAxes(image_bgr, camera_matrix, dist_coeffs, rvec, tvec, length)
        return image_bgr
