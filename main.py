#!/usr/bin/env python

'''photofs is a virtual file-system show photos in a convenient way.'''

__author__ = 'drseergio@gmail.com (Sergey Pisarenko)'

import errno
import logging
import os
import sys
import threading

import fuse
from fuse import Fuse

from photofs.storage import PhotoDb
from photofs.views import FsStat, GetViews
from photofs.walker import PhotoWalker
from photofs.watcher import PhotoWatcher

fuse.fuse_python_api = (0, 2)


class PhotoFS(Fuse):
  def main(self, *a, **kw):
    if not self.fuse_args.getmod('showhelp'):
      self._validate_args()
      self.db = PhotoDb(self.root)
      self.views = GetViews(self.db)

      if self.db.TryLock():
        logging.info('Acquired database lock, will write/update it')
        self.walker = PhotoWalker(self.root, self.db)
        self.watcher = PhotoWatcher(self.db, self.walker, self.root)
        if self.db.IsEmptyDb():
          self.walker.Walk()
        else:
          self.walker.Sync()
        self.watcher.Watch()
      else:
        logging.error(('Failed to acquire database lock, '
                       'another instance is already running'))
        sys.exit(0)

    return Fuse.main(self, *a, **kw)

  def fsdestroy(self):
    sys.exit(0)

  def RouteView(func):
    def inner(*args, **kwargs):
      path_split = args[1].split('/')

      if not path_split[1]:
        kwargs['is_root'] = True
        return func(*args, **kwargs)

      view = path_split[1]
      self = args[0]

      if view not in self.views.keys():
        return -errno.ENOENT

      kwargs['view'] = self.views[view]
      kwargs['path_split'] = path_split

      return func(*args, **kwargs)
    return inner

  @RouteView
  def getattr(self, path, is_root=False, view=None, path_split=None):
    if is_root or len(path_split) == 2:
      return FsStat()
    return view.getattr(path_split[2:])
 
  @RouteView
  def readdir(self, path, offset, is_root=False, view=None, path_split=None):
    entries = ['.', '..']
    if is_root:
      entries.extend(self.views.keys())
    else:
      entries.extend(view.readdir(path_split[2:], offset))

    for e in entries:
      yield fuse.Direntry(e)
 
  @RouteView
  def open(self, path, flags, view=None, path_split=None):
    return view.open(path_split[2:], flags)
 
  @RouteView
  def read(self, path, length, offset, view=None, path_split=None):
    return view.read(path_split[2:], length, offset)

  @RouteView
  def write(self, path, buf, offset, view=None, path_split=None):
    return view.write(path_split[2:], buf, offset)

  @RouteView
  def release(self, path, flags, view=None, path_split=None):
    return view.release(path_split[2:], flags)

  @RouteView
  def unlink(self, path, view=None, path_split=None):
    return view.unlink(path_split[2:])

  @RouteView
  def truncate(self, path, length, view=None, path_split=None):
    return view.truncate(path_split[2:], length)

  def _validate_args(self):
    if not self.cmdline[0].root:
      print '"root" parameter must be specified'
      sys.exit(0)

    if not os.path.isdir(self.cmdline[0].root):
      print 'Source path does not exist'
      sys.exit(0)

    self.root = self.cmdline[0].root


def main():
  photo_fs = PhotoFS()
  photo_fs.parser.add_option(mountopt='root', metavar='PATH',
                       help='Path to folder containing your photos.')
  photo_fs.parse(errex=1)
  photo_fs.main()


if __name__ == "__main__":
  main()
