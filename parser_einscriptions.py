#!/usr/bin/env python 
# -*- coding: utf-8 -*-

#test
# tolerate any ssl certificate
import requests
import requests.packages.urllib3.exceptions as ulib
requests.packages.urllib3.disable_warnings(ulib.InsecureRequestWarning)

# generic import...
import re, sys, os, json, copy, base64, ftplib
import datetime

# parsing import 
from lxml import etree, objectify
from lxml.objectify import StringElement, IntElement, FloatElement

# string file object
from io import StringIO, BytesIO

INSCRIPTION_URL = None
NORMA_FTP = None
NORMA_USER = None
NORMA_PSWD = None

# must correspond to the namespaces used in the xml.
NS1 = '{http://evd.vd.ch/xmlns/eVD-0041/2}'
NS2 = '{http://evd.vd.ch/xmlns/eVD-0039/2}'

try:
    # tries to load a password file
    from pswd import *
except ImportError:
    pass

from PyFileMaker import FMServer

# from libs.constantes import *
# from inscriptions.helper import *

if not NORMA_FTP or not NORMA_USER or not NORMA_PSWD or not INSCRIPTION_URL:
    print u"""
    
    Les mots de passes pour accèder au fichier Inscription sont 
    introuvables. Vous devez manuellement renseigner les variables 
    en majuscule dans le fichier (INSCRIPION_URL et NORMA_xx ).
    
    INSCRIPTION_URL doit avoir le format: 
    https://<username>:<password>@<ip_Inscription>:443 
    Le username et le password sont ceux qui ont des droits pour
    accéder à l'xml d'Inscription.
    
    Les autres sont par exemple:
    NORMA_FTP = '10.224.255.25'
    NORMA_USER = 'joe'
    NORMA_PSWD = '123'

    """
    sys.exit(1)


def node_to_obj( xml_element, map, ns=[ ] ):
    """Transforms an xml element into a python objects.

    The properties that will be transformed are those present in *map*.
    E.g. if map is {'foo':None, 'bar':None} then the returned objects 
    has obj.foo and obj.bar attribute regarless of the xml also having 
    these nodes.

    *ns* is a list of namespaces that will be used.
    """
    def get_node( xml, key, ns=[ ] ):
        for n in ns:
            v = getattr( xml_element, n+key, None )
            if v is not None:
                return v
        return None
    
    ret = copy.deepcopy( map )

    for key, value in map.iteritems():
        if isinstance( value, dict ):
            xml = get_node( xml_element, key, ns )
            if xml is not None:
                ret[key] = node_to_obj( xml, value, ns=ns )
            else:
                ret[key] = {}
        
        elif value is None or isinstance( value, basestring ):
            tag = value or key
            item = get_node( xml_element, tag, ns )
            if isinstance( item, (basestring, StringElement) ):
                ret[key] = unicode( item )
            elif isinstance( item, (int, IntElement) ):
                ret[key] = int( item )
            elif isinstance( item, (float, FloatElement) ):
                ret[key] = float( item )
            else:
                ret[key] = item

        # here, value must be a callable
        else:
            ret[key] = value( xml_element )
            
    return ret


# Minimalistic format for the xml for the parser.
base_obj = {
    'eleve' : {
        'uid': None,
        'nom': None,
        'prenom': None,
        'navs13': None,
        'anneeVoie' : None,
    },
    'previsionVoie': {
        'pronostic': None,
        'vgCours2' : None,
        'vgSem1': None,
        'vpTotal1': None,
        'vpTotal2': None,
        },
    'preavis': {
        'hasRaccordement': None,
        'hasPasGymnase': None,
        'hasPasRecommandation': None,
        'remarquesComplementaires': None,
        'preavisMaturite': {
            'langue2': None,
            'langue3': None,
            'niveauMath': None,
            'optionSpecifique': None,
            'disciplineArtistique': None,
        },
        'preavisEC' : {
            'langue2': None,
            'disciplineArtistique': None,
        },
        'preavisECG' : {
            'langue2': None,
            'disciplineArtistique': None,
        },
    },
    'inscription': {
        'formation': None,
        'hasRaccordement': None,
        'hasApprentissage': None,
        'autreEcole': None,
        'langue2': None,
        'langue3': None,
        'disciplineArtistique': None,
        'niveauMath': None,
        'optionSpecifique': None,
        'hasBilingueAnglais': None,
        'hasBilingueAllemand': None,
        'hasBilingueItalien': None,
        'hasClasseSpeciale': None,
    },
    'affectation': {
        'zoneAffectationAuto': None,
        'zoneAffectationSouhaitee': None,
    },
    'donneesComplementaires': {
        'etatCivilPere': None,
        'etatCivilMere': None,
        'professionMere': None,
        'professionPere': None,
        'assurance': None,
        'photo': None,
    },
    'numeroDemande': None,
}

