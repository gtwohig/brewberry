import RPi.GPIO as GPIO
import time, sys
from threading import Timer
import requests
import json
from pirc522 import RFID
import binascii

BREW_SERVER = 'http://brew.example.com' # replace with your kegbot server address
BREW_API_KEY = 'd6e7765af658b5b34cd1348ff2cd6aa6' # dummy/old example key
RED_LED_PIN = 37
GREEN_LED_PIN = 33
FLOW_SENSOR_1 = 32
FLOw_SENSOR_2 = 36

# board mode is easier
GPIO.setmode(GPIO.BOARD)

# maybe there will be multiple scripts
GPIO.setwarnings(False)



GPIO.setup(RED_LED_PIN, GPIO.OUT, initial=GPIO.HIGH)
GPIO.setup(GREEN_LED_PIN, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(FLOW_SENSOR_1, GPIO.IN, pull_up_down = GPIO.PUD_UP)
GPIO.setup(FLOW_SENSOR_2, GPIO.IN, pull_up_down = GPIO.PUD_UP)

rdr = RFID()
util = rdr.util()
util.debug = True



global tap1
tap1 = {'tap_number': 1,
        'last_tick_time': time.time(),
        'ticks_this_drink': 0,
        'auth_token': '',
        'pouring':False,
        'stop_timer':None}

global tap1
tap2 = {'tap_number': 2,
        'last_tick_time': time.time(),
        'ticks_this_drink': 0,
        'auth_token': '',
        'pouring':False,
        'stop_timer':None}

global swiped_id 
global swiped_user_name
swiped_id = None
swiped_user_name = None

def tap1Tick(channel):
    global tap1
    tap1['ticks_this_drink'] = tap1['ticks_this_drink'] + 1
    tap1['last_tick_time'] = time.time()
    if tap1['pouring'] == False:
        tap1['pouring'] = True
        Timer(2,post_drink_1,()).start()

    print('This drink ticks now: ' + str(tap1['ticks_this_drink']) + ' Pouring: ' + str(tap1['pouring']))

def tap2Tick(channel):
    global tap2
    tap2['ticks_this_drink'] = tap2['ticks_this_drink'] + 1
    tap2['last_tick_time'] = time.time()
    if tap2['pouring'] == False:
        tap2['pouring'] = True
        Timer(2,post_drink_2,()).start()

    print('This drink ticks now: ' + str(tap2['ticks_this_drink']) + ' Pouring: ' + str(tap2['pouring']))

def post_drink_1():
    global tap1
    global swiped_id
    if tap1['last_tick_time'] < time.time() - 1.5:
        print('DRINK OVER!')
        print(str(tap1['ticks_this_drink'])+ ' total ticks this drink')
        
        post_drink_endpoint = BREW_SERVER + '/api/taps/' + tap1['tap_number']
        print('endpoint: ' + post_drink_endpoint)
        post_drink_params = {
            'api_key': BREW_API_KEY,
            'ticks': str(tap1['ticks_this_drink']),
        }

        if swiped_user_name != None:
            post_drink_params['username'] = swiped_user_name


        print(post_drink_params)
        if tap1['ticks_this_drink'] >= 5:
            response = requests.post(post_drink_endpoint,data=post_drink_params)
            print(response)
            print(response.json())
        else:
            print("drink too small, resetting")
        # reset tap1
        tap1 = {'tap_number': 1,
            'last_tick_time': time.time(),
            'ticks_this_drink': 0,
            'auth_token': '',
            'pouring':False,
            'stop_timer':None}
        # reset swiped id
        swiped_id = None
        swiped_user_name = None
        GPIO.output(RED_LED_PIN, GPIO.HIGH)
        GPIO.output(GREEN_LED_PIN, GPIO.LOW)  

    else:
        print('not done yet, sleeping ' + str(tap1['last_tick_time'] + 2 - time.time()) + 'seconds more')
        Timer(tap1['last_tick_time'] + 2 - time.time(),post_drink_1,()).start()

def post_drink_2():
    global tap2
    global swiped_id
    if tap2['last_tick_time'] < time.time() - 1.5:
        print('DRINK OVER!')
        print(str(tap1['ticks_this_drink'])+ ' total ticks this drink')
        
        post_drink_endpoint = BREW_SERVER + '/api/taps/' + tap2['tap_number']
        print('endpoint: ' + post_drink_endpoint)
        post_drink_params = {
            'api_key': BREW_API_KEY,
            'ticks': str(tap2['ticks_this_drink']),
        }

        if swiped_user_name != None:
            post_drink_params['username'] = swiped_user_name

        print(post_drink_params)
        if tap2['ticks_this_drink'] >= 5:
            response = requests.post(post_drink_endpoint,data=post_drink_params)
            print(response)
            print(response.json())
        else:
            print("drink too small, resetting")
        # reset tap1
        tap2 = {'tap_number': 2,
            'last_tick_time': time.time(),
            'ticks_this_drink': 0,
            'auth_token': '',
            'pouring':False,
            'stop_timer':None}
        # reset swiped id
        swiped_id = None
        swiped_user_name = None
        GPIO.output(RED_LED_PIN, GPIO.HIGH)
        GPIO.output(GREEN_LED_PIN, GPIO.LOW)  

    else:
        print('not done yet, sleeping ' + str(tap2['last_tick_time'] + 2 - time.time()) + 'seconds more')
        Timer(tap2['last_tick_time'] + 2 - time.time(),post_drink_2,()).start()


GPIO.add_event_detect(FLOW_SENSOR_1, GPIO.FALLING, callback=tap1Tick)
GPIO.add_event_detect(FLOW_SENSOR_2, GPIO.FALLING, callback=tap2Tick)

while True:
    rdr.wait_for_tag()
    (error, data) = rdr.request()
    if not error:
        print("\nDetected: " + format(data, "02x"))
    (error, uid) = rdr.anticoll()
    if not error:
        print("Card read UID by byte: "+str(uid[0])+"-"+str(uid[1])+"-"+str(uid[2])+"-"+str(uid[3])+"-"+str(uid[4]))
        print('card UID: ' + str(hex(int.from_bytes(uid[0:4], byteorder='big'))))
        swiped_id = str(hex(int.from_bytes(uid[0:4], byteorder='big')))
        get_username_endpoint = BREW_SERVER + '/api/auth-tokens/core.rfid/' + swiped_id + '?api_key=' + BREW_API_KEY
        print('calling /api/auth-tokens/core.rfid/' + swiped_id)
        get_username_response = requests.get(get_username_endpoint).json()

        if get_username_response['meta']['result'] == 'ok':
            print('found user')
            swiped_user_name = get_username_response['object']['username']
            GPIO.output(RED_LED_PIN, GPIO.LOW)
            GPIO.output(GREEN_LED_PIN, GPIO.HIGH)
        else:
            print(swiped_id + ' does not match any user')
            for i in range(0,5):
                GPIO.output(RED_LED_PIN, GPIO.LOW)
                GPIO.output(GREEN_LED_PIN, GPIO.HIGH)
                sleep(.5)
                GPIO.output(RED_LED_PIN, GPIO.HIGH)
                GPIO.output(GREEN_LED_PIN, GPIO.LOW)
                sleep(.5)
            swiped_id = None
            swiped_user_name = None

        time.sleep(1)


GPIO.cleanup()


