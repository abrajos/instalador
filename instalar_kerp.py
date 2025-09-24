#!/usr/bin/env python3
import subprocess
import os
import re

def run(cmd):
    print(f"Ejecutando: {cmd}")
    subprocess.run(cmd, shell=True, check=True)

def get_el_version():
    """Detecta versión de Enterprise Linux (8 o 9)"""
    with open("/etc/redhat-release") as f:
        content = f.read()
    match = re.search(r"release (\d+)", content)
    if match:
        return int(match.group(1))
    else:
        raise RuntimeError("No se pudo detectar versión de EL (8 o 9)")

def update_system():
    print("🔹 Actualizando sistema...")
    run("dnf -y update")

def install_php_apache():
    print("🔹 Instalando PHP 8, Apache y módulos necesarios...")
    run("dnf -y install php php-cli php-devel php-mbstring php-mysqlnd php-pdo php-json httpd")

def install_postgres14():
    print("🔹 Instalando PostgreSQL 14...")
    el_version = get_el_version()
    if el_version == 9:
        repo_url = "https://download.postgresql.org/pub/repos/yum/reporpms/EL-9-x86_64/pgdg-redhat-repo-latest.noarch.rpm"
    elif el_version == 8:
        repo_url = "https://download.postgresql.org/pub/repos/yum/reporpms/EL-8-x86_64/pgdg-redhat-repo-latest.noarch.rpm"
    else:
        raise RuntimeError(f"Versión EL {el_version} no soportada")

    run(f"dnf -y install {repo_url}")
    run("dnf -qy module disable postgresql")
    run("dnf -y install postgresql14 postgresql14-server postgresql14-contrib")

    data_dir = "/var/lib/pgsql/14/data"
    if not os.path.exists(data_dir) or not os.listdir(data_dir):
        print("🔹 Inicializando PostgreSQL 14...")
        run("/usr/pgsql-14/bin/postgresql-14-setup initdb")
    else:
        print("🔹 Directorio de datos de PostgreSQL 14 no está vacío, se omite initdb.")

    run("systemctl enable --now postgresql-14")
    run("systemctl enable --now httpd")

def setup_firewall():
    print("🔹 Configurando firewall...")
    ports = [22, 80, 443, 5432, 8010]
    for port in ports:
        run(f"firewall-cmd --permanent --add-port={port}/tcp")
    run("firewall-cmd --reload")

def setup_postgres_users():
    print("🔹 Configurando usuarios y base de datos PostgreSQL...")
    db_pass = "postgres"
    run(f'sudo -u postgres psql -c "ALTER USER postgres WITH ENCRYPTED PASSWORD E\'{db_pass}\'"')
    run('sudo -u postgres psql -c "CREATE DATABASE dbkerp WITH ENCODING=\'UTF-8\';"')
    run('sudo -u postgres psql -c "CREATE USER dbkerp_conexion WITH PASSWORD \'dbkerp_conexion\';"')
    run('sudo -u postgres psql -c "ALTER ROLE dbkerp_conexion SUPERUSER;"')
    run('sudo -u postgres psql -c "CREATE USER dbkerp_admin WITH PASSWORD \'a1a69c4e834c5aa6cce8c6eceee84295\';"')
    run('sudo -u postgres psql -c "ALTER ROLE dbkerp_admin SUPERUSER;"')

def install_kerp():
    print("🔹 Instalando KERP desde GitHub...")
    run("dnf -y install git")
    if not os.path.exists("/var/www/html/kerp"):
        os.makedirs("/var/www/html/kerp")
    run("git clone https://github.com/kplian/pxp.git /var/www/html/kerp/pxp")
    run("chown -R apache.apache /var/www/html/kerp")
    run("chmod 700 -R /var/www/html/kerp")

    # Copiar DatosGenerales.sample.php a DatosGenerales.php y modificar rutas
    src = "/var/www/html/kerp/pxp/lib/DatosGenerales.sample.php"
    dst = "/var/www/html/kerp/pxp/lib/DatosGenerales.php"
    with open(src, "r") as f_in, open(dst, "w") as f_out:
        for line in f_in:
            f_out.write(line)
    with open(dst, "r") as f:
        data = f.read()
    data = data.replace("/web/lib/lib_control/", "/kerp/pxp/lib/lib_control/")
    data = data.replace("/kerp-boa/", "/kerp/")
    data = data.replace("/var/lib/pgsql/9.1/data/pg_log/", "/var/lib/pgsql/14/data/pg_log/")
    with open(dst, "w") as f:
        f.write(data)

    # Crear enlaces simbólicos
    links = {
        "/var/www/html/kerp/pxp/lib": "/var/www/html/kerp/lib",
        "/var/www/html/kerp/pxp/index.php": "/var/www/html/kerp/index.php",
        "/var/www/html/kerp/pxp/sis_generador": "/var/www/html/kerp/sis_generador",
        "/var/www/html/kerp/pxp/sis_organigrama": "/var/www/html/kerp/sis_organigrama",
        "/var/www/html/kerp/pxp/sis_parametros": "/var/www/html/kerp/sis_parametros",
        "/var/www/html/kerp/pxp/sis_seguridad": "/var/www/html/kerp/sis_seguridad",
        "/var/www/html/kerp/pxp/sis_workflow": "/var/www/html/kerp/sis_workflow",
    }
    for src, dst in links.items():
        if not os.path.exists(dst):
            os.symlink(src, dst)

    run("mkdir -p /var/www/html/kerp/reportes_generados")
    run("setfacl -R -m u:apache:wrx /var/www/html/kerp/reportes_generados")
    run("setfacl -R -m u:postgres:wrx /var/www/html")

def create_php_info():
    print("🔹 Generando info.php para verificar PHP...")
    with open("/var/www/html/info.php", "w") as f:
        f.write("<?php phpinfo(); ?>")

def main():
    update_system()
    install_php_apache()
    install_postgres14()
    setup_firewall()
    setup_postgres_users()
    install_kerp()
    create_php_info()
    print("✅ Instalación completa. Accede a http://localhost/info.php para verificar PHP.")

if __name__ == "__main__":
    main()
