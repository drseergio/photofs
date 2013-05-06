#!/usr/bin/env python

'''photofs is a virtual file-system show photos in a convenient way.'''

__author__ = 'drseergio@gmail.com (Sergey Pisarenko)'

import os
import sys

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
      self.db = PhotoDb()
      self.walker = PhotoWalker(self.root, self.db)
      self.view = GetView(self.mode)(self.db)
      self.walker.Walk()
      self.watcher = PhotoWatcher(self.db, self.walker, self.root)
      self.watcher.Watch()

    return Fuse.main(self, *a, **kw)

  def fsdestroy(self):
    self.watcher.Stop()
    self.db.Delete()

  def getattr(self, path):
    return self.view.getattr(path)
 
  def readdir(self, path, offset):
    return self.view.readdir(path, offset)
 
  def open(self, path, flags):
    return self.view.open(path, flags)
 
  def read(self, path, length, offset):
    return self.view.read(path, length, offset)

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
