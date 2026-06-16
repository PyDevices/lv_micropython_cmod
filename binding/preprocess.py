import subprocess


def preprocess(args):
    """Return preprocessed source text and a description of how it was produced."""
    if not args.ep:
        pp_cmd = (
            "gcc -E -std=c99 -DPYCPARSER {macros} {include} {input} {first_input}".format(
                input=" ".join("-include %s" % inp for inp in args.input),
                first_input="%s" % args.input[0],
                macros=" ".join("-D%s" % define for define in args.define),
                include=" ".join("-I %s" % inc for inc in args.include),
            )
        )
        source = subprocess.check_output(pp_cmd.split()).decode()
    else:
        pp_cmd = "Preprocessing was disabled."
        with open(args.ep, "r") as f:
            source = f.read()
    return source, pp_cmd
