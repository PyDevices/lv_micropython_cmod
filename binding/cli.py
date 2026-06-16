"""LVGL binding generator CLI."""

from __future__ import print_function

import os
import sys
from argparse import ArgumentParser

_LVMP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _LVMP_DIR)
sys.path.insert(0, os.path.join(_LVMP_DIR, "pycparser"))

from .generator import run_circuitpython, run_micropython
from binding.metadata import save_metadata
from binding.preprocess import preprocess


def build_arg_parser():
    parser = ArgumentParser(
        description="Generate LVGL Python bindings from preprocessed headers."
    )
    parser.add_argument(
        "--target",
        choices=["micropython", "circuitpython"],
        default="micropython",
        help="Binding target runtime (default: micropython)",
    )
    parser.add_argument(
        "-I",
        "--include",
        dest="include",
        help="Preprocessor include path",
        metavar="<Include Path>",
        action="append",
    )
    parser.add_argument(
        "-D",
        "--define",
        dest="define",
        help="Define preprocessor macro",
        metavar="<Macro Name>",
        action="append",
    )
    parser.add_argument(
        "-E",
        "--external-preprocessing",
        dest="ep",
        help="Assume input file is already preprocessed",
        metavar="<Preprocessed File>",
        action="store",
    )
    parser.add_argument(
        "-J",
        "--lvgl-json",
        dest="json",
        help="JSON from the LVGL JSON generator for missing information",
        metavar="<JSON file>",
        action="store",
    )
    parser.add_argument(
        "-M",
        "--module_name",
        dest="module_name",
        help="Module name",
        metavar="<Module name string>",
        action="store",
    )
    parser.add_argument(
        "-MP",
        "--module_prefix",
        dest="module_prefix",
        help="Module prefix that starts every function name",
        metavar="<Prefix string>",
        action="store",
    )
    parser.add_argument(
        "-MD",
        "--metadata",
        dest="metadata",
        help="Optional file to emit metadata (introspection)",
        metavar="<MetaData File Name>",
        action="store",
    )
    parser.add_argument("input", nargs="+")
    parser.set_defaults(include=[], define=[], ep=None, json=None, input=[])
    return parser


def main(argv=None):
    if argv is None:
        argv = sys.argv
    args = build_arg_parser().parse_args(argv[1:])

    if args.target == "circuitpython":
        source, pp_cmd = preprocess(args)
        cmd_line = " ".join(argv)
        _result, namespace, emitted = run_circuitpython(
            args, source, pp_cmd, sys.stdout, cmd_line
        )
        if args.metadata:
            save_metadata(namespace, args.metadata)
        return 0 if emitted else 2

    if args.target != "micropython":
        raise SystemExit("Unsupported target: %s" % args.target)

    source, pp_cmd = preprocess(args)
    cmd_line = " ".join(argv)

    _result, namespace = run_micropython(args, source, pp_cmd, sys.stdout, cmd_line)

    if args.metadata:
        save_metadata(namespace, args.metadata)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
