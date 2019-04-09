#!/usr/bin/python3

import os
import shlex
import subprocess
import time

import requests

CLUSTER_NAME = '@CLUSTER_NAME@'
MACHINE_TYPE = '@MACHINE_TYPE@' # e.g. n1-standard-1, n1-starndard-2
INSTANCE_TYPE = '@INSTANCE_TYPE@' # e.g. controller, login, compute

PROJECT = '@PROJECT@'
ZONE = '@ZONE@'

APPS_DIR = "/apps"
CURR_SLURM_DIR = APPS_DIR + '/slurm/current'
MUNGE_DIR = "/etc/munge"
MUNGE_KEY = '@MUNGE_KEY@'
SLURM_VERSION = '@SLURM_VERSION@'
DEF_PART_NAME = "debug"
BUCKET_NAME = '@BUCKET_NAME@'

CONTROL_MACHINE = CLUSTER_NAME + '-controller'

# DB config
MYSQL_USER = '@MYSQL_USER@'
MYSQL_USER_PASS = '@MYSQL_USER_PASS@'
MYSQL_ROOT_PASS = '@MYSQL_ROOT_PASS@'
MYSQL_SERVER = '@MYSQL_SERVER@'

# Apache config
ENCORE_PATH = '@ENCORE_PATH@'

# Flask config
SERVER_NAME = "@SERVER_NAME@"
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
ADMIN_USERS = '@ADMIN_USERS@'

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

MOTD_HEADER = '''

                                 SSSSSSS
                                SSSSSSSSS
                                SSSSSSSSS
                                SSSSSSSSS
                        SSSS     SSSSSSS     SSSS
                       SSSSSS               SSSSSS
                       SSSSSS    SSSSSSS    SSSSSS
                        SSSS    SSSSSSSSS    SSSS
                SSS             SSSSSSSSS             SSS
               SSSSS    SSSS    SSSSSSSSS    SSSS    SSSSS
                SSS    SSSSSS   SSSSSSSSS   SSSSSS    SSS
                       SSSSSS    SSSSSSS    SSSSSS
                SSS    SSSSSS               SSSSSS    SSS
               SSSSS    SSSS     SSSSSSS     SSSS    SSSSS
          S     SSS             SSSSSSSSS             SSS     S
         SSS            SSSS    SSSSSSSSS    SSSS            SSS
          S     SSS    SSSSSS   SSSSSSSSS   SSSSSS    SSS     S
               SSSSS   SSSSSS   SSSSSSSSS   SSSSSS   SSSSS
          S    SSSSS    SSSS     SSSSSSS     SSSS    SSSSS    S
    S    SSS    SSS                                   SSS    SSS    S
    S     S                                                   S     S
            #######                                         ##
            #       #    #  ####   ####  #####  ######     #  #
            #       ##   # #    # #    # #    # #           ##
            #####   # #  # #      #    # #    # #####      ###
            #       #  # # #      #    # #####  #         #   # #
            #       #   ## #    # #    # #   #  #         #    #
            ####### #    #  ####   ####  #    # ######     ###  #
                SSS
                SSS
                SSS
                SSS
 SSSSSSSSSSSS   SSS   SSSS       SSSS    SSSSSSSSS   SSSSSSSSSSSSSSSSSSSS
SSSSSSSSSSSSS   SSS   SSSS       SSSS   SSSSSSSSSS  SSSSSSSSSSSSSSSSSSSSSS
SSSS            SSS   SSSS       SSSS   SSSS        SSSS     SSSS     SSSS
SSSS            SSS   SSSS       SSSS   SSSS        SSSS     SSSS     SSSS
SSSSSSSSSSSS    SSS   SSSS       SSSS   SSSS        SSSS     SSSS     SSSS
 SSSSSSSSSSSS   SSS   SSSS       SSSS   SSSS        SSSS     SSSS     SSSS
         SSSS   SSS   SSSS       SSSS   SSSS        SSSS     SSSS     SSSS
         SSSS   SSS   SSSS       SSSS   SSSS        SSSS     SSSS     SSSS
SSSSSSSSSSSSS   SSS   SSSSSSSSSSSSSSS   SSSS        SSSS     SSSS     SSSS
SSSSSSSSSSSS    SSS    SSSSSSSSSSSSS    SSSS        SSSS     SSSS     SSSS


'''


