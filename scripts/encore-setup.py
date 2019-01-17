#!/usr/bin/python

import os
import shlex
import subprocess

MYSQL_USER      = 'flask-user'
MYSQL_USER_PASS = 'flask-user-pass'
MYSQL_ROOT_PASS = 'test-pass'
MYSQL_SERVER    = 'localhost'

ENCORE_URL      = 'localhost'
ENCORE_PATH     = '/srv/encore'


def install_packages():
    packages = ['apache2',
                'curl',
                'git',
                'libapache2-mod-wsgi',
                'libmysqlclient-dev',
                'libffi-dev',
                'libssl-dev',
                'mysql-client',
                'mysql-server',
                'python3-pip',
                'python3-setuptools',
                'unzip']

    subprocess.call(['sudo', 'apt-get', 'update'])
    subprocess.call(['sudo', 'DEBIAN_FRONTEND=noninteractive', 'apt-get', 'install', '-y'] + packages)

def setup_encore():
    subprocess.call(shlex.split('mkdir -p /srv/encore'))
    subprocess.call(shlex.split('curl -L https://github.com/statgen/encore/archive/encore-gcp.zip --output /tmp/encore.zip'))
    subprocess.call(shlex.split('unzip /tmp/encore.zip -d /tmp/'))
    subprocess.call(shlex.split('cp -r /tmp/encore-encore-gcp/. /srv/encore/'))
    subprocess.call(shlex.split('rm -rf /tmp/encore.zip /tmp/encore-encore-gcp'))

def install_python_requirements():
    subprocess.call(['pip3', 'install', '--upgrade', 'pip'])
    subprocess.call(['pip3', 'install', '-r', '/srv/encore/requirements.txt'])

def setup_mysql():
    subprocess.call(['mkdir', '-p', '/var/lib/mysqld'])
    subprocess.call(['chown', '-R', 'mysql:mysql', '/var/lib/mysqld'])
    subprocess.call(['usermod', '-d', '/var/lib/mysql/', 'mysql'])
    subprocess.call(shlex.split('sudo service mysql start'))
    subprocess.call(['mysql', '-u', 'root', '-e',
        "CREATE USER '%s'@'%s' IDENTIFIED BY '%s'" % (MYSQL_USER, MYSQL_SERVER,MYSQL_USER_PASS)])
    subprocess.call(['mysql', '-u', 'root', '-e',
        "GRANT DELETE, INSERT, SELECT, UPDATE, EXECUTE ON encore.* TO '%s'@'%s'" % (MYSQL_USER, MYSQL_SERVER)])
    subprocess.call(['mysql', '-u', 'root', '-e',
        "DELETE FROM mysql.user WHERE User=''"])
    subprocess.call(['mysql', '-u', 'root', '-e',
        "FLUSH PRIVILEGES"])
    subprocess.call(['mysql', '-u', 'root', '-e',
        "ALTER USER 'root'@'%s' IDENTIFIED WITH mysql_native_password BY '%s'" % (MYSQL_SERVER, MYSQL_ROOT_PASS)])

def setup_apache():
    conf = """
<VirtualHost *:80>
    ServerAdmin webmaster@{encore_url}
    ServerName {encore_url}
    Redirect permanent / https://{encore_url}/
    ErrorLog "/var/log/apache2/{encore_url}-error.log"
    CustomLog "/var/log/apache2/{encore_url}-access.log" common
</VirtualHost>

<VirtualHost *:443>
    ServerAdmin webmaster@{encore_url}
    DocumentRoot "{encore_path}"
    ServerName {encore_url}
    ErrorLog "/var/log/apache2/{encore_url}-error.log"
    CustomLog "/var/log/apache2/{encore_url}-access.log" common

    SSLEngine on

    SSLCertificateFile    /etc/ssl/certs/{encore_url}.cert
    SSLCertificateKeyFile /etc/ssl/private/{encore_url}.key

    WSGIDaemonProcess {encore_url} processes=1 threads=1 user=encore group=encore home={encore_path}
    WSGIProcessGroup {encore_url}
    WSGIScriptAlias / {encore_path}/encore.wsgi
	WSGIPassAuthorization On

    <Location /server-info>
      SetHandler server-info
      Order deny,allow
      Deny from all
    </Location>

    <Directory {encore_path}>
        Require all granted
    </Directory>

    <Files {encore_path}/encore.wsgi>
        Require all granted
    </Files>
</VirtualHost>
""".format(encore_url = ENCORE_URL, encore_path = ENCORE_PATH)

    if not os.path.exists('/etc/apache2/sites-enabled'):
        os.makedirs('/etc/apache2/sites-enabled')
    f = open('/etc/apache2/sites-enabled/encore.conf', 'w')
    f.write(conf)
    f.close()

    wsgi = """
import os, sys

sys.path.insert(0, '{encore_path}')

from encore import create_app
application = create_app(os.path.join('{encore_path}', "flask_config.py"))
""".format(encore_path = ENCORE_PATH)

    f = open(ENCORE_PATH + '/flask_config.py', 'w')
    f.write(wsgi)
    f.close()

def main():
    #install_packages()
    #setup_encore()
    #install_python_requirements()
    #setup_mysql()
    setup_apache()


if __name__ == '__main__':
    main()
