import serial,sys
from time import sleep,time



class CRC_CCITT:
   def __init__(self, inverted=True):
      self.inverted=inverted;
      self.tab=256*[[]]
      for i in xrange(256):
         crc=0
         c = i << 8
         for j in xrange(8):
            if (crc ^ c) & 0x8000:
               crc = ( crc << 1) ^ 0x1021
            else:
                  crc = crc << 1
            c = c << 1
            crc = crc & 0xffff
         self.tab[i]=crc;
   def update_crc(self, crc, c):
      c=0x00ff & (c % 256)
      if self.inverted: c=self.flip(c);
      tmp = ((crc >> 8) ^ c) & 0xffff
      crc = (((crc << 8) ^ self.tab[tmp])) & 0xffff
      return crc;
   def checksum(self,str):
      """Returns the checksum of a string.""";
      #crcval=0;
      crcval=0xFFFF;
      for c in str:
        crcval=self.update_crc(crcval, ord(c));
      return crcval;
   def flip(self,c):
      """Flips the bit order, because that's what Fossil wants."""
      l=[0, 8, 4, 12, 2, 10, 6, 14, 1, 9, 5, 13, 3, 11, 7, 15];
      return ((l[c&0x0F]) << 4) + l[(c & 0xF0) >> 4];
   def test(self):
      return True;

def hex(str):
  """Returns the hex decoded version of a byte string."""
  toret="";
  if str==None: return "none";
  for c in str:
    toret="%s %02x" % (toret,ord(c));
  return toret;
  
  
def tx(msg,rx=True):
  """Transmit a MetaWatch packet.  SFD, Length, and Checksum will be added."""
  #Prepend SFD, length.
  msg="\x01"+chr(len(msg)+4)+msg;
  #Append CRC.
  crc=CRC.checksum(msg);
  msg=msg+chr(crc&0xFF)+chr(crc>>8); #Little Endian

  port.write(msg);
  print "Sent message: %s" % hex(msg);

  
  
  
tty='/dev/tty.MetaWatch'
CRC=CRC_CCITT();


if len(sys.argv)>1:
    tty=sys.argv[1];
else:
    print "Usage: $ python pywmserial.py /dev/tty.watch"
    exit(1)
    
port=serial.Serial(tty)
port.flush()
port.flushOutput()
port.flushInput()

if not port:
    print "*Error opening serial port!"

sleep(1)

# buzz
port.write("\x01\x0c\x23\x00\x01\xf4\x01\xf4\x01\x01\x81\xb1")

sleep(1)
# load template
port.write("\x01\x07\x44\x00\x01\x18\xce")

sleep(0.5)

# update buffer
port.write("\x01\x07\x43\x10\x00\x08\x76")

sleep(0.5)



# test write buffer
t0 = time()

for i in range(96):
    msg = "\x40\x10"+chr(i)+"\xff\xff\xff\xff\x00\x00\x00\xff\xff\xff\xff\xff"
    sleep(0.01)
    tx(msg)

t1 = time()
delta = t1-t0
print "sent buffer in " + str(delta) + " seconds."

sleep(0.5)

# update buffer
port.write("\x01\x07\x43\x10\x00\x08\x76")    

port.flush()
port.flushOutput()
port.flushInput()
port.close()




