# -*- encoding: utf-8 -*-

'''filters.py transforms values returned by GExiv2 library.'''

__author__ = 'drseergio@gmail.com (Sergey Pisarenko)'

from datetime import datetime
from decimal import Decimal

_DATE_FORMAT = '%Y:%m:%d %H:%M:%S'


def filter_datetime(meta, k):
  value = meta.get(k)
  if not value:
    raise ValueError('photo does not have date information')
  return datetime.strptime(meta.get(k), _DATE_FORMAT)


def filter_fnumber(meta, k):
  value = meta.get(k)
  if not value:
    return None
  value_split = value.split('/')
  return str(round(Decimal(value_split[0]) / Decimal(value_split[1]), 1))


def filter_lens_spec(meta, k):
  value = meta.get(k)
  if not value and meta.get_focal_length():
    return str(int(meta.get_focal_length()))
  if value:
    value_split = value.split(' ')
    return value_split[0].split('/')[0] + '-' + value_split[1].split('/')[0]
  return None


def filter_label(meta, k):
  return escape(meta.get(k))


def escape(value):
  if value:
    return value.replace('/', '')
  return None
