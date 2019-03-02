import boto3, csv, time, urllib3, getopt, sys
#disable ssl warning(not reccomended)
urllib3.disable_warnings()

#Stop credentials from being used:
from botocore import UNSIGNED
from botocore.client import Config

#options
bucket = None    #-t,--bucket <bucket_name> Tag with argument, what bucket to fetch keys from *required
key = None       # --key, <keyname> what key to start from
recurse = False  #-r, Recurse, continue getting keys if returned a truncated list(will fetch EVERY key in bucket)
output = None    #-o, --output <file_name> name of output file, file is csv [default:bucket]
verbose = False  #-v, --verbose, lists all keynames as they are being fetched, shows progress every 1000 keys
checkACL = False #--acl, check wether each key is public or private
estimate = False #--estimate, estimate how long it would take to check --acl in bucket. based on average of 20 requests
#append = false

#other variables
numKeys = [0,0]         #totalkeys,public keys
startTime = time.time() #time we started the script
runTime = None          #run time, updates in script
estimateTimes = []      # for getEstimate, saves request times from to work out average response time
averageEstTime = None   #average of estimateTimes
s3 = boto3.client('s3', config=Config(signature_version=UNSIGNED))

#bucket = 'ryft-public-sample-data' #for tests DELETE

#prints help info
def usage():
	print "\n\x1b[0;33;49mThis python 2.7 script will fetch all keys from any specified public AWS s3 bucket and save it as a .csv file\x1b[0;37;49m \n"
	print "Usage:"
	print "  python2 s3getkeys.py -t <bucket> [--key=<key>] [-r] [-v] [--acl] [-o=<file>]"
	print "  python2 s3getkeys.py -t <bucket> [--key] [--estimate]"
	print "  python2 s3getkeys.py -t <bucket> [-h|--help]\n"
	print "Options:"
	print "  -t, --bucket <bucket> bucket to fetch keys from"
	print "  --key <key>           key to start from"
	print "  -r                    recursivly fetch all keys"
	print "  -v                    verbose, print keys"
	print "  --acl                 check if each key is public,"
	print "                        can take long time in large buckets"
	print "  -o, --output <file>   name of output file, do not include .csv[default:bucket]"
	#print "  -a                    append to existing file"
	print "  --estimate            estimate how long to run, filesize with [-r][--acl]"
	print "  -h,--help             show this help info"

#get options from command line
try:
	opts, args = getopt.getopt(sys.argv[1:], "t:rvo:h", ["bucket=","key=","acl","output=","estimate","help"])
except getopt.GetoptError as err:
	# print help information and exit
	print str(err)
	usage()
	sys.exit(2)
#loop though supplied options from the command line and set variables/flags to be used in script
for o, a in opts:
	if o in ("-t", "--bucket"):
		bucket = a
	elif o == "-r":
		recurse = True
	elif o == "-v":
		verbose = True
	elif o == "--key":
		key = a.encode('utf-8')
	elif o == "--acl":
		checkACL = True
	elif o in ("-o", "--output"):
		output = a.encode('utf-8')
	elif o in ("-h", "--help"):
		usage()
		sys.exit()
	elif o in ("--estimate"):
		estimate = True
	else:
		assert False, "unhandled option"	
if not output:     #if no output filename specified
	output = bucket  #set filename to bucketname

#print current progress to the terminal
def printProgress():
	if checkACL:
		logString = '\r  Progress: keys: ' + str(numKeys[0]) + ', public: ' + str(numKeys[1]) +', current runTime: ' + runTime + 's'
	else:
		logString = '\r  Progress: keys: ' + str(numKeys[0]) + ', current runTime: ' + str(runTime) + 's'
	sys.stdout.write(logString)  #print logstring
	sys.stdout.flush()           #clear print line
	
#get estimated time and filesize if you run query on bucket with options: [-r] recursivly, and [--acl] if each key is public
def getEstimate(_StartAfter=None,_ContinuationToken=None):
	global runTime
	if _StartAfter:
		objects = s3.list_objects_v2(Bucket=bucket,StartAfter=_StartAfter)
	elif _ContinuationToken:
		objects = s3.list_objects_v2(Bucket=bucket,ContinuationToken=_ContinuationToken)
	else:
		objects = s3.list_objects_v2(Bucket=bucket)
	#get response times for --acl checks and push to array
	if len(estimateTimes) < 20:             #if list less than 10, ie not executed yet
		for key in objects['Contents']:       #loop though keys
			keyStr = key['Key'].encode('utf-8') #get key and make sure it is encoded to utf-8, otherwise throws errors with some lang characters
			t0 = time.time()                    #get curr time
			isObjPublic(bucket,keyStr)          #make test request
			t1 = time.time()                    #get cur time
			requestTime = t1 - t0               #workout test request time
			estimateTimes.append(requestTime)   #append time to list
			if len(estimateTimes) > 19:         #if we have 20 estimateTimes
				break                             #break out of loop
		global averageEstTime
		averageEstTime = sum(estimateTimes) / len(estimateTimes)           #workout average lookup time
		print 'Average key info request time: ' + str(averageEstTime)+'s'  #print info
		
	numKeys[0] += objects['KeyCount']           #log how many keys we fetched
	t0 = time.time()                            #current time
	runTime = "{0:.2f}".format(t0 - startTime)  #update runtime
	printProgress()                             #print progress to terminal
	if objects['IsTruncated']:                  #if object list is truncated
		printProgress()                           #print current progress
		getEstimate(_ContinuationToken=objects['NextContinuationToken']) #recursivly continue until bucket no longer truncated
	else:
		estimateTime = "{0:.2f}".format(averageEstTime * numKeys[0]) #calculate estimate time to complete query
		print '\r\n\x1b[1;36;49mDone\x1b[0;37;49m \x1b[1;32;49mTotal keys:\x1b[0;37;49m ' + str(numKeys[0]) + ', \x1b[1;32;49mestimated time:\x1b[0;37;49m ' + estimateTime + 's'
		