# class Dummy(object):
#     def __setattr__( self, key, value ):
#         print "***", key, value
#     def __getattr__( self, key ):
#         return None
    
def parse_uid( source ):
    count = 0
    context = etree.iterparse(
        source,
        tag = NS2 + 'uid',
        events=('end',),
    )
    knowns_uids = set()
    for event, elem in context:
        knowns_uids.add( elem.text )
        elem.clear()
    return knowns_uids

def parse( source ):
    count = 0
    context = etree.iterparse(
        source,
        tag = NS1 + 'demandeType',
        # events=("start", "end"),
        events=('end',),
    )

    for event, elem in context:
        if event == 'start':
            pass
        elif event == 'end':
            count += 1
            obj = objectify.fromstring(  etree.tostring(elem) )

            test = node_to_obj(
                obj,
                base_obj,
                ns=(NS1,NS2)
            )
            elem.clear()
            yield test


def etab_preavis( item ):
    s = []
    item = item['preavis']
    if item['hasRaccordement']:
        s.append( 'Rac II' )
    if item['hasPasGymnase']:
        s.append( 'Pas gymnase' )
    if item['preavisMaturite']:
        s.append( 'EM' )
    if item['preavisEC']:
        s.append( 'EC' )
    if item['preavisECG']:
        s.append( 'ED' )
    if item['hasPasRecommandation']:
        s.append( 'Aucune recommandation' )
    
    return "\n".join( s ) if len(s) else ""

def etab_pronostic( item ):
    value = item['pronostic']
    if value in ('Admis', 'Incertain', 'Certain', 'Probable'):
        return value
    print u"Pronostic inconnu: {} ({})".format( value, uid )
    return ""

def eleve_os( item ):
    _map = {
        u'Arts Visuels' : u'arts visuels',
        u'Biologie et Chimie': u'biologie et chimie',
        u'Economie et Droit': u'économie et droit',
        u'Espagnol': u'espagnol',
        u'Latin (Suite OS)': u'latin',
        u'Italien (Suite OS)': u'italien',
        u'Grec': u'grec',
        u'Musique': u'musique',
        u'Philosophie et Psychologie': 'philosophie et psychologie',
        u'Physique et Application des Mathématiques': u'physique et applications des mathématiques',
        }
    return _map[ item['optionSpecifique'] ]

def eleve_art( item ):
    _map = {
        u'Arts Visuels' : u'arts visuels',
        u'Musique': u'musique',
        u'Sans Préférence': u'sans préférence',
        }
    return _map[ item['disciplineArtistique'] ]

def eleve_bilingue( item ):
    s = []
    if item['hasBilingueAnglais']:
        s.append( 'Anglais' )
    if item['hasBilingueAllemand']:
        s.append( 'Allemand' )
    if item['hasBilingueItalien']:
        s.append( 'Italien' )
        
    return "\n".join( s ) if len(s) else ""

def eleve_langue2_matu( item ):
    _map = {
        u'Allemand' : u'allemand',
        u'Italien Débutant': u'italien débutant',
        u'Italien (Suite OS)': u'italien standard',
        }
    return _map[ item['langue2'] ]

