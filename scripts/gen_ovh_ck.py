"""Génère une nouvelle Consumer Key OVH et affiche le lien de validation.

La clé d'application est lue depuis l'environnement : OVH_APPLICATION_KEY.
"""
import urllib.request, json
import os
import sys

APP_KEY = os.environ.get('OVH_APPLICATION_KEY', '')
if not APP_KEY:
    print('❌ OVH_APPLICATION_KEY absente de l\'environnement.')
    sys.exit(1)
BASE = 'https://eu.api.ovh.com/1.0'

req = urllib.request.Request(
    BASE + '/auth/credential',
    data=json.dumps({
        'accessRules': [{'method': 'GET', 'path': '/*'}, {'method': 'POST', 'path': '/*'},
                        {'method': 'PUT', 'path': '/*'}, {'method': 'DELETE', 'path': '/*'}],
        'redirection': 'https://github.com/vgac2025/lvx'
    }).encode(),
    headers={'X-Ovh-Application': APP_KEY, 'Content-Type': 'application/json', 'Accept': 'application/json'},
    method='POST'
)
try:
    resp = urllib.request.urlopen(req, timeout=10)
    d = json.loads(resp.read())
    print('consumerKey:', d.get('consumerKey'))
    print('validationUrl:', d.get('validationUrl'))
except Exception as e:
    print('ERREUR:', e)
