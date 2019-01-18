#!/usr/bin/python

import os
import shlex
import subprocess

# DB config
MYSQL_USER          = 'flask-user'
MYSQL_USER_PASS     = 'flask-user-pass'
MYSQL_ROOT_PASS     = 'test-pass'
MYSQL_SERVER        = 'localhost'

# Apache config
ENCORE_URL          = 'localhost'
ENCORE_PATH         = '/srv/encore'

# Flask config
SERVER_NAME         = "localhost:5000"
JOB_DATA_FOLDER     = "./"
PHENO_DATA_FOLDER   = "./"
GENO_DATA_FOLDER    = "./"
EPACTS_BINARY       = 'epacts'
QUEUE_JOB_BINARY    = 'sbatch'
MANHATTAN_BINARY    = 'make_manhattan_json.py'
QQPLOT_BINARY       = 'make_qq_json.py'
TOPHITS_BINARY      = 'make_tophits_json.py'
NEAREST_GENE_BED    = 'data/nearest-gene.bed'
VCF_FILE            = ""
HELP_EMAIL          = ""
SECRET_KEY          = None
JWT_SECRET_KEY      = None
GOOGLE_LOGIN_CLIENT_ID = None
GOOGLE_LOGIN_CLIENT_SECRET = None

BUILD_REF = {
    "GRCh37": {
        "fasta": "/data/ref/hs37d5.fa",
        "nearest_gene_bed": "/data/ref/nearest-gene.GRCh37.bed"
    },
    "GRCh38": {
        "fasta": "/data/ref/hs38DH.fa",
        "nearest_gene_bed": "/data/ref/nearest-gene.GRCh38.bed"
    }
}

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

    #TODO configure flask_config.py
    config = """
SERVER_NAME = "{server_name}"

JOB_DATA_FOLDER = "{job_data_folder}"
PHENO_DATA_FOLDER = "{pheno_data_folder}"
GENO_DATA_FOLDER = "{geno_data_folder}"
EPACTS_BINARY = "{epacts_binary}"
QUEUE_JOB_BINARY = "{queue_job_binary}"
MANHATTAN_BINARY = "{manhattan_binary}"
QQPLOT_BINARY = "{qqplot_binary}"
TOPHITS_BINARY = "{tophits_binary}"
NEAREST_GENE_BED = "{nearest_gene_bed}"

VCF_FILE = "{vcf_file}"

MYSQL_DB = "encore"
MYSQL_USER = "{mysql_user}"
MYSQL_PASSWORD = "{mysql_password}"

BUILD_REF = {{
    "GRCh37": {{
        "fasta": "/data/ref/hs37d5.fa",
        "nearest_gene_bed": "/data/ref/nearest-gene.GRCh37.bed"
    }},
    "GRCh38": {{
        "fasta": "/data/ref/hs38DH.fa",
        "nearest_gene_bed": "/data/ref/nearest-gene.GRCh38.bed"
    }}
}}


SECRET_KEY = {secret_key}
JWT_SECRET_KEY = {jwt_secret_key}

GOOGLE_LOGIN_CLIENT_ID = {google_login_client_id}
GOOGLE_LOGIN_CLIENT_SECRET = {google_login_client_secret}

HELP_EMAIL = "{help_email}"
""".format(server_name = SERVER_NAME,
           job_data_folder = JOB_DATA_FOLDER,
           pheno_data_folder = PHENO_DATA_FOLDER,
           geno_data_folder = GENO_DATA_FOLDER,
           epacts_binary = EPACTS_BINARY,
           queue_job_binary = QUEUE_JOB_BINARY,
           manhattan_binary = MANHATTAN_BINARY,
           qqplot_binary = QQPLOT_BINARY,
           tophits_binary = TOPHITS_BINARY,
           nearest_gene_bed = NEAREST_GENE_BED,
           vcf_file = VCF_FILE,
           mysql_user = MYSQL_USER,
           mysql_password = MYSQL_USER_PASS,
           secret_key = SECRET_KEY,
           jwt_secret_key = JWT_SECRET_KEY,
           google_login_client_id = GOOGLE_LOGIN_CLIENT_ID,
           google_login_client_secret = GOOGLE_LOGIN_CLIENT_SECRET,
           help_email = HELP_EMAIL)

    f = open('/srv/encore/flask_config.py', 'w')
    f.write(config)
    f.close()

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
    subprocess.call(['sudo', 'a2enmod', 'wsgi'])
    subprocess.call(['sudo', 'a2enmod', 'ssl'])

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

    f = open(ENCORE_PATH + '/encore.wsgi', 'w')
    f.write(wsgi)
    f.close()

def main():
    install_packages()
    setup_encore()
    install_python_requirements()
    setup_mysql()
    setup_apache()


if __name__ == '__main__':
    main()
