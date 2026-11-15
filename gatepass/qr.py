"""QR codes for the gate.

* Each visitor pass carries a QR that opens ``/visitor/scan/<reference>/``.
  An officer who scans it lands on the visit's desk page to approve it or
  record entry; anyone else sees the visitor pass.
* The gate poster carries a QR that opens the visitor registration form.

Codes are SVG so they stay sharp on a phone screen and on a printed poster.
"""

import io

import qrcode
import qrcode.image.svg
from django.conf import settings


def absolute_url(request, path):
    """Full URL for a QR. ``PUBLIC_BASE_URL`` wins, so phones get a reachable host."""
    base = getattr(settings, "PUBLIC_BASE_URL", "")
    if base:
        return base.rstrip("/") + path
    return request.build_absolute_uri(path)


def svg(data):
    code = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=2)
    code.add_data(data)
    code.make(fit=True)
    buffer = io.BytesIO()
    code.make_image(image_factory=qrcode.image.svg.SvgPathImage).save(buffer)
    return buffer.getvalue()
