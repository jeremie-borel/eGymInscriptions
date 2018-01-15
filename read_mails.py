# -*- coding: utf-8 -*-

import sys, os
import logging, datetime, imaplib, email, email.header, re
from collections import defaultdict

# disable request https warning
# http://stackoverflow.com/questions/27981545/suppress-insecurerequestwarning-unverified-https-request-is-being-made-in-pytho#28002687
import requests
import requests.packages.urllib3.exceptions as ulib
requests.packages.urllib3.disable_warnings(ulib.InsecureRequestWarning)


POSTFINANCE_MAIL = None
POSTFINANCE_SERVER = None
POSTFINANCE_PSWD = None
INSCRIPTION_URL = None
try:
    # tries to load a password file
    from pswd import *
except ImportError:
    pass

print INSCRIPTION_URL


from PyFileMaker import FMServer
fm = FMServer( url=INSCRIPTION_URL, debug=False )
fm.setDb( 'Inscription' )
# fm.setDb( 'InscriptionJeremie' )
fm.setLayout( 'XmlPaiement' )


_pat = re.compile( 
    r"""
    EINSGYM - (?P<cmd>[A-Z0-9-]*?) 
    -1- 
    (?P<y>\d{4})(?P<m>\d{2})(?P<d>\d{2})
    (?P<H>\d{2})(?P<M>\d{2})(?P<S>\d{2})
    
    \s+ / \s+ statut: \s+

    (?P<status>\d.*)$
    """, re.VERBOSE )

def read_email():
    print "Downloading emails..."
    mail_data = defaultdict( list )
    try:
        mail = imaplib.IMAP4_SSL( host=POSTFINANCE_SERVER, port=993 )
        mail.login( POSTFINANCE_MAIL , POSTFINANCE_PSWD )
        mail.select('Inbox')

        matched = 0
        unmatched = 0

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

            subject = []
            for line,encoding in email.header.decode_header(msg['Subject']):
                enc = encoding or 'utf-8'
                subject.append( line.decode(enc, 'replace') )
                
            subject = " ".join( subject )

            m = _pat.search( subject )
            if not m:
                unmatched += 1
                print "-"*30
                print "OUPS:::, not a confirmation mail ?"
                print subject
                print "-"*30
                continue

            matched += 1

            cmd_id = m.group('cmd')
            payment_date = datetime.datetime(
                year =   int(m.group('y')),
                month =  int(m.group('m')),
                day =    int(m.group('d')),
                hour =   int(m.group('H')),
                minute = int(m.group('M')),
                second = int(m.group('S')),
                )

            status = m.group('status')
            if 'test' in status.lower():
                continue

            tpl = ( payment_date, status, subject)
            mail_data[cmd_id].append( tpl )
            
        mail.close()
        mail.logout()

        print "Mails matched: {}, unmatched: {}".format( matched, unmatched )
        return mail_data
    except Exception, e:
        print unicode( e )

def get_status( data ):
    _map = {
        '9':u'OK',
        '91':u'OK',
        '1':u'ERREUR',
    }
    try:
        return _map[data]
    except KeyError:
        pass

    raise Exception( u"Invalid status {}".format(data) )
    



def download_paiements():
    print "Downloading paiements..."

    resultset = fm.doFindAll()

    ret = { r.numeroDemande:r for r in resultset }
    return ret


def main():
    
    mail_data = read_email()

    actual = download_paiements()

    for cmd, data in mail_data.items():
        tmp = sorted( data, key=lambda x:x[0] )
        date, status, raw = tmp[0]

        obj = {
            'numeroDemande': cmd.encode( 'utf8' ),
            'modePaiement': u'électronique'.encode( 'utf8' ),
            'resultatPaiement': status.encode( 'utf8' ),
            'datePaiement': date,
            'donneesBrutes': raw.encode( 'utf8' ),
            'commentaire': "" if len(tmp)==0 else "mails multiples",
        }

        if cmd not in actual.keys():
            print u"Creating payment for", cmd
            fm.doNew( obj )
            continue

        r = actual[cmd]
        flag = False
        for key,value in obj.items():
            if getattr( r, key ) != value:
                setattr( r, key, value )
                flag = True
        if flag:
            print u"Editing payment for", cmd
            fm.doEdit( r )


if __name__ == '__main__':
    main()
