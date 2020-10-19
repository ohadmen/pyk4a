from typing import Tuple, Union, Optional
import k4a_module
from enum import Enum
import numpy as np
import json
from pyk4a.config import Config, ColorControlMode, ColorControlCommand


# k4a_wait_result_t
class Result(Enum):
    Success = 0
    Failed = 1
    Timeout = 2


class K4AException(Exception):
    pass


class K4ATimeoutException(K4AException):
    pass


class PyK4A:
    TIMEOUT_WAIT_INFINITE = -1

    def __init__(self, config=Config(), device_id=0):
        self._device_id = device_id
        self._config = config
        self.is_running = False

    def __del__(self):
        if self.is_running:
            self.disconnect()

    def connect(self):
        self._device_open()
        self._start_cameras()
        self.is_running = True

    def disconnect(self):
        self._stop_cameras()
        self._device_close()
        self.is_running = False

    def get_calibration(self, as_str: bool = False):
        calibration = k4a_module.device_get_calibration()
        if not as_str:
            calibration = json.loads(calibration)
        return calibration

    def save_calibration_json(self, path):
        calibration = self.get_calibration(True)
        with open(path, 'w') as f:
            f.write(calibration)

    def load_calibration_json(self, path):
        with open(path, 'r') as f:
            calibration = f.read()
        res = k4a_module.calibration_set_from_raw(calibration, *self._config.unpack())
        self._verify_error(res)

    def _device_open(self):
        res = k4a_module.device_open(self._device_id)
        self._verify_error(res)

    def _device_close(self):
        res = k4a_module.device_close()
        self._verify_error(res)

    def _start_cameras(self):
        res = k4a_module.device_start_cameras(*self._config.unpack())
        self._verify_error(res)

    def _stop_cameras(self):
        res = k4a_module.device_stop_cameras()
        self._verify_error(res)

    def get_capture(self, timeout=TIMEOUT_WAIT_INFINITE, transform_to_color=True, color=True, ir=True, depth=True,pcl=True):
        r"""Fetch a capture from the device and return as numpy array(s) or None.

        Arguments:
            :param depth:
            :param ir:
            :param color:
            :param timeout: Timeout in ms. Default is infinite.


        Returns:
            :return img_color [, img_depth] # image could be None if config synchronized_images_only==False

        Examples::
            - if config synchronized_images_only=True
                >>> k4a.get_capture(color_only=True) # type: np.ndarray
            - if config synchronized_images_only=False, you must check if returs for each image is None
                >>> k4a.get_capture(color_only=True) # type: Optional[np.ndarray]
                >>> k4a.get_capture() # type: Tuple[Optional[np.ndarray], Optional[np.ndarray]]
        """
        img_color = None
        img_ir = None
        img_depth = None
        img_pcl = None

        res = k4a_module.device_get_capture(timeout)
        self._verify_error(res)

        if ir:
            img_ir = self._get_capture_ir(transform_to_color)
        if depth:
            img_depth = self._get_capture_depth(transform_to_color)
        if pcl:
            if not depth:
                raise RuntimeError("need depth to calculate pcl")
            img_pcl = k4a_module.transformation_depth_image_to_pcl(img_depth, transform_to_color)
        if color:
            img_color = self._get_capture_color()
            if not transform_to_color:
                if not depth:
                    raise RuntimeError("need depth to transofrm color to depth")
                img_color = k4a_module.transformation_color_image_to_depth_camera(img_color, img_depth)






        return img_color, img_ir, img_depth, img_pcl

    def _get_capture_color(self) -> Optional[np.ndarray]:
        return k4a_module.device_get_color_image()

    def _get_capture_ir(self, transform_to_color: bool) -> Optional[np.ndarray]:
        ir = k4a_module.device_get_ir_image()
        if ir is not None and transform_to_color:
            ir = k4a_module.transformation_depth_image_to_color_camera(ir, self._config.color_resolution)
        return ir

    def _get_capture_depth(self, transform_depth_to_color: bool) -> Optional[np.ndarray]:
        depth = k4a_module.device_get_depth_image()
        if transform_depth_to_color:
            depth = k4a_module.transformation_depth_image_to_color_camera(depth, self._config.color_resolution)
        return depth

    @property
    def sync_jack_status(self) -> Tuple[bool, bool]:
        res, jack_in, jack_out = k4a_module.device_get_sync_jack()
        self._verify_error(res)
        return jack_in == 1, jack_out == 1

    def _get_color_control(self, cmd: ColorControlCommand) -> Tuple[int, ColorControlMode]:
        res, mode, value = k4a_module.device_get_color_control(cmd)
        self._verify_error(res)
        return value, ColorControlMode(mode)

    def _set_color_control(self, cmd: ColorControlCommand, value: int, mode=ColorControlMode.MANUAL):
        res = k4a_module.device_set_color_control(cmd, mode, value)
        self._verify_error(res)

    @property
    def brightness(self) -> int:
        return self._get_color_control(ColorControlCommand.BRIGHTNESS)[0]

    @property
    def contrast(self) -> int:
        return self._get_color_control(ColorControlCommand.CONTRAST)[0]

    @property
    def saturation(self) -> int:
        return self._get_color_control(ColorControlCommand.SATURATION)[0]

    @property
    def sharpness(self) -> int:
        return self._get_color_control(ColorControlCommand.SHARPNESS)[0]

    @property
    def backlight_compensation(self) -> int:
        return self._get_color_control(ColorControlCommand.BACKLIGHT_COMPENSATION)[0]

    @property
    def gain(self) -> int:
        return self._get_color_control(ColorControlCommand.GAIN)[0]

    @property
    def powerline_frequency(self) -> int:
        return self._get_color_control(ColorControlCommand.POWERLINE_FREQUENCY)[0]

    @property
    def exposure(self) -> int:
        # sets mode to manual
        return self._get_color_control(ColorControlCommand.EXPOSURE_TIME_ABSOLUTE)[0]

    @property
    def exposure_mode_auto(self) -> bool:
        return self._get_color_control(ColorControlCommand.EXPOSURE_TIME_ABSOLUTE)[1] == ColorControlMode.AUTO

    @property
    def whitebalance(self) -> int:
        # sets mode to manual
        return self._get_color_control(ColorControlCommand.WHITEBALANCE)[0]

    @property
    def whitebalance_mode_auto(self) -> bool:
        return self._get_color_control(ColorControlCommand.WHITEBALANCE)[1] == ColorControlMode.AUTO

    @brightness.setter
    def brightness(self, value: int):
        self._set_color_control(ColorControlCommand.BRIGHTNESS, value)

    @contrast.setter
    def contrast(self, value: int):
        self._set_color_control(ColorControlCommand.CONTRAST, value)

    @saturation.setter
    def saturation(self, value: int):
        self._set_color_control(ColorControlCommand.SATURATION, value)

    @sharpness.setter
    def sharpness(self, value: int):
        self._set_color_control(ColorControlCommand.SHARPNESS, value)

    @backlight_compensation.setter
    def backlight_compensation(self, value: int):
        self._set_color_control(ColorControlCommand.BACKLIGHT_COMPENSATION, value)

    @gain.setter
    def gain(self, value: int):
        self._set_color_control(ColorControlCommand.GAIN, value)

    @powerline_frequency.setter
    def powerline_frequency(self, value: int):
        self._set_color_control(ColorControlCommand.POWERLINE_FREQUENCY, value)

    @exposure.setter
    def exposure(self, value: int):
        self._set_color_control(ColorControlCommand.EXPOSURE_TIME_ABSOLUTE, value)

    @exposure_mode_auto.setter
    def exposure_mode_auto(self, mode_auto: bool, value=2500):
        mode = ColorControlMode.AUTO if mode_auto else ColorControlMode.MANUAL
        self._set_color_control(ColorControlCommand.EXPOSURE_TIME_ABSOLUTE, value=value, mode=mode)

    @whitebalance.setter
    def whitebalance(self, value: int):
        self._set_color_control(ColorControlCommand.WHITEBALANCE, value)

    @whitebalance_mode_auto.setter
    def whitebalance_mode_auto(self, mode_auto: bool, value=2500):
        mode = ColorControlMode.AUTO if mode_auto else ColorControlMode.MANUAL
        self._set_color_control(ColorControlCommand.WHITEBALANCE, value=value, mode=mode)

    def _get_color_control_capabilities(self, cmd: ColorControlCommand) -> (bool, int, int, int, int, int):
        (res, supports_auto, min_value, max_value,
         step_value, default_value, default_mode) = k4a_module.device_get_color_control_capabilities(cmd)
        self._verify_error(res)
        return {
            "color_control_command": cmd,
            "supports_auto": supports_auto == 1,
            "min_value": min_value,
            "max_value": max_value,
            "step_value": step_value,
            "default_value": default_value,
            "default_mode": default_mode,
        }

    def reset_color_control_to_default(self):
        for cmd in ColorControlCommand:
            capability = self._get_color_control_capabilities(cmd)
            self._set_color_control(cmd, capability["default_value"], capability["default_mode"])

    @staticmethod
    def _verify_error(res):
        res = Result(res)
        if res == Result.Failed:
            raise K4AException()
        elif res == Result.Timeout:
            raise K4ATimeoutException()
