Original code by Travis Goodspeed https://github.com/travisgoodspeed/PyMetaWatch

Forked from Joe Hughes https://github.com/joehughes/PyMetaWatch 

Supports:
- bluetooth or tty connections 
- auto-reconnect
- control over all buttons
- basic mapping of buttons to shell commands 
- sending images
- sending text 

Python dependencies:
- PIL (for sending images and text)
- config 


Usage:

Default (uses serial mode - drops into idle mode)
python pymw.py --<type> <device> <mode>

------------------------------------

Device/Type Selection

TTY Serial
python pymw.py --serial </dev/tty.device> 

Bluetooth
python pymw.py --bt <watch-address> 

-----------------------------------

Modes

Interactive mode (enables all buttons and maps them to shell commands defined in pywm.cfg)
python pymw.py --<type> <device> interactive

Command line mode (send and image)
python pymw.py --<type> <device> --image <image.bmp>

Command line mode (send text)
python pymw.py --<type> <device> --text "some text"

Test Mode (continuously sends a testbuffer)
python pymw.py --<type> <device> testbuffer

-----------------------------------


These URLs are handy,
http://www.dpin.de/~nils/metawatch
http://www.metawatch.org/development.html
http://retrovirus.com/incr/2011/09/metawatch-hacks-resources/

Image sources:

dalek.bmp was derived from Dalek Stencil by Styrr
http://styrr.deviantart.com/art/Dalek-stencil-178678725
