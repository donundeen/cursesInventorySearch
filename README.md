# cursesInventorySearch
console-based app to search a google sheet that requires login

# Installation

install raberry pi OS Lite (no gui).

update and upgrade
`sudo apt update && sudo apt upgrade -y`

install git
`sudo apt install -y git`

install pip
`sudo apt install -y python3-pip`

install pandas
`sudo apt install -y python3-pandas`

all installs in one go:

`sudo apt install -y git python3-pip python3-pandas`

install this repo
`git clone git@github.com:donundeen/cursesInventorySearch.git`


# to run

`cd cursesInventorySearch`
`python main.py`

# changing screen resolution

https://www.raspberrypi.com/documentation/computers/configuration.html#set-the-kms-display-mode

`sudo nano /boot/firmware/cmdline.txt`

at the END of the line, NOT on a new line, add"
`video=HDMI-A-1:640x480@60,rotate=180`

on a small screen:640x480 is good

on other screens you might want to change this, or maybe the default is fine. You be you.
