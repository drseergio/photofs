# -*- encoding: utf-8 -*-

'''storage.py: stores photofs index.'''

__author__ = 'drseergio@gmail.com (Sergey Pisarenko)'

import fcntl
import hashlib
import os
import sqlite3
from threading import Lock, Timer


class PhotoDb(object):
  _CONF_DIR = os.path.join(os.path.expanduser('~'), '.photofs')
  _COLUMNS = [
      'path', 'datetime', 'last_modified', 'year', 'month', 'day', 'f','iso',
      'make', 'camera', 'focal_length', 'lens_model', 'lens_spec', 'label']
  _CACHE_REFRESH_MIN = 3  # check if cache is valid and build if needed

  def __init__(self, path):
    self._CreateConfFolder()
    self.db_path = os.path.join(self._CONF_DIR, self._GenerateDbId(path))
    self.db_existed = os.path.isfile(self.db_path)
    self.unique_tags = set()
    self.cache = {}
    self.cache_lock = Lock()
    self._PeriodicBuildCache()

  def BuildCache(self):
    self.GetYears()
    self.GetLabels()
    self.GetTags()

  def IsEmptyDb(self):
    return not self.db_existed

  def TryLock(self):
    lock_path = '%s%s' % (self.db_path, '.lock')
    try:
      self.lock_fd = open(lock_path, 'w')
      fcntl.lockf(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
      self.lock_fd.write('acquired')
    except IOError:
      return False

    self._CreateTables()
    return True

  def WaitLock(self):
    lock_path = '%s%s' % (self.db_path, '.lock')
    self.lock_fd = open(lock_path, 'w')
    fcntl.lockf(self.lock_fd, fcntl.LOCK_EX)
    self.lock_fd.write('acquired')

  def StorePhoto(self, path, meta):
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    values = [meta[c] for c in self._COLUMNS]
    cursor.execute('''INSERT INTO `files` (%s)
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''' % ','.join(self._COLUMNS),
        values)
    if meta['tags']:
      self._HandleTags(cursor, meta['tags'], path, meta['datetime'])
    conn.commit()
    conn.close()
    self._EmptyCache()

  def GetYears(self):
    cached = self._GetCache('years')
    if cached:
      return cached
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    years = set([])
    for row in cursor.execute('SELECT year FROM files'):
      years.add(str(row[0]))
    conn.close()
    self._SetCache('years', years)
    return years

  def GetMonths(self, year):
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    months = set([])
    for row in cursor.execute(
        'SELECT month FROM files WHERE year = ?', (year,)):
      months.add(str(row[0]))
    conn.close()
    return months

  def GetDays(self, year, month):
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    days = set([])
    for row in cursor.execute(
        'SELECT day FROM files WHERE year = ? AND month = ?', (year, month)):
      days.add(str(row[0]))
    conn.close()
    return days

  def ListPhotosByYear(self, year):
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    photos = []
    for row in cursor.execute(
        '''SELECT id FROM files
        WHERE year = ?
        ORDER BY datetime ASC''', (year,)):
      photos.append(row[0])
    conn.close()
    return photos

  def ListPhotosByMonth(self, year, month):
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    photos = []
    for row in cursor.execute(
        '''SELECT id FROM files
        WHERE year = ? AND month = ?
        ORDER BY datetime ASC''', (year,month)):
      photos.append(row[0])
    conn.close()
    return photos

  def ListPhotos(self, year, month, day):
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    photos = []
    for row in cursor.execute(
        '''SELECT id FROM files
        WHERE year = ? AND month = ? AND day = ?
        ORDER BY datetime ASC''', (year, month, day)):
      photos.append(row[0])
    conn.close()
    return photos

  def GetRealPhotoPath(self, photo_id):
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    cursor.execute(
        '''SELECT path FROM files WHERE id = ?''', (photo_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
      return result[0]
    return None

  def GetLabels(self):
    cached = self._GetCache('labels')
    if cached:
      return cached
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    labels = set([])
    for row in cursor.execute('SELECT label FROM files'):
      labels.add(str(row[0]))
    conn.close()
    self._SetCache('labels', labels)
    return labels

  def GetTags(self):
    cached = self._GetCache('tags')
    if cached:
      return cached
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    tags = set([])
    for row in cursor.execute('SELECT tag FROM files_tags'):
      tags.add(str(row[0]))
    conn.close()
    self._SetCache('tags', tags)
    return tags

  def ListPhotosByLabel(self, label):
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    photos = []
    for row in cursor.execute(
        '''SELECT id FROM files WHERE label = ? ORDER BY datetime ASC''',
        (label,)):
      photos.append(row[0])
    conn.close()
    return photos

  def ListSelectsByLabel(self, select_tag, label):
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    photos = []
    for row in cursor.execute(
        '''SELECT files.id FROM files, files_tags WHERE label = ? AND
        files_tags.tag = ? AND files_tags.files_rowid == files.id
        ORDER BY files.datetime ASC''',
        (label, select_tag)):
      photos.append(row[0])
    conn.close()
    return photos

  def ListPhotosByTags(self, tags):
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    photos = []
    for row in cursor.execute(
        '''SELECT files_rowid FROM files_tags
        WHERE tag IN (%s) GROUP BY files_rowid HAVING COUNT(files_rowid) = %d
        ORDER BY datetime ASC''' % (
            ','.join('?' * len(tags)), len(tags)), tags):
      photos.append(row[0])
    conn.close()
    return photos

  def DeletePhoto(self, photo_path):
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM files WHERE path = ?', (photo_path,))
    cursor.execute('DELETE FROM files_tags WHERE path = ?', (photo_path,))
    conn.commit()
    conn.close()
    self._EmptyCache()

  def GetConfValues(self, conf):
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    values = set([])
    for row in cursor.execute('SELECT `{0}` FROM files'.format(conf)):
      values.add(str(row[0]))
    conn.close()
    values.remove(None)
    return values

  def IsConfValueValid(self, conf, value):
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM files WHERE {0} = ?'.format(conf), (value,))
    result = cursor.fetchone()
    conn.close()
    return result != None

  def ListPhotosByConf(self, confs, values):
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    photos = []
    for row in cursor.execute(
        '''SELECT id FROM files WHERE {0} ORDER BY datetime ASC'''.format(
            ' AND '.join(['%s = ?' % c for c in confs])), values):
      photos.append(row[0])
    conn.close()
    return photos

  def GetAllPhotosLastModified(self):
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    photos = {}
    for row in cursor.execute('SELECT path, last_modified FROM files'):
      photos[row[0]] = row[1]
    conn.close()
    return photos

  def _CreateConfFolder(self):
    if not os.path.isdir(self._CONF_DIR):
      os.makedirs(self._CONF_DIR)

  def _GenerateDbId(self, path):
    abs_path = os.path.abspath(path)
    return hashlib.md5(abs_path).hexdigest()

  def _CreateTables(self):
    conn = sqlite3.connect(self.db_path)
    columns = ','.join(self._COLUMNS)
    cursor = conn.cursor()
    cursor.execute(
        '''CREATE TABLE IF NOT EXISTS
        `files_tags` (`path`, `tag`, `files_rowid`, `datetime`)''')
    cursor.execute(
        'CREATE INDEX IF NOT EXISTS `tags-path-index` ON `files_tags` (`path`)')
    cursor.execute(
        'CREATE INDEX IF NOT EXISTS `tags-tags-index` ON `files_tags` (`tag`)')
    cursor.execute(
        '''CREATE INDEX IF NOT EXISTS
        `tags-rowid-index` ON `files_tags` (`files_rowid`)''')

    cursor.execute(
        '''CREATE TABLE IF NOT EXISTS `files` (`id` INTEGER PRIMARY
        KEY AUTOINCREMENT, %s)''' % columns)
    for column in self._COLUMNS:
      cursor.execute(
          '''CREATE INDEX IF NOT EXISTS
          `files-{0}-index` ON `files` (`{0}`)'''.format(column))
    conn.commit()
    conn.close()

  def _GetCache(self, key):
    self.cache_lock.acquire()
    if key in self.cache:
      val = self.cache[key]
    else:
      val = None
    self.cache_lock.release()
    return val

  def _SetCache(self, key, value):
    self.cache_lock.acquire()
    self.cache[key] = value
    self.cache_lock.release()

  def _EmptyCache(self):
    self.cache_lock.acquire()
    self.cache = {}
    self.cache_lock.release()

  def _PeriodicBuildCache(self):
    t = Timer(self._CACHE_REFRESH_MIN * 60, self._PeriodicBuildCache)
    t.daemon = True
    t.start()

  def _HandleTags(self, cursor, tags, path, photo_datetime):
    rowid = cursor.lastrowid
    for tag in tags:
      tag_lower = tag.lower()
      if tag_lower not in self.unique_tags:
        self.unique_tags.add(tag_lower)
      cursor.execute(
          '''INSERT INTO files_tags VALUES(?, ?, ?, ?)''',
          (path, tag_lower, rowid, photo_datetime))
