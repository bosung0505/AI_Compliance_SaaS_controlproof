"""Synthetic, local-only bytes the runner uploads when it drives a consented path."""

from __future__ import annotations

import hashlib

_RESUME_TEXT = (
    "Synthetic ControlProof resume. Built a local test harness and documented its results "
    "for review. No real person is described in this document."
)


def synthetic_resume_pdf() -> bytes:
    """A minimal one-page PDF whose native text exceeds the target's OCR-free threshold."""
    stream = f"BT /F1 12 Tf 72 720 Td ({_RESUME_TEXT}) Tj ET"
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
            "/Resources << /Font << /F1 5 0 R >> >> >>"
        ),
        f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = "%PDF-1.4\n"
    offsets = []
    for index, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += f"{index} 0 obj\n{body}\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n"
    out += "".join(f"{offset:010d} 00000 n \n" for offset in offsets)
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    return out.encode("ascii")


def synthetic_recording_chunk() -> bytes:
    return bytes(1024)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
