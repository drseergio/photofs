#!/usr/bin/env python

'''photofs is a virtual file-system show photos in a convenient way.'''

__author__ = 'drseergio@gmail.com (Sergey Pisarenko)'

import logging
import os
import sys
import threading

import fuse
from fuse import Fuse

from photofs.storage import PhotoDb
from photofs.views import GetView, ListViews
from photofs.walker import PhotoWalker
from photofs.watcher import PhotoWatcher

fuse.fuse_python_api = (0, 2)


class PhotoFS(Fuse):
  def main(self, *a, **kw):
    if not self.fuse_args.getmod('showhelp'):
      self._validate_args()
      self.db = PhotoDb(self.root)
      self.view = GetView(self.mode)(self.db)

      if self.db.TryLock():
        logging.info('Acquired database lock, will write/update it')
        self.read_only = False
        self.walker = PhotoWalker(self.root, self.db)
        self.watcher = PhotoWatcher(self.db, self.walker, self.root)
        if self.db.IsEmptyDb():
          self.walker.Walk()
        else:
          self.walker.Sync()
        self.watcher.Watch()
      else:
        logging.error('Failed to acquire database lock, not doing updates')
        self.read_only = True

    return Fuse.main(self, *a, **kw)

  def fsinit(self):
    if self.read_only:
      thread = threading.Thread(target=self._wait_lock)
      thread.start()

  def fsdestroy(self):
    if not self.read_only:
      self.watcher.Stop()

  def getattr(self, path):
    return self.view.getattr(path)
 
  def readdir(self, path, offset):
    return self.view.readdir(path, offset)
 
  def open(self, path, flags):
    return self.view.open(path, flags)
 
  def read(self, path, length, offset, fh):
    return self.view.read(path, length, offset, fh)

  def write(self, path, buf, offset, fh):
    return self.view.write(path, buf, offset, fh)

  def release(self, path, flags, fh):
    return self.view.release(path, flags, fh)

  def truncate(self, path, length):
    return self.view.truncate(path, length)

  def _wait_lock(self):
    self.db.WaitLock()
    logging.info('Acquired database lock, will write/update it')
    self.read_only = False
    self.walker = PhotoWalker(self.root, self.db)
    self.watcher = PhotoWatcher(self.db, self.walker, self.root)
    self.walker.Sync()
    self.watcher.Watch()

  def _validate_args(self):
    if not self.cmdline[0].root:
      print '"root" parameter must be specified'
      sys.exit(0)

    if not self.cmdline[0].mode:
      print '"mode" parameter must be specified'
      sys.exit(0)

    if not os.path.isdir(self.cmdline[0].root):
      print 'Source path does not exist'
      sys.exit(0)

    modes = ListViews()
    if not self.cmdline[0].mode in modes:
      print 'Not a valid mode. Following modes are supported: %s' % ', '.join(
          modes)
      sys.exit(0)

    self.mode = self.cmdline[0].mode
    self.root = self.cmdline[0].root


def main():
  photo_fs = PhotoFS()
  photo_fs.parser.add_option(mountopt='root', metavar='PATH',
                       help='Path to folder containing your photos.')
  photo_fs.parser.add_option(mountopt='mode', metavar='MODE',
                       help='One of the following: date, sets, conf, tags')
  photo_fs.parse(errex=1)
  photo_fs.main()


if __name__ == "__main__":
  main()
