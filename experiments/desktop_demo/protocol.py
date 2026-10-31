"""Measured desktop-demo protocol, independent of camera and GUI APIs."""

import math

import numpy as np

from eye_tracker.intent.region_dwell import RegionDwell

SHAPES = ["circle", "square", "triangle", "diamond"]
WEB_TARGETS = ["overview", "notes", "search", "title", "reminder", "save", "details", "clear"]
WEB_ORDER = [
    "overview",
    "title",
    "reminder",
    "save",
    "details",
    "search",
    "notes",
    "clear",
    "reminder",
    "details",
    "title",
    "save",
]
# One instruction per WEB_ORDER task; each names the control and where it sits.
WEB_INSTRUCTIONS = [
    "Üstteki sekmelerden en soldaki “Genel bakış” sekmesini seç.",
    "Sol sütunda, en üstteki “Başlık” metin alanını seç.",
    "Sol sütunda, “Başlık”ın altındaki “Hatırlatıcı ekle” kutusunu seç.",
    "Sol sütunun altındaki büyük “Notu kaydet” düğmesini seç.",
    "Sağdaki not kartının sağ üst köşesindeki “Ayrıntı” düğmesini seç.",
    "Sağ üst köşedeki “Notlarda ara” arama alanını seç.",
    "Üstteki sekmelerden “Genel bakış”ın sağındaki “Notlar” sekmesini seç.",
    "Sol altta, “Notu kaydet”in sağındaki küçük “Temizle” bağlantısını seç.",
    "Sol sütundaki “Hatırlatıcı ekle” kutusunu yeniden seç.",
    "Sağdaki not kartında yer alan küçük “Ayrıntı” düğmesini yeniden seç.",
    "Sol sütunun üst kısmındaki “Başlık” metin alanını yeniden seç.",
    "Sol sütunun altındaki büyük “Notu kaydet” düğmesini yeniden seç.",
]
# Same normalized13-point layout as upstream CalibrationController.
_X = [50 / 1920, (50 / 1920 + 0.5) / 2, 0.5, (0.5 + 1870 / 1920) / 2, 1870 / 1920]
_Y = [50 / 1080, (50 / 1080 + 0.5) / 2, 0.5, (0.5 + 1030 / 1080) / 2, 1030 / 1080]
CALIBRATION_POINTS = [
    (_X[x], _Y[y])
    for x, y in [
        (0, 0),
        (2, 0),
        (4, 0),
        (1, 1),
        (3, 1),
        (0, 2),
        (4, 2),
        (1, 3),
        (3, 3),
        (0, 4),
        (2, 4),
        (4, 4),
        (2, 2),
    ]
]
CHECK_POINTS = [(0.25, 0.25), (0.75, 0.25), (0.5, 0.5), (0.25, 0.75), (0.75, 0.75)]
TRIAL_ORDER = [
    "circle",
    "diamond",
    "square",
    "triangle",
    "square",
    "circle",
    "triangle",
    "diamond",
    "triangle",
    "square",
    "diamond",
    "circle",
]


def finite_pair(value):
    return value is not None and len(value) == 2 and all(math.isfinite(v) for v in value)


UNIGAZE_POINTS = [
    (0.5, 0.5),
    (0.1, 0.1),
    (0.5, 0.1),
    (0.9, 0.1),
    (0.9, 0.5),
    (0.9, 0.9),
    (0.5, 0.9),
    (0.1, 0.9),
    (0.1, 0.5),
    (0.3, 0.3),
    (0.7, 0.3),
    (0.7, 0.7),
    (0.3, 0.7),
]


