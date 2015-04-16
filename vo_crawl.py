 # -*- coding: utf-8 -*-
import requests
import json
#import pprint

base_url = "https://www.vegvesen.no/nvdb/api"
index_url = 'http://localhost:9200/dpk/nvdb/'
search_expr = "{'objektTyper':[{'id':570,'antall':'15000','filter':[{'type':'Uhellskode','operator':'=','verdi':['Uhell med dyr innblandet']}]}]}&select=objektId,objektTypeId"
#gitt objekttype
#gitt filterkriterier
#angi mapping

#pp = pprint.PrettyPrinter(indent=1)


def punkt_til_koordinat_array_transformator(wkt):
    f = wkt.index('(')
    t = wkt.index(')')
    return map(float, wkt[f+1:t].split())  # [::-1]

ext_val = {
    'fylke': {'path': ['lokasjon', 'fylke', 'navn']},
    'kommune': {'path': ['lokasjon', 'kommune', 'navn']},
    'punkt':  {'path': ['lokasjon', 'geometriForenkletWgs84'], 'transform': punkt_til_koordinat_array_transformator},
    'art': {'path': ['egenskaper', {'k_field': 'navn', 'k_value': 'Hinder type', 'v_field': 'verdi'}],
            'assosiasjon': 571},
    'veg': {'path': ['lokasjon', 'vegReferanser', {'k_field': 'status', 'k_value': 'V', 'v_field': 'kategori'}]}
    }


def finn_objektverdi_fra_egenskapsliste(liste, k_field, k_value, v_field):
    for l in liste:
        if l.get(k_field, None) == k_value:
            return l.get(v_field)
    return None


def plukk_ut_data(hentet_objekt):
    resultat_objekt = {}
    try:
        for k, d in ext_val.iteritems():
            v = hentet_objekt
            assosiasjons_type_id = d.get('assosiasjon', None)
            if assosiasjons_type_id:
                v = hent_assosiert(hentet_objekt, assosiasjons_type_id)
            for part in d.get('path'):
                if type(part) == dict and type(v) == list:
                    v = finn_objektverdi_fra_egenskapsliste(v, part.get('k_field'), part.get('k_value'), part.get('v_field'))
                else:
                    v = v.get(part)
            if d.get('transform', None):
                v = d.get('transform')(v)
            resultat_objekt[k] = v
    except:
        print 'error >> ', hentet_objekt.get('objektId'), k, v, d
    return resultat_objekt


def hent_assosiert(veg_objekt, type_id):
    for a in veg_objekt.get('assosiasjoner'):
        r = a.get('relasjon')
        if r.get('typeId') == type_id:
            url = "{}{}.json".format(base_url, r.get('uri'))
            r = requests.get(url)
            return json.loads(r.text, r.encoding)
    return None


def hent_objekt(objekt_id):
    url = "{}/vegobjekter/objekt/{}.json".format(base_url, objekt_id)
    print url
    r = requests.get(url)
    vo = json.loads(r.text, r.encoding)
    return plukk_ut_data(vo)


def hent_trafikkulykker_med_dyr_innvolvert():
    url = "{}/sok?kriterie={}".format(base_url, search_expr)
    r = requests.get(url)
    vegobjekter = json.loads(r.text).get('resultater')[0].get('vegObjekter')
    resultatliste = []
    for vo in vegobjekter:
        ekstrahert = hent_objekt(vo.get('objektId'))
        if ekstrahert:
            print ekstrahert.get('art')
            resultatliste.append(ekstrahert)
    return resultatliste


def to_geoJson(res, fname='out.geojson'):
    gfc = {
            'type': 'FeatureCollection',
            'features': []
        }

    for r in res:
        gf = {
                'type': 'Feature',
                'geometry': {"type": "Point", "coordinates": []},
                'properties': {}
             }
        geom = r.pop('punkt')
        if geom:
            gf['geometry']['coordinates'] = geom
            for k, v in r.iteritems():
                gf.get('properties')[k] = v
            gfc['features'].append(gf)

    with open(fname, 'w') as outfile:
        json.dump(gfc, outfile)


def hent_alle_av_type(type_id):
    url = "{}/vegobjekter/{}.json".format(base_url, type_id)
    r = requests.get(url)
    vegobjekter = json.loads(r.text, r.encoding).get('vegObjekter')
    resultatliste = []
    for vo in vegobjekter:
        resultat_objekt = plukk_ut_data(vo)
        resultatliste.append(resultat_objekt)
        #rr = requests.post(index_url, data=json.dumps(resultat_objekt))
        print json.dumps(resultat_objekt)
    return resultatliste


if __name__ == '__main__':
    #res = hent_alle_av_type(570)
    #res = hent_objekt(80412613)
    res = hent_trafikkulykker_med_dyr_innvolvert()
    print 'found:', len(res)
    to_geoJson(res)
