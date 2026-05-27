"""
DOR — Distance & Ocular Regulator
Module: privacy.py
Privacy: Zero-I/O. No image data is written to disk or network at any point.

Frame destruction is performed inline at call sites via `frame = None`
to immediately allow garbage collection of image buffers.
"""
