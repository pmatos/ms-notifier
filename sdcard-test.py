from requests.auth import HTTPBasicAuth
import requests
import xml.etree.ElementTree as ET

username='pmatos'
password='iamtheMast3r!'

def main():
    r = requests.get('http://192.168.178.22/dev/sys/sdtest', auth=(username, password))
    tree = ET.fromstring(r.text)

    code = int(tree.attrib['Code'])
    assert code == 200
    value = tree.attrib['value']

    print(value)
    return 0

if __name__ == '__main__':
    exit(main())
