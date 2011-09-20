#!/usr/bin/python
# Quick an dirty MetaWatch client in Python for pybluez.
# Written by Travis Goodspeed on--not for--the Nokia N900.

# This doesn't work with very old versions of the MetaWatch.
# Be sure to use a minimum of 0.7.15 and 1.1.7.

import sys,os, time,serial,config



MODE_IDLE = 0
MODE_APPLICATION = 1
MODE_NOTIFICATION = 2
MODE_SCROLL = 3

STATUS_CHANGE_MODE = 0
STATUS_CHANGE_DISPLAYIMEOUT = 1

BUTTON_A = 0
BUTTON_B = 1
BUTTON_C = 2
BUTTON_D = 3
BUTTON_E = 5
BUTTON_F = 6

BUTTON_TYPE_IMMEDIATE = 0
BUTTON_TYPE_PRESSANDRELEASE = 1
BUTTON_TYPE_HOLDANDRELEASE = 2
BUTTON_TYPE_LONHOLDANDRELEASE = 3


class MetaWatch:
   def __init__(self, watchaddr=None, useSerial=False):
      self.CRC=CRC_CCITT();
      self.useSerial=useSerial
      self.buttonMap=['buttonA','buttonB','buttonC','reserved','buttonD','buttonE','buttonF']
      self.config=config.Config(file("pymw.cfg"))
      self.idleCounter=0
      self.tty=None
      if not useSerial:
          
          try:
             import bluetooth
          except ImportError:
             bluetooth = None
             import lightblue
             
          while watchaddr==None or watchaddr=="none":
             print "performing inquiry..."
             if bluetooth:
                nearby_devices = bluetooth.discover_devices(lookup_names = True)
             else:
                # Need to strip the third "device class" tuple element from results
                nearby_devices = map(lambda x:x[:2], lightblue.finddevices())
            
             print "found %d devices" % len(nearby_devices)
             for addr, name in nearby_devices:
                print "  %s - '%s'" % (addr, name)
                if name and 'MetaWatch Digital' in name:
                   watchaddr=addr;
             print "Identified Watch at %s" % watchaddr;

          # MetaWatch doesn't run the Service Discovery Protocol.
          # Instead we manually use the portnumber.
          port=1;
      
          print "Connecting to %s on port %i." % (watchaddr, port);
          if bluetooth:
             sock=bluetooth.BluetoothSocket(bluetooth.RFCOMM);
          else:
             sock=lightblue.socket();

          self.sock=sock;
          sock.settimeout(10);  #IMPORTANT Must be patient.
          sock.connect((watchaddr,port));
      else:
          self.tty=watchaddr
          self.sock=serial.Serial(self.tty)
          self.sock.timeout = 1
          self.sock.setBaudrate(4000000)
          print self.sock
          #self.sock.flush()
          self.sock.flushInput()
          self.sock.flushOutput()
      
      time.sleep(1)    
