import sys
from multiprocessing import Process
from scapy.all import *
import binascii
import os
from threading import Thread
from subprocess import Popen
import time
from netaddr import *
import manuf
import math
import threading
from wifi import Cell, Scheme
from tinydb import TinyDB, where

'''
working very very slowly

same BSSID but different other attributes such as encyption, channnel

same AP ESSID with different BSSID

OUI

'''
class scanning:
    """Class for a user of the chat client."""
    def __init__(self, intf, count, channel,BSSID, SSID, accesspoint):
        self.intf = intf
        self.BSSID = BSSID
        self.SSID = SSID
        self.accesspoint = accesspoint
        self.seq1 = 0
        self.flag1 = 0
        self.counter = 0
        self.channel = accesspoint["channel"]
        self.count = count
        self.accessPointsSQ = []
        self.seq_list = []
    
    
    def channel_change(self):
        os.system("sudo ifconfig %s down" %  self.intf )
        os.system("sudo iw dev "+  self.intf + " set type monitor")
        os.system("sudo ifconfig %s up" %  self.intf )
        try:
            os.system("sudo iw dev %s set channel %d" % (self.intf, self.channel))
            print "channel Change", self.channel
            print ""
        except Exception, err :
               print err 
    
    
    
    def set_ch(self, channel):
        self.channel = channel

    
    def ch_hop(self):
           channel = int(random.randrange(1,11))
           try:
               os.system("sudo iw dev %s set channel %d" % (self.intf, channel))
               print "channel Change", channel
           except Exception, err :
               print err  


    def checkTheSeq(self, li):
        start=int(li[0])
        print start,"Sequence"
        for e in li[1:]:
            a=int(e)
            if a > start:
                start=a
            else:
                return False
        return True
    
    
    def oui(self, frame):
        result = False
        p = manuf.MacParser()
        test = p.get_all(frame.lower())
        if test.manuf is not None:
            print "Real OUI Code"
            result = True
        return result
    
       
    def sniffAP(self):
        print "------------------Started-----------------------------------------------"
        def PacketHandler(frame):      
          if  frame.haslayer(Dot11) and frame.type == 0 and frame.subtype == 8:
             
            ### not much use as scanning the one channel
            try:
                val = self.datab.search((where('ssid') == str(frame.info)))
                #print "$$$$$$$$$$$$$$$$$$$    VAL    $$$$$$$$$$$$$$$$$$$$$$$$$$$$$"
                #print val, frame.info
                ch = int(ord(frame[Dot11Elt:3].info))
                if not ch == val["channel"]:
                    print "Channel Has changed"
                
            except:
                pass
            enc = None
            if self.flag1 == 0:
                result = self.oui(frame.addr2)
                print "********************    OUI ", result
                self.flag1 = 1

                
                ## direcly from Airoscapy
                capability = frame.sprintf("{Dot11Beacon:%Dot11Beacon.cap%}\
                {Dot11ProbeResp:%Dot11ProbeResp.cap%}")
                
                if re.search("privacy", capability): enc = True
                else: enc  = False
                
            if not self.accesspoint["encrypted"] == enc and enc != None:
                print "the encrpytion has changed"
            
              
            try:
                if frame.info == self.SSID or self.BSSID.lower() == frame.addr2:
                    try:
                        #print frame.SC
                        self.seq1 = frame.SC
                        self.seq_list.append(frame.SC)
                        self.counter += 1
                        
                        if self.counter == 50:
                            print "50 Sequenecec Numbers Collected"
                            val = self.checkTheSeq(self.seq_list)
                            print "----------------------------------------------------------------------- ", val
                            if val == False:
                                print "<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< Possible Evil Twin Invalid OUI >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> "
                            if not self.BSSID.lower() == frame.addr2:
                                print "<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< Possible Evil Twin Adddress Change >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> "       
                            self.seq_list = []
                            self.counter = 0
                            result = self.oui(frame.addr2)
                            print "******************** OUI ", result
                            if result == False:
                                print "<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< Possible Mac Spoof >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> "
                        self.accessPointsSQ.append(frame.SC)
                    except  Exception,e:
                        print "error", e
            except:
                pass
        sniff(iface=self.intf, count = self.count, prn=PacketHandler)
    
    
# lyre
# "C0:4A:00:E4:B6:70"
# zoom1
# "00:50:18:66:89:D6"


if __name__ == '__main__':
    interface = str(raw_input("Choose iface: "))
    os.system("sudo ifconfig %s down" %  interface)
    os.system("sudo iwconfig "+  interface + " mode managed")
    os.system("sudo ifconfig %s up" %  interface )
    cell = Cell.all(interface)
    db = TinyDB('db.json')
    
    
    Auth_AP = {}
    S = []
    #have a counter for user choice input
    count = 0

    for c in cell:
        count += 1
        print ":"+ str(count), " ssid:", c.ssid
            #create dictionary with informnation on the accesss point
        SSIDS = {"no" : count ,"ssid": c.ssid, "channel":c.channel,"encrypted":c.encrypted, \
                    "frequency":c.frequency,"address":c.address, "signal":c.signal, "mode":c.mode}
            #append this dictionary to a list
        S.append(SSIDS)
    
    
    
    
    ## get choice from the user
    input_var = int(input("Choose: "))
    print "-----------------------------------------"
    ap = S[input_var - 1]
    print ap["ssid"]
    print ap["address"]
    print ap["encrypted"]
    print ap["channel"]
    print "---------------------------------------------"
    

    
    loop = True
    while loop:
        try:
            input_var = int(input("1: Store Valid AP \n2: Disregard and Continue\n:"))     
            if input_var > 0 and input_var <= 2:
                loop = False
        except ValueError:
            pass
    
    if input_var == 1:
        #db.purge()
        #db.insert(S[input_var - 1])
        if db.search((where('ssid') == ap["ssid"]) & (where('address') == str(ap["address"]))) == []:
            db.insert(ap)
        else:
            print "This is already Stored in the database"

        
        '''
        print all database
        '''
        print db.all()
        
    
    
    for ap in db.all():
        try:
            print ""
            print "$$$$$$$$$$$$$$$$$$$$$$$   Sannning -----> " , ap["ssid"]
            s = scanning(intf="wlan4", count = 300, channel=ap["channel"], BSSID=ap["address"],SSID=ap["ssid"], accesspoint=ap)
            s.set_ch(ap["channel"])
            s.channel_change()
            s.sniffAP()
        except Exception, err:
            print(traceback.format_exc())
     
    #f = s.sniffAP()
   # s = scanning(intf="wlan4", count = 6000, channel =ap["channel"], BSSID=ap["address"],SSID=ap["ssid"],WIFIDATA=ap, datab=db)

    #pint 'A' * 2000


