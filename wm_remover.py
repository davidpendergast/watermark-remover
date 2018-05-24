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
PRECOMPUTED_DIR = "precomputed/"
EXPECTED_SIZE = [0, 0]

class _MyImg:
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
            for x in range(0, self.size[0]):
                for y in range(0, self.size[1]):
                    for i in range(0, 3):
                        self.data[i][x][y] = each_px(i, x, y)
            
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

    @staticmethod
    def from_pillow(pillow_img):
        pix = pillow_img.load()
        return _MyImg(pillow_img.size, each_px=lambda i,x,y: pix[x, y][i])


def get_image(directory, name):
    img = Image.open(directory + name)
    
    if EXPECTED_SIZE[0] != img.size[0] or EXPECTED_SIZE[1] != img.size[1]:
        raise ValueError("sample {} has wrong size: {}".format(name, img.size))
    
    return img.convert("RGB")
        
        
def build_ev_image(size, samples):
    if os.path.isfile(PRECOMPUTED_DIR + "ev_img.png"):
        print("found precomputed ev_img.png, let's just use that")
        return _MyImg.from_pillow(get_image(PRECOMPUTED_DIR, "ev_img.png"))
        
    print("building expected value image...\n")
    
    ev_img = _MyImg(size)
    for i in range(0, len(samples)):
        s_name = samples[i]
        print("({}/{}) processing {}".format(i+1, len(samples), s_name), end='\r')
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
    print("done")           
    return ev_img
        

def build_variance_image(size, ev_img, samples):
    if os.path.isfile(PRECOMPUTED_DIR + "var_img.png"):
        print("found precomputed var_img.png, let's just use that")
        return _MyImg.from_pillow(get_image(PRECOMPUTED_DIR, "var_img.png"))
        
    print("building variance image...\n")
    var_img = _MyImg(size)
    for i in range(0, len(samples)):
        s_name = samples[i]
        print("({}/{}) processing {}".format(i+1, len(samples), s_name), end='\r')
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
    print("done")        
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
            

def fill_gaps(size, base_img, ignore_pt, search_radius=13):
    """
        ignore_pt: f(i, x, y) -> bool
    """
    res_img = _MyImg(size)
    print("filling gaps...")
    
    for x in range(0, size[0]):
        print("processing slice {}/{}".format(x, size[0]), end='\r')
        for y in range(0, size[1]):
            for i in range(0, 3):
                if not ignore_pt(i, x, y):
                    # not watermarked, just set it
                    res_img.data[i][x][y] = base_img.data[i][x][y]
                else:
                    tot_weight = 0
                    tot_value = 0
                    for pt in points_in_circle((x, y), search_radius, (0, size[0]), (0, size[1])):
                        if ignore_pt(i, pt[0], pt[1]):
                            continue
                        
                        dist = math.sqrt((pt[0]-x)*(pt[0]-x) + (pt[1]-y)*(pt[1]-y))
                        w = (1 - dist/search_radius)
                        
                        tot_weight += w 
                        tot_value += w * base_img.data[i][pt[0]][pt[1]]
                        
                    if tot_weight == 0:
                        res_img.data[i][x][y] = 0
                    else:
                        res_img.data[i][x][y] = round(tot_value / tot_weight)
                        if res_img.data[i][x][y] > 255:
                            print("{} {} {} {} {}".format(i, x, y, tot_weight, tot_value))
    print("done")
                        
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
    # size = (200, 200)
    print("found image size: {}".format(size))
    EXPECTED_SIZE[0] = size[0]
    EXPECTED_SIZE[1] = size[1]
    
    ev_img = build_ev_image(size, samples)
    print("saving ev_img.png to " + OUTPUT_DIR)
    ev_img.to_Image().save(OUTPUT_DIR + "ev_img.png")
    # ev_img.to_Image().show()
    
    var_img = build_variance_image(size, ev_img, samples)
    print("saving var_img.png to " + OUTPUT_DIR)
    var_img.to_Image().save(OUTPUT_DIR + "var_img.png")
    # var_img.to_Image().show()
    
    print("building no-watermark expected value image...")
    no_wm_ev = fill_gaps(size, ev_img, lambda i,x,y: var_img.data[i][x][y] < 120)
    print("saving no_watermark_ev_img.png to " + OUTPUT_DIR)
    no_wm_ev.to_Image().save(OUTPUT_DIR + "no_watermark_ev_img.png")
    # no_wm_ev.to_Image().show()
    
    print("building no-watermark variance image...")
    no_wm_var = fill_gaps(size, var_img, lambda i,x,y: var_img.data[i][x][y] < 120)
    print("saving no_watermark_var_img.png to " + OUTPUT_DIR)
    no_wm_var.to_Image().save(OUTPUT_DIR + "no_watermark_var_img.png")
    # no_wm_var.to_Image().show()
        
    print("building watermark alpha image...")
    wm_alpha_img = _MyImg(size, each_px=alpha_img_builder(var_img, no_wm_var))
    print("saving wm_alpha_img.png to " + OUTPUT_DIR)
    wm_alpha_img.to_Image().save(OUTPUT_DIR + "wm_alpha_img.png")
    # wm_alpha_img.to_Image().show()
    
    print("building watermark color image...")
    wm_color_img = _MyImg(size, each_px=color_img_builder(ev_img, no_wm_ev, wm_alpha_img))
    print("saving wm_color_img.png to " + OUTPUT_DIR)
    wm_color_img.to_Image().save(OUTPUT_DIR + "wm_color_img.png")
    # wm_color_img.to_Image().show()
    
    for target in targets:
        print("building final image from " + target + "...")
        target_img = _MyImg.from_pillow(get_image(TARGET_DIR, target))
        original_img = _MyImg(size, each_px=original_image_builder(target_img, wm_alpha_img, wm_color_img))
        print("saving cleaned_" + target + " to " + OUTPUT_DIR)
        original_img.to_Image().save(OUTPUT_DIR + "cleaned_" + target)
        original_img.to_Image().show()
    

