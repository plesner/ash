# A command store backed by scripts in the file system.
class FileCommandStore(object):

  COMMAND_TEMPLATE = '%s.ash.py'
  COMMAND_PATTERN = re.compile(r'([^.]+)\.ash\.py')

  def __init__(self, root):
    self.root = root

  def lookup_command(self, name):
    command_file_name = FileCommandStore.COMMAND_TEMPLATE % name
    candidate = os.path.join(self.root, command_file_name)
    if os.path.exists(candidate):
      return FileCommand(name, candidate)
    else:
      return None

  def list_commands(self):
    for path in os.listdir(self.root):
      matcher = FileCommandStore.COMMAND_PATTERN.match(path)
      if matcher:
        name = matcher.group(1)
        filename = os.path.join(self.root, path)
        yield FileCommand(name, filename)


# A command object for executing a file.
class FileCommand(object):

  def __init__(self, name, script):
    self.name = name
    self.script = script

  def execute(self, raw_args, here):
    env = ScriptEnvironment()
    env.load(self.script)
    main = env.get_main_value()
    main.run(raw_args)

  def get_name(self):
    return self.name


# A command store that contains special commands.
class SpecialCommandStore(object):

  def __init__(self, repo):
    self.repo = repo
    self.commands = {
      '--complete--': SpecialCommand(self.generate_completions)
    }

  # Generate completions for the given partial command.
  def generate_completions(self, raw_args, here):
    if len(raw_args) == 0:
      return
    command = raw_args[0]
    command_args = raw_args[1:]
    if command_args:
      # We're completing on arguments.
      self.generate_command_argument_completions(command, here)
    else:
      # We're completing on the command, there are no arguments.
      self.generate_command_completions(command, here)

  # Generate completions that match on command names.
  def generate_command_completions(self, name, here):
    for command in self.repo.list_commands(here):
      command_name = command.get_name()
      if command_name.startswith(name):
        print command_name

  # Generate completions for a particular command.
  def generate_command_argument_completions(self, name, here):
    command = self.repo.lookup_command(name, here)
    if not command:
      return

  def lookup_command(self, name):
    return self.commands.get(name)

  def list_commands(self):
    return []


# A wrapper around a special command implementation that allows it to be called
# the same way as a file command.
class SpecialCommand(object):

  def __init__(self, callback):
    self.callback = callback

  def execute(self, raw_args, here):
    self.callback(raw_args, here)


# A collection of commands built based on the location of this script as the
# path this is being invoked from.
class CommandRepository(object):

  COMMAND_STORE_NAMES = ['ash', '.ash']

  def __init__(self):
    self.specials = SpecialCommandStore(self)
    self.path_roots = self.build_path_roots()

  # Returns the most appropriate command file to use for the given location.
  def lookup_command(self, name, here):
    for store in self.list_safe_command_stores(here):
      candidate = store.lookup_command(name)
      if not candidate is None:
        return candidate
    return None

  # Generates all commands visible from the given path.
  def list_commands(self, path):
    for store in self.list_safe_command_stores(path):
      for command in store.list_commands():
        yield command

  # Generates the list of safe stores accessible from the given path
  def list_safe_command_stores(self, path):
    yield self.specials
    for source in [self.walk_out(path), self.path_roots]:
      for path in source:
        store = self.find_command_store(path)
        if store and self.is_safe(store):
          yield FileCommandStore(store)

  # Is the given path a safe store? That is, is it located, directly or
  # indirectly, within one of this environment's path roots?
  def is_safe(self, path):
    # Resolve any symlinks so we get the raw file behind this path.
    resolved = self.resolve_path(path)
    # Try to find it within any of the path roots
    for path_root in self.path_roots:
      if resolved.startswith(path_root):
        # Found a candidate. Ask the file system to verify to be absolutely
        # sure.
        if self.is_path_within(path_root, resolved):
          return True
    return False

  # Returns true if the given child path is a file within the given parent
  # path.
  def is_path_within(self, parent, possible_child):
    for path in self.walk_out(possible_child):
      if os.path.samefile(path, parent):
        return True
    return False

  # Returns the command store under the given path, if there is one, otherwise
  # Null.
  def find_command_store(self, path):
    for name in CommandRepository.COMMAND_STORE_NAMES:
      candidate = os.path.join(path, name)
      if os.path.exists(candidate):
        return self.resolve_path(candidate)
    return None

  # Generates all paths starting from the given start point and stripping off
  # the last filenames one at a time until reaching the file system root.
  def walk_out(self, start):
    current = start
    previous = None
    while current != previous:
      yield current
      previous = current
      current = os.path.dirname(current)

  # Builds the list of path roots in the current command environment. Resolves
  # any symlinks so all paths will be real. The path list order will be left
  # unchanged.
  def build_path_roots(self):
    env_path = os.getenv('PATH')
    path_list = env_path.split(os.pathsep)
    result = []
    for raw_path in path_list:
      path_entry = self.resolve_path(raw_path)
      if path_entry:
        result.append(path_entry)
    return result

  # Takes an arbitrary path and returns the normalized real path it represents.
  # If the file is somehow invalid or doesn't exist returns None.
  def resolve_path(self, raw_path):
    if not os.path.exists(raw_path):
      return None
    return os.path.normpath(os.path.realpath(raw_path))
