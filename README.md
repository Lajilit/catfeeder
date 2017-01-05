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

3. Login with screen ([need TTL cable drivers|https://learn.adafruit.com/adafruits-raspberry-pi-lesson-5-using-a-console-cable/software-installation-mac)
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

Test app with wiringpi:

```python
# Servo Control
import time
import wiringpi

# use 'GPIO naming'
wiringpi.wiringPiSetupGpio()

# set #18 to be a PWM output
wiringpi.pinMode(18, wiringpi.GPIO.PWM_OUTPUT)

# set the PWM mode to milliseconds stype
wiringpi.pwmSetMode(wiringpi.GPIO.PWM_MODE_MS)

# divide down clock
wiringpi.pwmSetClock(192)
wiringpi.pwmSetRange(2000)

delay_period = 0.01

while True:
        for pulse in range(50, 250, 1):
                wiringpi.pwmWrite(18, pulse)
                time.sleep(delay_period)
        for pulse in range(250, 50, -1):
                wiringpi.pwmWrite(18, pulse)
                time.sleep(delay_period)
```

## App setup

```
sudo pip install Flask
```

Run the app, viewable on http://catfeeder.local:8080

```
python catfeeder.py
```
