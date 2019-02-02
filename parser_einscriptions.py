#!/usr/bin/env python 
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import
#test
# tolerate any ssl certificate
import requests
import requests.packages.urllib3.exceptions as ulib
requests.packages.urllib3.disable_warnings(ulib.InsecureRequestWarning)

# generic import...
import re, sys, os, json, copy, base64, paramiko
import datetime
from collections import defaultdict

# parsing import 
from lxml import etree, objectify
from lxml.objectify import StringElement, IntElement, FloatElement

# string file object
from io import StringIO, BytesIO

INSCRIPTION_URL = None
GYC_FTP = None
GYC_USER = None
GYC_PSWD = None

# must correspond to the namespaces used in the xml.
NS1 = '{http://evd.vd.ch/xmlns/eVD-0041/2}'
NS2 = '{http://evd.vd.ch/xmlns/eVD-0039/2}'

try:
    # tries to load a password file
    from pswd import *
except ImportError:
    pass

from pyfilemaker2.server import FmServer

# from libs.constantes import *
# from inscriptions.helper import *

if not GYC_FTP or not GYC_USER or not GYC_PSWD or not INSCRIPTION_URL:
    print """
    
    Les mots de passes pour accèder au fichier Inscription sont 
    introuvables. Vous devez manuellement renseigner les variables 
    en majuscule dans le fichier (INSCRIPION_URL et GYC_xx ).
    
    INSCRIPTION_URL doit avoir le format: 
    https://<username>:<password>@<ip_Inscription>:443 
    Le username et le password sont ceux qui ont des droits pour
    accéder à l'xml d'Inscription.
    
    Les autres sont par exemple:
    GYC_FTP = '10.224.255.25'
    GYC_USER = 'joe'
    GYC_PSWD = '123'

    """
    sys.exit(1)

_sftp = None
def get_sftp():
    global _sftp
    if _sftp:
        return _sftp
    s = paramiko.SSHClient()
    s.set_missing_host_key_policy( paramiko.AutoAddPolicy() )
    s.connect( GYC_FTP, username=GYC_USER, password=GYC_PSWD )

    _sftp = s.open_sftp()
    _sftp.chdir( 'photos' )
    return _sftp