#      self.setclock()
      #Buzz to indicate connection.
      self.buzz();
      time.sleep(0.5) 

   def close(self):
      print "*** closing"
      """Close the connection."""
      if self.useSerial:
          #self.sock.flush()
          self.sock.flushInput()
          self.sock.flushOutput()
      
      self.sock.close();


   verbose=1;
   def tx(self,msg,rx=True):
      """Transmit a MetaWatch packet.  SFD, Length, and Checksum will be added."""
      #Prepend SFD, length.
      msg="\x01"+chr(len(msg)+4)+msg;
      #Append CRC.
      crc=self.CRC.checksum(msg);
      msg=msg+chr(crc&0xFF)+chr(crc>>8); #Little Endian
      
      if self.useSerial:
          self.sock.write(msg);
      else:
          self.sock.send(msg);
          
      if self.verbose: print "Sent message: %s" % hex(msg);
      time.sleep(0.02)
      
      if not rx: return None;
      return self.rx();
   def rx(self):
      data=None;
      #Is there a reply?
      if self.useSerial:
          try:
              bytesToRead=self.sock.inWaiting()
              data=self.sock.read(bytesToRead)
              data=data[2:]
          except serial.serialutil.SerialException:
                print "*** Error - unable to read. Disconnected ?"
      else:
          try:
              data=self.sock.recv(32);
              data=data[2:];
          except IOError:
              pass;
          
              
      if self.verbose and len(data)>0: print "Received [%s]" % hex(data);
      return data;
   
   def writebuffer(self,mode,row1,data1,row2=None,data2=None):
      """Writes image data to the Draw Buffer.
      You'll need to send activatedisplay() to swap things over when done."""
      
      option=mode; #idle screen, single row.
      if row2!=None: option=option|0x10;
      
      packet="\x40%s%s%s\x00" % (
         chr(option),
         chr(row1),data1[0:12]
         );
      if row2!=None:
         packet="%s%s%s" % (
            packet,
            chr(row2),data2[0:11]);
      self.tx(packet,rx=False);
      
      return;
   def clearbuffer(self,mode=1,filled=True):
      self.loadtemplate(mode,filled);
   
   def testwritebuffer(self,mode=1):
      m=mode;
      image=["\x00\xFF\x00\xFF\x00\xFF\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
             "\xFF\x00\xFF\x00\xFF\x00\xFF\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
             ];
             
      t0 = time.time()
         
      self.loadtemplate(mode=m,filled=1);
      # Blank some rows.
      for foo in range(0,96):
         self.writebuffer(m,
                        foo, image[(foo/8)%2]
                        #);
                        ,foo+40, image[((foo+40)/8)%2]);
         #self.updatedisplay(mode=m,activate=1);
         #time.sleep(0.1);
         
      t1 = time.time()
      delta = t1-t0
      print "sent buffer in " + str(delta) + " seconds."
                
      self.updatedisplay(mode=m);
   
   def writeimage(self,mode=0,image="template.bmp", live=False):
      """Write a 1bpp BMP file to the watch in the given mode."""
      import Image;
      im=Image.open(image);
      pix=im.load();
      for y in range(0,96):
         rowstr="";
         rowdat="";
         for x in range(0,96,8):
            byte=0;
            for pindex in range(0,8):
               pixel=pix[x+pindex,y];
               if (pixel > 0):
                  pixel = 1
               rowstr="%s%i" % (rowstr,pixel);
               #byte=((byte<<1)+pixel);
               byte=((byte>>1)|(pixel<<7));
            rowdat="%s%s" % (rowdat,chr(byte));
         #print rowstr;
         self.writebuffer(mode,
                          y,rowdat)#,
                          #0,rowdat);
         if live:
            self.updatedisplay(mode=mode);
            time.sleep(0.1);
      self.updatedisplay(mode=mode);


   def writeText(self,mode=0,text=''):
      import Image,ImageDraw,ImageFont

      image = Image.new("1",(96,96))
      self.draw_word_wrap(image,text,1,1)
      image.save('tmp.bmp','BMP')
      self.writeimage(mode,"tmp.bmp",live=True)  

   def draw_word_wrap(self,img, text, xpos=0, ypos=0, max_width=95):
      import Image,ImageDraw,ImageFont
      font=ImageFont.load_default()
        
      # textwrapping adapted from http://jesselegg.com/archives/2009/09/5/simple-word-wrap-algorithm-pythons-pil/
      
      draw = ImageDraw.Draw(img)
      text_size_x, text_size_y = draw.textsize(text, font=font)
      remaining = max_width
      space_width, space_height = draw.textsize(' ', font=font)
      # use this list as a stack, push/popping each line
      output_text = []
      # split on whitespace...    
      for word in text.split(None):
        word_width, word_height = draw.textsize(word, font=font)
        if word_width + space_width > remaining:
          output_text.append(word)
          remaining = max_width - word_width
        else:
          if not output_text:
            output_text.append(word)
          else:
            output = output_text.pop()
            output += ' %s' % word
            output_text.append(output)
          remaining = remaining - (word_width + space_width)
      for text in output_text:
        draw.text((xpos, ypos), text, font=font, fill='white')
        ypos += text_size_y
      
      
      
   def updatedisplay(self,mode=0,activate=0):
      """Update the display to a particular mode."""
      if activate: mode=mode|0x10;
      self.tx("\x43%s" % chr(mode),rx=False);
   
   def loadtemplate(self,mode=0,filled=0):
      """Update the display to a particular mode."""
      self.tx("\x44%s%s" % (chr(mode),
                            chr(filled)),
              rx=False);
   
   
   
   def waitForDevice(self):
       self.sock.close()
       while not self.sock.isOpen():
           try:
               print "*** trying to reconnect."
               self.sock.open()
           except serial.serialutil.SerialException:
               print "*** error - unable to reconnect. sleeping 1 seconds."
               pass
           time.sleep(1)
       
       # reconnected
       time.sleep(1)
       self.buzz()
       print "*** reconnected!"
          
       
   def ping(self):
       try:
           self.setclock()
           return True
       except serial.serialutil.SerialException:
           return False
           
           
   def idle(self):
      """Wait a second."""
      time.sleep(0.5)
      self.idleCounter=(self.idleCounter+1)%10
      
      # ping the device to check if it's still connected
      if self.idleCounter==0:
          if not self.ping():
              print "*** Error - Disconnected! Entering wait loop..."
              self.waitForDevice()
          
      #time.sleep(1);
      data = self.rx();
      if not data:
        return
      
      cmd = data[0]
      if cmd == "\x34":
        # we received a button press
        buttonIndex = ord(data[1])
        print "button [%i] pressed" % buttonIndex; 
        
        if self.config:
            runScript = self.config.get(self.buttonMap[buttonIndex])
            if runScript:
                print runScript
                os.system(runScript)

      
   def buzz(self, ms_on=500, ms_off=500, cycles=1):
      """Buzz the buzzer."""
      
      ms_on = min(ms_on, 65535)
      ms_off = min(ms_off, 65535)
      cycles = min(cycles, 256)
      
      message = []
      message.append("\x23\x00\x01")
      message.append(chr(ms_on % 256))
      message.append(chr(ms_on / 256))
      message.append(chr(ms_off % 256))
      message.append(chr(ms_off / 256))
      message.append(chr(cycles))
      self.tx(''.join(message), False)

   def showtime(self, watch_controls_top):
      """Set whether the watch shows the time at top."""

      message = []
      message.append("\x42\x00")
      if watch_controls_top:
         message.append("\x00")
      else:
         message.append("\x01")

      self.tx(''.join(message), False)

   def gettype(self):
      """Get the version information."""
      devtyperesp=self.tx("\x01\x00");
      devtype=ord(devtyperesp[2]);
      types=["Reserved",
             "Ana-Digi", "Digital",
             "DigitalDev", "AnaDigitalDev"];
      self.devtype=types[devtype];
      print "Identified %s MetaWatch" % self.devtype;
   def getinfostr(self,item=0x00):
      """Get the information string."""
      string=self.tx("\x03\x00%s" % chr(item));
      return string[:len(string)-2];  #Don't include the checksum.
   def getinfo(self):
      """Get all the information strings.""";
      model=self.getinfostr(0);
      version=self.getinfostr(1);
      return "%s %s" % (model,version);
   def setclock(self):
      """Set the date and time of the watch to the system time."""
      ltime=time.localtime();
      #Year in BIG ENDIAN, not LITTLE.
      str="\x07\xdb%s%s%s%s%s%s\x01\x01" % (
         chr(ltime.tm_mon),  #month
         chr(ltime.tm_mday), #day of month
         chr((ltime.tm_wday+1) % 7), #day of week
         chr(ltime.tm_hour), #hour
         chr(ltime.tm_min),  #min
         chr(ltime.tm_sec),  #sec
         );
      self.tx("\x26\x00"+str, rx=False);
   
   def getclock(self):
      """Get the local time from the watch, in order to set it or measure drift."""
      #Year in LITTLE ENDIAN, not BIG.
      data=self.tx("\x27\x00");
      date=data[2:]
      #print "Interpreting %s" % hex(date);
      year=ord(date[1])*256+ord(date[0])
      month=ord(date[2]);
      day=ord(date[3]);
      dayofweek=ord(date[4]);
      hour=ord(date[5]);
      minute=ord(date[6]);
      second=ord(date[6]);
      print "%02i:%02i on %02i.%02i.%04i" % (
         hour, minute,
         day, month, year);

  
   def configureWatchMode(self,mode=0, save=0, displayTimeout=0, invertDisplay=True):
      msg=[]
      msg.append("\x41")
      msg.append(chr(mode))
      msg.append(chr(displayTimeout))
      msg.append(chr(invertDisplay))

      self.tx(''.join(msg),rx=False)
          
   def enableButton(self, mode=0,buttonIndex=0, type=BUTTON_TYPE_IMMEDIATE):
      msg=[]
      msg.append("\x46\x00")
      msg.append(chr(mode))
      msg.append(chr(buttonIndex))
      msg.append(chr(type))
      msg.append("\x34")
      msg.append(chr(buttonIndex))

      self.tx(''.join(msg),rx=False)
   
   def disableButton(self, mode=0,buttonIndex=0, type=BUTTON_TYPE_IMMEDIATE):
     msg=[]
     msg.append("\x47\x00")
     msg.append(chr(mode))
     msg.append(chr(buttonIndex))
     msg.append(chr(type))
     
     self.tx(''.join(msg),rx=False)
        
   def getButtonConfiguration(self,mode=0,buttonIndex=0):
      msg=[]
      msg.append("\x48\x00")
      msg.append(chr(mode))
      msg.append(chr(buttonIndex))
      msg.append("\x00\x00\x00")
      
      data = self.tx(''.join(msg))
       
      print "button:%i %s" %(buttonIndex, data)

   def getBatteryVoltage(self):
     str="\x56\x00"
     data=self.tx(str)
     volt=ord(data[1])*256+ord(data[0])
     chargerAttached=ord(data[2])
     isCharging=ord(data[3])
     print "battery:%s charger:%s isCharging:%s" %(volt,chargerAttached,isCharging)

   def setDisplayInverted(self, inverted=True):
     str=""
     if inverted:
        str="\x41\x00\x00\x01"
     else:
        str="\x41\x00\x00\x00"
     
     self.tx(str,rx=False)

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






