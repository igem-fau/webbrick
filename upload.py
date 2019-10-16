from datetime import datetime
import csv
import sys
import subprocess
from getpass import getpass
from io import StringIO
import re
import requests
import os
from bs4 import BeautifulSoup

MIME = {
    '.csv': 'text/csv',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.gif': 'image/gif',
    '.jpeg': 'image/jpeg',
    '.jpg': 'image/jpeg',
    '.mp3': 'audio/mpeg',
    '.ogg': 'audio/ogg',
    '.png': 'image/png',
    '.pdf': 'application/pdf',
    '.ppt': 'application/vnd.ms-powerpoint',
    '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    '.svg': 'image/svg+xml',
    '.swf': 'application/x-shockwave-flash',
    '.tar': 'application/x-tar',
    '.tiff': 'image/tiff',
    '.tif': 'image/tiff',
    '.ttf': 'font/ttf',
    '.txt': 'text/plain',
    '.wav': 'audio/wav',
    '.webm': 'video/webm',
    '.woff': 'font/woff',
    '.xls': 'application/vnd.ms-excel',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.zip': 'application/zip'
}

year = datetime.today().year

try:
    team = os.environ['IGEM_TEAM']

except KeyError:
    team = input("Enter your team's name: ")

prefix = "T--" + team + "--"

try:
    username = os.environ['IGEM_USERNAME']
except KeyError:
    username = input("Enter your username: ")

try:
    password = os.environ['IGEM_PASSWORD']
except KeyError:
    password = getpass("Enter your password: ")

login_url = "https://igem.org/Login2"

login_data = {
    "Login": "Login",
    "username": username,
    "password": password
}

def special_upload(*files):
    """Uploads all files passed to this function using iGEM's Special:Upload
    site. No descriptions are added. Returns the URLs of the files in a
    dictionary with the args as keys.
    """
    upload_url = "https://%d.igem.org/Special:Upload" % year
    paths = {}

    with requests.Session() as rs:
        login = rs.post(login_url, data=login_data)

        for f in files:
            token = rs.get(upload_url).text.split('\n')
            token = next(i for i in token if "wpEditToken" in i)
            token = token.split()[3]
            token = re.findall('"([^"]*)"', token)[0]
            ft = f.split('.')[-1] 

            try:
                filetype = MIME[ft]

            except KeyError:
                raise TypeError("Cannot upload this filetype:", ft)

            exists = rs.get("https://%d.igem.org/File:" % year + prefix + f)
            if "No file by this name" in exists.text:
                reupload = "1"

            else:
                reupload = "0"

            upload = rs.post(
                upload_url,
                files={
                    'wpUploadFile': (
                        f,
                        open(f, 'rb'),
                        filetype
                    ),
                    'wpDestFile': (
                        None,
                        StringIO(prefix + f)
                    ),
                    'wpUploadDescription': (
                        None,
                        StringIO('File uploaded by Python')
                    ),
                    'wpLicense': (
                        None,
                        StringIO('')
                    ),
                    'wpWatchthis': (
                        None,
                        StringIO('1')
                    ),
                    'wpEditToken': (
                        None,
                        StringIO(token)
                    ),
                    'title': (
                        None,
                        StringIO('Special:Upload')
                    ),
                    'wpUpload': (
                        None,
                        StringIO("Upload file")
                    ),
                    'wpIgnoreWarning': (
                        None,
                        StringIO("1")
                    ),
                    'wpForReUpload': (
                        None,
                        StringIO(reupload)
                    )
                },
            )
            
            wikipath = rs.get("https://%d.igem.org/File:" % year + prefix + f)
            wikipath = BeautifulSoup(wikipath.text, 'html5lib')
            wikipath = wikipath("a", {"class": "internal"})[0]
            paths[f] = wikipath("https://%d.igem.org" % year + wikipath['href'])

            return paths


def wiki_upload(html, wiki_url):
    """Upload the main wiki page of your team of the provided html.
    """
    with requests.Session() as rs:
        login = rs.post(login_url, data=login_data)
        sauce = rs.post(wiki_url, data={'action': 'edit'}).text
        soup = BeautifulSoup(sauce, "html5lib")

        parameters = {"wpTextbox1": (None, open(html, 'rb'))}

        for i in soup("input"):

            if i.get("value") == None:
                parameters[i.get("name")] = None

            elif len(i.get("value")) == 0:
                parameters[i.get("name")] = (None, StringIO(''))

            else:
                parameters[i.get("name")] = (None, StringIO(i.get("value")))

        parameters.pop("wpPreview", None)
        parameters.pop("wpDiff", None)
        parameters["wpStarttime"] = (None, StringIO('20191014074534'))
        parameters["wpEdittime"] = (None, StringIO('20191006152613'))

        post = rs.post(
            wiki_url,
            data = {'action': 'submit'},
            files = parameters
        )
        
        return rs.get(wiki_url).text


