class FlagCollection(object):
  "A description of a set of flags."

  def __init__(self):
    self.long_flags = {}
    self.short_flags = {}

  def add_flag(self, names, default=None):
    pass
