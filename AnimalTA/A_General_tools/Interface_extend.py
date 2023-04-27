from tkinter import *
import os
from AnimalTA.A_General_tools import Function_draw_mask, UserMessages, Class_stabilise
import math
import cv2
from copy import deepcopy
from tkinter import messagebox

class Extend(Frame):
    """ This Frame display a list of the videos from the project.
    The user can select some of them to extend some parameters defined for the previously selected video"""
    def __init__(self, parent, boss, value, Video_file, type=None, do_self=False, **kwargs):
        #value=the value of the parameter
        #type= the type of parameter (arenas, fps, tracking preparation, etc)
        #if do_self = True, the selected video will also be modified
        Frame.__init__(self, parent, bd=5, **kwargs)
        self.parent=parent
        self.boss=boss
        self.boss.unbind_all("<MouseWheel>")#We don't want the mouse wheel to move the project behind
        self.grid(sticky="nsew")
        self.Vid = Video_file
        self.type=type
        self.list_vid=self.boss.liste_of_videos
        self.do_self=do_self
        self.value=value
        self.all_sel=False

        #Import messages
        self.Language = StringVar()
        f = open(UserMessages.resource_path(os.path.join("AnimalTA","Files","Language")), "r", encoding="utf-8")
        self.Language.set(f.read())
        self.LanguageO = self.Language.get()
        f.close()

        Grid.columnconfigure(self.parent, 0, weight=1)  ########NEW
        Grid.rowconfigure(self.parent, 0, weight=1)  ########NEW

        self.Messages = UserMessages.Mess[self.Language.get()]
        self.winfo_toplevel().title(self.Messages["Extend1"] + " "+ self.Messages[type])

        #This button allows to directly select/unselect all the videos from the list
        self.sel_state=StringVar()
        self.sel_state.set(self.Messages["ExtendB1"])
        self.bouton_sel_all=Button(self,textvariable=self.sel_state,command=self.select_all)
        self.bouton_sel_all.grid(row=0,columnspan=2, sticky="nsew")

        #Navigate throught the list
        self.yscrollbar = Scrollbar(self)
        self.yscrollbar.grid(row=1,column=1, sticky="ns")
        self.Liste=Listbox(self, selectmode = EXTENDED, width=100, yscrollcommand=self.yscrollbar.set)

        #To validate and share the parameters
        self.bouton=Button(self,text=self.Messages["Validate"],command=self.validate)
        self.bouton.grid(row=2, sticky="nsew")
        self.yscrollbar.config(command=self.Liste.yview)

        #Progression time-bar to show the loading
        self.loading_canvas=Frame(self)
        self.loading_state=Label(self.loading_canvas, text="")
        self.loading_state.grid(row=0, column=0)

        self.loading_bar=Canvas(self.loading_canvas, height=10)
        self.loading_bar.create_rectangle(0, 0, 400, self.loading_bar.cget("height"), fill="red")
        self.loading_bar.grid(row=0, column=1)

        #We add all the videos
        self.list_vid_minus=[]
        for i in range(len(self.list_vid)):
            if self.list_vid[i]!=self.Vid or self.do_self:
                #The untracked videos will not be displayed if we want to share analyses parameters
                if not (type=="analyses_smooth" or type=="analyses_thresh" or type=="analyses_explo" or type=="analyses_inter" or type=="analyses_deform") or (self.list_vid[i].Tracked):
                    self.list_vid_minus.append(self.list_vid[i])
                    self.Liste.insert(i, self.list_vid[i].User_Name)
                    if self.list_vid[i].Tracked and not (type=="analyses_smooth" or type=="analyses_thresh" or type=="analyses_explo" or type=="analyses_inter" or type=="analyses_deform"):
                        self.Liste.itemconfig(self.Liste.size()-1, {'fg': 'red'})
                        #The tracked videos will appear in red if they were already tracked (except for changes in analyses parameters).
                        #Indeed, changing a parameter of these videos will remove the trackings.

        self.Liste.grid(row=1,column=0, sticky="nsew")

        Grid.columnconfigure(self, 0, weight=1)  ########NEW
        Grid.rowconfigure(self, 0, weight=1)  ########NEW
        Grid.rowconfigure(self, 1, weight=100)  ########NEW
        Grid.rowconfigure(self, 2, weight=1)  ########NEW

        self.grab_set()
        self.parent.protocol("WM_DELETE_WINDOW", self.rebind)

    def select_all(self):
        if not self.all_sel: #Select all the videos from the list
            self.Liste.select_set(0, END)
            self.sel_state.set(self.Messages["ExtendB2"])
            self.all_sel=True
        else: #Unselect all the videos from the list
            self.Liste.selection_clear(0, END)
            self.sel_state.set(self.Messages["ExtendB1"])
            self.all_sel=False

    def validate(self):
        #Apply the parameters to the selected videos and close the window
        if self.type=="back" or self.type=="stab": #There is only in the case of background that the process is slow (we don't show loading bar for other kind of parameters).
            self.loading_canvas.grid(row=3, column=0, columnspan=2)

        list_item = self.Liste.curselection()
        nb_items=len(list_item)
        item=0
        problems = []  # A list of problematic videos (i.e. of the spatial or temporal corpping asked are outside of the video duration/size)
        for V in list_item:
            #If the tracking parameters were changed we remove the existing trackings
            cleared=True
            if self.list_vid_minus[V].Tracked and self.type!="analyses_smooth" and self.type!="analyses_thresh" and self.type!="analyses_explo" and self.type!="analyses_inter" and self.type!="analyses_deform":
                cleared=self.list_vid_minus[V].clear_files()
                self.list_vid_minus[V].Tracked = False
            if cleared:
                if self.type == "scale":
                    self.list_vid_minus[V].Scale[0] = self.value[0]
                    self.list_vid_minus[V].Scale[1] = self.value[1]
                elif self.type == "mask":
                    self.list_vid_minus[V].Mask[0] = 1
                    self.list_vid_minus[V].Mask[1] = deepcopy(self.value)
                elif self.type == "track":
                    self.list_vid_minus[V].Track[0] = 1
                    mask = Function_draw_mask.draw_mask(self.list_vid_minus[V])
                    Arenas, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    nb_ar = len(Arenas)
                    self.list_vid_minus[V].Track[1] = deepcopy(self.value)
                    self.list_vid_minus[V].Track[1][6] = deepcopy(self.value)[6][0:nb_ar]

                elif self.type == "fps":
                    if self.list_vid_minus[V].Frame_rate[1] != self.list_vid_minus[V].Frame_rate[0] / self.value:
                        self.list_vid_minus[V].Frame_rate[1] = self.list_vid_minus[V].Frame_rate[0] / self.value
                        self.list_vid_minus[V].Frame_nb[1] = math.floor(self.list_vid_minus[V].Frame_nb[0] / round(
                            self.list_vid_minus[V].Frame_rate[0] / self.list_vid_minus[V].Frame_rate[1]))  ######NEW

                elif self.type == "stab":
                    self.loading_bar.delete('all')
                    heigh = self.loading_bar.cget("height")
                    self.bouton.config(state="disable")
                    self.loading_bar.create_rectangle(0, 0, 400, heigh, fill="red")
                    self.loading_bar.create_rectangle(0, 0, ((item + 1) / nb_items) * 400, heigh, fill="blue")
                    self.loading_bar.update()
                    self.loading_state.config(
                        text=self.Messages["Video"] + ": {act}/{tot}".format(act=item + 1, tot=nb_items))
                    self.list_vid_minus[V].make_back()

                    self.list_vid_minus[V].Stab[0] = self.value[0]
                    self.list_vid_minus[V].Stab[2] = self.value[2].copy()

                    Which_part = [index for index, Fu_inf in enumerate(self.list_vid_minus[V].Fusion) if Fu_inf[0] <= self.list_vid_minus[V].Cropped[1][0]][-1]
                    Capture = cv2.VideoCapture(self.list_vid_minus[V].Fusion[Which_part][1])

                    Capture.set(cv2.CAP_PROP_POS_FRAMES, int(self.list_vid_minus[V].Cropped[1][0] - self.list_vid_minus[V].Fusion[Which_part][0]))
                    _, Prem_im=Capture.read()
                    if self.list_vid_minus[V].Cropped_sp[0]:
                        Prem_im = Prem_im[self.list_vid_minus[V].Cropped_sp[1][0]:self.list_vid_minus[V].Cropped_sp[1][2],self.list_vid_minus[V].Cropped_sp[1][1]:self.list_vid_minus[V].Cropped_sp[1][3]]
                    Capture.release()
                    self.list_vid_minus[V].Stab[1] = Class_stabilise.find_pts(self.list_vid_minus[V], Prem_im,
                                                                minDistance=self.list_vid_minus[V].Stab[2][0], blockSize=self.list_vid_minus[V].Stab[2][1],
                                                                quality=self.list_vid_minus[V].Stab[2][2], maxCorners=self.list_vid_minus[V].Stab[2][3])


                elif self.type == "crop":
                    if self.value[0][0]:
                        one_every = int(round(round(self.list_vid_minus[V].Frame_rate[0], 2) / self.list_vid_minus[V].Frame_rate[1]))
                        if self.value[0][1][0]<=self.list_vid_minus[V].Frame_nb[0]-1:
                            self.list_vid_minus[V].Cropped[0]=True
                            self.list_vid_minus[V].Cropped[1][0] = int(math.floor(self.value[0][1][0] / one_every) * one_every)
                        else:
                            problems.append([V,True])

                        if self.value[0][1][1] <= self.list_vid_minus[V].Frame_nb[0]-1:
                            self.list_vid_minus[V].Cropped[1][1] = int(math.floor(self.value[0][1][1] / one_every) * one_every)  # Avoid to try to open un-existing frames after changes in frame-rate

                        else:
                            self.list_vid_minus[V].Cropped[1][1]=self.list_vid_minus[V].Frame_nb[0]-1
                            problems.append([V,True])
                    else:
                        self.list_vid_minus[V].Cropped=[False,[0,self.list_vid_minus[V].Frame_nb[0]-1]]

                    if self.value[1][0]:
                        if self.value[1][1][0] < self.list_vid_minus[V].or_shape[0]:
                            self.list_vid_minus[V].Cropped_sp[1][0] = self.value[1][1][0]
                        else:
                            problems.append([V,False])

                        if self.value[1][1][1] < self.list_vid_minus[V].or_shape[1]:
                            self.list_vid_minus[V].Cropped_sp[0] = True
                            self.list_vid_minus[V].Cropped_sp[1][1] = self.value[1][1][1]
                        else:
                            problems.append([V,False])

                        if self.value[1][1][2] <= self.list_vid_minus[V].or_shape[0]:
                            self.list_vid_minus[V].Cropped_sp[0] = True
                            self.list_vid_minus[V].Cropped_sp[1][2] = self.value[1][1][2]
                        else:
                            self.list_vid_minus[V].Cropped_sp[1][2] = self.list_vid_minus[V].or_shape[0]
                            problems.append([V,False])

                        if self.value[1][1][3] <= self.list_vid_minus[V].or_shape[1]:
                            self.list_vid_minus[V].Cropped_sp[0] = True
                            self.list_vid_minus[V].Cropped_sp[1][3] = self.value[1][1][3]
                        else:
                            self.list_vid_minus[V].Cropped_sp[1][3] = self.list_vid_minus[V].or_shape[1]
                            problems.append([V,False])
                    else:
                        self.list_vid_minus[V].Cropped_sp= [False,[0,0,self.list_vid_minus[V].or_shape[0],self.list_vid_minus[V].or_shape[1]]]

                    if self.list_vid_minus[V].Cropped[1][1] == self.list_vid_minus[V].Frame_nb[0] - 1 and self.list_vid_minus[V].Cropped[1][0] == 0:
                        self.list_vid_minus[V].Cropped[0]=False
                    else:
                        self.list_vid_minus[V].Cropped[0]=True

                    if self.list_vid_minus[V].Cropped_sp[1] == [0,0,self.list_vid_minus[V].or_shape[0],self.list_vid_minus[V].or_shape[1]]:
                        self.list_vid_minus[V].Cropped_sp[0]=False
                    else:
                        self.list_vid_minus[V].Cropped_sp[0]=True

                    if self.list_vid_minus[V].Cropped_sp[0]:
                        new_shape=(self.list_vid_minus[V].Cropped_sp[1][2] - self.list_vid_minus[V].Cropped_sp[1][0],self.list_vid_minus[V].Cropped_sp[1][3] - self.list_vid_minus[V].Cropped_sp[1][1])
                        if self.list_vid_minus[V].shape!=new_shape:
                            self.list_vid_minus[V].Back = [False, []]
                            self.list_vid_minus[V].Track[1][6] = [1]
                            self.list_vid_minus[V].Mask[0] = False
                        self.list_vid_minus[V].shape=(self.list_vid_minus[V].Cropped_sp[1][2] - self.list_vid_minus[V].Cropped_sp[1][0],self.list_vid_minus[V].Cropped_sp[1][3] - self.list_vid_minus[V].Cropped_sp[1][1])


                elif self.type == "back":
                    self.loading_bar.delete('all')
                    heigh = self.loading_bar.cget("height")
                    self.bouton.config(state="disable")
                    self.loading_bar.create_rectangle(0, 0, 400, heigh, fill="red")
                    self.loading_bar.create_rectangle(0, 0, ((item + 1) / nb_items) * 400, heigh, fill="blue")
                    self.loading_bar.update()
                    self.loading_state.config(
                        text=self.Messages["Video"] + ": {act}/{tot}".format(act=item + 1, tot=nb_items))
                    self.list_vid_minus[V].make_back()

                elif self.type == "analyses_smooth":
                    if self.list_vid_minus[V].Tracked:
                        self.list_vid_minus[V].Smoothed = deepcopy(self.value)

                elif self.type == "analyses_thresh":
                    if self.list_vid_minus[V].Tracked:
                        self.list_vid_minus[V].Analyses[0] = deepcopy(self.value)

                elif self.type == "analyses_explo":
                    if self.list_vid_minus[V].Tracked:
                        self.list_vid_minus[V].Analyses[2] = deepcopy(self.value)

                elif self.type == "analyses_inter":
                    if self.list_vid_minus[V].Tracked:
                        if len(self.list_vid_minus[V].Analyses) < 4:
                            self.list_vid_minus[V].Analyses.append(0)
                        self.list_vid_minus[V].Analyses[3] = deepcopy(self.value)

                elif self.type == "analyses_deform":
                    if self.list_vid_minus[V].Tracked:
                        self.list_vid_minus[V].Analyses[4] = deepcopy(self.value)


            item+=1
        if len(problems)>0:
            Time=[]
            Size=[]
            for Pb in problems:
                if Pb[1]:
                    if self.list_vid_minus[Pb[0]].User_Name not in Time:
                        Time.append(self.list_vid_minus[Pb[0]].User_Name)
                else:
                    if self.list_vid_minus[Pb[0]].User_Name not in Size:
                        Size.append(self.list_vid_minus[Pb[0]].User_Name)

            Message=""
            if len(Time)>0:
                Message=Message+"The following videos were not cropped as asked because their duration is shorter than expected cropping:\n" + str(", ".join(Time))
                if len(Size)>0:
                    Message=Message+"\n \n"

            if len(Size) > 0:
                Message=Message+"The following videos were not cropped as asked because their size is smaller than expected cropping:\n" + str(", ".join(Size))

            messagebox.showwarning("Some videos have not been normally processed",Message)


        self.boss.update_projects()
        self.boss.bind_all("<MouseWheel>", self.boss.on_mousewheel)
        self.parent.destroy()

    def rebind(self):
        self.parent.destroy()
        self.boss.bind_all("<MouseWheel>", self.boss.on_mousewheel)

"""
root = Tk()
root.geometry("+100+100")
Video_file=Class_Video.Video(File_name="D:/Post-doc/Experiments/Group_composition/Shoaling/Videos_conv_cut/Track_by_mark/Deinterlace/14_12_01.avi")
Video_file.Back[0]=True

im=cv2.imread("D:/Post-doc/Experiments/Group_composition/Shoaling/Videos_conv_cut/Track_by_mark/Deinterlace/14_12_01_background.bmp")
im=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)
Video_file.Back[1]=im
interface = Scale(parent=root, boss=None, Video_file=Video_file)
root.mainloop()
"""