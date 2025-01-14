from tkinter import *
import numpy as np
import cv2
from AnimalTA.A_General_tools import Class_Scroll_crop, Function_draw_mask as Dr, Video_loader as VL, UserMessages, Color_settings, Message_simple_question as MsgBox
import time
import PIL.Image, PIL.ImageTk
import psutil
import os
import math
from PIL import ImageFont, ImageDraw, Image

class Lecteur(Frame):
    """
    A class inherited from TkFrame that will contain the video reader.
    It allows to visualize the video, zoom in/out, move in the video time space (with a time-bar) and interact with its
    containers (higher level classes) through bindings on the image canvas.
    """

    def __init__(self, parent, Vid, ecart=0, show_cropped=True, show_whole_frame=False, **kwargs):
        Frame.__init__(self, parent, bd=5, **kwargs)
        self.parent=parent #The container of the Video Reader
        self.Vid=Vid #The Video to be displayed
        self.ecart=ecart #How much visible frame we add before and after the beginning/end of the cropped video
        self.show_cropped=show_cropped#Should we present the time after cropping from 0 or from the real time
        self.first=True #Just a flag to initiate the Video Reader
        self.config(borderwidth=0, highlightthickness=0,**Color_settings.My_colors.Frame_Base)
        self.show_whole_frame=show_whole_frame

        #Impotrt the language settings
        self.Language = StringVar()
        f = open(UserMessages.resource_path(UserMessages.resource_path(os.path.join("AnimalTA","Files","Language"))), "r", encoding="utf-8")
        self.Language.set(f.read())
        self.LanguageO = self.Language.get()
        self.Messages = UserMessages.Mess[self.Language.get()]
        f.close()

        self.bind("<Configure>", self.update_ratio)

        #Relative to the video:
        self.one_every = self.Vid.Frame_rate[0] / self.Vid.Frame_rate[1]
        self.current_part = 0

        if self.Vid.Frame_rate[1]>=1:
            self.fr_rate = self.Vid.Frame_rate[1]
        else:
            self.fr_rate=1

        self.wait = (1 / (self.fr_rate))
        self.to_sub = round(self.Vid.Cropped[1][0] / self.one_every)

        self.update_image(round(self.Vid.Cropped[1][0]/self.one_every), first=True)
        self.playing=False

        self.canvas_video = Canvas(self, highlightthickness=0, borderwidth=0,**Color_settings.My_colors.Frame_Base)
        self.canvas_video.grid(row=1, column=0, sticky="nsew")
        Grid.columnconfigure(self, 0, weight=1)
        Grid.rowconfigure(self, 1, weight=1)

        self.Frame_scrollbar = Frame(self,**Color_settings.My_colors.Frame_Base, bd=0, highlightthickness=0)
        self.Frame_scrollbar.grid(row=2, column=0, sticky="swe")
        Grid.columnconfigure(self.Frame_scrollbar, 0, weight=1)
        self.Scrollbar = Class_Scroll_crop.Pers_Scroll(self.Frame_scrollbar, container=self, bd=2, highlightthickness=1, relief='ridge', ecart=self.ecart, show_cropped=self.show_cropped)  #################NEWWWW
        self.Scrollbar.grid(sticky="ew")

        self.canvas_buttons = Frame(self, bd=2, highlightthickness=1, **Color_settings.My_colors.Frame_Base)
        self.canvas_buttons.grid(row=3, column=0, sticky="nsew")
        Grid.columnconfigure(self.canvas_buttons, 0, weight=1)

        # Buttons:
        self.bouton_Play = Button(self.canvas_buttons, text=self.Messages["PlayB1"], command=self.play, **Color_settings.My_colors.Button_Base)
        self.bouton_Play.grid(row=0, column=1, sticky="we")
        self.bouton_Stop = Button(self.canvas_buttons, text=self.Messages["PlayB2"], command=self.stop, **Color_settings.My_colors.Button_Base)
        self.bouton_Stop.grid(row=0, column=3, sticky="we")
        self.bouton_GTBeg = Button(self.canvas_buttons, text=self.Messages["PlayB3"], command=self.GotoBeg, **Color_settings.My_colors.Button_Base)
        self.bouton_GTBeg.grid(row=0, column=5, sticky="we")
        self.bouton_GTEnd = Button(self.canvas_buttons, text=self.Messages["PlayB4"], command=self.GotoEnd, **Color_settings.My_colors.Button_Base)
        self.bouton_GTEnd.grid(row=0, column=7, sticky="we")


        #Speed of playback
        self.speed=IntVar()
        self.speed.set(0)
        self.Speed_S = Scale(self.canvas_buttons, label=self.Messages["Control10"], variable=self.speed, from_=-10, to=100, orient=HORIZONTAL, command=self.change_speed, **Color_settings.My_colors.Scale_Base)
        self.Speed_S.grid(row=0, column=9, sticky="we")

        if self.Vid.Frame_rate[1] < 1:
            self.Speed_S.config(fg=Color_settings.My_colors.list_colors["Fg_not_valide"])

        self.canvas_buttons.grid_columnconfigure((1,3,5,7,9), weight=3, uniform="column")
        self.canvas_buttons.grid_columnconfigure((0,2,4,6,8), weight=1, uniform="column")
        self.canvas_buttons.columnconfigure(5, minsize=50)

        self.canvas_video.focus_set()
        self.check_memory_overload() #Security to avoid problems of memory overload due to the decord library (see https://github.com/dmlc/decord/issues/27)

        #For zoom:
        self.zoom_strength = 1.25
        if type(self.parent).__name__ == "Cropping":
            self.show_whole_frame=True

        if self.show_whole_frame:
            self.zoom_sq = [0, 0, self.Vid.or_shape[1], self.Vid.or_shape[0]]#We want to show the whole frames if we are in the cropping process
            self.Size=self.Vid.or_shape
        else:
            self.zoom_sq = [0, 0, self.Vid.shape[1], self.Vid.shape[0]]#If not, we show the cropped frames
            self.Size = self.Vid.shape

        self.ratio = 1#How much do we zoom in
        self.ZinSQ = [-1, ["NA", "NA"]]#used to zoom in a particular area

    def update_ratio(self, *args):
        '''Calculate the ratio between the original size of the video and the displayed image'''
        self.ratio=max((self.zoom_sq[2]-self.zoom_sq[0])/self.canvas_video.winfo_width(),(self.zoom_sq[3]-self.zoom_sq[1])/self.canvas_video.winfo_height())

    def check_memory_overload(self):
        '''Security to avoid problems of memory overload due to the decord library (see https://github.com/dmlc/decord/issues/27)'''
        self.parent.after(1000, self.check_memory_overload)
        if psutil.virtual_memory()._asdict()["percent"]>99.8:
            self.parent.End_of_window()

            question = MsgBox.Messagebox(parent=self, title=self.Messages["TError_memory"],
                                       message=self.Messages["Error_memory"], Possibilities=[self.Messages["Continue"]])
            self.wait_window(question)


    def change_speed(self, *args):
        '''Modify the playback speed by changing the time to wait between two frames. It also reinitiate the self.jump_image variable to 1 (all images are displayed by default)'''
        if self.speed.get()==0:
            self.wait=(1 / (self.fr_rate))
        elif self.speed.get()<0:
            self.wait = (1 / (self.fr_rate))*(abs(self.speed.get()))
        elif self.speed.get()>0:
            self.wait = (1 / (self.fr_rate))/(abs(self.speed.get())+1)
        self.jump_image=1


    def GotoBeg(self):
        '''Go to the beginning of the video'''
        if not self.Vid.Cropped[0]:
            new_frame=0
        else:
            new_frame=round(self.Vid.Cropped[1][0]/self.one_every)

        self.Scrollbar.active_pos = new_frame  ####NEW
        self.Scrollbar.refresh()
        self.update_image(new_frame)

    def GotoEnd(self):
        '''Go to the end of the video'''
        new_frame = round(self.Vid.Cropped[1][1]/self.one_every)

        self.Scrollbar.active_pos = new_frame  ####NEW
        self.Scrollbar.refresh()
        self.update_image(new_frame)


    def playbacks(self, *arg):
        '''Change from play to stop or reverse'''
        if self.playing:
            self.stop()
        else:
            self.play()

    def back1(self, *arg):
        '''move one frame backward'''
        if self.Scrollbar.active_pos>0 and (self.ecart==0 or (self.ecart>0 and self.Scrollbar.active_pos>self.Vid.Cropped[1][0]/self.one_every-self.ecart)) :
            self.Scrollbar.active_pos=self.Scrollbar.active_pos-1
            self.Scrollbar.refresh()

            #If the video os made of several videos
            if self.Vid.Fusion[self.current_part][0]>(self.Scrollbar.active_pos * self.one_every):
                self.current_part-=1
                self.capture = VL.Video_Loader(self.Vid, self.Vid.Fusion[self.current_part][1], not self.show_whole_frame)

            TMP_image_to_show = self.capture[int(self.Scrollbar.active_pos*self.one_every)-self.Vid.Fusion[self.current_part][0]]
            self.parent.modif_image(TMP_image_to_show)


    def move1(self, event=None, nb_fr=1, aff=True, begin=0, select=False, *arg):
        '''move one frame forward'''
        if self.Scrollbar.active_pos<(self.Vid.Frame_nb[1]-nb_fr) and (self.ecart==0 or (self.ecart > 0 and self.Scrollbar.active_pos<=(self.Vid.Cropped[1][1]/self.one_every) + self.ecart -nb_fr)):
            self.Scrollbar.active_pos+=nb_fr
            self.Scrollbar.refresh()

            if (self.Scrollbar.active_pos*self.one_every)-self.Vid.Fusion[self.current_part][0]<len(self.capture):
                TMP_image_to_show = self.capture[int(self.Scrollbar.active_pos*self.one_every)-self.Vid.Fusion[self.current_part][0]]

            else:
                self.current_part += 1
                self.capture = VL.Video_Loader(self.Vid, self.Vid.Fusion[self.current_part][1], not self.show_whole_frame)
                TMP_image_to_show = self.capture[int(self.Scrollbar.active_pos * self.one_every) - self.Vid.Fusion[self.current_part][0]]

            if select:# Only for view and correct tracks
                self.parent.selected_rows=list(range(begin,self.Scrollbar.active_pos-self.to_sub+1))
            return(self.parent.modif_image(TMP_image_to_show, aff=aff))

    def play(self, select=False, begin=0):
        # Within check that we are not outside of the video
        within = self.Scrollbar.active_pos < (self.Vid.Frame_nb[1] - 1) and (self.ecart == 0 or (
                    self.ecart > 0 and self.Scrollbar.active_pos < (
                        self.Vid.Cropped[1][1] / self.one_every) + self.ecart))
        if within:
            self.playing = True

        self.jump_image = 1
        if begin < 0: begin = 0
        while self.playing and within:  ######NEW
            duration_beg = time.time()
            within = self.Scrollbar.active_pos < (self.Vid.Frame_nb[1] - 1) and (self.ecart == 0 or (
                        self.ecart > 0 and self.Scrollbar.active_pos < (
                            self.Vid.Cropped[1][1] / self.one_every) + self.ecart))
            if (self.Scrollbar.active_pos <= (
                    self.Vid.Cropped[1][1] / self.one_every) and self.Scrollbar.active_pos + self.jump_image > (
                    self.Vid.Cropped[1][1] / self.one_every)):
                self.move1(nb_fr=round(self.Vid.Cropped[1][1] / self.one_every) - self.Scrollbar.active_pos,
                           begin=begin,
                           select=select)  # We advance from nb_fr frames, this allow to display the video at high speed by omitting frames to go faster
                self.playing = False
            elif self.Scrollbar.active_pos + self.jump_image >= (self.Vid.Cropped[1][1] / self.one_every):
                self.move1(nb_fr=self.jump_image, begin=begin,
                           select=False)  # We advance from nb_fr frames, this allow to display the video at high speed by omitting frames to go faster
            else:
                self.move1(nb_fr=self.jump_image, begin=begin,
                           select=select)  # We advance from nb_fr frames, this allow to display the video at high speed by omitting frames to go faster
            self.update()

            duration = 0
            while duration <= (self.wait * (self.jump_image) - 0.00001) and self.playing:  # To ensure that we keep the good frame rate
                duration = time.time() - duration_beg

            if duration>0:
                if duration > (self.wait * (self.jump_image) * 1.1):  # If the reading was too slow, we omit more frames
                    self.jump_image += int((duration / (self.wait * (self.jump_image)) - 1))
                elif duration < (self.wait * (self.jump_image) * 1.1) and self.jump_image > 1:  # If the reading was too fast, we omit less frames
                    self.jump_image -= max(1, int(((self.wait * (self.jump_image) / duration) - 1)))
            else:
                self.jump_image=1

            if not within:
                self.playing = False


    def stop(self):
        '''stop the video'''
        self.playing = False

    def update_image(self, frame, first=False, actual_pos=None, return_img=False):
        '''Change the currently displayed frame.
        frame=position of the frame we want to display
        first=if it is the first time this operation is done
        return_img=IF true, the function return the image without triggering image modification of the parent
        This fonction is calling another fonction that will apply the mandatory changes to the image (all kind of modifications: draw the trajectories, grayscaled, add the mask, etc).
        This second fonction is a method of the object containing this Video Reader.'''
        Which_part=0
        if len(self.Vid.Fusion)>1:#If videos were concatenated, wecdetermine which segment of the video we are interested in
            Which_part = [index for index, Fu_inf in enumerate(self.Vid.Fusion) if Fu_inf[0] <= (frame * self.one_every)][-1]#Determine in which segment of the video is the frame to be display

        if first:#If it is the first time the reader display a frame
            self.capture=VL.Video_Loader(self.Vid, self.Vid.Fusion[Which_part][1], not self.show_whole_frame)
            self.Prem_image_to_show = self.capture[int(frame * self.one_every) - self.Vid.Fusion[Which_part][0]]
            #We calculate the average pixel values (in grayscaled) and the value range for potential future light correction.
            #If there is no background, we use the first frame as a reference frame
            #If there is a background, we use the background as reference frame

            if not self.show_whole_frame:
                if self.Vid.Back[0]!=1:
                    grey = cv2.cvtColor(self.Prem_image_to_show, cv2.COLOR_BGR2GRAY)
                else:
                    grey = self.Vid.Back[1].copy()

                mask=Dr.draw_mask(self.Vid)[:, :].astype(bool)

                if self.Vid.Mask[0]:
                    grey2=grey[mask]
                else:
                    grey2=np.copy(grey)
                self.or_bright= np.sum(grey2) / (255 * grey2.size)  # Mean value

                TMP_image_to_show = np.copy(self.Prem_image_to_show)
                self.last_img=TMP_image_to_show

        else:
            if Which_part!=self.current_part:#If we are changing from one video segment to another (concatenated videos)
                del self.capture
                self.capture = VL.Video_Loader(self.Vid, self.Vid.Fusion[Which_part][1], not self.show_whole_frame)

            TMP_image_to_show = self.capture[int(frame * self.one_every) - self.Vid.Fusion[Which_part][0]]

            if not return_img:
                self.parent.modif_image(TMP_image_to_show, actual_pos=actual_pos)

        self.current_part = Which_part
        if return_img:
            return(TMP_image_to_show)


    def Zoom(self, event, Zin=True):
        '''When the user hold <Ctrl> and click on the frame, zoom on the image.
        If <Ctrl> and right click, zoom out'''
        if not bool(event.state & 0x1):
            self.new_zoom_sq = [0, 0, self.Size[1], self.Size[0]]
            event.x = int( self.ratio * (event.x - (self.canvas_video.winfo_width()-self.shape[1])/2)) + self.zoom_sq[0]
            event.y = int( self.ratio * (event.y - (self.canvas_video.winfo_height()-self.shape[0])/2)) + self.zoom_sq[1]
            PX = event.x / self.Size[1]
            PY = event.y / self.Size[0]

            if self.ZinSQ[0]<3:
                if Zin:
                    new_total_width = self.Size[1] / self.ratio * self.zoom_strength
                    new_total_height = self.Size[0] / self.ratio * self.zoom_strength
                else:
                    new_total_width = self.Size[1] / self.ratio / self.zoom_strength
                    new_total_height = self.Size[0] / self.ratio / self.zoom_strength

                if new_total_width>self.canvas_video.winfo_width():
                    missing_px=new_total_width - (self.canvas_video.winfo_width()-5)
                    ratio_old_new=self.Size[1]/new_total_width
                    self.new_zoom_sq[0] = int(PX * missing_px*ratio_old_new)
                    self.new_zoom_sq[2] = int(self.Size[1] - ((1 - PX) * missing_px*ratio_old_new))

                if new_total_height>self.canvas_video.winfo_height():
                    missing_px=new_total_height - (self.canvas_video.winfo_height()-5)
                    ratio_old_new=self.Size[0]/new_total_height
                    self.new_zoom_sq[1] = int(PY * missing_px*ratio_old_new)
                    self.new_zoom_sq[3] = int(self.Size[0] - ((1 - PY) * missing_px*ratio_old_new))

                if self.new_zoom_sq[3]-self.new_zoom_sq[1] > 50 and self.new_zoom_sq[2]-self.new_zoom_sq[0]>50:
                    self.zoom_sq = self.new_zoom_sq
                    self.update_ratio()
                    self.parent.modif_image(self.parent.last_empty)

            elif event.x>=0 and event.x<=self.Size[1] and event.y>=0 and event.y<=self.Size[0] and self.ZinSQ[1][0]>=0 and self.ZinSQ[1][0]<=self.Size[1] and self.ZinSQ[1][1]>=0 and self.ZinSQ[1][1]<=self.Size[0]:
                zoom_sq = [min(self.ZinSQ[1][0], event.x), min(self.ZinSQ[1][1], event.y) , max(self.ZinSQ[1][0], event.x), max(self.ZinSQ[1][1], event.y)]
                if (zoom_sq[2] - zoom_sq[0]) > 50 and (zoom_sq[3] - zoom_sq[1])>50:
                    self.zoom_sq=zoom_sq
                    self.update_ratio()
                    self.parent.modif_image(self.parent.last_empty)
                self.ZinSQ = [-1, ["NA", "NA"]]

            self.canvas_video.delete("Rect")


    def Sq_Zoom_beg(self, event):
        event_t_x = int( self.ratio * (event.x - (self.canvas_video.winfo_width()-self.shape[1])/2)) + self.zoom_sq[0]
        event_t_y = int( self.ratio * (event.y - (self.canvas_video.winfo_height()-self.shape[0])/2)) + self.zoom_sq[1]
        self.ZinSQ=[0,[event_t_x,event_t_y],[event.x,event.y]]
        self.canvas_video.delete("Rect")

    def Sq_Zoom_mov(self,event):
        self.canvas_video.delete("Rect")

        event_t_x = int( self.ratio * (event.x - (self.canvas_video.winfo_width()-self.shape[1])/2)) + self.zoom_sq[0]
        event_t_y = int( self.ratio * (event.y - (self.canvas_video.winfo_height()-self.shape[0])/2)) + self.zoom_sq[1]

        zoom_sq = [min(self.ZinSQ[1][0], event_t_x), min(self.ZinSQ[1][1], event_t_y), max(self.ZinSQ[1][0], event_t_x),max(self.ZinSQ[1][1], event_t_y)]
        if (zoom_sq[2] - zoom_sq[0]) > 50 and (zoom_sq[3] - zoom_sq[1])>50 and event_t_x>=0 and event_t_x<=self.Size[1] and event_t_y>=0 and event_t_y<=self.Size[0] and self.ZinSQ[1][0]>=0 and self.ZinSQ[1][0]<=self.Size[1] and self.ZinSQ[1][1]>=0 and self.ZinSQ[1][1]<=self.Size[0]:
            self.canvas_video.create_rectangle(self.ZinSQ[2][0], self.ZinSQ[2][1], event.x, event.y, outline="white", tags="Rect")
        else:
            self.canvas_video.create_rectangle(self.ZinSQ[2][0], self.ZinSQ[2][1], event.x, event.y, outline="red", tags="Rect")
        self.canvas_video.create_rectangle(self.ZinSQ[2][0],self.ZinSQ[2][1],event.x,event.y, dash=(3,3), outline="black", tags="Rect")

        if self.ZinSQ[0]>=0:
            self.ZinSQ[0]+=1



    def bindings(self):
        '''Make all the bindings'''
        self.bind_all("<Right>", self.move1)
        self.bind_all("<Left>", self.back1)
        self.bind_all("<space>", self.playbacks)
        self.canvas_video.bind("<Control-B1-Motion>", self.Sq_Zoom_mov)
        self.canvas_video.bind("<Control-B1-ButtonRelease>", lambda x: self.Zoom(event=x,Zin=True))
        self.canvas_video.bind("<Control-B3-ButtonRelease>", lambda x: self.Zoom(event=x,Zin=False))
        self.canvas_video.bind("<Configure>", lambda x: self.afficher_img(self.last_img))
        self.Frame_scrollbar.bind("<Configure>", self.Scrollbar.refresh)

        self.canvas_video.bind("<Shift-B1-Motion>", lambda x: self.callback_move(event=x,Shift=True))
        self.canvas_video.bind("<B1-Motion>", self.callback_move)
        self.canvas_video.bind("<Motion>", self.mouse_over)
        self.canvas_video.bind("<ButtonRelease>", self.release)
        self.canvas_video.bind("<Button-3>", self.right_click)
        self.canvas_video.bind("<Button-1>", self.callback)

    def unbindings(self):
        '''Remove all the bindings'''
        try:
            self.unbind_all("<Right>")
            self.unbind_all("<Left>")
            self.unbind_all("<space>")
            self.Frame_scrollbar.unbind("<Configure>")

            self.canvas_video.unbind("<Control-1>")
            self.canvas_video.unbind("<Control-3>")
            self.canvas_video.unbind("<Shift-1>")
            self.canvas_video.unbind("<Configure>")

            self.canvas_video.unbind("<Motion>")
            self.canvas_video.unbind("<Button-1>")
            self.canvas_video.unbind("<B1-Motion>")
            self.canvas_video.unbind("<ButtonRelease>")

        except:
            pass

    def mouse_over(self, event):
        try:
            event.x = int( self.ratio * (event.x - (self.canvas_video.winfo_width()-self.shape[1])/2)) + self.zoom_sq[0]
            event.y = int( self.ratio * (event.y - (self.canvas_video.winfo_height()-self.shape[0])/2)) + self.zoom_sq[1]
            self.parent.mouse_over([event.x,event.y])
        except:
            pass

    def callback(self, event):
        '''When we press on the frame, the info about where the frame was clicked is sent to the Video Reader container'''
        if not bool(event.state & 0x1) and bool(event.state & 0x4):
            self.Sq_Zoom_beg(event)

        else:
            event.x = int( self.ratio * (event.x - (self.canvas_video.winfo_width()-self.shape[1])/2)) + self.zoom_sq[0]
            event.y = int( self.ratio * (event.y - (self.canvas_video.winfo_height()-self.shape[0])/2)) + self.zoom_sq[1]
            self.parent.pressed_can((event.x,event.y), event)

    def callback_move(self, event, Shift=False, *args):
        '''The info about where the frame was clicked is sent to the Video Reader container'''
        event.x = self.ratio * (event.x - (self.canvas_video.winfo_width()-self.shape[1])/2) + self.zoom_sq[0]
        event.y = self.ratio * (event.y - (self.canvas_video.winfo_height()-self.shape[0])/2) + self.zoom_sq[1]

        if event.x<0:
            event.x=0

        if event.y < 0:
            event.y=0

        if event.x>=self.Size[1]:
            event.x=self.Size[1]

        if event.y >= self.Size[0]:
            event.y = self.Size[0]

        self.parent.moved_can((event.x,event.y), Shift)

    def right_click(self, event):
        if not (event.state & 0x4):
            '''The info about where the frame was clicked is sent to the Video Reader container'''
            event.x = self.ratio * (event.x - (self.canvas_video.winfo_width()-self.shape[1])/2) + self.zoom_sq[0]
            event.y = self.ratio * (event.y - (self.canvas_video.winfo_height()-self.shape[0])/2) + self.zoom_sq[1]
            if  event.x >= 0 and event.y >= 0 and event.x <= self.Size[1] and event.y <= self.Size[0]:
                self.parent.right_click((event.x,event.y))

    def release(self, event):
        '''The info about where the frame was clicked is sent to the Video Reader container'''
        event.x = self.ratio * (event.x - (self.canvas_video.winfo_width()-self.shape[1])/2) + self.zoom_sq[0]
        event.y = self.ratio * (event.y - (self.canvas_video.winfo_height()-self.shape[0])/2) + self.zoom_sq[1]
        self.parent.released_can((event.x,event.y))

    def afficher_img(self, img, locked=False):
        '''Once the image is adapted by the video container, it is here resized and displayed'''
        self.update_ratio()
        self.last_img=img
        if self.first:
            self.first=False

        if not self.Size==img.shape:
            self.Size = img.shape
            self.zoom_sq = [0, 0, self.Size[1], self.Size[0]]  # If not, we show the cropped frames


        image_to_show2 = img[self.zoom_sq[1]:self.zoom_sq[3], self.zoom_sq[0]:self.zoom_sq[2]]
        width=int((self.zoom_sq[2]-self.zoom_sq[0])/self.ratio)
        height=int((self.zoom_sq[3]-self.zoom_sq[1])/self.ratio)

        TMP_image_to_show2 = cv2.resize(image_to_show2,(width, height))
        self.shape= TMP_image_to_show2.shape

        if self.Scrollbar.active_pos<self.Scrollbar.crop_beg or self.Scrollbar.active_pos>self.Scrollbar.crop_end:
            #If we are outside of the cropped parts, we apply a black veil on the image
            img2= cv2.add(TMP_image_to_show2,np.array([-75.0]))
        else:
            img2=TMP_image_to_show2

        if locked:
            fontpath = os.path.join(".", "simsun.ttc")
            font = ImageFont.truetype(fontpath, 20)
            stroke_width = 2
            first_im = Image.fromarray(img2)
            draw = ImageDraw.Draw(first_im)
            draw.text((TMP_image_to_show2.shape[1] - 40,TMP_image_to_show2.shape[0] - 25), "[○]", font=font, fill=(255, 255, 255, 0), stroke_width=stroke_width)
            draw.text((TMP_image_to_show2.shape[1] - 40,TMP_image_to_show2.shape[0] - 25), "[○]", font=font, fill=(0, 0, 0, 0))
            img2 = np.array(first_im)


        self.image_to_show3 = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(img2))
        self.can_import = self.canvas_video.create_image((self.canvas_video.winfo_width()-self.shape[1])/2, (self.canvas_video.winfo_height()-self.shape[0])/2, image=self.image_to_show3, anchor=NW)
        self.canvas_video.config(height=self.shape[1],width=self.shape[0])
        self.canvas_video.itemconfig(self.can_import, image=self.image_to_show3)
        self.update_idletasks()

    def proper_close(self):
        '''Destruction of the Video Reader'''
        self.unbindings()
        del self.capture
        self.stop()
        self.Scrollbar.close_N_destroy()
        self.Scrollbar.destroy()
