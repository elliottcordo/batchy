# Very Simple Batch Control
![romance](docs/Lets-Get-Batchy.jpg)

Batchy is a very simple microservice for managing the state of jobs and workflows.  It tracks all the information about the last run of a job and will compute new run parameters when a new batch is opened.  There is also a small app called Waitsy, which can be used to "front end" workflow steps to allow for cross job dependencies.

# Batchy

## Data Model
Batchy is platformed on a NoSQL database called Redis.   It stores its data as a hash, so there is no fixed data model so to speak.  You can have as many parameters as you like and name them whatever makes sense for your application. Below is a list of special fields which have meaning within Batchy.

* batch_id - ETL batch ID, unix epoch time
* status - new, open, success, failed
* from_date - date to be used by ETL to restrict data processing
* reprocess_hours - how many hours you want to deduct from the prior batch start time when calculating from_date upon batch open
* batch_start: when the batch last started
* batch_end: when the batch last completed
* trunc_start: when set to true Batchy will always trunc the calculated from_date back to midnight

When you are running a batch Batchy will write to two keys:
* wf_name -  which will contain the current status of the latest job
* wf_name-batch_id - which will contain the current status of a given job

For the most part you will only look at the key representing the latest job, however you may want to look at the batch_id based version to review a historical load or troubleshoot.


## Basic Batchy Operations:

1. To create a new workflow into Batchy you need to create a new yaml file and place it in the cfg folder (this should be moved up to the server environment via standard git workflow). You can also start with a bare param file.  Batchy will automatically build other necessary "special"" ETL params. 

2. To import this workflow into the Redis DB you will need to run the following endpoint (in this case and all other example commands wf1 should be replace by the appropriate workflow name):
`http://0.0.0.0:5000/load_cfg/wf1`
3. You can check the status of your batch now, or at any time using this endpoint:
`http://0.0.0.0:5000/get_status/wf1`
4. To open a batch issue the following command.  Note that you can optionally specify a format for this endpoint, the acceptable values are json or infa (which will create an informatica style param file).
`http://0.0.0.0:5000/open_batch/wf1/json`
 Batchy will only calculate a new from_date if the prior batch had a status of success, otherwise it will assume it needs to run the same batch again.
 5.  To close a batch you can use one of the following endpoints depending on success or failure:
 * `http://0.0.0.0:5000/close_batch/wf1`
 * `http://0.0.0.0:5000/fail_batch/wf1`    

 
# Waitsy
 
 As mentioned a small app named Waitsy was developed to monitor workflows managed by Batchy.  It is assumed that it will live alongside Batchy on the same server, however since it uses python standard lib it should be portable (just be sure to change the URL constant at the top of the script.)

Basic usage: 
`waitsy.py -wf wf1` 

The above command will loop indefinitely untill it recieves a success for all job steps of workflow wf1 for todays date (yesterday's sucess doesn't count.)
 
 
# A Few Helpful Redis CLI commands:
 * `keys wf*` will find all keys matching that pattern
 * `hgetall wf1-1467149783` will return hash for a given key
 
