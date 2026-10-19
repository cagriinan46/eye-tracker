import ctypes as C


class Point(C.Structure):
    _fields_ = [("x", C.c_double), ("y", C.c_double)]


class Size(C.Structure):
    _fields_ = [("width", C.c_double), ("height", C.c_double)]


class Rect(C.Structure):
    _fields_ = [("origin", Point), ("size", Size)]


objc = C.CDLL("/usr/lib/libobjc.A.dylib")
objc.objc_getClass.argtypes = [C.c_char_p]
objc.objc_getClass.restype = C.c_void_p
objc.sel_registerName.argtypes = [C.c_char_p]
objc.sel_registerName.restype = C.c_void_p
address = C.cast(objc.objc_msgSend, C.c_void_p).value


def send(obj, name, result=C.c_void_p, argtypes=(), args=()):
    return C.CFUNCTYPE(result, C.c_void_p, C.c_void_p, *argtypes)(address)(
        obj, objc.sel_registerName(name.encode()), *args
    )


def rect(obj, name):
    r = send(obj, name, Rect)
    return [r.origin.x, r.origin.y, r.size.width, r.size.height]


def geometry(title=None):
    app = send(objc.objc_getClass(b"NSApplication"), "sharedApplication")
    windows = send(app, "windows")
    out = []
    for i in range(send(windows, "count", C.c_ulong)):
        w = send(windows, "objectAtIndex:", argtypes=(C.c_ulong,), args=(i,))
        name = send(send(w, "title"), "UTF8String", C.c_char_p).decode()
        if (title is not None and name != title) or (
            title is None and "diagnostic" not in name.lower()
        ):
            continue
        view = send(w, "contentView")
        image = send(view, "imageView")
        out.append(
            {
                "title": name,
                "window_frame": rect(w, "frame"),
                "content_bounds": rect(view, "bounds"),
                "content_frame": rect(view, "frame"),
                "image_frame": rect(image, "frame") if image else None,
            }
        )
    return out
