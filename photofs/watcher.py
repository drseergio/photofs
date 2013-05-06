# -*- encoding: utf-8 -*-

'''watcher.py: listens for inotify updates to update photofs views.'''

__author__ = 'drseergio@gmail.com (Sergey Pisarenko)'

import os

from pyinotify import WatchManager, ThreadedNotifier, EventsCodes, ProcessEvent


class PhotoWatcher(ProcessEvent):
  MASK = (EventsCodes.ALL_FLAGS['IN_DELETE'] |
          EventsCodes.ALL_FLAGS['IN_CLOSE_WRITE'])

  def __init__(self, db, walker, root):
    self.root = root
    self.db = db
    self.walker = walker
    self.wm = WatchManager()

  def Watch(self):
    self.notifier = ThreadedNotifier(self.wm, self)
    self.notifier.start()
    self.wdd = self.wm.add_watch(self.root, self.MASK, rec=True)

  def Stop(self):
    self.notifier.stop()

  def process_IN_DELETE(self, event):
    self.db.DeletePhoto(os.path.join(event.path, event.name))

  def process_IN_CLOSE_WRITE(self, event):
    full_path = os.path.join(event.path, event.name)
    try:
      meta = self.walker.ReadMetadata(full_path)
    except Exception:
      return

    self.db.DeletePhoto(full_path)
    self.db.StorePhoto(full_path, meta)
