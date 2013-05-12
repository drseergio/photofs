# -*- encoding: utf-8 -*-

'''views.py: implements various viewing modes that photofs provides.'''

__author__ = 'drseergio@gmail.com (Sergey Pisarenko)'

import fuse

import calendar
import errno
import inspect
import os
import re
import stat
import sys
from time import time

_VIEW_REGEX = re.compile(r'^_PhotoFs\w+View$')


class _AbstractView(object):
  _FILE_ID_REGEX = re.compile(r'^\d+\s\((0x\w+)\).jpg$')

  def __init__(self, photo_db):
    self.photo_db = photo_db

  def open(self, _path, _flags):
    return 0

  def read(self, path, length, offset):
    path_split = path.split('/')
    match = self._FILE_ID_REGEX.match(path_split[-1])
    if match:
      photo_id = int(match.group(1), 16)
      real_path = self.photo_db.GetRealPhotoPath(photo_id)
      if real_path:
        file_handle = open(real_path, 'rb')
        file_handle.seek(offset)
        return file_handle.read(length)
    return -errno.EINVAL

  def _GetRealFileStat(self, st, filename):
    match = self._FILE_ID_REGEX.match(filename)
    if match:
      photo_id = int(match.group(1), 16)
      real_path = self.photo_db.GetRealPhotoPath(photo_id)
      if real_path:
        real_stat = os.stat(real_path)
        st.st_mode = real_stat.st_mode
        st.st_nlink = 1
        st.st_uid = real_stat.st_uid
        st.st_gid = real_stat.st_gid
        st.st_size = real_stat.st_size
        st.st_atime = real_stat.st_atime
        st.st_mtime = real_stat.st_mtime
        st.st_ctime = real_stat.st_ctime
        return st
    return None

  def _FormatPhotoList(self, ids):
    digits = len(str(len(ids)))
    return ['%0{0}d (%s).jpg'.format(digits) % (i, hex(x))
        for i, x in enumerate(ids, 1)]


class _PhotoFsDateView(_AbstractView):
  _NAME = 'date'

  def getattr(self, path):
    st = _FsStat()

    path_split = path.split('/')
    if len(path_split) == 2:
      if path_split[1]:  # check if year exists
        years = self.photo_db.GetYears()
        if path_split[1] in years:
          return st
      else:  # root node
        return st
    elif len(path_split) == 3:
      if path_split[2]:  # check if month exists
        real_st = self._GetRealFileStat(st, path_split[2])
        if (real_st):
          return real_st

        months = self.photo_db.GetMonths(path_split[1])
        month = path_split[2].split('-')[0]
        if month in months:
          return st
    elif len(path_split) == 4:
      if path_split[3]:  # check if day exists
        real_st = self._GetRealFileStat(st, path_split[3])
        if (real_st):
          return real_st

        days = self.photo_db.GetDays(path_split[1], path_split[2].split('-')[0])
        if path_split[3] in days:
          return st
    elif len(path_split) == 5:
      real_st = self._GetRealFileStat(st, path_split[4])
      if (real_st):
        return real_st

    return -errno.ENOENT
 
  def readdir(self, path, _offset):
    entries = ['.', '..']

    path_split = path.split('/')
    if path == '/':  # list years
      entries.extend(self.photo_db.GetYears())
    elif len(path_split) == 2:  # list months
      year = path_split[1]
      entries.extend(self._FormatMonths(self.photo_db.GetMonths(year)))
      entries.extend(
          self._FormatPhotoList(self.photo_db.ListPhotosByYear(year)))
    elif len(path_split) == 3:  # list days
      year = path_split[1]
      month = path_split[2].split('-')[0]
      entries.extend(self.photo_db.GetDays(year, month))
      entries.extend(
          self._FormatPhotoList(self.photo_db.ListPhotosByMonth(year,month)))
    elif len(path_split) == 4:  # list actual photos
      year = path_split[1]
      month = path_split[2].split('-')[0]
      day = path_split[3]
      entries.extend(
          self._FormatPhotoList(self.photo_db.ListPhotos(year, month, day)))

    for e in entries:
      yield fuse.Direntry(e)
 
  def _FormatMonths(self, months):
    return [str('%s-%s' % (m, calendar.month_abbr[int(m)])) for m in months]


