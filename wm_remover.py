from PIL import Image
import os
import sys
import math

"""
    usage: "python3 wm_remover.py [dir] [n]"

    [dir] is the directory containing the sample and target directories.
    [n] (optional argument) is the max number of samples to use.
"""

class MyImg:
    def __init__(self, size, each_px=None):
        """
            each_px: f(i, x, y) = int
        """
        self.size = (size[0], size[1])
        self.r = []
        self.g = []
        self.b = []
        
        for _ in range(0, size[0]):
            self.r.append([0] * size[1])
            self.g.append([0] * size[1])
            self.b.append([0] * size[1])
            
        self.data = [self.r, self.g, self.b]
        
        if each_px is not None:
            print("building image...")
            for x in range(0, self.size[0]):
                print("filling slice {}/{}".format(x+1, size[0]), end='\r')
                for y in range(0, self.size[1]):
                    for i in range(0, 3):
                        self.data[i][x][y] = each_px(i, x, y)
            print()
            
    def color(self, x, y):
        return (self.r[x][y], self.g[x][y], self.b[x][y])
            
    def to_Image(self):
        img = Image.new("RGB", self.size)
        pix = img.load()
        for x in range(0, self.size[0]):
            for y in range(0, self.size[1]):
                color = (self.r[x][y], self.g[x][y], self.b[x][y])
                if color[0] > 255 or color[1] > 255 or color[2] > 255:
                    raise ValueError("invalid color: {}".format(color)) 
                pix[x, y] = color
        
        return img

    def from_pillow(pillow_img):
        pix = pillow_img.load()
        return MyImg(pillow_img.size, each_px=lambda i,x,y: pix[x, y][i])

        
def get_image(directory, name, mode="RGB"):
    img = Image.open(directory + name)
    return img.convert(mode)
        
        
def build_ev_image(size, sample_dir, samples):
    ev_img = MyImg(size)
    for i in range(0, len(samples)):
        s_name = samples[i]
        print("({}/{}) processing {}".format(i+1, len(samples), s_name), end='\r')
        s_img = get_image(sample_dir, s_name)
        pix = s_img.load()
        for x in range(0, size[0]):
            for y in range(0, size[1]):
                for i in range(0, 3):
                    ev_img.data[i][x][y] += pix[x, y][i]
                
    for x in range(0, size[0]):
        for y in range(0, size[1]):
            for i in range(0, 3):
                ev_img.data[i][x][y] = round(ev_img.data[i][x][y] / len(samples))
    print()           
    return ev_img
        

def build_variance_image(size, ev_img, sample_dir, samples):
    var_img = MyImg(size)
    for i in range(0, len(samples)):
        s_name = samples[i]
        print("({}/{}) processing {}".format(i+1, len(samples), s_name), end='\r')
        s_img = get_image(sample_dir, s_name)
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
    print()        
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
            dist2 = dx*dx + dy*dy
            if (dist2 <= radius*radius):
                yield (x, y)
    
    
def search_for_point(start, i, direction, ignore_pt, x_bounds, y_bounds, overshoot=0):
    pos = [start[0], start[1]]
    while pos[0] >= x_bounds[0] and pos[0] < x_bounds[1] and pos[1] >= y_bounds[0] and pos[1] < y_bounds[1]:
        if ignore_pt(i, pos[0], pos[1]) == 1:
            if overshoot > 0:
                overshoot -= 1
            else:
                return (pos[0], pos[1])
        else:
            pos[0] += direction[0]
            pos[1] += direction[1]
    return None
            

def fill_gaps(size, base_img, ignore_pt, search_radius=12):
    """
        ignore_pt: f(i, x, y) -> float from 0 to 1.0
    """
    res_img = MyImg(size)
    x_bounds = [0, size[0]]
    y_bounds = [0, size[1]]
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    
    for x in range(0, size[0]):
        print("filling slice {}/{}".format(x+1, size[0]), end='\r')
        for y in range(0, size[1]):
            for i in range(0, 3):
                if ignore_pt(i, x, y) >= 0.5:
                    # not watermarked, just set it
                    res_img.data[i][x][y] = base_img.data[i][x][y]
                else:
                    total_weight = 0
                    total_data = 0

                    for pt in points_in_circle((x, y), search_radius, (0, size[0]), (0, size[1])):
                        w = ignore_pt(i, pt[0], pt[1])
                        if w == 0:
                            continue
                        
                        dist = math.sqrt((pt[0]-x)*(pt[0]-x) + (pt[1]-y)*(pt[1]-y))
                        w *= (1 - dist/search_radius)
                       
                        total_weight += w 
                        total_data += w * base_img.data[i][pt[0]][pt[1]]
                        
                    if total_weight == 0:
                        # this is bad, probably a blank image or something
                        continue
                        
                    res_img.data[i][x][y] = min(255, round(total_data / total_weight))
    print()                
    return res_img
    
    
def alpha_img_builder(var_img, var_img_no_watermark):
    def _builder(i, x, y):
        if var_img_no_watermark.data[i][x][y] == 0:
            return 0
        else:
            ratio = var_img.data[i][x][y] / var_img_no_watermark.data[i][x][y]
            return round(255 * (1 - math.sqrt(ratio)))
    return _builder
    
    
def color_img_builder(ev_img, ev_img_no_wm, alpha_img):
    def _builder(i, x, y):
        alpha = alpha_img.data[i][x][y]
        if (alpha == 0):
            return 0
        else:
            a = alpha / 255
            return min(255, round((ev_img.data[i][x][y] / a + ev_img_no_wm.data[i][x][y]*(1 - 1/a))))
    return _builder
    
   