#check if a key inside a bucket is public
def isObjPublic(_bucket,_key):
	try:
		#try to read properties object, works if access is public
		obj = s3.head_object(Bucket=_bucket,Key=_key)
		return(True, 'public')
	except Exception as e:
		#object read failed	
		error = str(e)
		#shorten error message
		if 'Forbidden' in error: error = 'private'
		elif 'Not Found' in error: error = 'not found'
		return(False,error)
		#e returns either:
		#'An error occurred (404) when calling the HeadObject operation: Not Found'
		#'An error occurred (403) when calling the HeadObject operation: Forbidden'

#loop through bucket, get all keys, save to csv
def getKeys(_bucket,_marker=None):
	if _marker:
		objects = s3.list_objects(Bucket=_bucket,Marker =_marker)
	else:
		objects = s3.list_objects(Bucket=_bucket)

	for key in objects['Contents']:
			global numKeys, runTime
			numKeys[0] +=1                        #update number of keys
			keyStr = key['Key'].encode('utf-8')   #get key and make sure it is encoded to utf-8, otherwise throws errors with some lang characters
			size = key['Size']                    #get file size in bytes
			lastMod = str(key['LastModified'])    #get date of last modified
			access = 'unknown'                    #wether object is public/private
			logString = keyStr                    #start making string to print to terminal, only if -v|--verbose was enabled
			t0 = time.time()                      #time logging	
			runTime = "{0:.2f}".format(t0 - startTime)#update long script has been running, total
			#if check(if key public) flag = True
			if checkACL:
				ispublic = isObjPublic(_bucket,keyStr)  #check if object is public
				access = ispublic[1]                    #get returned string 'public'|'private'
				logString += ': ' + access              #append logString with acesss. Example: 'Files/images/1.jpg:public'
				if ispublic[0]: numKeys[1] +=1          #if this object IS public, increase total public keys tally
			#write info to file
			writer.writerow({'key':keyStr,'size':size,'last_mod':lastMod,'access':access})
			if verbose: print(logString)              #if -v|--verbose, print logstring
			else:                                     #else
				printProgress()                         #print current progress(continusly updates one line)
	#if user does not want truncated list but objects IS truncated recursivly continue from last key
	if recurse and objects['IsTruncated']:        #note:this fires once every thousand keys
		lastKey = objects['Contents'][-1]['Key']    #get the last key
		if verbose:                                 #if -v|--verbose
			print('\x1b[1;32;49mNext Marker:\x1b[0;37;49m ' + lastKey) #print info. Example: 'Next Marker: Files/images/1.jpg' 
			print('\x1b[1;32;49mRun time:\x1b[0;37;49m ' + runTime + 's, \x1b[1;32;49mTotal Keys:\x1b[0;37;49m ' + str(numKeys[0])) #print info
		getKeys(bucket, lastKey)                    #recursivly continue fetching keys, until list is no longer truncated

#if bucket was supplied in command line		
if bucket:
	#if --estimate option used
	if estimate:
		print '\x1b[0;33;49mGetting estimated time, will print Done when finished\x1b[0;37;49m:'
		#if a key to start from supplied
		if key:
			getEstimate(_StartAfter=key)  #get estimate with supplied StartAfter key
		else:                           #else
			getEstimate()                 #get estimate
	#else if estimate option NOT used:		
	else:
		#open/create file
		with open(output+'.csv','w') as fh:                   #open .csv file, using supplied name(-o|--output)/bucket name
			fieldnames = ['key','size','last_mod','access']     #set feildnames on csv
			writer = csv.DictWriter(fh, fieldnames=fieldnames)  #create writer
			writer.writeheader()                                #write header file
			#print info
			cliInfo = '\x1b[0;33;49mFetching keys from: ' + str(bucket) + ', will print Done when finished\x1b[0;37;49m:'
			print cliInfo
			#get keys
			if key:                 #if key supplied with --key in command line
				getKeys(bucket, key)  #get keys ,starting after supplied --key  and write to .csv file
			else:                   #else
				getKeys(bucket)       #get keys starting at beginning of bucket, and write to .csv file
			#when fnished getting keys print info
			print('\r\n\x1b[1;36;49mDone\x1b[0;37;49m saved as: ' + output + '.csv')
			logString = 'Query time: ' + runTime + 's,' + ' Total keys: ' + str(numKeys[0])
			if checkACL: logString += ', Public: ' + str(numKeys[1])
			print(logString)
else:  #else, user did NOT supply a bucket name
	assert False, "no bucket provided" 
