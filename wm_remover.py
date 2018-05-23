from PIL import Image
import os

TARGET_DIR = "targets/"
SAMPLE_DIR = "samples/"
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
    for s_name in samples:
        print("loading " + s_name)
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
        
        

if __name__ == "__main__":
    samples = os.listdir(SAMPLE_DIR)
    targets = os.listdir(TARGET_DIR)
    
    print("found {} samples and {} targets".format(len(samples), len(targets)))
    
    if len(samples) == 0 or len(targets) == 0:
        raise ValueError("must have samples and targets")
        
    size = Image.open(TARGET_DIR + targets[0]).size
    print("found image size: {}".format(size))
    EXPECTED_SIZE[0] = size[0]
    EXPECTED_SIZE[1] = size[1]
    
    ev_img = build_ev_image(size, samples)
    ev_img.to_Image().show()
    
        
    
        


#im = Image.open('dead_parrot.jpg') # Can be many different formats.
#pix = im.load()
#print(im.size)  # Get the width and hight of the image for iterating over
#print(pix[x,y])  # Get the RGBA Value of the a pixel of an image
#pix[x,y] = value  # Set the RGBA Value of the image (tuple)
#im.save('alive_parrot.png')