def eleve_langue3_matu( item ):
    _map = {
        u'Grec' : u'grec',
        u'Anglais': u'anglais',
        u'Latin (Suite OS)': u'latin',
        }
    return _map[ item['langue3'] ]

def eleve_langue2( item ):
    _map = {
        u'Allemand' : u'allemand',
        u'Italien (Suite OS)': u'italien',
        u'Italien Débutant': u'italien',
        }
    return _map[ item['langue2'] ]

def eleve_math( item ):
    return item['niveauMath'].lower()
    
def eleve_speciale( item ):
    if item['hasClasseSpeciale']:
        return 'oui'
    return ''

def eleve_autre_formation( item ):
    s = []
    if item['hasRaccordement']:
        s.append( u'raccordement de type II' )
    if item['hasApprentissage']:
        s.append( u'apprentissage' )
    if item['autreEcole']:
        s.append( item['autreEcole'] )

    return u"\n".join( s ) if len(s) else ""

def main():

    import argparse
    
    parser = argparse.ArgumentParser(
        description='Exports eInscription into Inscription on Norma.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    
    parser.add_argument('-f', '--file', dest="file", default="", required=True,
                            help='XML File to parse' )
    parser.add_argument('-o', '--old-file', dest="old_file",
                            default=None, required=False,
                            help='XML File considered as already parsed.' )

    parser.add_argument('-T', '--true', dest="simulate", action="store_false",
                            default=True, required=False,
                            help='Simulation mode off. Does something on Inscription' )

    parser.add_argument('-v', '--verbose', dest="verbose", action="store_true",
                            default=False, required=False,
                            help='Verbose mode on.' )

    parser.add_argument('-F', '--filter', dest="filter", 
                            nargs="*",
                            default=[], required=False,
                            help='Filter on those uids only.' )

    parser.add_argument('--force', dest="overwrite", action="store_true",
                            default=False, required=False,
                            help='Overwrites existing Inscription on Norma' )

    args = parser.parse_args()
        
    print u"Loading XML file {}".format( args.file )

    if args.simulate:
        print u"Simulation mode ON"
    else:
        print u"Simulation mode OFF"
    
    fm = FMServer( url=INSCRIPTION_URL, debug=False )
    fm.setDb( 'Inscription' )
    # fm.setDb( 'InscriptionJeremie' )
    fm.setLayout( 'STDInscription' )

    def _setattr( item, key, value ):
        if value is None:
            return
        if isinstance( value, unicode ):
            v = value.encode('utf8')
        else:
            v = value
            
        if getattr( item, key ) != value:
            setattr( item, key, v )
            
    count = 0
    found = 0
    updated = 0
    skipped = 0
    photo = 0

    if args.verbose:
        print "Setting FTP"
    ftp = ftplib.FTP( NORMA_FTP )
    ftp.login( NORMA_USER, NORMA_PSWD )
    
    old_uids = None
    if args.old_file:
        print "Parsing uids from old file"
        old_uids = parse_uid( source=args.old_file )
        print "Found {} processed uids".format(len(old_uids))

    now = datetime.datetime.now()

    for query in parse( args.file ):
        uid = query['eleve']['uid']

        if args.filter and uid.lower() not in args.filter:
            skipped += 1
            continue

        if old_uids and uid in old_uids:
            skipped += 1
            if args.verbose:
                print "Uid {} is in old file".format( uid )
            continue

        if args.verbose:
            print "Parsing ", uid
        
        count += 1
        
        ins = query['inscription']
        if not ins:
            print u"Pas d'inscription pour {}".format( uid )
            continue

        image = query['donneesComplementaires']['photo']
        if args.verbose:
            print "Len of image is ", len(image)

        resultset = fm.doFind({'uid':uid})

        if not resultset:
            print u"uid {} not found in the FMS db".format(uid)
            continue
        if len(resultset)>1:
            print u"More than one uid found for {} in the FMS db".format(uid)
            continue

        found += 1
        res = resultset[0]

        if res['sectionSaisie'] and not args.overwrite:
            skipped += 1
            continue

        if image and ( len(args.filter) or not args.simulate ):
            if len(args.filter):
                tfile = open( '/tmp/'+uid.lower()+'.jpg', 'wb' )
                tfile.write( base64.b64decode( image ) )
                
            data = BytesIO( base64.b64decode( image ) )
            name = 'photos_lagapeo/' + uid.lower() + ".jpg"
            ftp.storbinary("STOR " + name, data, 1024*8 )
        
        try:
            ecole = ins['formation']
            voie = query['previsionVoie']
            affectation = query['affectation']
            comp = query['donneesComplementaires']

            if image:
                _setattr( res, 'flagPhotoAUploader', '1' )
                photo += 1
            
            _setattr( res, 'etabPreavis', etab_preavis( query ) )
            _setattr( res, 'etabRemarque', query['preavis']['remarquesComplementaires'] )
            _setattr( res, 'eleveAutreFormation', eleve_autre_formation(ins) )
            _setattr( res, 'zoneRecrutement',affectation.get( 'zoneAffectationAuto',None))
            _setattr( res, 'autreZoneAffectation',
                      affectation.get( 'zoneAffectationSouhaitee',None) )
            _setattr( res, 'numeroDemande', query.get('numeroDemande','') )

            # _setattr( res, 'mereEtatCivil', comp.get('etatCivilMere',None) )
            # _setattr( res, 'pereEtatCivil', comp.get('etatCivilPere',None) )
            # _setattr( res, 'mereProfession', comp.get('professionMere',None) )
            # _setattr( res, 'pereProfession', comp.get('professionPere',None) )
            # _setattr( res, 'eleveAssurance', comp.get('assurance',None) )
    
            EM = bool( ecole == u'Ecole de maturité' )
            ECG = bool( ecole == u'Ecole de culture générale' )
            EC = bool( ecole == u'Ecole de commerce' )

            if not EM and not EC and not ECG:
                print u"L'élève {} n'est inscrit dans aucune école.".format(uid)
                continue
            
            if EM:
                _setattr( res, 'sectionSaisie', 'M' )
                _setattr( res, 'eleveOptionOs', eleve_os(ins) )
                _setattr( res, 'eleveBilingue', eleve_bilingue(ins) )
                _setattr( res, 'eleveOptionL2', eleve_langue2_matu(ins) )
                _setattr( res, 'eleveOptionL3', eleve_langue3_matu(ins) )
                _setattr( res, 'eleveOptionMa', eleve_math(ins) )

                _setattr( res, 'etabMoyenneInscription', voie.get('vpTotal1',None) )
                _setattr( res, 'etabMoyenneInscriptionFMA', voie.get('vpTotal2',None) )
            if EC:
                _setattr( res, 'sectionSaisie', 'E' )
            if ECG:
                _setattr( res, 'sectionSaisie', 'D' )
            
            if EC or ECG:
                _setattr( res, 'eleveOptionL2', eleve_langue2(ins) )
                _setattr( res, 'etabMoyenneInscription', voie.get('vgCours2',None) )
                _setattr( res, 'etabMoyenneInscriptionFMA', voie.get('vgSem1',None) )

            if EC or ECG or EM:
                _setattr( res, 'elevePrevision', voie.get('pronostic',None) )
                _setattr( res, 'eleveOptionOa', eleve_art(ins) )
                _setattr( res, 'eleveClasseSpeciale', eleve_speciale(ins) )

            res.dateInscription = now

        except KeyError as e:
            print u"Could not process {}".format( uid )
            raise

        res.flagInscriptionOK = 1
        res.flagEInscription = 1
        if args.simulate:
            print u"Simulation de l'inscription de {}".format( uid )
        else:
            print u"Edition de l'inscription de {}".format( uid )
            fm.doEdit( res )
        updated += 1

    print u"Total number of inscription (with photos: {}) in the xml: {}".format( photo, count )
    print u"Total number of uid found in Norma: {}".format( found )
    print u"Total number of record skipped in Norma: {}".format( skipped )
    print u"Total number of record edited in Norma: {}".format( updated )
        
if __name__ == '__main__':
    main()