def build_object( elem ):
    class _Unset: pass

    def _get( node, key, ns=None, default=_Unset ):
        _ns = ns or ""
        try:
            val = node[_ns+key]
            if isinstance( val, objectify.BoolElement ):
                return bool(val)
            if isinstance( val, objectify.IntElement ):
                return int(val)
            if isinstance( val, objectify.FloatElement ):
                return float(val)
            if isinstance( val, objectify.StringElement ):
                return unicode(val)
            raise TypeError( "Unkown xml type {}".format( type(val) ))
        except AttributeError:
            if default is _Unset:
                raise AttributeError("No such attribute {}".format(key))
            return default
        
        
    xml = objectify.fromstring(  etree.tostring(elem) )

    el = xml.eleve
    ins = xml.inscription

    obj = {
        'numeroDemande': _get( xml, 'numeroDemande' ),
        'eleve' : {
            'uid': _get( el, 'uid', ns=NS2 ),
            'nom': _get( el, 'nom', ns=NS2 ),
            'prenom': _get( el, 'prenom', ns=NS2),
            'navs13': _get( el, 'navs13', ns=NS2 ),
            'anneeVoie' : _get( el, 'anneeVoie', ns=NS2 ),
        },
        'preavis': {
            'hasRaccordement': bool(xml['preavis']['hasRaccordement']),
            'hasPasGymnase': bool(xml['preavis']['hasPasGymnase']),
            'hasPasRecommandation': bool(xml['preavis']['hasPasRecommandation']),
            'remarquesComplementaires': _get( xml['preavis'], 'remarquesComplementaires', ns=None, default=None ),
        },
        'inscription': {
            'formation': _get( ins, 'formation' ),
            'hasRaccordement': _get( ins, 'hasRaccordement' ),
            'hasApprentissage': _get( ins, 'hasApprentissage' ),
            'autreEcole': _get( ins, 'autreEcole', default=None ),
            'langue2': _get( ins, 'langue2' ),
            'langue3': _get( ins, 'langue3', default=None ),
            'disciplineArtistique': _get( ins, 'disciplineArtistique' ),
            'niveauMath': _get( ins, 'niveauMath', default=None ),
            'optionSpecifique': _get( ins, 'optionSpecifique', default=None ),
            'hasBilingueAnglais': _get( ins, 'hasBilingueAnglais' ),
            'hasBilingueAllemand': _get( ins, 'hasBilingueAllemand' ),
            'hasBilingueItalien': _get( ins, 'hasBilingueItalien' ),
            'hasClasseSpeciale': _get( ins, 'hasClasseSpeciale' ),
            'dateInscription': _get( ins, 'dateInscription' ),
            'choixDeuxiemeAnnee': _get( ins, 'choixDeuxiemeAnnee', default=None ),
        },
        'affectation': {
            'zoneAffectationAuto': _get( xml.affectation, 'zoneAffectationAuto', default=None ),
            'zoneAffectationSouhaitee': _get( xml.affectation, 'zoneAffectationSouhaitee', default=None ),
            'motivation': _get( xml.affectation, 'motivation', default=None ),
        },
    }

    # previsionVoie
    try:
        obj['pronostic'] = unicode(xml['previsionVoie']['pronostic'])
    except AttributeError:
        obj['pronostic'] =  None

    # construction des preavis MATU, EC, ECG
    try:
        obj['preavis']['preavisMaturite'] = {}
        preavis = xml['preavis']['preavisMaturite']
        tmp = obj['preavis']['preavisMaturite']
        tmp['langue2'] = _get( preavis, key='langue2' )
        tmp['langue3'] = _get( preavis, key='langue3' )
        tmp['niveauMath'] = _get( preavis, key='niveauMath' )
        tmp['optionSpecifique'] = _get( preavis, key='optionSpecifique' )
        tmp['disciplineArtistique'] = _get( preavis, key='disciplineArtistique' )
    except AttributeError:
        pass
    try:
        obj['preavis']['preavisEC'] = {}
        preavis = xml['preavis']['preavisEC']
        tmp = obj['preavis']['preavisEC']
        tmp['langue2'] = _get( preavis, key='langue2' )
        tmp['disciplineArtistique'] = _get( preavis, key='disciplineArtistique' )
    except AttributeError:
        pass
    try:
        obj['preavis']['preavisECG'] = {}
        preavis = xml['preavis']['preavisECG']
        tmp = obj['preavis']['preavisECG']
        tmp['langue2'] = _get( preavis, key='langue2' )
        tmp['disciplineArtistique'] = _get( preavis, key='disciplineArtistique' )
    except AttributeError:
        pass

    # construction des niveaux des matières du sec I.
    try:
        obj['eleve']['niveaux'] = {}
        for niveau in el[NS2+'niveaux'][NS2+'niveau']:
            matiere = _get( niveau, 'matiere', ns=NS2 )
            valeur = _get( niveau, 'valeur', ns=NS2 )
            if not matiere:
                raise ValueError("No matiere defined")
            if matiere in obj['eleve']['niveaux']:
                raise KeyError("Matiere is defined twice")
            obj['eleve']['niveaux'][matiere] = valeur
    except AttributeError:
        pass

    # resultats du sec I
    tmp = None
    try:
        obj['eleve']['resultats'] = {}
        tmp = obj['eleve']['resultats']
        for result in el[NS2+'resultats'][NS2+'resultat']:
            grp = _get( result, 'groupe', ns=NS2 )
            tmp[grp] = {
                'points': _get( result, 'points', ns=NS2 ),
                'nbDisciplines': _get( result, 'nbDisciplines', ns=NS2 ),
            }
    except AttributeError:
        pass

    # photo 
    try:
        obj['photo'] = str( xml['donneesComplementaires']['photo'] )
    except AttributeError:
        obj['photo'] = None

    return obj