def testMode(addr=None,useSerial=True):
    print "*** entering test mode"
    mw=MetaWatch(addr,useSerial);
    try:
       while True:
             mw.testwritebuffer()
             time.sleep(1)
             mw.clearbuffer(mode=MODE_IDLE,filled=True);
             mw.updatedisplay(mode=MODE_IDLE)
    except KeyboardInterrupt:
              mode=0
              mw.updatedisplay(mode)
              pass
    mw.close();


def idleMode(addr=None,useSerial=True):
    print "**** entering idle mode"
    mw=MetaWatch(addr,useSerial);
    
    mw.enableButton(MODE_IDLE,BUTTON_A, BUTTON_TYPE_IMMEDIATE)
    mw.enableButton(MODE_IDLE,BUTTON_B, BUTTON_TYPE_IMMEDIATE)
    mw.enableButton(MODE_IDLE,BUTTON_C, BUTTON_TYPE_IMMEDIATE)
    mw.enableButton(MODE_IDLE,BUTTON_D, BUTTON_TYPE_IMMEDIATE)
    mw.enableButton(MODE_IDLE,BUTTON_E, BUTTON_TYPE_IMMEDIATE)
    mw.enableButton(MODE_IDLE,BUTTON_F, BUTTON_TYPE_IMMEDIATE)
      
    try:
       while True:
             mw.idle()
    except KeyboardInterrupt:
              mode=0
              mw.updatedisplay(MODE_IDLE)
              pass
      
    mw.close(); 