def pathupdate(file_, src_dict):
    """Change the sources of pictures, etc to the correct path on the iGEM
    website.
    """
    with open(file_, 'r') as original:
        updated = original.readlines()
        updated = "".join(updated)

        for old_path, new_path in src_dict.items():
            updated = updated.replace(old_path, new_path)

    with open(file_, 'w') as new:
        new.write(updated)


if __name__ == '__main__':

    if sys.argv[-1] == "--upload-pictures":
        os.chdir('static')
        uploaded_files = special_upload(*os.listdir())

        with open("wikipaths.csv", "w") as paths:
            csvwriter = csv.writer(paths)
            csvwriter.writerows([[old, new] for old, new in uploaded_files.items()])

        os.chdir('..')

    else:
        uploaded_files = dict(csv.read("wikipaths.csv", "r"))

    for (root, directory, files) in os.walk('.'):

        for f in files:
            pathupdate("/".join([root, f]), uploaded_files)

    wiki_url = "https://%d.igem.org/wiki/index.php?title=Team:%s" % (year, team)
    subprocess.run(['hugo'])
    os.chdir('public')
   
    if 'Home' in os.listdir():
        wiki_upload('Home/index.html', wiki_url)
   
    if 'Team' in os.listdir():
        wiki_upload('Team/index.html', wiki_url + '/Team')
   
    if 'Collaborations' in os.listdir():
        wiki_upload('Collaborations/index.html', wiki_url + '/Collaborations')
   
    if 'Description' in os.listdir():
        wiki_upload('Description/index.html', wiki_url + '/Description')
   
    if 'Design' in os.listdir():
        wiki_upload('Design/index.html', wiki_url + '/Design')
   
    if 'Experiments' in os.listdir():
        wiki_upload('Experiments/index.html', wiki_url + '/Experiments')
   
    if 'Notebook' in os.listdir():
        wiki_upload('Notebook/index.html', wiki_url + '/Notebook')
   
    if 'Contribution' in os.listdir():
        wiki_upload('Contribution/index.html', wiki_url + '/Contribution')
   
    if 'Results' in os.listdir():
        wiki_upload('Results/index.html', wiki_url + '/Results')
   
    if 'Demonstrate' in os.listdir():
        wiki_upload('Demonstrate/index.html', wiki_url + '/Demonstrate')
   
    if 'Improve' in os.listdir():
        wiki_upload('Improve/index.html', wiki_url + '/Improve')
   
    if 'Attributions' in os.listdir():
        wiki_upload('Attributions/index.html', wiki_url + '/Attributions')
   
    if 'Parts' in os.listdir():
        wiki_upload('Parts/index.html', wiki_url + '/Parts')
   
    if 'Basic_Part' in os.listdir():
        wiki_upload('Basic_Part/index.html', wiki_url + '/Basic_Part')
   
    if 'Composite_Part' in os.listdir():
        wiki_upload('Composite_Part/index.html', wiki_url + '/Composite_Part')
   
    if 'Part_Collection' in os.listdir():
        wiki_upload('Part_Collection/index.html', wiki_url + '/Part_Collection')
   
    if 'Safety' in os.listdir():
        wiki_upload('Safety/index.html', wiki_url + '/Safety')
   
    if 'Human_Practices' in os.listdir():
        wiki_upload('Human_Practices/index.html', wiki_url + '/Human_Practices')
   
    if 'Public_Engagement' in os.listdir():
        wiki_upload('Public_Engagement/index.html', wiki_url + '/Public_Engagement')
   
    if 'Entrepreneurship' in os.listdir():
        wiki_upload('Entrepreneurship/index.html', wiki_url + '/Entrepreneurship')
   
    if 'Measurement' in os.listdir():
        wiki_upload('Measurement/index.html', wiki_url + '/Measurement')
   
    if 'Hardware' in os.listdir():
        wiki_upload('Hardware/index.html', wiki_url + '/Hardware')
   
    if 'Measurement' in os.listdir():
        wiki_upload('Measurement/index.html', wiki_url + '/Measurement')
   
    if 'Model' in os.listdir():
        wiki_upload('Model/index.html', wiki_url + '/Model')
   
    if 'Plant' in os.listdir():
        wiki_upload('Plant/index.html', wiki_url + '/Plant')
