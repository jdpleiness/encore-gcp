#!/usr/bin/python3

import os
import shlex
import subprocess
import requests

# DB config
MYSQL_USER = '@MYSQL_USER@'
MYSQL_USER_PASS = '@MYSQL_USER_PASS@'
MYSQL_ROOT_PASS = '@MYSQL_ROOT_PASS@'
MYSQL_SERVER = '@MYSQL_SERVER@'

# Apache config
ENCORE_PATH = '@ENCORE_PATH@'

# Flask config
JOB_DATA_FOLDER = "@JOB_DATA_FOLDER@"
PHENO_DATA_FOLDER = "@PHENO_DATA_FOLDER@"
GENO_DATA_FOLDER = "@GENO_DATA_FOLDER@"
EPACTS_BINARY = '@EPACTS_BINARY@'
QUEUE_JOB_BINARY = '@QUEUE_JOB_BINARY@'
MANHATTAN_BINARY = '@MANHATTAN_BINARY@'
QQPLOT_BINARY = '@QQPLOT_BINARY@'
TOPHITS_BINARY = '@TOPHITS_BINARY@'
NEAREST_GENE_BED = '@NEAREST_GENE_BED@'
VCF_FILE = "@VCF_FILE@"
HELP_EMAIL = "@HELP_EMAIL@"
SECRET_KEY = '@SECRET_KEY@'
JWT_SECRET_KEY = '@JWT_SECRET_KEY@'
GOOGLE_LOGIN_CLIENT_ID = '@GOOGLE_LOGIN_CLIENT_ID@'
GOOGLE_LOGIN_CLIENT_SECRET = '@GOOGLE_LOGIN_CLIENT_SECRET@'

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

def get_external_ip():
    url = 'http://metadata/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip'
    headers = {'Metadata-Flavor': 'Google'}
    request = requests.get(url, headers=headers)
    return request.text

def get_hostname():
    url = 'http://metadata.google.internal/computeMetadata/v1/instance/hostname'
    headers = {'Metadata-Flavor': 'Google'}
    request = requests.get(url, headers=headers)
    return request.text.split('.', 1)[0]

def install_packages():
    packages = ['apache2',
                'curl',
                'git',
                'libapache2-mod-wsgi-py3',
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
    if not os.path.exists('/srv/encore'):
        subprocess.call(shlex.split('mkdir -p /srv/encore'))
        subprocess.call(shlex.split('curl -L https://github.com/statgen/encore/archive/encore-gcp.zip --output /tmp/encore.zip'))
        subprocess.call(shlex.split('unzip /tmp/encore.zip -d /tmp/'))
        subprocess.call(shlex.split('cp -r /tmp/encore-encore-gcp/. /srv/encore/'))
        subprocess.call(shlex.split('rm -rf /tmp/encore.zip /tmp/encore-encore-gcp'))

        server_name = get_external_ip()

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
""".format(server_name=server_name,
           job_data_folder=JOB_DATA_FOLDER,
           pheno_data_folder=PHENO_DATA_FOLDER,
           geno_data_folder=GENO_DATA_FOLDER,
           epacts_binary=EPACTS_BINARY,
           queue_job_binary=QUEUE_JOB_BINARY,
           manhattan_binary=MANHATTAN_BINARY,
           qqplot_binary=QQPLOT_BINARY,
           tophits_binary=TOPHITS_BINARY,
           nearest_gene_bed=NEAREST_GENE_BED,
           vcf_file=VCF_FILE,
           mysql_user=MYSQL_USER,
           mysql_password=MYSQL_USER_PASS,
           secret_key=SECRET_KEY,
           jwt_secret_key=JWT_SECRET_KEY,
           google_login_client_id=GOOGLE_LOGIN_CLIENT_ID,
           google_login_client_secret=GOOGLE_LOGIN_CLIENT_SECRET,
           help_email=HELP_EMAIL)

        f = open('/srv/encore/flask_config.py', 'w')
        f.write(config)
        f.close()

    install_python_requirements()

def install_python_requirements():
    subprocess.call(['pip3', 'install', '--upgrade', 'pip'])
    subprocess.call(['pip3', 'install', '-r', '/srv/encore/requirements.txt'])

def setup_mysql():
    if not os.path.exists('/var/lib/mysqld'):
        subprocess.call(['mkdir', '-p', '/var/lib/mysqld'])
        subprocess.call(['chown', '-R', 'mysql:mysql', '/var/lib/mysqld'])
        subprocess.call(['usermod', '-d', '/var/lib/mysql/', 'mysql'])
        subprocess.call(shlex.split('sudo service mysql start'))
        subprocess.call(['mysql', '-u', 'root', '-e',
            "CREATE USER '%s'@'%s' IDENTIFIED BY '%s'" % (MYSQL_USER, MYSQL_SERVER, MYSQL_USER_PASS)])
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

    conf = """<VirtualHost *:80>
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

    SSLCertificateFile    /etc/ssl/certs/{encore_url}.crt
    SSLCertificateKeyFile /etc/ssl/private/{encore_url}.key

    WSGIDaemonProcess {encore_url} processes=1 threads=1 home={encore_path}
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
""".format(encore_url=get_external_ip(), encore_path=ENCORE_PATH)

    if not os.path.exists('/etc/apache2/sites-available'):
        os.makedirs('/etc/apache2/sites-available')
    f = open('/etc/apache2/sites-available/encore.conf', 'w')
    f.write(conf)
    f.close()

    wsgi = """#!/usr/bin/python3
import os, sys

sys.path.insert(0, '{encore_path}')

from encore import create_app
application = create_app(os.path.join('{encore_path}', "flask_config.py"))
""".format(encore_path=ENCORE_PATH)

    f = open(ENCORE_PATH + '/encore.wsgi', 'w')
    f.write(wsgi)
    f.close()

    if not os.path.exists('/etc/ssl/certs/%s.crt' % (get_external_ip())):
        subprocess.call(["sudo", "openssl", "req", "-x509", "-nodes", "-days",
            "365", "-newkey", "rsa:2048", "-keyout", "/etc/ssl/private/%s.key" % get_external_ip(),
            "-out", "/etc/ssl/certs/%s.crt" % get_external_ip(), "-subj", "/C=US/ST=MI/L=A2/O=UM/CN=%s"
            % get_external_ip()])

    subprocess.call(shlex.split('sudo a2ensite encore'))
    subprocess.call(shlex.split('sudo service apache2 restart'))

def main():
    install_packages()
    setup_encore()
    setup_mysql()
    setup_apache()


if __name__ == '__main__':
    main()
