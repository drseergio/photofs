# -*- encoding: utf-8 -*-

'''views.py: implements various viewing modes that photofs provides.'''

__author__ = 'drseergio@gmail.com (Sergey Pisarenko)'

import fuse

import calendar
import errno
import inspect
import os
import re
import shutil
import stat
import sys
from time import time

_VIEW_REGEX = re.compile(r'^_PhotoFs\w+View$')


class _AbstractView(object):
  _FILE_ID_REGEX = re.compile(r'^\d+\s\((0x\w+)\).jpg$')
  _QEYTAKS_TMP_REGEX = re.compile(r'^\d+\s\((0x\w+)\).jpg(\d+)$')

  def __init__(self, photo_db):
    self.photo_db = photo_db
    self.tmp_files = {}

  '''Pretend that we can write to the folder.

  Some libaries like to write into temporary files and then replace the original
  file. This method will trick them into thinking that it's all working while we
  actually mess with files in /tmp.
  '''
  def getattr(self, path_split):
    match = self._QEYTAKS_TMP_REGEX.match(path_split[-1])
    if match:
      photo_id = int(match.group(1), 16)
      real_path = self.photo_db.GetRealPhotoPath(photo_id)
      if real_path:
        st = FsStat()
        st.st_nlink = 1
        st.st_mode = 33188
        tmp_key = '/'.join(path_split)
        self.tmp_files[tmp_key] = os.path.join(
            '/tmp', match.group(1) + match.group(2))
        return st
    return None

  def open(self, path_split, flags):
    real_path = self._GetRealPath(path_split)
    if real_path:
      if (flags & 3) == os.O_RDONLY:
        return open(real_path, 'rb')
      elif (flags & 3) == os.O_WRONLY or (flags & 3) == os.O_RDWR:
        return open(real_path, 'wb')
      elif flags & os.O_APPEND:
        return open(real_path, 'ab')
      else:
        return -errno.EINVAL
    else:
      match = self._QEYTAKS_TMP_REGEX.match(path_split[-1])
      if match:
        real_path = self.tmp_files['/'.join(path_split)]
        return open(real_path, 'ab')
    return -errno.ENOENT

  def read(self, path_split, length, offset, fh):
    fh.seek(offset)
    return fh.read(length)

  def write(self, path_split, buf, offset, fh):
    fh.seek(offset)
    fh.write(buf)
    return len(buf)

  def truncate(self, path_split, length):
    fd = self.open(path_split, os.O_WRONLY)
    os.ftruncate(fd.fileno(), length)

  def release(self, path_split, flags, fh):
    fh.close()

  def unlink(self, path_split):
    return 0

  def rename(self, oldPath_split, newPath_split):
    tmp_key = '/'.join(oldPath_split)
    tmp_path = self.tmp_files[tmp_key]
    del self.tmp_files[tmp_key]
    real_path = self._GetRealPath(newPath_split)
    return shutil.move(tmp_path, real_path)

  def _GetRealPath(self, path_split):
    match = self._FILE_ID_REGEX.match(path_split[-1])
    if match:
      photo_id = int(match.group(1), 16)
      real_path = self.photo_db.GetRealPhotoPath(photo_id)
      return real_path
    return None

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
  _YEAR_ALL_FOLDER = 'all'

  def getattr(self, path_split):
    tmp = super(_PhotoFsDateView, self).getattr(path_split)
    if tmp:
      return tmp
    st = FsStat()

    if len(path_split) == 1:
      years = self.photo_db.GetYears()
      if path_split[0] in years:
        return st
    elif len(path_split) == 2:
      if path_split[1] == self._YEAR_ALL_FOLDER:
        return st
      if path_split[1]:  # check if month exists
        months = self.photo_db.GetMonths(path_split[0])
        month = path_split[1].split('-')[0]
        if month in months:
          return st
    elif len(path_split) == 3:
      if path_split[2]:  # check if day exists
        real_st = self._GetRealFileStat(st, path_split[2])
        if (real_st):
          return real_st

        days = self.photo_db.GetDays(path_split[0], path_split[1].split('-')[0])
        if path_split[2] in days:
          return st
    elif len(path_split) == 4:
      real_st = self._GetRealFileStat(st, path_split[3])
      if (real_st):
        return real_st

    return -errno.ENOENT
 
  def readdir(self, path_split, _offset):
    entries = []

    if not path_split:  # list years
      entries.extend(self.photo_db.GetYears())
    elif len(path_split) == 1:  # list months
      year = path_split[0]
      entries.extend(self._FormatMonths(self.photo_db.GetMonths(year)))
      entries.append(self._YEAR_ALL_FOLDER)
    elif len(path_split) == 2:
      year = path_split[0]
      if path_split[1] == self._YEAR_ALL_FOLDER:
        entries.extend(
            self._FormatPhotoList(self.photo_db.ListPhotosByYear(year)))
      else:  # list days
        month = path_split[1].split('-')[0]
        entries.extend(self.photo_db.GetDays(year, month))
        entries.extend(
            self._FormatPhotoList(self.photo_db.ListPhotosByMonth(year,month)))
    elif len(path_split) == 3:  # list actual photos
      year = path_split[0]
      month = path_split[1].split('-')[0]
      day = path_split[2]
      entries.extend(
          self._FormatPhotoList(self.photo_db.ListPhotos(year, month, day)))

    return entries
 
  def _FormatMonths(self, months):
    return [str('%s-%s' % (m, calendar.month_abbr[int(m)])) for m in months]


