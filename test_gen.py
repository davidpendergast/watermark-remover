import wm_remover
import random

if __name__ == "__main__":
    size = [40, 40]
    directory = "test_imgs/"
    n_images = 100
    
    wm_image = wm_remover.get_image(directory, "wm.png", mode="RGBA")
    wm_pix = wm_image.load()
    
    for n in range(0, n_images):
        img = wm_remover.MyImg(size, each_px = lambda i,x,y: random.randint(0, 255))
        for x in range(0, size[0]):
            for y in range(0, size[1]):
                for i in range(0, 3):
                    img_c = img.data[i][x][y]
                    wm_c = wm_pix[x, y][i]
                    alpha = wm_pix[x, y][3] / 255
                    
                    img.data[i][x][y] = round(img_c * (1.0 - alpha) + wm_c * alpha)
                    
        filepath = directory + "samples/test_img{}.png".format(n)
        print("created " + filepath) 
        img.to_Image().save(filepath)       
        
