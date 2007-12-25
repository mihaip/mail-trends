# Based on _FileCache from 
# http://python-twitter.googlecode.com/svn/trunk/twitter.py
# Modified to pickle/unpickle data

import md5
import os
import tempfile
import cPickle

class FileCacheError(Exception):
  '''Base exception class for FileCache related errors'''


class FileCache(object):

  DEPTH = 3

  def __init__(self, root_directory=None):
    self._InitializeRootDirectory(root_directory)

  def Get(self, key):
    path = self._GetPath(key)
    if os.path.exists(path):
      return cPickle.load(open(path))
    else:
      return None

  def Set(self, key, data):
    path = self._GetPath(key)
    directory = os.path.dirname(path)
    if not os.path.exists(directory):
      os.makedirs(directory)
    if not os.path.isdir(directory):
      raise FileCacheError('%s exists but is not a directory' % directory)
    temp_fd, temp_path = tempfile.mkstemp()
    temp_fp = os.fdopen(temp_fd, 'w')
    cPickle.dump(data, temp_fp)
    temp_fp.close()
    if not path.startswith(self._root_directory):
      raise FileCacheError('%s does not appear to live under %s' %
                           (path, self._root_directory))
    if os.path.exists(path):
      os.remove(path)
    os.rename(temp_path, path)

  def Remove(self, key):
    path = self._GetPath(key)
    if not path.startswith(self._root_directory):
      raise FileCacheError('%s does not appear to live under %s' %
                            (path, self._root_directory ))
    if os.path.exists(path):
      os.remove(path)

  def GetCachedTime(self, key):
    path = self._GetPath(key)
    if os.path.exists(path):
      return os.path.getmtime(path)
    else:
      return None

  def _GetUsername(self):
    '''Attempt to find the username in a cross-platform fashion.'''
    return os.getenv('USER') or \
        os.getenv('LOGNAME') or \
        os.getenv('USERNAME') or \
        os.getlogin() or \
        'nobody'

  def _GetTmpCachePath(self):
    username = self._GetUsername()
    cache_directory = 'python.cache_' + username
    return os.path.join(tempfile.gettempdir(), cache_directory)

  def _InitializeRootDirectory(self, root_directory):
    if not root_directory:
      root_directory = self._GetTmpCachePath()
    root_directory = os.path.abspath(root_directory)
    if not os.path.exists(root_directory):
      os.mkdir(root_directory)
    if not os.path.isdir(root_directory):
      raise FileCacheError('%s exists but is not a directory' %
                           root_directory)
    self._root_directory = root_directory

  def _GetPath(self, key):
    hashed_key = md5.new(key).hexdigest()
    return os.path.join(self._root_directory,
                        self._GetPrefix(hashed_key),
                        hashed_key)

  def _GetPrefix(self, hashed_key):
    return os.path.sep.join(hashed_key[0:FileCache.DEPTH])