class _PhotoFsSetsView(_AbstractView):
  _NAME = 'sets'
  _SELECTS_DIR = 'selects'
  _SELECTS_TAG = 'select'

  def getattr(self, path):
    st = _FsStat()

    path_split = path.split('/')
    if len(path_split) == 2:
      if path_split[1]:
        labels = self.photo_db.GetLabels()
        if path_split[1] in labels:
          return st
      else:
        return st
    elif len(path_split) == 3:
      if path_split[2] == self._SELECTS_DIR:
        return st
      real_st = self._GetRealFileStat(st, path_split[2])
      if (real_st):
        return real_st
    elif len(path_split) == 4:
      real_st = self._GetRealFileStat(st, path_split[3])
      if (real_st):
        return real_st

    return -errno.ENOENT

  def readdir(self, path, _offset):
    entries = ['.', '..']

    path_split = path.split('/')
    if path == '/':  # list sets
      entries.extend(self.photo_db.GetLabels())
    elif len(path_split) == 3:
      entries.extend(
          self._FormatPhotoList(self.photo_db.ListSelectsByLabel(
              self._SELECTS_TAG, path_split[1])))
    elif path_split[1]:
      entries.append(self._SELECTS_DIR)
      entries.extend(
          self._FormatPhotoList(self.photo_db.ListPhotosByLabel(path_split[1])))

    for e in entries:
      yield fuse.Direntry(e)


class _PhotoFsTagsView(_AbstractView):
  _NAME = 'tags'

  def getattr(self, path):
    st = _FsStat()

    if path == '/':
      return st

    path_split = path.split('/')
    tags = set(self.photo_db.GetTags())
    used_tags = path_split[1:]

    real_st = self._GetRealFileStat(st, path_split[-1])
    if (real_st):
      return real_st

    if (len(set(used_tags)) == len(used_tags) and
        set(used_tags).issubset(tags)):
      return st

    return -errno.ENOENT

  def readdir(self, path, _offset):
    entries = ['.', '..']

    path_split = path.split('/')
    tags = set(self.photo_db.GetTags())
    if path == '/':
      entries.extend(tags)
    else:
      used_tags = path_split[1:]
      photos = self._FormatPhotoList(self.photo_db.ListPhotosByTags(used_tags))
      if photos:
        entries.extend(tags.difference(used_tags))
        entries.extend(photos)

    for e in entries:
      yield fuse.Direntry(e)


class _PhotoFsConfView(_AbstractView):
  _NAME = 'conf'
  _PARAMS = set([
    'f', 'iso', 'make', 'camera', 'focal_length', 'lens_model', 'lens_spec'])

  def getattr(self, path):
    st = _FsStat()

    if path == '/':
      return st

    path_split = path.split('/')
    used_conf = path_split[1::2]

    real_st = self._GetRealFileStat(st, path_split[-1])
    if (real_st):
      return real_st

    if (len(set(used_conf)) == len(used_conf) and
        set(used_conf).issubset(self._PARAMS)):
      if len(path_split) % 2 != 0:
        if not self.photo_db.IsConfValueValid(path_split[-2], path_split[-1]):
          return -errno.ENOENT
      return st

    return -errno.ENOENT

  def readdir(self, path, _offset):
    entries = ['.', '..']

    path_split = path.split('/')
    if path == '/':
      entries.extend(self._PARAMS)
    else:
      if len(path_split) % 2 == 0 and path_split[-1] in self._PARAMS:
        entries.extend(self.photo_db.GetConfValues(path_split[-1]))
      else:
        used_conf = path_split[1::2]
        photos = self._FormatPhotoList(
            self.photo_db.ListPhotosByConf(path_split[1::2], path_split[2::2]))
        if photos:
          entries.extend(self._PARAMS.difference(used_conf))
          entries.extend(photos)

    for e in entries:
      yield fuse.Direntry(e)


class _FsStat(fuse.Stat):
  def __init__(self):
    self.st_mode = stat.S_IFDIR | 0755
    self.st_ino = 0
    self.st_dev = 0
    self.st_nlink = 2
    self.st_uid = 0
    self.st_gid = 0
    self.st_size = 4096
    self.st_atime = int(time())
    self.st_mtime = self.st_atime
    self.st_ctime = self.st_atime


def ListViews(): 
  views = []
  for name, obj in inspect.getmembers(sys.modules[__name__]):
    if inspect.isclass(obj) and _VIEW_REGEX.match(name):
      views.append(obj._NAME)
  return views


def GetView(view_name):
  for name, obj in inspect.getmembers(sys.modules[__name__]):
    if (inspect.isclass(obj) and _VIEW_REGEX.match(name)
        and obj._NAME == view_name):
      return obj
  raise ValueError('%s is not a supported view' % view_name)
