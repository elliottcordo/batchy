from ConfigParser import ConfigParser as Conf
import os
import sys
import logging
from  datetime import datetime, timedelta
import time
import yaml
import json
import redis
from flask import Flask, render_template, Response, request

# ------------------------------------------------------------------------

os.chdir(os.path.dirname(sys.argv[0]))

# ------------------------------------------------------------------------
# declare application

app = Flask(__name__, static_url_path = "/static", static_folder = "static")
app.debug = True

# ------------------------------------------------------------------------
# helper

def json_serial(data):
    """
    JSON serializer for objects not serializable by default json code"
    :param obj:
    :return:
    """
    if isinstance(data, datetime):
        serial = data.isoformat()
        return serial
    raise TypeError ("Type not serializable")


def render_response(data, format='json', status=200):
    if format == 'json':
        wdata = json.dumps(data,default=json_serial, indent=4)
        mimetype = "application/json"
    elif format == 'infa':
        wdata = infa_param(data)
        mimetype = None
    else:
        status = 500
    resp = Response(response=wdata, status=status,)
    return resp


def parse_yaml(jobname):
    """
    reads yaml file into python object
    :return: checklist
    """
    with open(("cfg/%s.yaml") % jobname, 'r') as yam:
        pyam = yaml.load(yam)
    return pyam

def infa_param(data):
    result = ''
    for k, v in data.iteritems():
        result += '\n[' + str(k) + ']\n'
        for k1, v1, in v.iteritems():
            result += '$$' + str(k1) + '=' + str(v1) + '\n'

    return result

class RedisInteraction(object):
    """
    small wrapper on redis interaction to handle json serdes
    """
    def __init__(self):
        cfg_path =  "{0}/batchy.cfg".format(sys.path[0])
        c = Conf()
        c.read(cfg_path)
        server = c.get('redis', 'server')
        self.rconn = redis.StrictRedis(host=server, port=6379, db=0)

    def h_write(self, key, data):
        for k,v in data.iteritems():
            self.rconn.hset(key, k, json.dumps(v, default=json_serial))

    def h_write_batch(self, key, data):
        batch_id = None
        for v in data.itervalues():
            if v.get('batch_id',None) != None:
                batch_id = v.get('batch_id')

        batch_key =  key + '-' + str(batch_id if batch_id != None else str(int(time.time())) + '-init')
        r.h_write(batch_key, data)
        r.h_write(key, data)


    def h_getall(self, key):
        data = self.rconn.hgetall(key)
        result={}
        for k, v in data.iteritems():
            result[k] = json.loads(v)
        return result


# ------------------------------------------------------------------------
# flask stuff

@app.route('/index')        #http://localhost:5000/index
def index():
    return 'Batchy v0.00001'


# ------------------------------------------------------------------------
# load and status interactions

@app.route('/load_cfg/<string:wf>', endpoint='load_cfg')
def load_cfg(wf):
    """
    load state of a workflow from yaml, will delete and replace values for given workflow
    :param wf:
    :return:
    """
    cfg = parse_yaml(wf)
    r.rconn.delete(wf)
    r.h_write_batch(wf, cfg)
    return render_response(cfg)


@app.route('/get_status/<string:wf>', endpoint='get_status')
def get_status(wf):
    """
    get config
    :param wf:
    :return:
    """
    cfg = r.h_getall(wf)
    return render_response(cfg)


# ------------------------------------------------------------------------
# batch interactions

@app.route('/open_batch/<string:wf>/<string:fmt>', endpoint='open_batch1')
@app.route('/open_batch/<string:wf>', endpoint='open_batch')
def open_batch(wf, fmt='json'):
    """
    get's state of last run and opens batch based on params
    :param batch:
    :return:
    """
    batch = r.h_getall(wf)
    from_date = datetime.utcnow()
    batch_id = int(time.time()) # datetime.utcnow().strftime('%Y%m%d-%H%M%S-%f')[:-3]

    # now iterate and assign values for new batch
    for k, v in batch.iteritems():

        # now we look at prior status and compute the from_date
        if v.get('status') == 'success':
            offset = v.get('reprocess_hours', 0)
            old_batch_start = datetime.strptime(v.get('batch_start', '1776-07-04T23:59:00.000'), "%Y-%m-%dT%H:%M:%S.%f")
            from_date = old_batch_start - timedelta(hours=offset)

        if v.get('from_date') == None:
            from_date = datetime.strptime('1776-07-04T23:59:00.000', "%Y-%m-%dT%H:%M:%S.%f")

        if v.get('trunc_start', False) == True:
            from_date = from_date.replace(minute=0, hour=0, second=0, microsecond=0)

        batch[k]['from_date'] = from_date
        batch[k]['batch_start'] = datetime.utcnow()
        batch[k]['batch_end'] = None
        batch[k]['status'] = 'open'
        batch[k]['batch_id'] = batch_id

    infa_param(batch)

    #write new batch
    r.h_write_batch(wf, batch)

    return render_response(batch, fmt)


@app.route('/close_batch/<string:wf>', endpoint='close_batch')
def close_batch(wf):
    """
    closes batch
    :param batch:
    :return:
    """
    batch = r.h_getall(wf)
    for k, v in batch.iteritems():
        batch[k]['batch_end'] = datetime.utcnow()
        batch[k]['status'] = 'success'

    r.h_write_batch(wf, batch)
    return render_response(batch)


@app.route('/fail_batch/<string:wf>', endpoint='fail_batch')
def fail_batch(wf):
    """
    closes batch
    :param batch:
    :return:
    """
    batch = r.h_getall(wf)
    for k, v in batch.iteritems():
        batch[k]['batch_end'] = datetime.utcnow()
        batch[k]['status'] = 'failure'

    r.h_write_batch(wf, batch)
    return render_response(batch)


# ------------------------------------------------------------------------
#logging wrapper:

def log(message):
    logging.info(message)
    print(message)

# ------------------------------------------------------------------------

if __name__ == '__main__':
    r = RedisInteraction()
    app.run(host='0.0.0.0', debug = True)
