import sys
import os

try:
    from cPickle import loads, dumps
except ImportError:
    from pickle import loads, dumps

from bento.compat.api \
    import \
        rename
from bento.core.utils import \
        pprint, subst_vars, ensure_dir, virtualenv_prefix
from bento.core.platforms import \
        get_scheme
from bento.core import \
        PackageOptions, PackageDescription
from bento._config \
    import \
        CONFIGURED_STATE_DUMP, BENTO_SCRIPT

from bento.commands.core import \
        Command, Option, OptionGroup
from bento.core.subpackage \
    import \
        get_extensions, get_compiled_libraries, get_packages
from bento.commands.errors \
    import \
        UsageException

import yaku.context

class _ConfigureState(object):
    def __init__(self, bento_script, pkg, paths=None, flags=None, user_data=None):
        self.filename = bento_script.name
        self.pkg = pkg

        if flags is None:
            self.flags = {}
        else:
            self.flags = flags

        if paths is None:
            self.paths = {}
        else:
            self.paths = paths

        if user_data is None:
            self.user_data = {}
        else:
            self.user_data = user_data

    def dump(self, node):
        node.parent.mkdir()
        node.safe_write(dumps(self), 'wb')

    @classmethod
    def from_dump(cls, node):
        return loads(node.read('rb'))

def set_scheme_options(scheme, options):
    """Set path variables given in options in scheme dictionary."""
    for k in scheme:
        if hasattr(options, k):
            val = getattr(options, k)
            if val:
                if not os.path.isabs(val):
                    msg = "value given for path option '%s' " \
                          "should be an absolute path (value " \
                          "given was '%s')" % (k, val)
                    raise UsageException(msg)
                scheme[k] = val
    # XXX: define default somewhere and stick with it
    if options.prefix is not None and options.eprefix is None:
        scheme["eprefix"] = scheme["prefix"]

def get_flag_values(cmd, cmd_argv):
    """Return flag values from the command instance and its arguments.

    Assumes cmd is an instance of Configure."""
    o, a = cmd.options_context.parser.parse_args(cmd_argv)
    flag_values = _get_flag_values(cmd.flags, o)
    return flag_values

def _get_flag_values(flag_names, options):
    """Return flag values as defined by the options."""
    flag_values = {}
    for option_name in flag_names:
        flag_value = getattr(options, option_name, None)
        if flag_value is not None:
            if flag_value.lower() in ["true", "yes"]:
                flag_values[option_name] = True
            elif flag_value.lower() in ["false", "no"]:
                flag_values[option_name] = False
            else:
                msg = """Option %s expects a true or false argument"""
                raise UsageException(msg % "--%s" % option_name)
    return flag_values

def _setup_options_parser(options_context, package_options):
    """Setup the command options parser, merging standard options as well
    as custom options defined in the bento.info file, if any.
    """
    scheme, scheme_opts_d = get_scheme(sys.platform)

    p = options_context

    # Create default path options
    scheme_opts = {}
    for name, opt_d in scheme_opts_d.items():
        o = opt_d.pop("opts")
        opt = Option(*o, **opt_d)
        scheme_opts[name] = opt

    # Add custom path options (as defined in bento.info) to the path scheme
    for name, f in package_options.path_options.items():
        scheme_opts[name] = \
            Option('--%s' % f.name,
                   help='%s [%s]' % (f.description, f.default_value))

    p.add_group("installation_options", "Installation fine tuning")
    for opt in scheme_opts.values():
        p.add_option(opt, "installation_options")

    flag_opts = {}
    if package_options.flag_options:
        flags_group = p.add_group("optional_features", "Optional features")
        for name, v in package_options.flag_options.items():
            flag_opts[name] = Option(
                    "--%s" % v.name,
                    help="%s [default=%s]" % (v.description, v.default_value))
            p.add_option(flag_opts[name], "optional_features")

class ConfigureCommand(Command):
    long_descr = """\
Purpose: configure the project
Usage: bentomaker configure [OPTIONS]"""
    short_descr = "configure the project."

    def __init__(self):
        Command.__init__(self)

    def _setup_flags_and_scheme(self, package_options):
        self.scheme = _compute_scheme(package_options)
        self.flags = package_options.flag_options.keys()

    def run(self, ctx):
        run_node = ctx.run_node
        bento_script = ctx.top_node.find_node(BENTO_SCRIPT)
        if bento_script is None:
            raise IOError("%s not found ?" % BENTO_SCRIPT)

        self._setup_flags_and_scheme(ctx.package_options)
        args = ctx.get_command_arguments()
        o, a = ctx.options_context.parser.parse_args(args)
        if o.help:
            ctx.options_context.parser.print_help()
            return

        venv_prefix = virtualenv_prefix()
        if venv_prefix is not None:
            self.scheme["prefix"] = self.scheme["eprefix"] = venv_prefix
        set_scheme_options(self.scheme, o)
        flag_vals = _get_flag_values(self.flags, o)

        ctx.setup()
        s = _ConfigureState(bento_script, ctx.pkg, self.scheme, flag_vals, {})

        dump_node = ctx.build_node.make_node(CONFIGURED_STATE_DUMP)
        s.dump(dump_node)

def _compute_scheme(package_options):
    """Compute path and flags-related options as defined in the script file(s)

    Parameters
    ----------
    package_options: PackageOptions
    """
    scheme, scheme_opts_d = get_scheme(sys.platform)

    # XXX: abstract away those, as it is copied from distutils
    py_version = sys.version.split()[0]
    scheme['py_version_short'] = py_version[0:3]
    scheme['pkgname'] = package_options.name

    for name, f in package_options.path_options.items():
        scheme[name] = f.default_value
    return scheme