def start_motd():

    msg = MOTD_HEADER + """
*** Slurm is currently being installed/configured in the background. ***
A terminal broadcast will announce when installation and configuration is
complete.

Partition {} will be marked down until the compute image has been created.
For instances with gpus attached, it could take ~10 mins after the controller
has finished installing.

""".format(DEF_PART_NAME)

    if INSTANCE_TYPE != "controller":
        msg += """/home on the controller will be mounted over the existing /home.
Any changes in /home will be hidden. Please wait until the installation is
complete before making changes in your home directory.

"""

    with open('/etc/motd', 'w') as motd_file:
        motd_file.write(msg)


def end_motd(broadcast=True):

    with open('/etc/motd', 'w') as motd_file:
        motd_file.write(MOTD_HEADER)

    if not broadcast:
        return

    subprocess.call(['wall', '-n',
        '*** Slurm ' + INSTANCE_TYPE + ' daemon installation complete ***'])

    if INSTANCE_TYPE != "controller":
        subprocess.call(['wall', '-n', """
/home on the controller was mounted over the existing /home.
Either log out and log back in or cd into ~.
"""])


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
                'build-essential',
                'cmake',
                'curl',
                'ghostscript',
                'git',
                'gnuplot',
                'groff',
                'help2man',
                'libapache2-mod-wsgi-py3',
                'libmysqlclient-dev',
                'libffi-dev',
                'libssl-dev',
                'lsb-release',
                'mysql-client',
                'mysql-server',
                'munge',
                'nfs-common',
                'python3-pip',
                'python3-setuptools',
                'r-base',
                'rpm',
                'unzip']

    subprocess.call(['sudo', 'apt-get', 'update'])
    subprocess.call(['sudo', 'DEBIAN_FRONTEND=noninteractive', 'apt-get', 'install', '-y'] + packages)
    subprocess.call(shlex.split('pip3 install cget'))

    # Install libreadline6 because 18.04 only includes 5 and 7 and slurm bins need it
    subprocess.call(shlex.split('curl -L http://mirrors.kernel.org/ubuntu/pool/main/r/readline6/libreadline6_6.3-8ubuntu2_amd64.deb --output /tmp/libreadline6_6.3-8ubuntu2_amd64.deb'))
    subprocess.call(shlex.split('dpkg -i /tmp/libreadline6_6.3-8ubuntu2_amd64.deb'))


