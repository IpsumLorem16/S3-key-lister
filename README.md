# S3-key-lister
List all keys in any public Amazon s3 bucket, option to check if each object is public or private. Saves result as a .csv file


<p align="center">
  <img width="645" height="410" src="https://raw.githubusercontent.com/IpsumLorem16/S3-key-lister/master/s3getkeys-acl-v-orig.gif">
</p>

## Notes: 
- Still a work in progress, works very well but not all options have been added yet.  
- Made on linux for linux, might have bugs when running on windows, and printed text in the terminal..formatting will probably be a little screwed up.  
- Large buckets with hundreds of thousands of keys can take a long time to go over with --acl, this is something that will be improved on v2.  
- Uses python 2.7