def parse_test( source ):
    count = 0
    context = etree.iterparse(
        source,
        tag = NS1 + 'hasClasseSpeciale',
        events=('end',),
    )
    t,f = 0,0
    for event, elem in context:
        if elem.text == 'true':
            t += 1
        elif elem.text == 'false':
            f += 1
        else:
            raise ValueError( elem.text )
            
        elem.clear()
    print "Class spéciale: t:", t, " f:", f
    

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

            test = build_object( elem )
            yield elem, test
            elem.clear()


def etab_preavis( item ):
    s = []
    item = item['preavis']
    if bool(item['hasRaccordement']):
        s.append( 'Rac II' )
    if bool(item['hasPasGymnase']):
        s.append( 'Pas gymnase' )
    if bool(item['preavisMaturite']):
        s.append( 'EM' )
    if bool(item['preavisEC']):
        s.append( 'EC' )
    if bool(item['preavisECG']):
        s.append( 'ED' )
    if bool(item['hasPasRecommandation']):
        s.append( 'Aucune recommandation' )
    
    return "\n".join( s ) if len(s) else ""

def etab_pronostic( item ):
    value = item['pronostic']
    if value in ('Admis', 'Incertain', 'Certain', 'Probable'):
        return value
    print "Pronostic inconnu: {} ({})".format( value, uid )
    return ""

def eleve_os( item ):
    _map = {
        'Arts Visuels' : 'arts visuels',
        'Biologie et Chimie': 'biologie et chimie',
        'Economie et Droit': 'économie et droit',
        'Espagnol': 'espagnol',
        'Latin (suite OS)': 'latin',
        'Italien (suite OS)': 'italien',
        'Grec': 'grec',
        'Musique': 'musique',
        'Philosophie et Psychologie': 'philosophie et psychologie',
        'Physique et Application des Mathématiques': 'physique et applications des mathématiques',
        'Aucune': 'Aucune',
        }
    return _map[ item['optionSpecifique'] ]

def eleve_art( item ):
    _map = {
        'Arts Visuels' : 'arts visuels',
        'Musique': 'musique',
        'Sans Préférence': 'sans préférence',
        }
    return _map[ item['disciplineArtistique'] ]

def eleve_bilingue( item ):
    s = []
    if bool(item['hasBilingueAnglais']):
        s.append( 'Anglais' )
    if bool(item['hasBilingueAllemand']):
        s.append( 'Allemand' )
    if bool(item['hasBilingueItalien']):
        s.append( 'Italien' )
        
    return "\n".join( s ) if len(s) else ""

def eleve_langue2_matu( item ):
    _map = {
        'Allemand' : 'allemand',
        'Italien Débutant': 'italien débutant',
        'Italien (Suite OS)': 'italien standard',
        'Italien standard (Suite OS)': 'italien standard',
        }
    return _map[ item['langue2'] ]

def eleve_langue3_matu( item ):
    _map = {
        'Grec' : 'grec',
        'Anglais': 'anglais',
        'Latin (Suite OS)': 'latin',
        }
    return _map[ item['langue3'] ]

def eleve_langue2( item ):
    _map = {
        'Allemand' : 'allemand',
        # 'Italien (Suite OS)': 'italien',
        'Italien': 'italien',
        }
    return _map[ item['langue2'] ]

def eleve_math( item ):
    return unicode(item['niveauMath']).lower()
    
def eleve_speciale( item ):
    if bool(item['hasClasseSpeciale']):
        return 'oui'
    return ''

def eleve_autre_formation( item ):
    s = []
    if bool(item['hasRaccordement']):
        s.append( 'raccordement de type II' )
    if bool(item['hasApprentissage']):
        s.append( 'apprentissage' )
    if item['autreEcole'] is not None:
        s.append( unicode(item['autreEcole']) )

    return "\n".join( s ) if len(s) else None

