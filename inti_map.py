# -*- coding: utf-8 -*-
"""
Created on Sun Mar  3 17:33:13 2024

@author: valer
"""

import numpy as np
import cv2 as cv2
#import sys
import os
#import matplotlib.pyplot as plt
import PySimpleGUI as sg
from PIL import Image
import io
import yaml



version = ' 0.1 by Valerie Desnoux'

"""
************************************************************************
Application "you are here" sur le spectre solaire de ca II H&K à H-alpha
************************************************************************

Image spectre solaire sp_sun.png
Assemblage de 30 image png de spectre solaire 2D no ROI avec Hugin
Taille pixel ASI178 x2 par binning
assemblage vertical pour correspondre a acquisition

Image synthetique spectre solaire annoté raies principales sun_spectre_anot_V2.png
Profil à partir d'une zone de 200 pixels du spectre sp_sun.png
Profil dupliqué pour image 2D de 800 pixels de large

Version 0.1 Antibes 22 mars 2024
- bon pour premiere edition
- gestion taille pixel, zoom

TODO : si sc=1 verif offset et pos rectangle

"""

def synth_spectrum (template, ratio_pix) :
    debug=False
    
    h,w = template.shape[0], template.shape[1]
    
    if ratio_pix !=1 :
        template=cv2.resize(template, dsize=(w, int(h*0.5)), interpolation=cv2.INTER_LANCZOS4)
        template=cv2.GaussianBlur(template,(5,1),cv2.BORDER_DEFAULT)

    #print('Pattern Dimensions : ',template.shape)
    template=template[:,w//2-100:(w//2)+100]
    moy=1*np.mean(template,1)
    moy=np.array(moy, dtype='uint8')
    vector_t= np.array([moy]).T

    temp_r=np.tile(vector_t, (1,400))
    #print('Dimensions : ',temp_r.shape)

    if debug :
        cv2.imwrite('resized.png', template)
        print('Resized Pattern Dimensions : ',template.shape)
    
    return temp_r

def template_locate (img_r, temp_r) :
    
    # Trouve la bonne region de temp_r dans le spectre img_r complet 
    matched= cv2.matchTemplate(img_r, temp_r, cv2.TM_CCOEFF_NORMED)
    
    # Coordinates of the bounding box
    (minVal, maxVal, minLoc, maxLoc) = cv2.minMaxLoc(matched)
    
    return maxLoc

def img_resize (nomfich,dimx, dimy):
    image = Image.open(nomfich)
    iw,ih=image.size
    if dimy==0 :
        dimy=ih
    if dimx==0 :
        dimx=iw
    image.thumbnail((dimx, dimy))
    with io.BytesIO() as output:
        image.save(output, format="PNG")
        out = output.getvalue()
    return out

def seuil_image (i, Seuil_haut, Seuil_bas):
    img=np.copy(i)
    img[img>Seuil_haut]=Seuil_haut
    if Seuil_haut!=Seuil_bas :
        img_seuil=(img-Seuil_bas)* (65535/(Seuil_haut-Seuil_bas))
        img_seuil[img_seuil<0]=0
    else:
        img_seuil=img
    return img_seuil

def get_init_yaml():
    # recupere les parametres utilisateurs enregistrés lors de la session
    # precedente dans un fichier ini.yamp 

    #my_ini=os.path.dirname(sys.argv[0])+'/inti.yaml'
    my_ini=os.getcwd()+'/inti_map.yaml'
    my_dictini={'directory':'', 'lang':'FR','screen_scale':2,'my_pixel_size':'4.8'}

    try:
        #print('mon repertoire : ', mydir_ini)
        with open(my_ini, "r") as f1:
            my_dictini = yaml.safe_load(f1)
    except:
        pass
    return my_dictini

def set_init_yaml(my_dictini):

   my_ini=os.getcwd()+'/inti_map.yaml'
   try:
       
       with open(my_ini, "w") as f1:
           yaml.dump(my_dictini, f1, sort_keys=False)
   except:
       print('erreur ecriture inti_map.yaml')

"""
===========================================================================
Program starts here
===========================================================================
"""


my_dictini = get_init_yaml()
sc = my_dictini['screen_scale']
LG_str = my_dictini['lang']
if LG_str == 'FR' : LG=1
if LG_str =='EN' : LG=2
WorkDir = my_dictini['directory']
my_pixel_size_str = my_dictini['my_pixel_size']

module_dir = os.getcwd()

# dimension et coordonnées du viewport image sun_sp_anot
dim_sx = 300*sc
#dim_sx=720*sc
dim_sy = 720*sc
sx0 = 0
sy0 = dim_sy

# dimension et coordonnées du viewport image template
dim_tx = 400*sc
dim_ty = 300*sc
tx0 = 0
ty0 = dim_ty

# dimension et coordonnées du viewport image match
dim_mx = 400*sc
dim_my = 300*sc
mx0 = 0
my0 = dim_my

# dimension et coordonnées du viewport image color
dim_cx=710*sc
dim_cy=25*sc
cx0=0
cy0=dim_cy

# initialisations
dx0 = 0
dy0 = 0
#step_zoom=50*sc
dim_zx = 0
dim_zy = 0

# taille du pixel de la mosaique du spectre solaire
# acquise avec ASI178 en bin 2
pixel_ref = 2.4 *2


"""
PysimpleGUI interface
----------------------------------------------------------------------------
"""
sg.set_options(dpi_awareness=True, scaling=sc)
sg.set_options(font="Arial, 10")
sg.theme('Dark2')
sg.theme_button_color(('white', '#500000'))
sg.theme_element_text_color('darkgrey')


if LG==1 :
    colonne_A= [
        [sg.Graph(canvas_size=(dim_sx,dim_sy),graph_bottom_left=(0, 0),graph_top_right=(dim_sx, dim_sy),border_width = 1, 
                  drag_submits=True,enable_events=True,key='-FULLSP-',background_color='tan')],]
    colonne_B = [
        [sg.Button(button_text=LG_str, key='-LANG-', border_width=1, button_color='#404040')],
        [sg.Text('Image Spectre à localiser  :', size=(25, 1))],
        [sg.InputText(default_text='',size=(50,1),enable_events=True,key='-LOADTEMPLATE-'),
         sg.FileBrowse('Ouvrir', target='-LOADTEMPLATE-',file_types=(("png file", "*.png "),),initial_folder=WorkDir)],
        [sg.Text('Taille pixel : '), sg.InputText(default_text=my_pixel_size_str,size=(4,1),enable_events=True,key='-PIXSIZE-'),sg.Text(' microns'),
         sg.Text('',size=(1,1)), sg.Button('Localise', key='-LOCATE-')],
        [sg.Graph(canvas_size=(dim_tx,dim_ty),graph_bottom_left=(0, 0),graph_top_right=(dim_tx, dim_ty),border_width = 1, 
         drag_submits=True, enable_events=True,key='-TEMPLATE-',background_color='tan')],
        [sg.Text('Région trouvée :')],
        [sg.Graph(canvas_size=(dim_mx,dim_my),graph_bottom_left=(0, 0),graph_top_right=(dim_mx, dim_my),border_width = 1, 
         drag_submits=True, enable_events=True,key='-MATCH-',background_color='tan')],
        ]
else :
    colonne_A= [
        [sg.Graph(canvas_size=(dim_sx,dim_sy),graph_bottom_left=(0, 0),graph_top_right=(dim_sx, dim_sy),border_width = 1, 
                  drag_submits=True,enable_events=True,key='-FULLSP-',background_color='tan')],]
    colonne_B = [
        [sg.Button(button_text=LG_str, key='-LANG-', border_width=1, button_color='#404040')],
        [sg.Text('Spectrum image to localize  :', size=(25, 1))],
        [sg.InputText(default_text='',size=(50,1),enable_events=True,key='-LOADTEMPLATE-'),
         sg.FileBrowse('Open', target='-LOADTEMPLATE-',file_types=(("png file", "*.png "),),initial_folder='')],
        [sg.Text('Pixel size : '), sg.InputText(default_text=pixel_ref,size=(4,1),enable_events=True,key='-PIXSIZE-'),sg.Text(' microns'),
         sg.Text('',size=(1,1)), sg.Button('Locate', key='-LOCATE-')],
        [sg.Graph(canvas_size=(dim_tx,dim_ty),graph_bottom_left=(0, 0),graph_top_right=(dim_tx, dim_ty),border_width = 1, 
         drag_submits=True, enable_events=True,key='-TEMPLATE-',background_color='tan')],
        [sg.Text('Region found :')],
        [sg.Graph(canvas_size=(dim_mx,dim_my),graph_bottom_left=(0, 0),graph_top_right=(dim_mx, dim_my),border_width = 1, 
         drag_submits=True, enable_events=True,key='-MATCH-',background_color='tan')],
        ]
    


layout = [
        [sg.Column(colonne_A),sg.Column(colonne_B, vertical_alignment='Center',)],
        [sg.Graph(canvas_size=(dim_cx,50),graph_bottom_left=(0, 0),graph_top_right=(dim_cx, 50),border_width = 0, 
                  drag_submits=True,enable_events=True,key='-COLORSP-',background_color='tan')],
        [sg.Button('Reset'), sg.Button('Zoom 1:1'), sg.Button('Exit')]
        ]

window = sg.Window('INTI map '+version, layout, location=(0,10),finalize=True,return_keyboard_events=True)
    
# diverses initialisation
sun_sp_viewport = window.Element("-FULLSP-")
template_viewport = window.Element("-TEMPLATE-")
match_viewport = window.Element("-MATCH-")
color_sp_viewport = window.Element("-COLORSP-")
dragging=False

# charge image spectre coloré
img_color=cv2.imread(module_dir+os.path.sep+'sun_spectre_color.png')
img_color = cv2.cvtColor(img_color, cv2.COLOR_BGR2RGB)
ch,cw = img_color.shape[0], img_color.shape[1]  #ch et cw sont les dimensions de l'image annotée plein format
r_cr=dim_cx/cw
color_resized = cv2.resize(img_color, (int(cw*r_cr),ch), interpolation = cv2.INTER_AREA)
with io.BytesIO() as output:
    image = Image.fromarray(color_resized)
    image.save(output, format="PNG")
    color_out = output.getvalue()
    
# place image locatio is the top-left corner of the image sx0=0 sy0=dim_sy
color_sp_viewport.DrawImage(data=color_out, location=(0,dim_cy))


# charge image spectre annoté en plein format
#img_sun=cv2.imread(module_dir+'\\sun_spectre_annot.png')
img_sp=cv2.imread(module_dir+os.path.sep+'sun_spectre_annot_V2.png')
img_sp = cv2.cvtColor(img_sp, cv2.COLOR_BGR2RGB)
ih,iw = img_sp.shape[0], img_sp.shape[1]  #ih et iw sont les dimensions de l'image annotée plein format
r_sp=dim_sx/iw
#cv2.line(img_sp,(0,19312),(800,19312),color=(255,0,0), thickness=5)

image_resized = cv2.resize(img_sp, (int(iw*r_sp),int(ih*r_sp)), interpolation = cv2.INTER_AREA)
with io.BytesIO() as output:
    image = Image.fromarray(image_resized)
    image.save(output, format="PNG")
    sp_out = output.getvalue()
    
# place image locatio is the top-left corner of the image sx0=0 sy0=dim_sy
sun_sp_viewport.DrawImage(data=sp_out, location=(sx0,sy0))

# actualise les dimensions de l'image à afficher, plus grande que la fenetre du canvas
dim_zy, dim_zx = image_resized.shape[0], image_resized.shape[1]
window.BringToFront()

while True:
    event, values = window.read()
    #print(event)
       
    if event==sg.WIN_CLOSED or event=='Sortir' or event=="Exit":
        my_dictini ['directory'] = WorkDir
        my_dictini ['my_pixel_size'] = str(values['-PIXSIZE-'])
        set_init_yaml(my_dictini)
        break
    
    if event == '-LANG-' :
        if window['-LANG-'].get_text() == 'FR' :
            window['-LANG-'].update('EN')
            LG=2
            my_dictini['lang']='EN'
        else :
            window['-LANG-'].update('FR')
            LG=1
            my_dictini['lang']='FR'
            
    if values['-LOADTEMPLATE-'] != '' and os.path.isfile(values['-LOADTEMPLATE-']):
        template_name=values['-LOADTEMPLATE-'] 
        # extract directory from file_name to save it in yaml
        WorkDir = os.path.dirname(values['-LOADTEMPLATE-'])+os.path.sep
        bio=img_resize(template_name,dim_tx,dim_ty)
        template_viewport.erase()
        template_viewport.DrawImage(data=bio, location=(tx0,ty0))
        
    if event=='-LOCATE-' and values['-LOADTEMPLATE-'] != '':
        dx0=0
        dy0=0
        my_pixel_size= float(values['-PIXSIZE-'])
        ratio_pix= my_pixel_size/pixel_ref
        
        img_r=cv2.imread(module_dir+os.path.sep+'sun_spectre.png',cv2.IMREAD_GRAYSCALE)
        ih,iw = img_r.shape[0], img_r.shape[1]
        
        template=cv2.imread(template_name, cv2.IMREAD_GRAYSCALE)
        
        temp_r= synth_spectrum(template, ratio_pix)
        maxLoc = template_locate (img_r, temp_r)
        #print(maxLoc)
        (startX, startY) = maxLoc
        startX=0
        endX = startX + temp_r.shape[1]
        endY = startY + temp_r.shape[0]
        img_here=img_sp[startY:endY,:]
        mh,mw = img_here.shape[0], img_here.shape[1]

        # resize image match
        rw = dim_mx/mw
        rh = dim_my/mh
        r = min(rw,rh)
        match_viewport.erase()
        resized = cv2.resize(img_here, (int(mw*r),int(mh*r)), interpolation = cv2.INTER_AREA)
        with io.BytesIO() as output:
            image = Image.fromarray(resized)
            image.save(output, format="PNG")
            out = output.getvalue()
        match_viewport.DrawImage(data=out, location=(mx0,my0))
        
        # deplace image sp_spectre_anot 
        # TODO : il faut sans doute revenir à la taille "reset" car zoom facteur est r_sp
        zoom=r_sp
        # test facteur de zoom different de r_sp pour revenir a taille du reset
        dim_zy, dim_zx = image_resized.shape[0], image_resized.shape[1]
        #zoom= iw/dim_zx
        sun_sp_viewport.erase()
        #scrolly=int(startY*zoom)+dim_sy-100
        #sun_sp_viewport.DrawImage(data=sp_out, location=(sx0,scrolly))
        offset=(dim_sy//2)-400
        scrolly=int((startY)*zoom)-offset
        sun_sp_viewport.DrawImage(data=sp_out, location=(sx0,sy0))
        sun_sp_viewport.move(0,scrolly)
        recty2=int(mh*r_sp)
        #sp_rect=sun_sp_viewport.draw_rectangle((1,dim_sy-100), (dim_sx,dim_sy-100-recty2), line_color='gold',line_width = 2)
        sp_rect=sun_sp_viewport.draw_rectangle((1,dim_sy-offset), (dim_sx,dim_sy-offset-recty2), line_color='gold',line_width = 4)
        
        
        #rectangle sur spectre coloré
        c_rect1= (startY * (dim_cx/ih))
        c_rect2= (endY * (dim_cx/ih))
        try :
            color_sp_viewport.delete_figure(color_rect)
        except :
            pass
        color_rect = color_sp_viewport.draw_rectangle ((c_rect1,0),(c_rect2,dim_cy-1), line_color="white", line_width=2)
        #ha = 19312 * ((cw) / ih)
        
        #color_line=color_sp_viewport.draw_rectangle((ha,0),(ha+1,ch), line_color="white", line_width=2)
        # reset variables de position 
        dx0=0
        #dy0=0
        dy0=scrolly
        sx0=0
        sy0=dim_sy
        """
        dim_zx = dim_sx
        #dim_zy=dim_sy
        dim_zy=int(ih*r_sp)
        """
        
    if event == '-FULLSP-' :
            
        x,y=values['-FULLSP-']
        # xline,yline=x,y
        #print(dx0, dy0)
        
        if not dragging:

            start_point=(x,y)
            
            dragging =True
            Lastxy=x,y
        else:
            end_point=(x,y)

        delta_x, delta_y= x-Lastxy[0], y-Lastxy[1]
        # uniquement axe vertical
        #delta_x, delta_y= 0, y-Lastxy[1]
        sun_sp_viewport.move(delta_x, delta_y)
       
        Lastxy=x,y
        

    if event.endswith('+UP'):
        end_point=(x,y)
        
        try:
            delta_x=(end_point[0]-start_point[0])
            delta_y=(end_point[1]-start_point[1])
            dx0=dx0+delta_x
            dy0=dy0+delta_y

            #print(delta_x, delta_y,'...', dx0, dy0)
            #sun_sp_viewport.change_coordinates((-dx0, -dy0),(dim_sx-dx0, dim_sy-dy0))
           
        except:
            pass
        
        start_point, end_point = None, None  # enable grabbing a new rect
        dragging = False
        #print(dx0, dy0)
        
    if event=='MouseWheel:Down':    # zoom 
        
        if dim_zx <=8000:
            
            sun_sp_viewport.erase()

            zoom=1.25
            
            dim_zy, dim_zx = image_resized.shape[0], image_resized.shape[1]

            dim_zx=int(zoom*dim_zx)
            dim_zy=int(zoom*dim_zy)
            offset=abs(zoom-1)*(dim_sy//2)

        
            image_resized = cv2.resize(img_sp, (dim_zx,dim_zy), interpolation = cv2.INTER_AREA)
            with io.BytesIO() as output:
                image = Image.fromarray(image_resized)
                image.save(output, format="PNG")
                out = output.getvalue()
            sun_sp_viewport.DrawImage(data=out, location=(sx0,sy0))
            dy0=int((dy0+offset)*zoom)
            #dx0=-300
            sun_sp_viewport.move(dx0,dy0)
            #zoom_tot=zoom_tot*zoom
            
        else:
            print ('image plus grande que 8000 pixels')
    
    if event=='MouseWheel:Up':  # dezoome
        
        if dim_zx >=200:
            sun_sp_viewport.erase()
            #dim_zx=dim_zx-step_zoom
            #r_zp=dim_zx/iw
            #dim_zy=int(r_zp*ih)
            zoom=0.8
            
            dim_zy, dim_zx = image_resized.shape[0], image_resized.shape[1]
            
            dim_zx=int(zoom*dim_zx)
            dim_zy=int(zoom*dim_zy)
            
            offset=abs(zoom-1)*(dim_sy//2)

        else:
            sx0=0
            sy0=dim_sy
            sun_sp_viewport.erase()
            
        try :
            image_resized = cv2.resize(img_sp, (dim_zx,dim_zy), interpolation = cv2.INTER_AREA)
            with io.BytesIO() as output:
                image = Image.fromarray(image_resized)
                image.save(output, format="PNG")
                out = output.getvalue()
            sun_sp_viewport.DrawImage(data=out, location=(sx0,sy0))
            dy0=int((dy0-offset)*zoom)
            #dx0=-300
            sun_sp_viewport.move(dx0,dy0)
            #zoom_tot=zoom_tot*zoom

        except :
            pass

            
    if event == 'Reset' :
        sx0 = 0
        sy0 = dim_sy
        dx0=0
        dy0=0
        #zoom_tot=1
        #dim_zx=dim_sx
        sun_sp_viewport.erase()
        image_resized = cv2.resize(img_sp, (int(iw*r_sp),int(ih*r_sp)), interpolation = cv2.INTER_AREA)
        with io.BytesIO() as output:
            image = Image.fromarray(image_resized)
            image.save(output, format="PNG")
            sp_out = output.getvalue()
        sun_sp_viewport.change_coordinates((0, 0),(dim_sx, dim_sy))
        sun_sp_viewport.DrawImage(data=sp_out, location=(sx0,sy0))
    
    if event == 'Zoom 1:1' :
        sx0 = 0
        sy0 = dim_sy

        sun_sp_viewport.erase()
        dim_zy, dim_zx = image_resized.shape[0], image_resized.shape[1]
        
        zoom= iw/dim_zx  # facteur multiplicatif pour mettre image_resized a iw, ih

        #img_resized = cv2.resize(img_sp, (int(iw*r_sp),int(ih*r_sp)), interpolation = cv2.INTER_AREA)
        image_resized= np.copy (img_sp)
        with io.BytesIO() as output:
            image = Image.fromarray(image_resized)
            image.save(output, format="PNG")
            sp_out = output.getvalue()
        #zoom=1.512/zoom_tot
        print('z ', zoom)
        #dim_zx=int(zoom*dim_zx)
        #dim_zy=int(zoom*dim_zy)
        offset=abs(zoom-1)*(dim_sy//2)
        sun_sp_viewport.DrawImage(data=sp_out, location=(sx0,sy0))

        #sun_sp_viewport.move(dx0,int((dy0+offset)*zoom))
        #dx0=-300
        if zoom>1 :
            dy0=int((dy0+offset)*zoom)
        else:
            dy0=int((dy0-offset)*zoom)
        
        sun_sp_viewport.move(dx0,dy0)
        #zoom_tot=1.512

window.close()


