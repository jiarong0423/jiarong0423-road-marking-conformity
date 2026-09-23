"""The isolated modules, sharing the project's `marking` package name.

They are not on the delivery path - see ../../README.md - but they still
import `extract`, `sequential` and `vanishing`, which are. Rather than
copy those (a second thing to be wrong about the same question), this
extends the package's search path to the real one, so `marking.pipeline`
resolves here and `marking.extract` resolves there.

Putting isolation/src BEFORE src on sys.path is what makes this the
isolated view; the project's own tests never do that, so nothing on the
delivery path can reach these four modules by accident.
"""
from pathlib import Path

__path__.append(str(Path(__file__).resolve().parents[3] / "src" / "marking"))