def setup_encore():
    if not os.path.exists('/srv/encore'):
        subprocess.call(shlex.split('mkdir -p /srv/encore'))
        subprocess.call(shlex.split('curl -L https://github.com/statgen/encore/archive/encore-gcp.zip --output /tmp/encore.zip'))
        subprocess.call(shlex.split('unzip /tmp/encore.zip -d /tmp/'))
        subprocess.call(shlex.split('cp -r /tmp/encore-encore-gcp/. /srv/encore/'))
        subprocess.call(shlex.split('rm -rf /tmp/encore.zip /tmp/encore-encore-gcp'))

        config = """SERVER_NAME = "{server_name}"

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
ADMIN_USERS = "{admin_users}"

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


SECRET_KEY = "{secret_key}"
JWT_SECRET_KEY = "{jwt_secret_key}"

GOOGLE_LOGIN_CLIENT_ID = "{google_login_client_id}"
GOOGLE_LOGIN_CLIENT_SECRET = "{google_login_client_secret}"

HELP_EMAIL = "{help_email}"
""".format(server_name=SERVER_NAME,
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
           help_email=HELP_EMAIL,
           admin_users=ADMIN_USERS)

        with open('/srv/encore/flask_config.py', 'w') as config_file:
            config_file.write(config)

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
        prc = subprocess.Popen(['mysql', '-u', 'root'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        _, _ = prc.communicate(open("/srv/encore/schema.sql", 'rb').read())
        subprocess.call(['mysql', '-u', 'root', '-p', 'encore', '-e', "INSERT INTO users (id, full_name, can_analyze, email) VALUES ('1', 'Admin', '1', '%s')" % (ADMIN_USERS)])
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
    with open('/etc/apache2/sites-available/encore.conf', 'w') as config_file:
        config_file.write(conf)

    wsgi = """#!/usr/bin/python3
import os, sys

sys.path.insert(0, '{encore_path}')

from encore import create_app
application = create_app(os.path.join('{encore_path}', "flask_config.py"))
""".format(encore_path=ENCORE_PATH)

    with open(ENCORE_PATH + '/encore.wsgi', 'w') as config_file:
        config_file.write(wsgi)

    if not os.path.exists('/etc/ssl/certs/%s.crt' % (get_external_ip())):
        subprocess.call(["sudo", "openssl", "req", "-x509", "-nodes", "-days",
            "365", "-newkey", "rsa:2048", "-keyout", "/etc/ssl/private/%s.key" % get_external_ip(),
            "-out", "/etc/ssl/certs/%s.crt" % get_external_ip(), "-subj", "/C=US/ST=MI/L=A2/O=UM/CN=%s"
            % get_external_ip()])

    subprocess.call(shlex.split('sudo a2ensite encore'))
    subprocess.call(shlex.split('sudo service apache2 restart'))


def add_slurm_user():
    SLURM_UID = str(992)
    subprocess.call(['groupadd', '-g', SLURM_UID, 'slurm'])
    subprocess.call(['useradd', '-m', '-c', 'SLURM Workload Manager',
        '-d', '/var/lib/slurm', '-u', SLURM_UID, '-g', 'slurm',
        '-s', '/bin/bash', 'slurm'])


def setup_munge():

    munge_service_patch = "/lib/systemd/system/munge.service"
    with open(munge_service_patch, 'w') as munge_file:
        munge_file.write("""
[Unit]
Description=MUNGE authentication service
Documentation=man:munged(8)
After=network.target
After=syslog.target
After=time-sync.target
""")

        if INSTANCE_TYPE != "controller":
            munge_file.write("RequiresMountsFor={}\n".format(MUNGE_DIR))

        munge_file.write("""
[Service]
Type=forking
ExecStart=/usr/sbin/munged --num-threads=10
PIDFile=/var/run/munge/munged.pid
User=munge
Group=munge
Restart=on-abort

[Install]
WantedBy=multi-user.target""")

    subprocess.call(['systemctl', 'enable', 'munge'])

    if INSTANCE_TYPE != "controller":
        with open('/etc/fstab', 'a') as fstab_file:
            fstab_file.write("""
{1}:{0}    {0}     nfs      rw,hard,intr  0     0
""".format(MUNGE_DIR, CONTROL_MACHINE))
        return

    if MUNGE_KEY:
        with open(MUNGE_DIR + '/munge.key', 'w') as munge_file:
            munge_file.write(MUNGE_KEY)

        subprocess.call(['chown', '-R', 'munge:munge', MUNGE_DIR, '/var/log/munge/'])
        os.chmod(MUNGE_DIR + '/munge.key', 0o400)
        os.chmod(MUNGE_DIR, 0o700)
        os.chmod('/var/log/munge/', 0o700)
    else:
        subprocess.call(['create-munge-key'])


def start_munge():
    subprocess.call(shlex.split('systemctl stop munge'))

    # Set munge UID and GID to match NFS mount for /etc/munge
    subprocess.call(shlex.split('usermod -u 991 munge'))
    subprocess.call(shlex.split('groupmod -g 991 munge'))
    subprocess.call(['chown', '-R', 'munge:munge', MUNGE_DIR, '/var/log/munge/', '/var/lib/munge/', '/var/run/munge/'])

    subprocess.call(['systemctl', 'restart', 'munge'])


def setup_bash_profile():

    with open('/etc/profile.d/slurm.sh', 'w') as slurm_file:
        slurm_file.write("""
S_PATH=%s
PATH=$PATH:$S_PATH/bin:$S_PATH/sbin
""" % CURR_SLURM_DIR)


def setup_nfs_apps_vols():
    with open('/etc/fstab', 'a') as fstab_file:
        fstab_file.write("""
{1}:{0}    {0}     nfs      rw,sync,hard,intr  0     0
""".format(APPS_DIR, CONTROL_MACHINE))


def setup_nfs_home_vols():
    with open('/etc/fstab', 'a') as fstab_file:
        fstab_file.write("""
{0}:/home    /home     nfs      rw,sync,hard,intr  0     0
""".format(CONTROL_MACHINE))


def mount_nfs_vols():
    while subprocess.call(['mount', '-a']):
        print("Waiting for " + APPS_DIR + " and /home to be mounted")
        time.sleep(5)


def install_fuse():
    with open('/etc/apt/sources.list.d/gcsfuse.list', 'w') as source_file:
        source_file.write("deb http://packages.cloud.google.com/apt gcsfuse-bionic main")

    curl_ps = subprocess.Popen(('curl', 'https://packages.cloud.google.com/apt/doc/apt-key.gpg'), stdout=subprocess.PIPE)
    _ = subprocess.Popen(('sudo', 'apt-key', 'add'), stdin=curl_ps.stdout)

    subprocess.call(shlex.split('sudo apt-get update'))
    subprocess.call(shlex.split('sudo apt-get install gcsfuse -y'))


def mount_buckets():
    subprocess.call(shlex.split('mkdir /data'))
    subprocess.call(shlex.split('gcsfuse -o allow_other --implicit-dirs {} /data'.format(BUCKET_NAME)))


def setup_binaries():
    subprocess.call(shlex.split('cp -r /srv/encore/plot-epacts-output/. /apps/'))


def install_epacts():
    subprocess.call(shlex.split('curl -L https://github.com/statgen/epacts/archive/develop.zip --output /tmp/epacts.zip'))
    subprocess.call(shlex.split('unzip /tmp/epacts.zip -d /tmp/'))
    subprocess.call(shlex.split('cget install -DCMAKE_C_FLAGS="-fPIC" -DCMAKE_CXX_FLAGS="-fPIC" -f /tmp/EPACTS-develop/requirements.txt'), cwd='/tmp/EPACTS-develop')
    subprocess.call(shlex.split('mkdir /tmp/EPACTS-develop/build'))
    subprocess.call(shlex.split('cmake -DCMAKE_INSTALL_PREFIX=/apps/ -DCMAKE_TOOLCHAIN_FILE=/tmp/EPACTS-develop/cget/cget/cget.cmake -DCMAKE_BUILD_TYPE=Release /tmp/EPACTS-develop'), cwd='/tmp/EPACTS-develop/build')
    subprocess.call(shlex.split('make install'), cwd='/tmp/EPACTS-develop/build')


def main():
    if not os.path.exists(APPS_DIR + '/slurm'):
        os.makedirs(APPS_DIR + '/slurm')

    if not os.path.exists('/var/log/slurm'):
        os.makedirs('/var/log/slurm')

    install_packages()
    install_fuse()
    mount_buckets()
    setup_encore()
    setup_mysql()
    setup_apache()

    start_motd()
    # Setup Slurm
    add_slurm_user()
    setup_munge()
    setup_bash_profile()
    setup_nfs_apps_vols()
    setup_nfs_home_vols()
    mount_nfs_vols()

    start_munge()

    part_state = subprocess.check_output(shlex.split("{}/bin/scontrol show part {}".format(CURR_SLURM_DIR, DEF_PART_NAME)))
    while "State=UP" not in str(part_state):
        part_state = subprocess.check_output(shlex.split("{}/bin/scontrol show part {}".format(CURR_SLURM_DIR, DEF_PART_NAME)))

    setup_binaries()
    install_epacts()

    end_motd()

    subprocess.call(shlex.split("gcloud compute instances remove-metadata {} "
                                "--zone={} --keys=startup-script".format(get_hostname(), ZONE)))


if __name__ == '__main__':
    main()
