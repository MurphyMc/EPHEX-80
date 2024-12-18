try:
  from ephex_charset import chars, widths
except Exception:
  # Well, at least bitmaps will work
  pass

from array import array
import sys

# This is like the baseline space between dots.
PIX = 1.0

SVG_HEADER = """<?xml version="1.0" encoding="ISO-8859-1" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" height="{h}" width="{w}" version="1.1" xmlns:xlink="http://www.w3.org/1999/xlink" >
"""

SVG_FOOTER = """</svg>
"""

DOT = """<circle cx="{x}" cy="{y}" r="{r}" style="stroke-width:0px; fill-opacity:{opacity}; fill:black;" />
"""


def err_out (s):
  print >>sys.stderr, s


def scale (n):
  """
  Sloppy function that takes a size of some sort and returns it
  formatted for the output SVG.
  """
  if type(n) is str:
    if n.endswith("pt"):
      return n
  return str(n) + "pt"


class EPHEX (object):
  def __init__ (self, auto_cr = True, dot_size = 1.2,
                left_edge = 0.0, darkness = 0.6):
    """
    auto_cr inserts a CR after LF if True
    dot_size is the diameter of an individual dot
    left_edge is where the head returns to after CR (inches)
    darkness is how dark/black the ink is
    """

    self.form_feed_callback = None

    self._xs = array('d')
    self._ys = array('d')

    self.auto_cr = auto_cr
    self.dot_size = dot_size
    self.left_edge = left_edge
    self.darkness = darkness

    self.proportional = False

    # Line spacing.  This is the default for this printer.
    self.line_spacing = 12

    self.x = self.left_edge
    self.y = 0

    # Set functions to handle the single-character control codes
    self._codes = {}
    for c,f in self.__class__.__dict__.iteritems():
      if c.startswith("_code_"):
        ch = int(c[6:], 16)
        self._codes[chr(ch)] = getattr(self, c)

    # These printers have simple codes wired to some of the more
    # specific print modes.  These can be altered using <ESC>?.
    self._graphic_modes = {"K":0,"L":1,"Y":2,"Z":3}


    # Initialize the generator used for the state machine
    self._g = self._feed_input()
    self._g.send(None)

  def _code_7 (self):
    out("<!-- BEEP -->")

  def _code_8 (self):
    # Backspace
    pass

  def _code_9 (self):
    # Tab
    pass

  def _code_A (self):
    # newline
    self.y += self.line_spacing
    if self.auto_cr:
      self._code_D()

  def _code_B (self):
    # VT (vertical tab)
    pass

  def _code_C (self):
    if self.form_feed_callback:
      self.form_feed_callback(self)

  def _code_D (self):
    # Carriage return
    self.x = self.left_edge


  def save (self, file_or_name):
    close = False
    if isinstance(file_or_name, str):
      file_or_name = file(file_or_name, "w")
      close = True

    for p in self._save_generator():
      file_or_name.write(p)

    if close:
      file_or_name.close()

  def save_to_string (self):
    s = ''
    for p in self._save_generator():
      s += p
    return s

  def drain (self):
    s = ''
    for i in xrange(len(self._xs)):
      x = self._xs[i]
      y = self._ys[i]

      s += DOT.format(x=scale(x),y=scale(y),r=scale(self.dot_size/2.0),
                      opacity=self.darkness)

    del self._xs[:]
    del self._ys[:]

    return s

  def _save_generator (self):
    assert len(self._xs) == len(self._ys)
    yield SVG_HEADER.format(w=scale(8.5*72), h=scale(11*72))

    for i in xrange(len(self._xs)):
      x = self._xs[i]
      y = self._ys[i]

      yield DOT.format(x=scale(x),y=scale(y),r=scale(self.dot_size/2.0),
                       opacity=self.darkness)

    yield SVG_FOOTER

  def _stripe (self, c):
    x = self.x
    for i,p in enumerate('%09i' % (int(bin(c)[2:]),)):
      if p == '1':
        y = self.y + i * PIX
        self._xs.append(x)
        self._ys.append(y)

  def _print (self, c):
    # Print a character
    o = chars[ord(c)]
    o = o[0:10]
    x = self.x
    for col in o:
      self._stripe(col)
      self.x += PIX/2.0 #TODO: adjust based on speed?
    if self.proportional:
      self.x = x + (widths[ord(c)])/2.0
    else:
      self.x += PIX/1.0

  def feed_input (self, data):
    """
    Feed some data (print instructions), which may produce some output.
    """
    for d in data:
      self._g.send(d)


  def _feed_input (self):
    """
    Internal use.

    Creates the generator used for feeding input data.
    """
    while True:
      c = (yield)
      if c is None: break
      f = self._codes.get(c)
      if f is not None:
        f()
      elif c >= ' ' and c <= '\xf8':
        self._print(c)
      elif c == '\x1b':
        c = (yield)
        cn = ord(c)

        # Line Spacing
        if c == '0':
          self.line_spacing = 9
        elif c == '1':
          self.line_spacing = 7
        elif c == '2':
          self.line_spacing = 12
        elif c == 'A':
          c = ord((yield))
          self.line_spacing = c
        elif c == '3':
          c = ord((yield))
          self.line_spacing = c/3.0
        elif c == 'J':
          c = ord((yield))/3.0
          self.y += c
        elif c == 'j':
          c = ord((yield))/3.0
          self.y -= c

        elif c == 'p':
          # Proportional
          c = (yield)
          self.proportional = (c == '1')

        # Dot Graphics
        elif c == "?":
          c = (yield)
          m = ord((yield))
          if c in "KLYZ":
            self._graphic_modes[c] = m
          else:
            err_out("Bad code for mode alias")
        elif c == "^":
          pass
          #TODO: nine pin mode
        elif c in "KLYZ*":
          fast = False # High speed, doesn't print consecutive dots

          m = self._graphic_modes.get(c)
          if m is None:
            if c == "*":
              m = ord((yield))

          if m == 0:
            ppi = 1.0/60
          elif m == 1:
            ppi = 1.0/120
          elif m == 2:
            fast = True
            ppi = 1.0/120
          elif m == 3:
            fast = True
            ppi = 1.0/240
          elif m == 4:
            ppi = 1.0/80
          elif m == 5:
            ppi = 1.0/72
          elif m == 6:
            ppi = 1.0/90

          n1 = ord((yield))
          n2 = ord((yield))
          w = n1 + n2 * 256

          for i in xrange(w):
            c = ord((yield))
            self._stripe(c)
            self.x += (ppi * 72.0)

        else:
          sys.stderr.write("Don't know %X (%s).\n" % (ord(c),ord(c)))
