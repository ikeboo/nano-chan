## Jetson orin nano Jetpack 6.2

## Jetson Stats
```sh
sudo apt update
sudo apt install python3-pip
sudo pip install jetson-stats
sudo reboot
jtop
```

## VNC
```sh
sudo apt update
sudo apt install vino
cd /usr/lib/systemd/user/graphical-session.target.wants
```
```sh
sudo ln -s ../vino-server.service ./.
gsettings set org.gnome.Vino prompt-enabled false
gsettings set org.gnome.Vino require-encryption false
```
## SSH
set static ip
```
sudo apt-get install netplan.io
```
check no config exists
```
ls /etc/netplan
```

```
sudo touch /etc/netplan/00-installer-config.yaml
sudo vim /etc/netplan/00-installer-config.yaml
sudo chmod 600 /etc/netplan/00-installer-config.yaml
```

```yaml
network:
  version: 2
  wifis:
    wlan0:
      dhcp4: false
      access-points:
        "your SSID":
          password: "xxxxxxxx"
      addresses: 
        - 192.168.11.100/24
      routes:
        - to: default
          via: 192.168.11.1
      nameservers:
        addresses: 
          - 192.168.11.1
```

```sh
sudo apt install openvswitch-switch
sudo netplan apply
```

# Unlock resource clock limitation
```
sudo jetson_clocks
```