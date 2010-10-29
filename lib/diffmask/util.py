#!/usr/bin/python
#	vim:fileencoding=utf-8
# (C) 2010 Michał Górny, distributed under the terms of 3-clause BSD license

def toString(obj):
	""" Convert the diffmask object to string. If it has a `toString'
		method, use it. Otherwise, hope it'll converted implicitly. This
		is a cheap wrapper to avoid Python2/3 string incompatibility.
		"""
	if hasattr(obj, 'toString'):
		return obj.toString()
	else:
		return obj

class DiffmaskList(list):
	""" An enhanced list class. """
	def toString(self):
		""" Convert the list to a string. """
		return ''.join([toString(x) for x in self])

	def find(self, key):
		""" Return the list entry being equal to the passed one or None,
			if no match occured. """
		for e in self:
			if e == key:
				return e
		else:
			return None
