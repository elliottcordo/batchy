#!/usr/bin/env python
import requests
import json
from time import sleep
import argparse

from datetime import date, datetime

# we will assume batchy and waitsy exist on the same machine so we will store as a constant
# however since we use 100% python standard lib, you could take this script, edit the constant and run anywhere you like
# keeping it simple!

URL = 'http://0.0.0.0:5000/get_status/'

parser = argparse.ArgumentParser()
parser.add_argument('-wf','--workflow', help ="workflow name you want to watch")
args = parser.parse_args()
wf = args.workflow

today_str = str(datetime.utcnow().date())
print 'hoy es ' + today_str

wf_status = 'ready'

while True:
    # make call to batchy api
    response = requests.get(URL + wf)
    data = json.loads(response.content)

    status = None
    batch_end_str = None

    # loop through jobs, if any one job is not done (future proof) we will not call the workflow completed)
    for j in data.itervalues():
        status = j.get('status')
        batch_end_str = str(j.get('batch_end', '1776-07-04'))[:10]
        # if no success or the last batch end date isn't today we keep loopin!
        if status != 'success' or batch_end_str != today_str:
            wf_status = 'not ready'
            break
        else:
            wf_status = 'ready'

    print 'wf status: ' + wf_status
    print 'last status: %s on %s' % (status, batch_end_str)

    if wf_status == 'ready':
        print 'yippee - we is done homey!'
        exit()

    sleep(10)

