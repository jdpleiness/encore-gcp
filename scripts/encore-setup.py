#!/usr/bin/python

import shlex
import subprocess

MYSQL_USER      = 'flask-user'
MYSQL_USER_PASS = 'flask-user-pass'
MYSQL_ROOT_PASS = 'test-pass'
MYSQL_SERVER    = 'localhost'

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
    pass

def main():
    install_packages()
    setup_encore()
    install_python_requirements()
    setup_mysql()
    setup_apache()


if __name__ == '__main__':
    main()