def eleve_niveaux( item ):
    if not item.keys():
        return None
    out = [ (matiere, niveau) for matiere,niveau in item.items() ]
    out = sorted( out, key=lambda x:x[0])
    out = "\n".join( "{}: {}".format(k,v) for k,v in out )
    return out

def eleve_choix_od_future( item ):
    _map = {
        'Santé' : 'santé',
        'Socio-éducative': 'socio-éducative',
        'Socio-pédagogique': 'socio-pédagogique',
        'Communication et Information': 'communication et information',
        'Artistique': 'artistique',
        None: '',
    }
    return _map[ item['choixDeuxiemeAnnee'] ]

def parse_date( stamp ):
    d = datetime.datetime.strptime( stamp, '%d.%m.%Y' )
    return d

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
    parser.add_argument('-t', '--test', dest="test", action='store_true',
                            default=False, required=False,
                            help='Does execute test on the xml.(debug)' )

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
        
    print "Loading XML file {}".format( args.file )

    if args.test:
        print "Test while parsing file"
        parse_test( source=args.file )
        print "Done!"
        return

    if args.simulate:
        print "Simulation mode ON"
    else:
        print "Simulation mode OFF"
    
    fm = FmServer( 
        url=INSCRIPTION_URL,
        request_kwargs={
            'timeout': 60,
        },
        debug=False,
        db='Inscription',
    )
    fm.layout = 'STDInscription' 

    def _setattr( item, key, value ):
        if value is None:
            return
        if item.get( key, None ) != value:
            item[key] = value
            
    count = 0
    found = 0
    updated = 0
    up_to_date = 0
    skipped = 0
    photo = 0
    
    old_uids = None
    if args.old_file:
        print "Parsing uids from old file"
        old_uids = parse_uid( source=args.old_file )
        print "Found {} processed uids".format(len(old_uids))

    now = datetime.datetime.now()

    if args.filter:
        print "Filtering on '{}'".format("', '".join(args.filter))

    for xml, obj in parse( args.file ):
        uid = unicode(obj['eleve']['uid'])
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
            if args.filter:
                print "*"*40, "DUMP"
                print etree.tostring(xml, pretty_print=True)
                cp = copy.deepcopy(obj)
                cp['photo'] = 'erased by me'
                print json.dumps( cp, indent=2 )

        count += 1
        
        ins = obj['inscription']
        if not ins:
            print "Pas d'inscription pour {}".format( uid )
            continue

        image = obj['photo']
        if args.verbose:
            print "Len of image is ", (len(image) if image else 'NA')
            print "Numero de demande:", obj.get('numeroDemande','NA')

        resultset = tuple( fm.do_find({'uid':uid},max=3) )

        if not resultset:
            print "uid {} not found in the FMS db".format(uid)
            continue
        if len(resultset)>1:
            print "More than one uid found for {} in the FMS db".format(uid)
            continue

        found += 1
        res = resultset[0]
        original = copy.deepcopy(res)

        if res['sectionSaisie'] and not args.overwrite:
            skipped += 1
            continue

        if image and ( len(args.filter) or not args.simulate ):
            if len(args.filter):
                tfile = open( '/tmp/'+uid.lower()+'.jpg', 'wb' )
                tfile.write( base64.b64decode( image ) )
                
            data = BytesIO( base64.b64decode( image ) )
            name = uid.lower() + ".jpg"

            sftp = get_sftp()
            sftp.putfo( data, name )
    
        try:
            ecole = ins['formation']
            affectation = obj['affectation']
            zone = affectation.get( 'zoneAffectationAuto',None)

            if image:
                _setattr( res, 'flagPhotoAUploader', '1' )
                photo += 1
            
            _setattr( res, 'etabPreavis', etab_preavis( obj ) )
            _setattr( res, 'etabRemarque', obj['preavis']['remarquesComplementaires'] )
            _setattr( res, 'eleveAutreFormation', eleve_autre_formation(ins) )
            _setattr( res, 'zoneRecrutement',zone)
            _setattr( res, 'autreZoneAffectation',
                      affectation['zoneAffectationSouhaitee'] )

            _setattr( res, 'motivationAutreZoneAffectation', affectation['motivation'] )

            _setattr( res, 'numeroDemande', obj['numeroDemande'] )

            EM = bool( ecole == 'Ecole de maturité' )
            ECG = bool( ecole == 'Ecole de culture générale' )
            EC = bool( ecole == 'Ecole de commerce' )

            if not EM and not EC and not ECG:
                print "L'élève {} n'est inscrit dans aucune école.".format(uid)
                continue
            
            if EM:
                _setattr( res, 'sectionSaisie', 'M' )
                _setattr( res, 'eleveOptionOs', eleve_os(ins) )
                _setattr( res, 'eleveBilingue', eleve_bilingue(ins) )
                _setattr( res, 'eleveOptionL2', eleve_langue2_matu(ins) )
                _setattr( res, 'eleveOptionL3', eleve_langue3_matu(ins) )
                _setattr( res, 'eleveOptionMa', eleve_math(ins) )

            if EC:
                _setattr( res, 'sectionSaisie', 'E' )
            if ECG:
                _setattr( res, 'sectionSaisie', 'D' )
                _setattr( res, 'choixODFuture', eleve_choix_od_future(ins) )
            
            if EC or ECG:
                _setattr( res, 'eleveOptionL2', eleve_langue2(ins) )

            if EC or ECG or EM:
                _setattr( res, 'elevePrevision', obj['pronostic'] )
                _setattr( res, 'eleveOptionOa', eleve_art(ins) )
                _setattr( res, 'eleveClasseSpeciale', eleve_speciale(ins) )

            if obj['eleve']['resultats']:
                tmp = obj['eleve']['resultats']
                _setattr( res, 'groupe1NbPts', tmp['Groupe 1']['points'] )
                _setattr( res, 'groupe1NbDisc', tmp['Groupe 1']['nbDisciplines'] )
                _setattr( res, 'groupe2NbPts', tmp['Groupe 2']['points'] )
                _setattr( res, 'groupe2NbDisc', tmp['Groupe 2']['nbDisciplines'] )

            _setattr( res, 'niveauxDisciplines', eleve_niveaux(obj['eleve']['niveaux']) )
            _setattr( res, 'dateInscription', parse_date( ins['dateInscription'] ) )
        except KeyError as e:
            print "Could not process {}".format( uid )
            #print "*"*40
            #print json.dumps( query, indent=2 )
            print "*"*40
            print e
            # raise
            continue

        has_changed = False
        for key in res.changed_keys():
            if key == 'flagPhotoAUploader':
                continue
            if original[key] != res[key]:
                has_changed = True
                break
        if not has_changed:
            up_to_date += 1
            continue

        if args.verbose:
            for key in res.changed_keys():
                print "{: <40}: {} -> {} / {}".format(
                    key,
                    original[key],
                    res[key],
                    "YES" if original[key] == res[key] else "NO",
                )

        res.flagInscriptionOK = 1
        res.flagEInscription = 1
        if args.simulate:
            print "Simulation de l'inscription de {} ({})".format( uid, zone )
        else:
            print "Edition de l'inscription de {} ({})".format( uid, zone )
            fm.do_edit( res )
        updated += 1

    print "Total number of inscription (with photos: {}) in the xml: {}".format( photo, count )
    print "Total number of uid found in Norma: {}".format( found )
    print "Total number of record skipped in Norma: {}".format( skipped )
    print "Total number of record edited in Norma: {}".format( updated )
    print "Total number of record up to date in Norma: {}".format( up_to_date )
        
if __name__ == '__main__':
    main()