def original_image_builder(target_img, wm_alpha_img, wm_color_img):
    def _builder(i, x, y):
        alpha = wm_alpha_img.data[i][x][y]
        if alpha == 255:
            return 0
        else:
            I_wm = target_img.data[i][x][y]
            a = alpha / 255
            wm = wm_color_img.data[i][x][y]
            I = (I_wm - a*wm) / (1 - a)
            return max(0, min(255, round(I))) 
    return _builder
            
            
class WatermarkRemover:
    def __init__(self, root_dir, var_range=(120, 255), n_samples=None, size_override=None):
        self.SAMPLE_DIR = root_dir + "samples/"
        self.TARGET_DIR = root_dir + "targets/"
        self.OUTPUT_DIR = root_dir + "outputs/"
        self.PRECOMPUTED_DIR = root_dir + "precomputed/"
        
        self.SIZE_OVERRIDE = size_override
        self.N_SAMPLES = n_samples
        self.VAR_RANGE = var_range
        
    def start(self):
        print("~welcome to the watermark destroyer~")
        print("       built by dpendergast         ")
        
        samples = os.listdir(self.SAMPLE_DIR)
        if self.N_SAMPLES is not None:
            del samples[self.N_SAMPLES:]  
        
        targets = os.listdir(self.TARGET_DIR)
        
        print("\nfound {} samples and {} targets".format(len(samples), len(targets)))
        
        if len(samples) == 0 or len(targets) == 0:
            raise ValueError("must have samples and targets")
            
        size = Image.open(self.TARGET_DIR + targets[0]).size
        if self.SIZE_OVERRIDE is not None:
            size = self.SIZE_OVERRIDE
            
        print("using image size: {}".format(size))
        
        if os.path.isfile(self.PRECOMPUTED_DIR + "ev_img.png"):
            print("found precomputed ev_img.png, let's just use that")
            ev_img = MyImg.from_pillow(get_image(self.PRECOMPUTED_DIR, "ev_img.png"))
        else:
            print("\nbuilding average image from {} samples...".format(len(samples)))
            ev_img = build_ev_image(size, self.SAMPLE_DIR, samples)
            print("saving ev_img.png to " + self.OUTPUT_DIR)
            ev_img.to_Image().save(self.OUTPUT_DIR + "ev_img.png")
            # ev_img.to_Image().show()
        
        if os.path.isfile(self.PRECOMPUTED_DIR + "var_img.png"):
            print("found precomputed var_img.png, let's just use that")
            var_img = MyImg.from_pillow(get_image(self.PRECOMPUTED_DIR, "var_img.png"))
        else: 
            print("\nbuilding variance image from {} samples...".format(len(samples)))
            var_img = build_variance_image(size, ev_img, self.SAMPLE_DIR, samples)
            print("saving var_img.png to " + self.OUTPUT_DIR)
            var_img.to_Image().save(self.OUTPUT_DIR + "var_img.png")
            # var_img.to_Image().show()
        
        v1 = self.VAR_RANGE[0]
        v2 = self.VAR_RANGE[1]
        
        def ignore_pt(i,x,y):
            var = max(var_img.color(x, y))
            if var < v1:
                return 0.0
            elif var < v2:
                return (var - v1) / (v2 - v1)
            else:
                return 1.0
        
        print("\nbuilding no-watermark expected value image...")
        no_wm_ev = fill_gaps(size, ev_img, ignore_pt)
        print("saving no_watermark_ev_img.png to " + self.OUTPUT_DIR)
        no_wm_ev.to_Image().save(self.OUTPUT_DIR + "no_watermark_ev_img.png")
        #no_wm_ev.to_Image().show()
        
        print("\nbuilding no-watermark variance image...")
        no_wm_var = fill_gaps(size, var_img, ignore_pt)
        print("saving no_watermark_var_img.png to " + self.OUTPUT_DIR)
        no_wm_var.to_Image().save(self.OUTPUT_DIR + "no_watermark_var_img.png")
        #no_wm_var.to_Image().show()
            
        print("\nbuilding watermark alpha image...")
        wm_alpha_img = MyImg(size, each_px=alpha_img_builder(var_img, no_wm_var))
        print("saving wm_alpha_img.png to " + self.OUTPUT_DIR)
        wm_alpha_img.to_Image().save(self.OUTPUT_DIR + "wm_alpha_img.png")
        # wm_alpha_img.to_Image().show()
        
        print("\nbuilding watermark color image...")
        wm_color_img = MyImg(size, each_px=color_img_builder(ev_img, no_wm_ev, wm_alpha_img))
        print("saving wm_color_img.png to " + self.OUTPUT_DIR)
        wm_color_img.to_Image().save(self.OUTPUT_DIR + "wm_color_img.png")
        # wm_color_img.to_Image().show()
        
        for target in targets:
            print("\nbuilding final image from " + target + "...")
            target_img = MyImg.from_pillow(get_image(self.TARGET_DIR, target))
            original_img = MyImg(size, each_px=original_image_builder(target_img, wm_alpha_img, wm_color_img))
            print("saving cleaned_" + target + " to " + self.OUTPUT_DIR)
            original_img.to_Image().save(self.OUTPUT_DIR + "cleaned_" + target)
    

if __name__ == "__main__":
    args = sys.argv
    root_dir = args[1]
    n = None if len(args) < 3 else int(args[2])
    
    WatermarkRemover(root_dir + "/", var_range=[80, 140], n_samples=n).start()
    

