# A helper for running script commands. This sets up the special environment
# that scripts use to hook into the framework and records relevant state
# while running.
class ScriptEnvironment(object):

  def __init__(self):
    self.module_manager = SyntheticModuleManager(self)
    self.main = None
    self.commands = {}

  # Load the script, running it to register the relevant hooks.
  def load(self, script):
    hook = self.module_manager.new_meta_hook()
    try:
      sys.meta_path.append(hook)
      execfile(script, self.module_manager.globals)
    finally:
      sys.meta_path.remove(hook)

  # Set the main entry-point.
  def set_main_value(self, value):
    self.main = self.wrap_in_handler(value)

  def wrap_in_handler(self, value):
    if type(value) is types.FunctionType:
      action = FunctionAction(value)
    else:
      action = value()
    return SimpleActionHandler(action)

  # Returns the main value registered within this environment
  def get_main_value(self):
    return self.main

  # Sets this script's dispatcher.
  def set_dispatcher(self, value):
    handler = self.wrap_in_handler(value)
    self.main = DispatcherActionHandler(handler, self.commands)

  # Creates a function that works as the result of a @command decorator.
  def new_command_trampoline(self, name):
    commands = self.commands
    wrap_in_handler = self.wrap_in_handler
    def add_command(value):
      commands[name] = wrap_in_handler(value)
    return add_command

  # Returns a shell command built with the given name.
  def shell(self, name):
    run_shell_command = self.run_shell_command
    def run_trampoline(*args, **kwargs):
      return run_shell_command(name, args, kwargs)
    return run_trampoline

  def sh(self, names):
    sh = self.sh
    run_sh_command = self.run_sh_command
    class ShBuilder(object):
      def __call__(self, *args, **kwargs):
        command = names + list(args)
        return run_sh_command(command, kwargs)
      def __getattr__(self, name):
        return sh(names + [name])
    return ShBuilder()

  def run_shell_command(self, name, args, kwargs):
    print name, args, kwargs

  # Runs a raw shell command.
  def run_sh_command(self, command, kwargs):
    return ShellProcess(command)

  def do_process(self, process):
    return process.do()


# A action implementation.
class Action(object):

  def __init__(self):
    pass


# An action implementation based on a function.
class FunctionAction(object):

  def __init__(self, callback):
    self.callback = callback

  def run(self, args):
    return (self.callback)()


# Utility for managing the synthetic modules that allow scripts to hook in to
# the framework using imports.
class SyntheticModuleManager(object):

  def __init__(self, env):
    self.env = env
    self.globals = {'do': self.env.do_process}

  # Returns an import meta hook configured to return the synthetic modules
  # defined my this manager.
  def new_meta_hook(self):
    return ImportMetaHook(self)

  # Build the dict containing the special modules that scripts can import to
  # hook into the framework.
  def build_modules(self):
    return {
      'ash': self.new_module_proxy(self.build_ash_module())
    }

  # Given a dict, returns an object that has a property for each dict entry
  # whose value is the mapping for that entry.
  def new_module_proxy(self, entries):
    class ModuleProxy(object):
      def __getattr__(self, name):
        if name in entries:
          return entries[name]
        else:
          raise AttributeError(name)
    return ModuleProxy()

  # Builds the 'ash' module.
  def build_ash_module(self):
    entries = {}
    entries['main'] = self.env.set_main_value
    entries['sh'] = self.new_sh_module()
    entries['dispatcher'] = self.env.set_dispatcher
    entries['command'] = self.env.new_command_trampoline
    entries['Action'] = Action
    return entries

  # Builds the ash shell trampoline module.
  def new_shell_module(self):
    env = self.env
    class ShellProxy(object):
      def __getattr__(self, name):
        return env.shell(name)
    return ShellProxy()

  # Builds the raw sh trampoline module
  def new_sh_module(self):
    env = self.env
    class ShProxy(object):
      def __getattr__(self, name):
        return env.sh([name])
      def __call__(self, *args, **kwargs):
        return env.run_sh_command(args, kwargs)
    return ShProxy()

  # Registers a module as having been loaded, making it available to the
  # script when run.
  def register_module(self, name, value):
    self.globals[name] = value


# An import meta hook that allows scripts to load in artifical framework
# modules. This interface is defined by PEP 302.
class ImportMetaHook(object):

  def __init__(self, manager):
    self.manager = manager
    self.modules = manager.build_modules()

  def find_module(self, module_name, package_path):
    # If the requested module is one we own return ourselves at the module
    # loader.
    if module_name in self.modules:
      return self

  def load_module(self, module_name):
    result = self.modules[module_name]
    self.manager.register_module(module_name, result)
    return result


# An action handler implements delegation to a particular action. A logical
# action might be implements either as a single action implementation or
# multiple and the handler implements dispatching to the correct one.
class ActionHandler(object):

  # Runs this action.  
  @abstractmethod
  def run(self, args):
    pass


# Implementation of a dispatcher action.
class DispatcherActionHandler(ActionHandler):
  
  def __init__(self, default_handler, commands):
    self.default_handler = default_handler
    self.commands = commands

  def run(self, args):
    if len(args) > 0:
      command_name = args[0]
      if command_name in self.commands:
        rest_args = args[1:]
        command = self.commands[command_name]
        return command.run(rest_args)
    return self.default_handler.run(args)


# Action handler that simply delegates to an action object.
class SimpleActionHandler(ActionHandler):

  def __init__(self, action):
    self.action = action

  def run(self, args):
    return self.action.run(args)
