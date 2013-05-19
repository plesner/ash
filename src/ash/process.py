# An abstraction of a process.
class Process(object):

  def __init__(self):
    self.is_running = False
    self.is_complete = False

  # Ensure that this process has been started.
  def ensure_running(self):
    if self.is_running:
      return
    self.is_running = True
    self.start_process()

  def wait_for_completion(self):
    if self.is_complete:
      return
    self.block_until_complete()
    self.is_complete = True

  # Creates a new process that pipes input from this process' stdout into
  # the target process' stdin.
  def __or__(self, that):
    assert not self.is_running
    assert not that.is_running
    return PipedProcess(self.clone(), that.clone())

  # Returns True if this process is truthy, that is if it exited successfully,
  # otherwise False. Paradoxically the test for a successful run is whether the
  # return code is 0, so in reality this does exactly the opposite of what it
  # says.
  def __nonzero__(self):
    self.ensure_running()
    self.wait_for_completion()
    return self.was_successful()

  # Generates lines of input from this process.
  def __iter__(self):
    assert not self.is_running
    self.capture_stdout()
    self.ensure_running()
    return self.generate_stdout_lines()

  # Runs this process to completion.
  def do(self):
    self.ensure_running()
    self.wait_for_completion()

  # Called to start this process. Subclasses must implement this.
  @abstractmethod
  def start_process(self):
    pass

  # Creates a copy of this process. This process must not be running when this
  # is called. Subclasses must implement this.
  @abstractmethod
  def clone(self):
    pass

  # Blocks the caller until this process is done running
  @abstractmethod
  def block_until_complete(self):
    pass

  # Returns True iff this process, which has already completed, was successful.
  @abstractmethod
  def was_successful(self):
    pass

  # Generates lines from stdout.
  @abstractmethod
  def generate_stdout_lines(self):
    pass


# A process backed by a shell command.
class ShellProcess(Process):

  def __init__(self, command):
    super(ShellProcess, self).__init__()
    self.command = command
    self.process = None
    self.params = {'bufsize': -1, 'close_fds': True}
    self.runner = threading.Thread(target=self.run_external_process)
    self.process_started = threading.Semaphore(0)
    self.fds_to_close = []

  def start_process(self):
    self.runner.start()
    self.process_started.acquire()

  def block_until_complete(self):
    self.runner.join()

  def run_external_process(self):  
    self.process = subprocess.Popen(self.command, **self.params)
    self.process_started.release()
    self.process.wait()
    for fd in self.fds_to_close:
      os.close(fd)

  def clone(self):
    result = ShellProcess(self.command)
    result.params = dict(self.params)
    return result

  def capture_stdout(self):
    self.params['stdout'] = subprocess.PIPE

  def generate_stdout_lines(self):
    for line in self.process.stdout:
      yield line

  def set_stdin(self, value, close_on_exit):
    if close_on_exit:
      self.fds_to_close.append(value)
    self.params['stdin'] = value

  def set_stdout(self, value, close_on_exit):
    if close_on_exit:
      self.fds_to_close.append(value)
    self.params['stdout'] = value

  def __str__(self):
    return '#<%s>' % ' '.join(self.command)


# A pseudo-process that represents piping the output of one process into the
# input of another.
class PipedProcess(Process):

  def __init__(self, source, target):
    super(PipedProcess, self).__init__()
    self.source = source
    self.target = target
    (pipein, pipeout) = os.pipe()
    self.source.set_stdout(pipeout, True)
    self.target.set_stdin(pipein, True)

  def block_until_complete(self):
    return self.target.block_until_complete()

  def capture_stdout(self):
    self.target.capture_stdout()

  def generate_stdout_lines(self):
    return self.target.generate_stdout_lines()

  def start_process(self):
    self.source.start_process()
    self.target.start_process()

  def set_stdin(self, value, close_on_exit):
    self.source.set_stdin(value, close_on_exit)

  def set_stdout(self, value, close_on_exit):
    self.target.set_stdout(value, close_on_exit)

  def clone(self):
    return PipedProcess(self.source.clone(), self.target.clone())

  def __str__(self):
    return '(%s | %s)' % (self.source, self.target)
