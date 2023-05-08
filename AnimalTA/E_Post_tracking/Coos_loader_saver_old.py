import os
import csv
import numpy as np

def load_coos(Vid, TMP=False):
    # Importation of the coordinates associated with the current video
    if Vid.User_Name == Vid.Name:
        file_name = Vid.Name
        point_pos = file_name.rfind(".")
        if file_name[point_pos:].lower()!=".avi":#Old versions of AnimalTA did not allow to rename or duplicate the videos, the name of the video was the file name without the ".avi" extension
            file_name = Vid.User_Name
        else:
            file_name = file_name[:point_pos]
    else:
        file_name = Vid.User_Name

    if not TMP:
        file_tracked_not_corr = os.path.join(Vid.Folder, "coordinates", file_name + "_Coordinates.csv")
        file_tracked_corr = os.path.join(Vid.Folder, "corrected_coordinates", file_name + "_Corrected.csv")
    else:
        file_tracked_corr = os.path.join(Vid.Folder, "TMP_portion", file_name + "_TMP_portion_Coordinates.csv")

    if os.path.isfile(file_tracked_corr):
        path = file_tracked_corr
    else:
        path = file_tracked_not_corr

    try:#Old versions of AnimalTA did not had the possibility to have a variable number of targets, this is to avoid compatibility problems
        if Vid.Track[1][8]:
            return load_fixed(Vid, path)
        else:
            return load_variable(Vid, path)
    except:
        Vid.Track[1].append(False)



def save(Vid, Coos, TMP=False):
    # Save the coordinates associated with the current video
    if Vid.User_Name == Vid.Name:
        file_name = Vid.Name
        point_pos = file_name.rfind(".")
        if file_name[point_pos:].lower()!=".avi":#Old versions of AnimalTA did not allow to rename or duplicate the videos, the name of the video was the file name without the ".avi" extension
            file_name = Vid.User_Name
        else:
            file_name = file_name[:point_pos]
    else:
        file_name = Vid.User_Name

    if not TMP:
        if not os.path.isdir(os.path.join(Vid.Folder, "corrected_coordinates")):
            os.makedirs(os.path.join(Vid.Folder,"corrected_coordinates"))
        path = os.path.join(Vid.Folder, "corrected_coordinates", file_name + "_Corrected.csv")
    else:
        if not os.path.isdir(os.path.join(Vid.Folder + "TMP_portion")):
            os.makedirs(os.path.join(Vid.Folder + "TMP_portion"))
        path = os.path.join(Vid.Folder, "TMP_portion", file_name + "_TMP_portion_Coordinates.csv")

    if os.path.isfile(path):
        path = path

    if Vid.Track[1][8]:
        save_fixed(Vid, Coos, path)
    else:
        save_variable(Vid, Coos, path)


def load_variable(Vid, path):
    Coos = []
    one_every=int(round(round(Vid.Frame_rate[0], 2) / Vid.Frame_rate[1]))
    with open(path, encoding="utf-8") as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=";")
        or_table = list(csv_reader)

    for ind in range(len(Vid.Identities)):
        print(ind)
        Ind_Coos = np.array([["NA", "NA"]] * (int((Vid.Cropped[1][1] - Vid.Cropped[1][0])/one_every) + 1), dtype="object")
        Coos.append(Ind_Coos)

    Coos = np.array(Coos, dtype=np.object)
    or_table = np.array(or_table)

    who_is_here = [[] for x in range(int((Vid.Cropped[1][1] - Vid.Cropped[1][0])/one_every) + 1)]

    count = 0
    for Ind in Vid.Identities:
        print(Ind)
        subset = or_table[np.where((np.array(or_table[:, 2]) == str(Ind[0])) & (np.array(or_table[:, 3]) == str(Ind[1][3:])))]
        if len(subset)>0:
            time = subset[:, 0].astype('float')
            time = time.astype('int32')
            time=time-int(Vid.Cropped[1][0]/one_every)
            T_Coos = subset[:, 4:6].tolist()
            Coos[count, time] = T_Coos
            for im in time:
                who_is_here[im] = who_is_here[im] + [count]
            count += 1

    return(Coos, who_is_here)


def load_fixed(Vid, path):
    Coos = []
    with open(path, encoding="utf-8") as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=";")
        or_table = list(csv_reader)
    or_table = np.array(or_table)

    for Ind in range(len(Vid.Identities)):
        Ind_Coos = or_table[1:,2*Ind+2:2*Ind+4].tolist()
        Coos.append(Ind_Coos)
    return (Coos, [list(range(len(Vid.Identities)))]*len(Ind_Coos))

def save_fixed(Vid, Coos, path):
    Coos=np.array(Coos)
    one_every=int(round(round(Vid.Frame_rate[0], 2) / Vid.Frame_rate[1]))
    General_Coos=np.zeros([Coos.shape[1]+1,Coos.shape[2]*Coos.shape[0]+2], dtype="object")
    General_Coos[1:,0]=list(range(Vid.Cropped[1][0],Vid.Cropped[1][1]+one_every,one_every))
    tmp=np.array(General_Coos[1:, 0]/one_every/Vid.Frame_rate[1], dtype="float")
    General_Coos[1:, 1]=np.around(tmp,2)
    General_Coos[0,:]=["Frame","Time"]+[Col+"_Arena"+str(ind[0])+"_"+str(ind[1]) for ind in Vid.Identities for Col in ["X","Y"]]
    for Ind in range(Coos.shape[0]):
        General_Coos[1:,Ind*2+2:Ind*2+2+2]=Coos[Ind]

    np.savetxt(path, General_Coos, delimiter=';', encoding="utf-8", fmt='%s')



def save_variable(Vid, Coos, path):
    Coos=np.array(Coos)
    one_every = int(round(round(Vid.Frame_rate[0], 2) / Vid.Frame_rate[1]))
    Pos=np.where(Coos[:,:,0]!="NA")
    new_Coos=Coos[Pos[0],Pos[1]]
    Ars=[Vid.Identities[P][0] for P in Pos[0]]
    Inds = [Vid.Identities[P][1][3:] for P in Pos[0]]

    new_Coos=np.vstack((Pos[1]+int(Vid.Cropped[1][0]/one_every),(Pos[1]+int(Vid.Cropped[1][0])/one_every)/Vid.Frame_rate[1], Ars, Inds, new_Coos[:,0], new_Coos[:,1])).T
    new_Coos=new_Coos[new_Coos[:,0].astype(float).argsort(),:]
    first_row = ["Frame", "Time", "Arena", "Ind", "X", "Y"]
    new_Coos=np.vstack([first_row, new_Coos])
    np.savetxt(path, new_Coos, delimiter=';', encoding="utf-8", fmt='%s')