#!/usr/bin/env python 
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

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


from pyfilemaker2 import FmServer
fm = FmServer( 
    url=INSCRIPTION_URL,
    request_kwargs={
        'timeout': 60,
    },
    debug=False,
    db='Inscription',
    layout = 'XmlPaiement',
)

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

def read_email( past=None ):
    print "Downloading emails...",
    mail_data = {}
    try:
        mail = imaplib.IMAP4_SSL( host=POSTFINANCE_SERVER, port=993 )
        mail.login( POSTFINANCE_MAIL , POSTFINANCE_PSWD )
        mail.select('Inbox')

        matched = 0
        unmatched = 0

        if past is None:
            print "all"
            rv, data = mail.search(None, 'ALL')
        else:
            dd = datetime.datetime.now() - datetime.timedelta( days=int(past) )
            arg = '(SENTSINCE {})'.format(dd.strftime( '%d-%b-%Y'))
            print arg
            rv, data = mail.search(None, arg )
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
                if "TEST" in subject:
                    continue
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

            if status == '0':
                # incomplete or invalid payment
                continue

            key = 'e' + m.group('key')
            if key in mail_data:
                if mail_data[key]['status'] == status and \
                   mail_data[key]['date'] == payment_date:
                    continue
                print "****", key, status, cmd_id
                print "NNNNN", mail_data[key]['status']
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

        print "Mails parsed: {}, parse failed: {}, total:{}".format(
            matched,
            unmatched,
            len(mail_data),
        )
        return mail_data
    except Exception, e:
        raise e
        print unicode( e )

def get_status( data ):
    """Le statut numérique du mail est mappé vers le 
    binaire OK/ERREUR pour le fichier Inscription
    
    OK: le paiement a été effectué
    ERREUR: NOT OK.
    """
    _map = {
        '9':u'OK',
        '91':u'OK',
        '1':u'ERREUR',
        '2':u'ERREUR',
        '92': u'ERREUR',
    }
    try:
        return _map[data]
    except KeyError:
        pass

    raise Exception( u"Invalid status {}".format(data) )
    



def download_paiements():
    print "Downloading existing reccords from Inscription..."

    resultset = fm.do_find({
        'modePaiement':ELECTRONIQUE,
    })

    ret = { r['paiementId']:r for r in resultset }
    return ret


def main( options ):
    
    mail_data = read_email( past=options.days )
    if not mail_data:
        return

    actual = download_paiements()
    count = 0
    created, edited, up_to_date = 0,0,0
    for key, data in mail_data.items():
        try:
            fstatus = get_status( data['status'] )
        except Exception as e:
            print u"Exception while parsing status of {}".format(key)
            print u"*"*30
            print data
            print u"*"*30
            continue
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
            fm.do_new( obj )
            created += 1
            continue

        r = actual[key]
        flag = False
        for k,value in obj.items():
            if k in r and r[k] != value:
                r[k] = value
                # do not update if only donnesBrutes has changed
                if k != 'donneesBrutes':
                    flag = True
        if flag:
            edited += 1
            fm.do_edit( r )
            continue

        up_to_date += 1

    print "Number of payement line created: ", created
    print "Number of edited payement", edited
    print "Number of payement up to date", up_to_date

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description="""Upload des informations de paiements *électroniques*
        depuis les mails de confirmation Postfinance vers le fichier 
        Inscription.

        La procédure du script est la suivante:
        charge tous les mails
        - charge tous les paiements présents dans Inscriptions
        - upload sur Inscription la différence des deux.
        
        """,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
        
    parser.add_argument('--test', dest="test", action="store_true",
                            default=False, required=False,
                            help='Tests de lecture sur Inscription.' )

    parser.add_argument('-d', dest="days", action="store",
                            default=False, required=False,
                            help='Number of days in the paste to download the mails.' )


    args = parser.parse_args()

    if args.test:
        print "no test to run"
        # fm.setLayout( 'StdInscription' )
        # # fm.doView()
        # print "oualalal"
        # # fm = FMServer( url=INSCRIPTION_URL, debug=False )
        # # fm.setDb( 'essaimneuf' )

        # # fm.setLayout( 'StdEleves' )

        # r = fm.doFind({'uid':'29cd84929987490c85b97f6567d49511'})
        # print r
        sys.exit(0)

    if not args.test:
        main( options=args )