def main(): 
  watchaddr=None;
  useSerial=True
  mode=MODE_IDLE;
  
  if len(sys.argv)>=3:
      cmd = sys.argv[1]
      arg = sys.argv[2]
      
      if cmd=='--serial':
          useSerial=True
          watchaddr=arg
      else:
          useSerial=False
          watchaddr=arg
      
      print cmd + " " + arg
      
      if len(sys.argv)==4:
          option = sys.argv[3]
          if option=='testbuffer':
              testMode(watchaddr,useSerial)
          elif option=='interactive':
              idleMode(watchaddr,useSerial)
          else:
              imgfile="010dev.bmp";
              if len(sys.argv)>2:
                 imgfile=sys.argv[2];
                 mw.writeimage(mode=mode,image=imgfile,live=True);
  else:
      idleMode(watchaddr,useSerial)      


  

  #mw.getBatteryVoltage()
  #mw.configureWatchMode(mode=mode, displayTimeout=20, invertDisplay=False)

  # First, clear the draw buffer to a filled template.
 # mw.clearbuffer(mode=mode,filled=True);



  #mw.updatedisplay(mode)
  #mw.writeText(mode,"Hello World  Hello World again and again and again and again and again and again...")

#  #Push a bird into the buffer.
#  try:
#     mw.writeimage(mode=mode,image=imgfile,live=True);
#  except ImportError:
#     print "Error, Python Imaging Library (PIL) needs to be installed"
#  except:
#     print "Error loading image.  Probably not in the working directory.";


  
if __name__ == '__main__':
  main()