class _PhotoFsSetsView(_AbstractView):
  _NAME = 'albums'
  _SELECTS_DIR = 'selects'
  _SELECTS_TAG = 'select'

  def getattr(self, path_split):
    tmp = super(_PhotoFsSetsView, self).getattr(path_split)
    if tmp:
      return tmp
    st = FsStat()

    if len(path_split) == 1:
      labels = self.photo_db.GetLabels()
      if path_split[0] in labels:
        return st
    elif len(path_split) == 2:
      if path_split[1] == self._SELECTS_DIR:
        return st
      real_st = self._GetRealFileStat(st, path_split[1])
      if (real_st):
        return real_st
    elif len(path_split) == 3:
      real_st = self._GetRealFileStat(st, path_split[2])
      if (real_st):
        return real_st

    return -errno.ENOENT

  def readdir(self, path_split, _offset):
    entries = []

    if not path_split:  # list sets
      entries.extend(self.photo_db.GetLabels())
    elif len(path_split) == 2:
      entries.extend(
          self._FormatPhotoList(self.photo_db.ListSelectsByLabel(
              self._SELECTS_TAG, path_split[0])))
    else:
      entries.append(self._SELECTS_DIR)
      entries.extend(
          self._FormatPhotoList(self.photo_db.ListPhotosByLabel(path_split[0])))

    return entries


class _PhotoFsTagsView(_AbstractView):
  _NAME = 'tags'

  def getattr(self, path_split):
    tmp = super(_PhotoFsTagsView, self).getattr(path_split)
    if tmp:
      return tmp
    st = FsStat()

    tags = set(self.photo_db.GetTags())
    used_tags = path_split

    real_st = self._GetRealFileStat(st, path_split[-1])
    if (real_st):
      return real_st

    if (len(set(used_tags)) == len(used_tags) and
        set(used_tags).issubset(tags)):
      return st

    return -errno.ENOENT

  def readdir(self, path_split, _offset):
    entries = []

    tags = set(self.photo_db.GetTags())
    if not path_split:
      entries.extend(tags)
    else:
      used_tags = path_split
      photos = self._FormatPhotoList(self.photo_db.ListPhotosByTags(used_tags))
      if photos:
        entries.extend(tags.difference(used_tags))
        entries.extend(photos)

    return entries


class _PhotoFsConfView(_AbstractView):
  _NAME = 'camera'
  _PARAMS = set([
    'f', 'iso', 'make', 'camera', 'focal_length', 'lens_model', 'lens_spec'])

  def getattr(self, path_split):
    tmp = super(_PhotoFsConfView, self).getattr(path_split)
    if tmp:
      return tmp
    st = FsStat()

    used_conf = path_split[::2]

    real_st = self._GetRealFileStat(st, path_split[-1])
    if (real_st):
      return real_st

    if (len(set(used_conf)) == len(used_conf) and
        set(used_conf).issubset(self._PARAMS)):
      if len(path_split) % 2 == 0:
        if not self.photo_db.IsConfValueValid(path_split[-2], path_split[-1]):
          return -errno.ENOENT
      return st

    return -errno.ENOENT

  def readdir(self, path_split, _offset):
    entries = []

    if not path_split:
      entries.extend(self._PARAMS)
    else:
      if len(path_split) % 2 != 0 and path_split[-1] in self._PARAMS:
        entries.extend(self.photo_db.GetConfValues(path_split[-1]))
      else:
        used_conf = path_split[::2]
        photos = self._FormatPhotoList(
            self.photo_db.ListPhotosByConf(path_split[::2], path_split[1::2]))
        if photos:
          entries.extend(self._PARAMS.difference(used_conf))
          entries.extend(photos)

    return entries


class FsStat(fuse.Stat):
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


def GetViews(db): 
  views = {}
  for name, obj in inspect.getmembers(sys.modules[__name__]):
    if inspect.isclass(obj) and _VIEW_REGEX.match(name):
      views[obj._NAME] = obj(db)
  return views
