# catfeeder

## Raspberry PI Setup

### Install Linux

1. Pi to SD card fast xfer using unbuffered disk (rdisk)
    ```
    sudo bash -c 'dd if=/Users/USERNAME/Downloads/2016-11-25-raspbian-jessie-lite.img | pv | dd of=/dev/rdisk# bs=1m'
    ```

2. Update SD card, add to `/boot/config.txt`
    ```
    dtoverlay=pi3-disable-bt
    systemctl disable hciuart
    ```

3. Login with screen ([need TTL cable drivers](https://learn.adafruit.com/adafruits-raspberry-pi-lesson-5-using-a-console-cable/software-installation-mac))
    ```
    sudo screen /dev/cu.usbserial 115200
    ```

    user / pass is `pi` / `raspberry`

4. Enable wifi
    ```
    sudo nano /etc/wpa_supplicant/wpa_supplicant.conf
    ```
    Go to the bottom of the file and add the following:

    ```
    network={
        ssid="The_SSID"
        psk="Your_wifi_password"
    }
    ```

    Then reboot.

### mDNS Support

```
sudo apt-get install avahi-daemon
echo "catfeeder" | sudo tee /etc/hostname
```

Then reboot.

Now the Pi should respond to [catfeeder.local](http://catfeeder.local)

## Servo Setup w/software GPIO

### Python libs

Python Dev, wiringpi, and RPi.GPIO Installation

```
sudo apt-get update
sudo apt-get -y install wiringpi python-rpi.gpio python3-rpi.gpio python-dev
```

Make sure we have PIP..

```
curl https://bootstrap.pypa.io/get-pip.py | sudo python
sudo pip install RPi.GPIO
sudo pip install wiringpi
```

[Command line test](https://learn.adafruit.com/adafruits-raspberry-pi-lesson-8-using-a-servo-motor?view=all#software) with wiringpi

Test app from python REPL:

```python
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BOARD)
GPIO.setup(11,GPIO.OUT)
pwm=GPIO.PWM(11,50)
pwm.start(5)
sleep(2)
pwm.stop()
```

## App setup

```
sudo pip install Flask
```

Run the app, viewable on http://catfeeder.local:8080

```
python catfeeder.py
```

### Run on startup

Copy `catfeeder` into `/etc/init.d`, then run:

```
sudo update-rc.d catfeeder defaults
```
