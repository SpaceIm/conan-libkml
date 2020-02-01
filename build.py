#!/usr/bin/env python

from bincrafters import build_template_default

if __name__ == "__main__":

    builder = build_template_default.get_builder(None, False, False, "missing", None, None, options=["boost:header_only=True"])

    builder.run()