class Session:
    def __init__(self, model_name="mgaze", scenario="shapes"):
        if model_name not in ("unigaze", "mgaze"):
            raise ValueError("Unknown gaze model")
        if scenario not in ("shapes", "web"):
            raise ValueError("Unknown interaction scenario")
        self.scenario = scenario
        self.targets = WEB_TARGETS if scenario == "web" else SHAPES
        self.trial_order = WEB_ORDER if scenario == "web" else TRIAL_ORDER
        self.model_name = model_name
        self.feature_count = 2 if model_name == "unigaze" else 258
        self.sample_count = 20 if model_name == "unigaze" else 45
        self.calibration_points = UNIGAZE_POINTS if model_name == "unigaze" else CALIBRATION_POINTS
        self.raw_check_samples = []
        self.phase = "preparation"
        self.calibrated = False
        self.message = ""
        self.token = 0
        self.onset = None
        self.index = 0
        self.geometry = None
        self.samples, self.training, self.check_results, self.trials = [], [], [], []
        self.regions = {}
        self.dwell = RegionDwell()
        self.paused_at = None
        self.last_point = None
        self.last_sample = None

    def transition(self, phase):
        self.phase = phase
        self.raw_check_samples = []
        self.token += 1
        self.onset = None
        self.last_sample = None
        self.dwell.reset()

    @property
    def point(self):
        if self.phase == "calibration":
            return self.calibration_points[self.index]
        if self.phase == "check":
            return CHECK_POINTS[self.index]
        return None

    @property
    def expected(self):
        return self.trial_order[self.index] if self.phase == "demo" else None

    @property
    def instruction(self):
        if self.phase != "demo" or self.scenario != "web":
            return None
        return WEB_INSTRUCTIONS[self.index]

    def start_calibration(self, geometry):
        if (
            len(geometry) != 5
            or not all(math.isfinite(x) for x in geometry)
            or geometry[0] < 640
            or geometry[1] < 480
            or geometry[4] <= 0
        ):
            raise ValueError("Invalid window geometry")
        self.calibrated = False
        self.geometry = list(geometry)
        self.samples, self.training, self.check_results, self.trials = [], [], [], []
        self.index, self.paused_at = 0, None
        self.message = ""
        self.transition("calibration")

    def ack(self, token, now):
        if token == self.token and self.onset is None and self.paused_at is None:
            self.onset = now

    def fail(self, message):
        self.message = message
        self.transition("error")

    def retry_calibration(self):
        if self.phase != "calibration_retry":
            raise ValueError("Tekrar beklenecek kalibrasyon noktası yok.")
        self.samples = []
        self.message = ""
        self.transition("calibration")

    def insufficient_calibration(self):
        self.message = (
            f"{self.index + 1}. noktada {len(self.samples)}/{self.sample_count} geçerli örnek alındı. "
            "Tamamlanan noktalar korundu. Hazır olduğunda bu noktayı tekrar dene."
        )
        self.transition("calibration_retry")

    def geometry_changed(self, geometry):
        if self.geometry is not None and list(geometry) != self.geometry:
            self.calibrated = False
            self.fail("Pencerenin yeri değişti. Bakışlarını yeniden ayarlayalım.")

    def calibration_arrays(self):
        return np.concatenate(self.training), np.repeat(
            self.calibration_points, self.sample_count, axis=0
        )

    def fitted(self):
        self.index = 0
        self.samples = []
        self.transition("check")

    def set_regions(self, regions):
        if set(regions) != set(self.targets):
            raise ValueError("Registered control regions required")
        clean = {}
        for name, rect in regions.items():
            if len(rect) != 4 or not all(math.isfinite(x) for x in rect):
                raise ValueError("Invalid region")
            x, y, w, h = rect
            if x < 0 or y < 0 or w <= 0 or h <= 0 or x + w > 1.00001 or y + h > 1.00001:
                raise ValueError("Region outside viewport")
            for a, b, c, d in clean.values():
                if min(x + w, a + c) > max(x, a) and min(y + h, b + d) > max(y, b):
                    raise ValueError("Overlapping regions")
            clean[name] = list(rect)
        if clean != self.regions:
            self.dwell.reset()
        self.regions = clean

    def start_demo(self):
        if self.phase not in ("ready", "results") and not self.calibrated:
            raise ValueError("Önce göz ayarını tamamla.")
        self.index = 0
        self.trials = []
        self.paused_at = None
        self.transition("demo")

    def pause(self, now):
        self.dwell.reset()
        if self.phase == "demo" and self.paused_at is None:
            self.paused_at = now
        elif self.phase in ("calibration", "calibration_retry", "check", "fitting"):
            self.calibrated = False
            self.fail("Göz ayarı yarıda kaldı. Hazır olduğunda yeniden başlayabilirsin.")

    def resume(self, now):
        if self.phase == "demo" and self.paused_at is not None:
            if self.onset is not None:
                self.onset += now - self.paused_at
            else:
                self.token += 1
            self.paused_at = None
            self.dwell.reset()

    def finish_trial(self, selected, elapsed):
        self.trials.append(
            dict(
                expected=self.expected,
                selected=selected,
                outcome="timeout"
                if selected is None
                else "correct"
                if selected == self.expected
                else "incorrect",
                elapsed_s=elapsed,
                modality="gaze",
                scenario=self.scenario,
                target_size_px=[
                    self.regions[self.expected][2] * self.geometry[0],
                    self.regions[self.expected][3] * self.geometry[1],
                ]
                if self.expected in self.regions and self.geometry
                else None,
            )
        )
        self.index += 1
        self.transition("results" if self.index == len(self.trial_order) else "demo")

    def sample(self, now, features, point, raw_point=None):
        self.last_point = list(point) if finite_pair(point) else None
        if self.paused_at is not None or self.onset is None:
            return
        if self.last_sample is not None and now <= self.last_sample:
            self.dwell.reset()
            return
        self.last_sample = now
        elapsed = now - self.onset
        if self.phase == "calibration":
            if elapsed > 15:
                self.insufficient_calibration()
            else:
                timed = self.model_name == "unigaze"
                if elapsed >= 1.5 and (not timed or elapsed < 7.5) and features is not None:
                    a = np.asarray(features, dtype=np.float32)
                    if a.shape == (self.feature_count,) and np.isfinite(a).all():
                        self.samples.append(a.copy())
                finished = elapsed >= 7.5 if timed else len(self.samples) >= self.sample_count
                if finished:
                    if len(self.samples) < self.sample_count:
                        self.insufficient_calibration()
                        return
                    indices = np.linspace(0, len(self.samples) - 1, self.sample_count, dtype=int)
                    self.training.append(np.array(self.samples)[indices])
                    self.samples = []
                    self.index += 1
                    self.transition("fitting" if self.index == 13 else "calibration")
        elif self.phase == "check":
            if 1 <= elapsed < 3 and finite_pair(point):
                self.samples.append(
                    float(np.linalg.norm((np.array(point) - self.point) * self.geometry[:2]))
                )
                if finite_pair(raw_point):
                    self.raw_check_samples.append(
                        float(
                            np.linalg.norm((np.array(raw_point) - self.point) * self.geometry[:2])
                        )
                    )
            if elapsed >= 3:
                if len(self.samples) < 5:
                    self.fail("Kısa kontrolde göz verisi yetersiz. Yeniden kalibre et.")
                    return
                self.check_results.append(
                    dict(
                        target=list(self.point),
                        n=len(self.samples),
                        mean_px=float(np.mean(self.samples)),
                        raw_n=len(self.raw_check_samples),
                        raw_mean_px=float(np.mean(self.raw_check_samples))
                        if self.raw_check_samples
                        else None,
                    )
                )
                self.samples = []
                self.index += 1
                if self.index == 5:
                    self.calibrated = True
                self.transition("ready" if self.index == 5 else "check")
        elif self.phase == "demo":
            if elapsed >= 15:
                self.finish_trial(None, 15.0)
                return
            if elapsed >= 1 and not finite_pair(point):
                # A brief measurement gap holds, but never advances, the dwell.
                self.dwell.missing(now)
                return
            target = None
            if elapsed >= 1:
                for name, (x, y, w, h) in self.regions.items():
                    if x <= point[0] < x + w and y <= point[1] < y + h:
                        target = name
                        break
            if self.dwell.update(now, target):
                self.finish_trial(target, elapsed)

    def measurement_progress(self, now):
        if self.phase not in ("calibration", "check"):
            return None
        duration = 7.5 if self.phase == "calibration" else 3.0
        settle = 1.5 if self.phase == "calibration" else 1.0
        elapsed = max(0, now - self.onset) if self.onset is not None else 0
        fraction = max(0, 1 - elapsed / duration)
        if self.phase == "calibration" and self.model_name == "mgaze":
            fraction = max(0, 1 - len(self.samples) / self.sample_count)
        return dict(
            index=self.index + 1,
            total=13 if self.phase == "calibration" else 5,
            remaining_s=max(0, duration - elapsed),
            sample_based=self.phase == "calibration" and self.model_name == "mgaze",
            samples=len(self.samples),
            required_samples=self.sample_count,
            remaining_fraction=fraction,
            settling=elapsed < settle,
            phase=self.phase,
        )

    def snapshot(self):
        return dict(
            phase=self.phase,
            scenario=self.scenario,
            can_demo=self.calibrated or self.phase in ("ready", "results"),
            message=self.message,
            token=self.token,
            index=self.index,
            point=self.point,
            expected=self.expected,
            instruction=self.instruction,
            paused=self.paused_at is not None,
            dwell_target=self.dwell.target,
            dwell_progress=self.dwell.progress,
            sample_count=len(self.samples),
            checks=list(self.check_results),
            trials=list(self.trials),
            total_trials=len(self.trial_order),
        )
