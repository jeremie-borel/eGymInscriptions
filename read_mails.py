# -*- coding: utf-8 -*-

import sys, os, copy
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


from PyFileMaker import FMServer
fm = FMServer( url=INSCRIPTION_URL, debug=False )
fm.setDb( 'Inscription' )
fm.setLayout( 'XmlPaiement' )

ELECTRONIQUE = u'électronique'

_pat = re.compile( 
    r"""
    PAYID: \s+ (?P<key>\d+) 
    
    .*?
     
    EINSGYM - (?P<cmd>[A-Z0-9-]*?) 
    -1- 
    (?P<y>\d{4})(?P<m>\d{2})(?P<d>\d{2})
    (?P<H>\d{2})(?P<M>\d{2})(?P<S>\d{2})
    
    \s+ / \s+ statut: \s+

    (?P<status>\d.*)$
    """, re.VERBOSE|re.DOTALL )

def read_email():
    print "Downloading emails..."
    mail_data = {}
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
            author = email.header.decode_header(msg['From'])
            if 'noreply-postfinance@v-psp.com' not in author[0]:
                continue

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

            key = 'e' + m.group('key')
            if key in mail_data:
                raise KeyError("Double key !!!")

            tpl = {
                'key':    key,
                'cmd':    cmd_id,
                'date':   payment_date,
                'status': status, 
                'raw':    subject,
            }
            mail_data[key] = tpl
            
        mail.close()
        mail.logout()

        print "Mails matched: {}, unmatched: {}, matched and not test:{}".format(
            matched,
            unmatched,
            len(mail_data),
        )
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
    print "Downloading existing reccords from Inscription..."

    resultset = fm.doFind(encode_obj({
        'modePaiement':ELECTRONIQUE,
    }))

    ret = { r.paiementId:r for r in resultset }
    return ret

def encode_obj( obj ):
    """Encodes all unicode as utf8 strings"""
    o = copy.copy( obj )
    for k, v in o.iteritems():
        if isinstance( v, unicode ):
            o[k] = v.encode( 'utf8' )
    return o

def main():
    
    mail_data = read_email()
    actual = download_paiements()
    count = 0
    for key, data in mail_data.items():
        fstatus = get_status( data['status'] )
        cmd = data['cmd']
        obj = {
            'paiementId': key,
            'numeroDemande': cmd,
            'modePaiement': ELECTRONIQUE,
            'resultatPaiement': fstatus,
            'datePaiement': data['date'],
            'donneesBrutes': data['raw'],
            #'commentaire': "" if len(tmp)==0 else "mails multiples",
        }

        if key not in actual.keys():
            print u"Creating payment for", cmd, key
            fm.doNew( encode_obj(obj) )
            continue

        r = actual[key]
        flag = False
        for k,value in obj.items():
            if getattr( r, k ) != value:
                print getattr( r, k ), value, getattr( r, k ) == value
                if isinstance( value, unicode ):
                    v = value.encode( 'utf8' )
                else:
                    v = value
                setattr( r, k, v )
                flag = True
        if flag:
            print u"Editing payment for", cmd, key
            fm.doEdit( r )

        count += 1
        if count > 30:
            break

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Reads the mails.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
        
    parser.add_argument('--test', dest="test", action="store_true",
                            default=False, required=False,
                            help='Tests inscriptions on Norma.' )

    args = parser.parse_args()

    if args.test:
        print "tagada"
        fm.setLayout( 'StdInscription' )
        # fm.doView()
        print "oualalal"
        # fm = FMServer( url=INSCRIPTION_URL, debug=False )
        # fm.setDb( 'essaimneuf' )

        # fm.setLayout( 'StdEleves' )

        r = fm.doFind({'uid':'29cd84929987490c85b97f6567d49511'})
        print r
        sys.exit(0)

    main()
