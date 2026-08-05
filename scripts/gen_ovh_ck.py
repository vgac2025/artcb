"""Génère une nouvelle Consumer Key OVH et affiche le lien de validation."""
import urllib.request, json

APP_KEY = '59f86de7e76ab0e7'
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
