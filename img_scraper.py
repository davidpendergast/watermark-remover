""" 
    usage: "python3 img_scraper.py [n]"
    
    [n] is the number of (randomish) images to grab. Images will be named 
    samplexxx.jpg and placed into samples/

""" 

import urllib.request
import sys
import random
import os.path

def download_image(url, filename):
    print("downloading: " + url + " as " + filename)
    with open(filename,'wb') as f:
        f.write(urllib.request.urlopen(url).read())
        
def _get_url(n1, n2):
    """
    n1: in [1001, 1200ish]
    n2: in [0, 50]
    """
    n1_str = str(n1)
    n2_str = '0' + str(n2) if n2 < 10 else str(n2)
    return 'https://iconic-imagecdn.azureedge.net/MFT2018-01/07/826907/{}/00{}.jpg?preset=p'.format(n1_str, n2_str)
    
if __name__ == '__main__':
    num_to_grab = int(sys.argv[1])
    random.seed(12345271829)
    for i in range(0, num_to_grab):
        n1 = random.randint(1001, 1200)
        n2 = random.randint(0, 50)
        path = "samples/sample{}_{}.jpg".format(n1, n2)
        if os.path.isfile(path):
            print("file already exists: {}".format(path))
        else:
            url = _get_url(n1, n2)
            download_image(url, path)
        
    

    
