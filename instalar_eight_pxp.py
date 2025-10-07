#!/usr/bin/env python3
import subprocess
import os
import sys

def run(cmd):
    print(f"Ejecutando: {cmd}")
    subprocess.run(cmd, shell=True, check=True)

def get_el_version():
    with open("/etc/redhat-release") as f:
        content = f.read()
    if "8." in content:
        return 8
    elif "9." in content:
        return 9
    else:
        raise RuntimeError("Esta versi車n de AlmaLinux no es soportada")

def update_system():
    print("?? Actualizando sistema...")
    run("dnf -y update")

def install_php_apache():
    print("?? Instalando PHP 7.4 y Apache...")
    run("dnf -y install https://rpms.remirepo.net/enterprise/remi-release-8.rpm")
    run("dnf -y module reset php")
    run("dnf -y module enable php:remi-7.4")
    run("dnf -y install php php-cli php-devel php-mbstring php-mysqlnd php-pdo php-json httpd")

def setup_firewall():
    print("?? Configurando firewall...")
    run("dnf -y install firewalld")
    run("systemctl enable --now firewalld")
    ports = [22, 80, 443, 8010]  # ?? Se quit車 5432 (PostgreSQL)
    for port in ports:
        run(f"firewall-cmd --permanent --add-port={port}/tcp")
    run("firewall-cmd --reload")

def install_kerp():
    print("?? Instalando KERP desde GitHub...")
    run("dnf -y install git")
    if not os.path.exists("/var/www/html/kerp"):
        os.makedirs("/var/www/html/kerp")
    run("git clone https://github.com/kplian/pxp.git /var/www/html/kerp/pxp")
    run("chown -R apache.apache /var/www/html/kerp")
    run("chmod 700 -R /var/www/html/kerp")

    src = "/var/www/html/kerp/pxp/lib/DatosGenerales.sample.php"
    dst = "/var/www/html/kerp/pxp/lib/DatosGenerales.php"
    if os.path.exists(src):
        with open(src, "r") as f_in, open(dst, "w") as f_out:
            f_out.writelines(f_in.readlines())

        with open(dst, "r") as f:
            data = f.read()
        data = data.replace("/web/lib/lib_control/", "/kerp/pxp/lib/lib_control/")
        data = data.replace("/kerp-boa/", "/kerp/")
        with open(dst, "w") as f:
            f.write(data)

    # Enlaces simb車licos
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

def configure_selinux():
    print("?? Configurando SELinux...")
    run("setsebool -P httpd_can_network_connect on")
    run("chcon -R -t httpd_sys_rw_content_t /var/www/html/kerp")

def create_php_info():
    print("?? Generando info.php...")
    with open("/var/www/html/info.php", "w") as f:
        f.write("<?php phpinfo(); ?>")

def main():
    update_system()
    install_php_apache()
    setup_firewall()
    install_kerp()
    configure_selinux()
    create_php_info()
    print("? Instalaci車n completa. Abre http://localhost/info.php para verificar PHP.")
    print("?? Recuerda que PostgreSQL no fue instalado (lo debes instalar manualmente si lo necesitas).")

if __name__ == "__main__":
    main()
