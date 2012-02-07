import copy

from bento.compat.api \
    import \
        unittest
from bento.commands.configure \
    import \
        ConfigureCommand
from bento.commands.build \
    import \
        BuildCommand
from bento.commands.install \
    import \
        InstallCommand
from bento.commands.sdist \
    import \
        SdistCommand
from bento.commands.core \
    import \
        HelpCommand, Command
from bento.commands.context \
    import \
        HelpContext, CmdContext, GlobalContext
from bento.commands.options \
    import \
        OptionsContext
import bento.commands.core

class TestHelpCommand(unittest.TestCase):
    def setUp(self):
        registry = bento.commands.core.CommandRegistry()

        # help command assumes those always exist
        registry.register("configure", Command)
        registry.register("build", Command)
        registry.register("install", Command)
        registry.register("sdist", Command)
        registry.register("build_wininst", Command)
        registry.register("build_egg", Command)
        self.registry = registry

        self.options_registry = bento.commands.options.OptionsRegistry()
        self.options_registry.register("configure", OptionsContext())

    def test_simple(self):
        help = HelpCommand()
        options = OptionsContext()
        for option in HelpCommand.common_options:
            options.add_option(option)
        global_context = GlobalContext(self.registry, None, None, None)
        context = HelpContext(global_context, [], options, None, None)

        help.run(context)

    def test_command(self):
        help = HelpCommand()
        options = OptionsContext()
        for option in HelpCommand.common_options:
            options.add_option(option)
        context = CmdContext(None, ["configure"], options, None, None)
        context.options_registry = self.options_registry

        help.run(context)
