import cv2

ARUCO_DICTS = [
    ("DICT_4X4_50",    cv2.aruco.DICT_4X4_50,    50),
    ("DICT_4X4_100",   cv2.aruco.DICT_4X4_100,   100),
    ("DICT_4X4_250",   cv2.aruco.DICT_4X4_250,   250),
    ("DICT_4X4_1000",  cv2.aruco.DICT_4X4_1000,  1000),
    ("DICT_5X5_50",    cv2.aruco.DICT_5X5_50,    50),
    ("DICT_5X5_100",   cv2.aruco.DICT_5X5_100,   100),
    ("DICT_5X5_250",   cv2.aruco.DICT_5X5_250,   250),
    ("DICT_5X5_1000",  cv2.aruco.DICT_5X5_1000,  1000),
    ("DICT_6X6_50",    cv2.aruco.DICT_6X6_50,    50),
    ("DICT_6X6_100",   cv2.aruco.DICT_6X6_100,   100),
    ("DICT_6X6_250",   cv2.aruco.DICT_6X6_250,   250),
    ("DICT_6X6_1000",  cv2.aruco.DICT_6X6_1000,  1000),
    ("DICT_7X7_50",    cv2.aruco.DICT_7X7_50,    50),
    ("DICT_7X7_100",   cv2.aruco.DICT_7X7_100,   100),
    ("DICT_7X7_250",   cv2.aruco.DICT_7X7_250,   250),
    ("DICT_7X7_1000",  cv2.aruco.DICT_7X7_1000,  1000),
]

APRILTAG_DICTS = [
    ("DICT_APRILTAG_16h5",  cv2.aruco.DICT_APRILTAG_16h5,  30),
    ("DICT_APRILTAG_25h9",  cv2.aruco.DICT_APRILTAG_25h9,  35),
    ("DICT_APRILTAG_36h10", cv2.aruco.DICT_APRILTAG_36h10, 2320),
    ("DICT_APRILTAG_36h11", cv2.aruco.DICT_APRILTAG_36h11, 587),
]

ALL_DICTS = ARUCO_DICTS + APRILTAG_DICTS
