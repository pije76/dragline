from string import Template
import dragline
import ConfigParser
import os
import inspect
from httplib2 import Http
from urllib import urlencode
import base64
from runner import load_modules
import argparse
import zipfile
import pkgutil
from defaultsettings import SpiderSettings
from getpass import getpass
config_file = os.path.expanduser('~/.dragline')


def zipdir(source, destination):
    folder = os.path.abspath(source)
    with zipfile.ZipFile(destination, 'w') as zipf:
        for root, dirs, files in os.walk(folder):
            path = os.path.relpath(root, folder)
            for filename in files:
                relname = os.path.join(path, filename)
                absname = os.path.join(root, filename)
                if filename.endswith(".py"):
                    zipf.write(absname, relname, zipfile.ZIP_DEFLATED)


def upload(url, username, password, foldername, spider_website=None):
    # check whether the folder is a spider
    if not "main.py" in os.listdir(foldername):
        return "Not a valid spider"

    # check if the main.py contain a spider class
    module, settings = load_modules(foldername)
    # check if main.py contain a spider class
    try:
        spider = getattr(module, "Spider")
    except Exception as e:
        return "Spider class not found"

    if not inspect.isclass(spider):
        return "Spider class not found"

    def get(value, default={}):
        try:
            return getattr(settings, value)
        except AttributeError:
            return default
    # create a spider object and check whether it contain required attributes
    settings = SpiderSettings(get('SPIDER'))
    spider_object = spider(settings)

    try:
        if spider_object.name and spider_object.start and spider_object.allowed_domains:
            spider_name = spider_object.name
        else:
            return "required attributes not found in spider"

    except Exception as e:
        print e
        return "Spider deploying failed"

    # zip the folder
    zipdir(foldername, "/tmp/%s.zip" % spider_name)
    zipf = base64.encodestring(open("/tmp/%s.zip" % spider_name, "rb").read())
    post_data = {'username': username, 'password': password, 'name':
                 spider_name, 'zipfile': zipf}
    if spider_website:
        post_data['website'] = spider_website
    headers = {'content-type': 'application/x-www-form-urlencoded'}
    h = Http()
    resp, content = h.request(
        url, "POST", body=urlencode(post_data), headers=headers)
    # read zip file
    return content


def deploy(serv_name, spider_dir):
    parser = ConfigParser.SafeConfigParser()
    parser.read(config_file)
    try:
        args = dict(parser.items(serv_name))
    except ConfigParser.NoSectionError:
        add_server(serv_name)
    args['foldername'] = spider_dir
    print upload(**args)


def generate(spider_dir):
    main = pkgutil.get_data(__package__, "templates/main.tem")
    s = Template(main)
    main = s.substitute(spider_name=spider_dir)
    settings = pkgutil.get_data(__package__, "templates/settings.tem")

    os.makedirs(spider_dir)
    mainfile = open(os.path.join(spider_dir, "main.py"), "w")
    mainfile.write(main)
    mainfile.close()
    settfile = open(os.path.join(spider_dir, "settings.py"), "w")
    settfile.write(settings)
    settfile.close()


def add_server(serv_name):
    url = raw_input("Enter URL:")
    usr_name = raw_input("Enter Username:")
    pwd = getpass("Enter the password:")
    parser = ConfigParser.SafeConfigParser()
    parser.read(config_file)
    if not parser.has_section(serv_name):
        parser.add_section(serv_name)
    parser.set(serv_name, 'url', url)
    parser.set(serv_name, 'username', usr_name)
    parser.set(serv_name, 'password', pwd)
    parser.write(open(config_file, 'w'))


def execute():
    parser = argparse.ArgumentParser(description='Dragline commandparse')
    subparsers = parser.add_subparsers(
        title='subcommands', description='valid subcommands', help='additional help')

    parser_first = subparsers.add_parser('init')
    parser_first.set_defaults(which='init')
    parser_first.add_argument('spider', help='spider name')

    parser_second = subparsers.add_parser('deploy')
    parser_second.set_defaults(which='deploy')
    parser_second.add_argument('server', help='server name')
    parser_second.add_argument('spider', help='spider name')

    parser_third = subparsers.add_parser('addserver')
    parser_third.set_defaults(which='addserver')
    parser_third.add_argument('server', help='assign work for a server')

    args = vars(parser.parse_args())

    if args['which'] == 'init':
        generate(args['spider'])
    elif args['which'] == 'deploy':
        deploy(args['server'], args['spider'])
    elif args['which'] == 'addserver':
        add_server(args['server'])


if __name__ == "__main__":
    execute()
