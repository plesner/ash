# State for the main entry-point
class Main(object):

  def __init__(self):
    self.repo = None

  # Print usage when no commands could be idenfitied.
  def print_usage_no_command(self):
    print "Usage: a <command> <flag> ..."

  # Returns, creating if necessary, the command repo.
  def get_command_repository(self):
    if self.repo is None:
      self.repo = CommandRepository()
    return self.repo

  # Runs a command with a given set of arguments.
  def execute_command(self, command, args, here):
    command.execute(args, here)
    return 0

  # Main entry-point method
  def main(self, argv):
    own_executable = argv[0]
    raw_args = argv[1:]
    if len(raw_args) == 0:
      self.print_usage_no_command()
      return 1
    command_name = raw_args[0]
    command_args = raw_args[1:]
    repo = self.get_command_repository()
    here = os.path.abspath('.')
    command = repo.lookup_command(command_name, here)
    if command is None:
      print 'No command "%s" found.' % command_name
      return 1
    return self.execute_command(command, command_args, here)


if (__name__ == '__main__') and not (__file__ == 'dontrun'):
  sys.exit(Main().main(sys.argv))
