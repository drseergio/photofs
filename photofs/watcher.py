# -*- encoding: utf-8 -*-

'''watcher.py: listens for inotify updates to update photofs views.'''

__author__ = 'drseergio@gmail.com (Sergey Pisarenko)'

import os

from pyinotify import WatchManager, ThreadedNotifier, EventsCodes, ProcessEvent


class PhotoWatcher(ProcessEvent):
  MASK = (EventsCodes.ALL_FLAGS['IN_DELETE'] |
          EventsCodes.ALL_FLAGS['IN_CLOSE_WRITE'] |
          EventsCodes.ALL_FLAGS['IN_MOVED_FROM'] |
          EventsCodes.ALL_FLAGS['IN_MOVED_TO'])

  def __init__(self, db, walker, root):
    self.root = root
    self.db = db
    self.walker = walker
    self.wm = WatchManager()
    self.wdds = []

  def Watch(self):
    self.notifier = ThreadedNotifier(self.wm, self)
    self.notifier.start()
    self.wdds.append(self.wm.add_watch(self.root, self.MASK, rec=True))
    # add soft link sub-folders
    for dirname, dirnames, _filenames in os.walk(self.root, followlinks=True):
      for d in dirnames:
        path = os.path.join(dirname, d)
        if os.path.islink(path):
          self.wdds.append(
              self.wm.add_watch(os.path.realpath(path), self.MASK, rec=True))

  def Stop(self):
    self.notifier.stop()

  def process_IN_DELETE(self, event):
    self.db.DeletePhoto(os.path.join(event.path, event.name))

  def process_IN_MOVED_FROM(self, event):
    self.process_IN_DELETE(event)

  def process_IN_MOVED_TO(self, event):
    full_path = os.path.join(event.path, event.name)
    try:
      meta = self.walker.ReadMetadata(full_path)
    except Exception:
      return

    self.db.StorePhoto(full_path, meta)

  def process_IN_CLOSE_WRITE(self, event):
    full_path = os.path.join(event.path, event.name)
    try:
      meta = self.walker.ReadMetadata(full_path)
    except Exception:
      return

    if self.db.HasPhoto(full_path):
      self.db.UpdatePhoto(full_path, meta)
    else:
      self.db.StorePhoto(full_path, meta)
