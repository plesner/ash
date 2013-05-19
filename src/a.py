#!/usr/bin/python

from abc import abstractmethod
import glob
import os
import os.path
import subprocess
import re
import sys
import threading
import types

script_file = sys.argv[0] # STRIP
script_root = os.path.dirname(os.path.abspath(script_file)) # STRIP
execfile(os.path.join(script_root, 'ash', 'process.py')) # IMPORT(process.py)
execfile(os.path.join(script_root, 'ash', 'env.py')) # IMPORT(env.py)
execfile(os.path.join(script_root, 'ash', 'command.py')) # IMPORT(command.py)
execfile(os.path.join(script_root, 'ash', 'main.py')) #IMPORT(main.py)
