from PIL import Image
import os
import sys
import math

"""
    usage: "python3 wm_remover.py [n]"
    
    [n] is the maximum number of samples to use.
"""

TARGET_DIR = "targets/"
SAMPLE_DIR = "samples/"
OUTPUT_DIR = "outputs/"
EXPECTED_SIZE = [0, 0]

class _MyImg:
    def __init__(self, size):
        self.size = (size[0], size[1])
        self.r = []
        self.g = []
        self.b = []
        
        for _ in range(0, size[0]):
            self.r.append([0] * size[1])
            self.g.append([0] * size[1])
            self.b.append([0] * size[1])
            
        self.data = [self.r, self.g, self.b]
        
    def to_Image(self):
        img = Image.new("RGB", self.size)
        pix = img.load()
        for x in range(0, self.size[0]):
            for y in range(0, self.size[1]):
                color = (self.r[x][y], self.g[x][y], self.b[x][y])
                pix[x, y] = color
        
        return img


def get_image(directory, name):
    img = Image.open(directory + name)
    if EXPECTED_SIZE[0] != img.size[0] or EXPECTED_SIZE[1] != img.size[1]:
        raise ValueError("sample {} has wrong size: {}".format(name, img.size))
    
    return img.convert("RGB")
        
        
def build_ev_image(size, samples):
    print("building expected value image...")
    ev_img = _MyImg(size)
    for i in range(0, len(samples)):
        s_name = samples[i]
        print("\t({}/{}) processing {}".format(i+1, len(samples), s_name))
        s_img = get_image(SAMPLE_DIR, s_name)
        pix = s_img.load()
        for x in range(0, size[0]):
            for y in range(0, size[1]):
                for i in range(0, 3):
                    ev_img.data[i][x][y] += pix[x, y][i]
                
    for x in range(0, size[0]):
        for y in range(0, size[1]):
            for i in range(0, 3):
                ev_img.data[i][x][y] = round(ev_img.data[i][x][y] / len(samples))
                
    return ev_img
        

def build_variance_image(size, ev_img, samples):
    print("building variance image")
    var_img = _MyImg(size)
    for i in range(0, len(samples)):
        s_name = samples[i]
        print("\t({}/{}) processing {}".format(i+1, len(samples), s_name))
        s_img = get_image(SAMPLE_DIR, s_name)
        pix = s_img.load()
        max_var = [0, 0, 0]
        for x in range(0, size[0]):
            for y in range(0, size[1]):
                for i in range(0, 3):
                    sq_diff = (ev_img.data[i][x][y] - pix[x, y][i]) ** 2
                    var_img.data[i][x][y] += sq_diff
                    max_var[i] = max(max_var[i], var_img.data[i][x][y])
                    
    for x in range(0, size[0]):
        for y in range(0, size[1]):
            for i in range(0, 3):
                # we only really care about relative variance, so we
                # just map it to [0, 256) linearly
                var = round(255 * var_img.data[i][x][y] / max_var[i])
                var_img.data[i][x][y] = var
                
    return var_img
    
def points_in_circle(center, radius, x_bounds, y_bounds):
    x1 = max(x_bounds[0], center[0] - radius)
    x2 = min(x_bounds[1], center[0] + radius)
    y1 = max(y_bounds[0], center[1] - radius)
    y2 = min(y_bounds[1], center[1] + radius)
    for x in range(x1, x2):
        for y in range(y1, y2):
            dx = (x - center[0])
            dy = (y - center[1])
            dist2 = dx*2 + dy*2
            if (dist2 <= radius*radius):
                yield (x, y)
            
    
def build_unwatermarked_ev_image(size, ev_img, var_img, search_radius=10):
    print("building unwatermarked expected value image")
    no_wm_ev_img = _MyImg(size)

    for x in range(0, size[0]):
        print("processing slice {}/{}".format(x, size[0]))
        for y in range(0, size[1]):
            for i in range(0, 3):
                if var_img.data[i][x][y] > 100:
                    # probably not watermarked, just set it
                    no_wm_ev_img.data[i][x][y] = ev_img.data[i][x][y]
                else:
                    tot_weight = 0
                    tot_value = 0
                    for pt in points_in_circle((x, y), search_radius, (0, size[0]), (0, size[1])):
                        var = var_img.data[i][pt[0]][pt[1]]
                        
                        if var < 70:
                            continue
                        
                        dist = math.sqrt((pt[0]-x)*(pt[0]-x) + (pt[1]-y)*(pt[1]-y))
                        w = (1 - dist/search_radius)**2
                        
                        tot_weight += w 
                        tot_value += w * ev_img.data[i][pt[0]][pt[1]]
                        
                    if tot_weight == 0:
                        # raise ValueError("No data to sample at {},{}".format(x, y))
                        no_wm_ev_img.data[i][x][y] = 0
                    else:
                        no_wm_ev_img.data[i][x][y] = round(tot_value / tot_weight)
                        
    return no_wm_ev_img
                    

if __name__ == "__main__":
    samples = os.listdir(SAMPLE_DIR)
    
    # allow control over how many samples to use, as this affects output
    # quality and speed dramatically.
    if len(sys.argv) > 1 and int(sys.argv[1]) < len(samples):
        del samples[int(sys.argv[1]):]  
    
    targets = os.listdir(TARGET_DIR)
    
    print("found {} samples and {} targets".format(len(samples), len(targets)))
    
    if len(samples) == 0 or len(targets) == 0:
        raise ValueError("must have samples and targets")
        
    size = Image.open(TARGET_DIR + targets[0]).size
    print("found image size: {}".format(size))
    EXPECTED_SIZE[0] = size[0]
    EXPECTED_SIZE[1] = size[1]
    
    ev_img = build_ev_image(size, samples)
    
    print("saving ev_img.png to " + OUTPUT_DIR)
    ev_img.to_Image().save(OUTPUT_DIR + "ev_img.png")
    ev_img.to_Image().show()
    
    var_img = build_variance_image(size, ev_img, samples)
    print("saving var_img.png to " + OUTPUT_DIR)
    var_img.to_Image().save(OUTPUT_DIR + "var_img.png")
    var_img.to_Image().show()
    
    no_wm_ev = build_unwatermarked_ev_image(size, ev_img, var_img)
    print("saving no_watermark_ev_img.png to " + OUTPUT_DIR)
    no_wm_ev.to_Image().save(OUTPUT_DIR + "no_watermark_ev_img.png")
    no_wm_ev.to_Image().show()
        
    
        


#im = Image.open('dead_parrot.jpg') # Can be many different formats.
#pix = im.load()
#print(im.size)  # Get the width and hight of the image for iterating over
#print(pix[x,y])  # Get the RGBA Value of the a pixel of an image
#pix[x,y] = value  # Set the RGBA Value of the image (tuple)
#im.save('alive_parrot.png')
