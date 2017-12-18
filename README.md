This program emulates the Epson FX-80 and various other dot matrix printers
of the era which were compatible with it.  It is incredibly rough at present,
but it works for the use case for which it was written: coupling with an
Apple II emulator and pretty faithfully recreating the greeting cards of my
youth (sans the tractor feed edges).

Things that don't work now, but might someday:
* PDF output (currently just SVG)
* Intelligent handling of multiple pages (banners, anyone?)
* Tighter integration with some computer emulators

For now, I use the linapple emulator and tell programs I'm using an
Apricon serial printer interface.  linapple will dump data to a
file.  Run ephex.py, passing it the file, and redirect standard
output to an SVG file, like:

  python ephex.py Printer.txt > mydoc.svg
