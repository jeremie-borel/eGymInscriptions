# -*- coding: utf-8 -*-

import sys, os
import logging, datetime, imaplib, email, email.header, re
 

POSTFINANCE_MAIL = None
POSTFINANCE_SERVER = None
POSTFINANCE_PSWD = None
try:
    # tries to load a password file
    from pswd import *
except ImportError:
    pass

from PyFileMaker import FMServer

_pat = re.compile( r"EINSGYM-(?P<cmd>[A-Z0-9-]*?)-1-(?P<y>\d{4})(?P<m>\d{2})(?P<d>\d{2})(?P<H>\d{2})(?P<M>\d{2})(?P<S>\d{2})" )

def read_email():
    try:
        mail = imaplib.IMAP4_SSL( host=POSTFINANCE_SERVER, port=993 )
        mail.login( POSTFINANCE_MAIL , POSTFINANCE_PSWD )
        mail.select('Inbox')

        rv, data = mail.search(None, 'ALL')
        if rv != 'OK':
            print "No message found!"
            return
        
        for i in reversed( data[0].split() ):
            rv, data = mail.fetch(i, '(RFC822)' )
            if rv != 'OK':
                print "Error recieving essage {}".format(i)
                continue

            msg = email.message_from_string(data[0][1])

            subject = ""
            for value,encoding in email.header.decode_header(msg['Subject']):
                
            decode = email.header.decode_header(msg['Subject'])[0]

            print 
            print "*"*40
            continue

            subject = unicode(decode[0])
            date_tuple = email.utils.parsedate_tz(msg['Date'])
            if date_tuple:
                local_date = datetime.datetime.fromtimestamp(
                    email.utils.mktime_tz(date_tuple)
                    )

            m = _pat.search( subject )
            if not m:
                print "-"*30
                print "OUPS:::, not a confirmation mail ?"
                print subject
                print "-"*30
                continue

            cmd_id = m.group('cmd')
            payment_date = datetime.datetime(
                year =   int(m.group('y')),
                month =  int(m.group('m')),
                day =    int(m.group('d')),
                hour =   int(m.group('H')),
                minute = int(m.group('M')),
                second = int(m.group('S')),
                )

            print "*"*130
            print cmd_id, payment_date
            print "Local Date:", local_date.strftime("%a, %d %b %Y %H:%M:%S")
            print decode

            # data = msg.get_payload( decode=True )
            # print type(data)
            
            # look at get_charset
            

            
            
        mail.close()
        mail.logout()
        
    except Exception, e:
        log.exception(e)

def main():
    read_email()
    
if __name__ == '__main__':
    main()
