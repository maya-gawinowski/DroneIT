# ------------------------------------------------------------------------------
#!/etc/Python3.1

#autheur : Maya Gawinowski, Gaëtan Lodde, Guénaël Chabraison

#date : 26/02/2020

#Programme : Drone IT!

#Version : 2.0

# ------------------------------------------------------------------------------

# IMPORT

import PIL.Image

import PIL.ImageTk



from tkinter import*

from tkinter import messagebox

import tkinter.font as tkFont

import mysql.connector as mariadb

from math import*

from datetime import datetime

from time import strftime

import threading

import time

# librairie du drone Parrot (modele Mambo)
from pyparrot.Minidrone import Mambo



#--------------------------------------------------------------------------------

# Adresse blutooth du drone mambo
MamboAddr = "D0:3A:CC:69:E6:3A"

# etat activation du drone
DroneOn = 1


# Bornes du graphe (Ligne/Colonne) dimension 5x5 metres
Borne_L_min = 0
Borne_L_max = 4
Borne_C_min = 0
Borne_C_max = 4


# nombre de maille sur une colonne/ligne = 5
Maille = Borne_C_max+1

# nombre de sommets du graphe
NombreSommet=Maille * Maille # correspond au nombre de sommets de la MNT



# Cette variable represente la distance en pixel entre 2 sommets
EcartPixel = 100

# Ces variables represente l'offset de la fenetre du graphe par rapport à l'ecran de l'ordinateur
Offset_x = 100
Offset_y = 100

# nombre de sommets selectionnés avec la souris
NbSelectedPoint = 0

# sommet courant selectionné
SommetCourant = 0

# un action stop (pause du drone en vol stationnaire est en cours)
ActionStop = 0

# Sommet selectionné lors d'un premier clic souris
P1=0

# Sommet selectionné lors d'un premier clic souris
P2=0

# etat du feu rouge (vert, orange, rouge)
FeuRouge = 0

# valeur des points a retirer du permis selon infraction (stop, feu rouge, sens interdit, accident)
PointStop = 4
PointFeuRouge = 4
PointSensInterdit = 4
PointAccident = 6

# variables représentant le nom des configurations dans la base de données
nomMapSave = ""
nomMapLoad = ""
listeNomMap = []

# Initialisation de la matrice contenant le graphe (par defaut initialis a -1 pour indiquer qu'il n'y a pas de voisin
Graphe = [[-1 for x in range(NombreSommet)] for x in range(NombreSommet)]

#creation de listes pour la recuperation de donnees afin de verifier si les sommets existent bien et s'il y a un lien etre eux
listeSommetExiste = []
listeLienSommet = []


# Cette table de sommets contient
# - les coordonnees (x,y) du sommet
# - le code de la contrainte associe a ce sommet (-1 : Sommet inactif, 0:pas de contrainte, 1 : Stop, 2 : Feu rouge, 3 : Sens Interdit)

TableSommets=[          # Sommet

                [1,1,0], # 0

                [2,1,0], # 1

                [3,1,0], # 2

                [4,1,0], # 3

                [5,1,0], # 4

                [1,2,0], # 5

                [2,2,0], # 6

                [3,2,0], # 7

                [4,2,0], # 8

                [5,2,0], # 9

                [1,3,0], # 10

                [2,3,0], # 11

                [3,3,0], # 12

                [4,3,0], # 13

                [5,3,0], # 14

                [1,4,0], # 15

                [2,4,0], # 16

                [3,4,0], # 17

                [4,4,0], # 18

                [5,4,0], # 19

                [1,5,0], # 20

                [2,5,0], # 21

                [3,5,0], # 22

                [4,5,0], # 23

                [5,5,0], # 24

            ]



# creation de la fenetre generale

Fen=Tk()

# determine taille de la fenetre
Fen.geometry('1300x700')

Fen.title("DRONE IT!")

# ------------------------------------------------------------------------------
# Cette fonction teste si le clic souris est dans la fenetre graphe

# pixel_x : coordonnée pixel x
# pixel_y : coordonnée pixel y

# ------------------------------------------------------------------------------
def testBordure (pixel_x,pixel_y):

    trouve = 0

    # calcul des bornes x,y min/max de la fenetre fraphe
    x0 = Offset_x - EcartPixel/2

    x1 = Offset_x + (((Maille-1)*EcartPixel) + EcartPixel/2)

    y0 = Offset_y - EcartPixel/2

    y1 = Offset_y + (((Maille-1)*EcartPixel) + EcartPixel/2)


    # test successif aux bornes x,y min/max pour determiner si clic souris à l'interieur de ces bornes
    if pixel_x > x0:

        if pixel_x <= x1:

            if pixel_y > y0:

                if pixel_y <= y1:

                    # les coordonnees pixel x,y se trouve à l'interieur de la fenetre graphe
                    trouve=1

                    return (trouve)


# ------------------------------------------------------------------------------
# Cette fonction determine sur quel sommet doit se realiser un evenement
# 
# event : type d'evenement
# ------------------------------------------------------------------------------
def recuperer_coord(event):

    global HmiContext

    global NbSelectedPoint

    global P1

    global P2

    x=event.x

    y=event.y



    # Test si on se trouve bien dans la frame selectionnable

    if testBordure (x,y) == 1:

        # si on se trouve dans la fenetre graphe, recuperation du sommet selectionné à partir coordonnees x,y
        s=convertPixelEnSommet (x,y)

        flipflop (s)


        # evenement de creation/suppression signalisation stop sur un sommet s
        if HmiContext == 1:

            createDeleteStop (s)

            HmiContext = 0


        # evenement de creation/suppression signalisation feu rouge sur un sommet s
        if HmiContext == 2:

            createDeleteFeuRouge (s)

            HmiContext = 0


        # evenement de creation/suppression signalisation sens interdit sur un sommet s
        if HmiContext == 3:

            createDeleteSensInterdit (s)

            HmiContext = 0


        # evenement de creation d'un plan de vol à partir d'un sommet s de depart
        if HmiContext == 4:

            definePlanVol (s)


        # evenement de suppression d'un sommet s : suppression des routes avec ses voisins, sommet s devient ianctif
        if HmiContext == 5:

            desactiverSommet (s)

            HmiContext = 0

            updateGraphe()

            
        # evenement de creation d'un plan de vol basé sur djisktra
        if HmiContext == 6:

            # test si il s'agit de la selection du sommet de depart ou du sommet d'arrivée
            if NbSelectedPoint == 0:

                # recuperation du sommet de depart selectionné par la souris
                P1 = s

                NbSelectedPoint = 1

            else:

                # recuperation du sommet d'arrivée selectionné par la souris
                P2 = s

                NbSelectedPoint = 0

                HmiContext=0

                # sommet depart et arrivée ont été selectionnés, declenchement de la recherche du plus court chemin
                dijkstra(Graphe,P1,P2,Visites,Distances,Precedents)

                # plus court chemin est insérer dans le plan de vol
                Chemin.reverse()

                # mise à jour du graphe
                updateGraphe ()


        
        # evenement de supression d'une route entre dun sommet 1 et un sommet 2
        if HmiContext == 9:

            # test si il s'agit de la selection du sommet 1 ou du Sommet 2
            if NbSelectedPoint == 0:

                # recuperation du sommet 1 selectionné par le clic souris
                P1 = s

                NbSelectedPoint = 1

            else:

                # recuperation du sommet 2 selectionné par le clic souris
                P2 = s

                NbSelectedPoint = 0

                HmiContext=0

                # suppression de la route
                deleteArcGraphe (P1, P2)

                # mise à jour du graphe
                updateGraphe ()


        # evenement de creation d'une route entre dun sommet 1 et un sommet 2
        if HmiContext == 10:

            # test si il s'agit de la selection du sommet 1 ou du Sommet 2
            if NbSelectedPoint == 0:

                # recuperation du sommet 1 selectionné par le clic souris
                P1 = s

                NbSelectedPoint = 1

            else:

                P2 = s

                NbSelectedPoint = 0

                HmiContext=0

                # creation de la route
                createArcGraphe (P1, P2)

                # mise à jour du graphe
                updateGraphe ()





# caneva pour visualiser le graphe

Can=Canvas(Fen,width=900,height=650)

Can.pack(padx=15, pady=15)

Can.bind("<Button-1>",recuperer_coord)



# ------------------------------------------------------------------------------

# VARIABLES GLOBALES

# ------------------------------------------------------------------------------




# variables pour dijkstra

Visites=[]      #liste des sommets que l'on a deja visite

Distances={}    # dictionnaires des distances

Precedents={}   # dictionnaire avec les sommets precedents et la distance depius

                # le premier sommet



Chemin=[] # liste des sommets qui composent le chemin trouve

Planvol=[] # liste des sommets qui composent le plan de vol

Vol=[] # liste des sommets voles par le drone



Distance=0.0 # distance a parcourir en prenant le chemin trouve


# angle de rotation du drone entre orientation actuel et orientation demandée pour rejoindre nouveau somet
RotationAngle = 0
# angle de rotation du drone
OrientationDrone = 0
# orientation courante du drone par rapport au Nord
CurrentDirection = 0

# nombre de points sur permis
Sv=StringVar()

"""

Les fonctions du programme "Drone IT" sont structurés en plusieurs ensembles selon une approche MVC

- MODELE

    - Gestion des données

CONTROLEUR    

    - Gestion des configurations du réseau (structures et contraintes)

    - Gestion des plans de vol

    - Gestion de l'execution du vol

    - Gestion des contraintes

    - Gestion des commandes du drone

VUE

    - Utilitaires de visualisation 

    - Gestion des visualisations

    - Gestion des évènement graphiques (Listener) 

"""



"""

MODELE

Les fonctions de gestion de données sont:

    - save ()

    - load ()
    
    - getName ()

    - newGraphe ()

"""
# ------------------------------------------------------------------------------
# Cette fonction sauvegarde dans la base de données la configuration des routes et des contraintes
# ------------------------------------------------------------------------------
def save():
    global nb_lignes, nb_colonnes, nomMapSave

   #i gere les sommets initiaux, j les sommets cibles, nb_matrice est à modifier à chaque fois (il sert pour les différentes maps), lienOui si il existe un lien entre le sommet i et j, lienNon si il n'en existe pas
    i = 0
    j = 0
    nb_matrice = 1
    lienOui = 1
    lienNon = 0
    
    # recuperation des noms de configuration dans la base de données
    getName()
    print ("nomMapSave :", nomMapSave)
    print ("Liste :", listeNomMap)
    
    trouve =0
    for i in range (len(listeNomMap)):
        # lors de la récuperation du nom de la map dans la base de données il y a des caracteres en-tete supplémentaire à enlever
        nomMap = listeNomMap[i]
        LongueurChaine = len  (nomMap)
        FinChaine = LongueurChaine - 3
        nomMap = nomMap[2:FinChaine]
        if nomMapSave == nomMap:
            print ("trouve :", nomMapSave)
            trouve =1
        
    
    if nomMapSave != "":
        #si la map n'existe pas dans la bdd
        if trouve == 1:
            #connexion a la bdd
            mariadb_connection = mariadb.connect(host='dwarves.iut-fbleau.fr', user='chabrais', password='MoTdEpAsSe', database='chabrais')
            cursor = mariadb_connection.cursor()

            #insertion des sommets et des contraintes
            for i in range(Maille):
                for j in range(Maille):
                    NumeroSommet = convertCoordEnPoint(j,i)
                        
                    #on effectue la requete sql pour envoyer les sommets et contraintes
                    cursor.execute("INSERT INTO TableSommets VALUES ('%s','%d','%d','%d','%d','%d');"%(nomMapSave,j+1,i+1,TableSommets[NumeroSommet][2],convertCoordEnPoint(j,i),TableSommets[NumeroSommet][2]))
                    mariadb_connection.commit()
                
            i = 0
            j = 0
                
            #insertion des liens entre les sommets
            for i in range(NombreSommet):
                for j in range(NombreSommet):
                        
                    #on effectue la requete sql pour envoyer les liens entre les sommets
                    cursor.execute("INSERT INTO Matrice VALUES ('%s','%d','%d','%d');"%(nomMapSave,i,j,Graphe[i][j]))
                    mariadb_connection.commit()
            mariadb_connection.close()
            
        #si la map existe dans la bdd
        else:
            #connexion a la bdd
            mariadb_connection = mariadb.connect(host='dwarves.iut-fbleau.fr', user='chabrais', password='MoTdEpAsSe', database='chabrais')
            cursor = mariadb_connection.cursor()
            
            #on supprime tout ce qui existe deja au nom pour le reinserer ensuite dans la table tableSommets
            query = "delete from TableSommets where nomMap = '%s' " % nomMapSave
            cursor.execute(query)
            mariadb_connection.commit()
            mariadb_connection.close()
            
            #connexion a la bdd
            mariadb_connection = mariadb.connect(host='dwarves.iut-fbleau.fr', user='chabrais', password='MoTdEpAsSe', database='chabrais')
            cursor = mariadb_connection.cursor()
            
            #connexion a la bdd
            mariadb_connection = mariadb.connect(host='dwarves.iut-fbleau.fr', user='chabrais', password='MoTdEpAsSe', database='chabrais')
            cursor = mariadb_connection.cursor()
            
            #on supprime tout ce qui existe deja au nom pour le reinserer ensuite dans la table Matrice
            query = "delete from Matrice where nomMap = '%s' " % nomMapSave
            cursor.execute(query)
            mariadb_connection.commit()
            mariadb_connection.close()
            
            #connexion a la bdd
            mariadb_connection = mariadb.connect(host='dwarves.iut-fbleau.fr', user='chabrais', password='MoTdEpAsSe', database='chabrais')
            cursor = mariadb_connection.cursor()

            i = 0
            j = 0

            #insertion des sommets et des contraintes
            for i in range(Maille):
                for j in range(Maille):
                    NumeroSommet = convertCoordEnPoint(j,i)
                        
                    #on effectue la requete sql pour envoyer les sommets et contraintes
                    cursor.execute("INSERT INTO TableSommets VALUES ('%s','%d','%d','%d','%d','%d');"%(nomMapSave,j+1,i+1,TableSommets[NumeroSommet][2],convertCoordEnPoint(j,i),TableSommets[NumeroSommet][2]))
                    mariadb_connection.commit()
                
            i = 0
            j = 0
                
            #insertion des liens entre les sommets
            for i in range(NombreSommet):
                for j in range(NombreSommet):
                        
                    #on effectue la requete sql pour envoyer les liens entre les sommets
                    cursor.execute("INSERT INTO Matrice VALUES ('%s','%d','%d','%d');"%(nomMapSave,i,j,Graphe[i][j]))
                    mariadb_connection.commit()
            mariadb_connection.close()




# ------------------------------------------------------------------------------   
# Cette fonction charge à partir de la base de données une configuration des routes et des contraintes
# ------------------------------------------------------------------------------
def load():
    global TableSommets, Graphe, nomMapLoad
    
    # reinitialisation des listes
    listeSommetExiste [:] = []
    listeLienSommet[:] = []

    
    #le compteur sert a l'affichage de la liste des sommets a la console afin de le faire dans la meme boucle que la recuperation des donnees
    compteur = 0
    
    #connexion a la bdd
    mariadb_connection = mariadb.connect(host='dwarves.iut-fbleau.fr', user='chabrais', password='MoTdEpAsSe', database='chabrais')
    cursor = mariadb_connection.cursor()
  
    # lors de la récuperation du nom de la map dans la base de données il y a des caracteres en-tete supplémentaire à enlever
    LongueurChaine = len  (nomMapLoad)
    FinChaine = LongueurChaine - 3
    nomMapLoad = nomMapLoad[2:FinChaine]

    
    #on execute la requete sql
    sql_select_query = """select * from TableSommets where nomMap = %s"""
    cursor.execute(sql_select_query, (nomMapLoad,))
    print("listeSommetExiste :", nomMapLoad)
    
    #on stocke le resultat de la requete dans une liste et on affiche cette liste proprement
    for result in cursor:
        listeSommetExiste.append(result)
        print("nomMap ="+listeSommetExiste[compteur][0]+", x ="+str(listeSommetExiste[compteur][1])+", y="+str(listeSommetExiste[compteur][2])+", codeContrainte="+str(listeSommetExiste[compteur][3])+", numSommet="+str(listeSommetExiste[compteur][4])+", Existe="+str(listeSommetExiste[compteur][5]))
        compteur = compteur+1
    #on ferme la connexion
    mariadb_connection.close()
   
    #on range le resultat dans la bonne liste
    i = 0
    for i in range(NombreSommet):
        s = listeSommetExiste[i][4]
        TableSommets[s][0] = listeSommetExiste[i][1]
        TableSommets[s][1] = listeSommetExiste[i][2]
        TableSommets[s][2] = listeSommetExiste[i][3]
   
    #on reinitialise le compteur afin de le reutiliser
    compteur = 0
    #on reouvre la connexion
    mariadb_connection = mariadb.connect(host='dwarves.iut-fbleau.fr', user='chabrais', password='MoTdEpAsSe', database='chabrais')
    cursor = mariadb_connection.cursor()
    #on recupere les donnees des liens entre les sommets

    sql_select_query = """select * from Matrice where nomMap = %s"""
    cursor.execute(sql_select_query, (nomMapLoad,))
    

    for result2 in cursor:
        listeLienSommet.append(result2)
        print("nomMap ="+str(listeLienSommet[compteur][0])+", SommetInitial ="+str(listeLienSommet[compteur][1])+", SommetCible="+str(listeLienSommet[compteur][2])+", Lien="+str(listeLienSommet[compteur][3]))
        compteur = compteur+1
    #on referme la connexion
    mariadb_connection.close()
    print ("nombre element compteur :", compteur)
    #on range les liens dans le Graphe
    i = 0
    j = 0
    compteur = 0
    for i in range(NombreSommet):
        for j in range (NombreSommet):
            Graphe[i][j] = listeLienSommet[compteur][3]
            compteur = compteur+1
 
    # mis à jour de la visualisation graphique apres chargement des données à partir de la base de données
    # updateGraphe ()
    updateGraphe ()

# ------------------------------------------------------------------------------   
# Cette fonction charge à partir de la base de données les noms des differentes configurations disponibles
# ------------------------------------------------------------------------------
def getName ():

    # ouverture de la connextion à la base de données
   
    mariadb_connection = mariadb.connect(host='dwarves.iut-fbleau.fr', user='chabrais', password='MoTdEpAsSe',      database='chabrais')
    cursor = mariadb_connection.cursor()
 
    #on execute la requete sql
    cursor.execute("SELECT DISTINCT nomMap FROM TableSommets")
    print("listeNomMap :")
    
    # reinitialisation à zéro de la listeNomMap
    listeNomMap[:] = []
    
    for result in cursor:
        listeNomMap.append(result)
        print(listeNomMap)

    # fermeture de la connection à la base de données
    mariadb_connection.close()

    
# ------------------------------------------------------------------------------
# Cette fonction construit un graphe vierge. Dans ce graphe tous les sommets sont liés avec leurs sommets voisins. 
# Pour tous les sommets (X,Y) du graphe, on definit une Arrete allant d'un sommet S1 a ses autres sommets voisin. 
# Le tableau Graphe de dimension [N sommets][N Sommets] contiendra toutes les Arretes trouves entre les Sommets. 
# En complement, il sera indique dans le tableau Graphe l'orientation de l'Arrete.

# Graphe       : Tableau representant la structure du Graphe 
# NombreSommet : Nombre de sommet total de la MNT

# ------------------------------------------------------------------------------
def newGraphe (Graphe, NombreSommet):

    NumeroSommet=0
    L=0
    C=0

    # Pour chaque Sommet recherche des Sommets (i) voisins eligibles

    for i in range (NombreSommet): # on parcourt l'ensemble des sommets


        # Conversion du numero du Sommet i en coordonnees du Sommet (L,C)

        (L,C)=convertPointEnCoord(i)

        # Determination des points voisins potentiels (uniquement 8 voisins maximum possible de part la geometrie de la maille
        # On determine l'angle suivant le point du Sommet S vers un de ses voisons (0,45,90, 135, 180, -45, -90, -135)


        SommetVoisin1=[C-1,L-1,-45]
        SommetVoisin2=[C-1,L,-90]
        SommetVoisin3=[C-1,L+1,-135]
        SommetVoisin4=[C,L+1,180]
        SommetVoisin5=[C+1,L+1,135]
        SommetVoisin6=[C+1,L,90]
        SommetVoisin7=[C+1,L-1,45]
        SommetVoisin8=[C,L-1,0]

        # on construit une variable aggegeant les 8 voisins
        V=[SommetVoisin1,SommetVoisin2,SommetVoisin3,SommetVoisin4,SommetVoisin5,SommetVoisin6,SommetVoisin7,SommetVoisin8]

        # on parcourt la liste des voisins
        for k in range (len(V)): 
            # on verifie que le voisin considere appartient bien a la maille
            if Borne_L_min<=V[k][1]<=Borne_L_max: 

                 # on verifie que le voisin considere appartient bien a la maille
                if Borne_C_min<=V[k][0]<=Borne_C_max:
                    #on convertit les coordonees du voisin en numero de sommet
                    NumeroSommet = convertCoordEnPoint (V[k][0], V[k][1]) 
                
                    # On remplit le tableau avec l'orientation correspondante
                    Graphe [i][NumeroSommet]= V [k][2] 
                    





"""

CONTROLEUR

Les fonctions de gestion de configuration de la structure du réseau sont:

    - create arcGraphe ()

    - delete arcGraphe ()

    - desactiverSommet ()



Les fonctions de gestion de configuration des contraintes du réseau sont:

    - createDeleteStop()

    - createDeleteFeuRouge()

    - createDeleteSensInterdit()

    

"""   

    
# ------------------------------------------------------------------------------
# Cette fonction construit un segment entre deux sommets S1 et S2. 
# il faut donc creer le lien entre S1 et S2 et inversement entre S2 et S1
# il faut reexplorer tous les voisins pour retrouver quel est l'angle entre S1 et S2 afin de remplir la table Graphe

# Sommet1 : sommet de départ
# Sommet2 : sommet d'arrivée

# ------------------------------------------------------------------------------

def createArcGraphe (Sommet1, Sommet2):


    # il faut d'abord recreer le lien entre le sommet1 et le sommet2
    # Conversion du numero du Sommet i en coordonnees du Sommet (L,C)
    (L,C)=convertPointEnCoord(Sommet1)



    # Determination des points voisins potentiels (uniquement 8 voisins maximum possible de part la geometrie de la maille

    # On determine l'angle suivant le point



    SommetVoisin1=[C-1,L-1,-45]

    SommetVoisin2=[C-1,L,-90]

    SommetVoisin3=[C-1,L+1,-135]

    SommetVoisin4=[C,L+1,180]

    SommetVoisin5=[C+1,L+1,135]

    SommetVoisin6=[C+1,L,90]

    SommetVoisin7=[C+1,L-1,45]

    SommetVoisin8=[C,L-1,0]



    V=[SommetVoisin1,SommetVoisin2,SommetVoisin3,SommetVoisin4,SommetVoisin5,SommetVoisin6,SommetVoisin7,SommetVoisin8]


    # on parcourt la liste des voisins
    for k in range (len(V)): 
        # on verifie que le voisin considere appartient bien a la maille
        if Borne_L_min<=V[k][1]<=Borne_L_max: 

            if Borne_C_min<=V[k][0]<=Borne_C_max:
                
                #on convertit les coordonees du voisin en numero de sommet
                NumeroSommet = convertCoordEnPoint (V[k][0], V[k][1]) 
    
                # on recherche si il s'agit bien du sommet 2
                if NumeroSommet == Sommet2:
                    # On remplit le tableau avec l'orientation correspondante
                    Graphe [Sommet1][Sommet2]= V [k][2] 

    # il faut d'abord recreer le lien entre le sommet2 et le sommet1
    # Conversion du numero du Sommet i en coordonnees du Sommet (L,C)
    (L,C)=convertPointEnCoord(Sommet2)


    # Determination des points voisins potentiels (uniquement 8 voisins maximum possible de part la geometrie de la maille
    # On determine l'angle suivant le point
    # Si le Sommet voisin est en diagonale : distance = 350 metres

    SommetVoisin1=[C-1,L-1,-45]

    SommetVoisin2=[C-1,L,-90]

    SommetVoisin3=[C-1,L+1,-135]

    SommetVoisin4=[C,L+1,180]

    SommetVoisin5=[C+1,L+1,135]

    SommetVoisin6=[C+1,L,90]

    SommetVoisin7=[C+1,L-1,45]

    SommetVoisin8=[C,L-1,0]



    V=[SommetVoisin1,SommetVoisin2,SommetVoisin3,SommetVoisin4,SommetVoisin5,SommetVoisin6,SommetVoisin7,SommetVoisin8]


    # on parcourt la liste des voisins
    for k in range (len(V)): 
        # on verifie que le voisin considere appartient bien a la maille
        if Borne_L_min<=V[k][1]<=Borne_L_max: 
        
            if Borne_C_min<=V[k][0]<=Borne_C_max:
                
                 #on convertit les coordonees du voisin en numero de sommet
                NumeroSommet = convertCoordEnPoint (V[k][0], V[k][1]) 

                # on recherche si il s'agit bien du sommet 1
                if NumeroSommet == Sommet1:
                    # On remplit le tableau avec l'orientation correspondante
                    Graphe [Sommet2][Sommet1]= V [k][2] 


    # Si le sommet1 etait inactif il faut le rendre actif
    if TableSommets[Sommet1][2] == -1:
        TableSommets[Sommet1][2] = 0

    # Si le sommet2 etait inactif il faut le rendre actif
    if TableSommets[Sommet2][2] == -1:
        TableSommets[Sommet2][2] = 0




# ------------------------------------------------------------------------------
# Cette fonction detruit un segment entre deux sommets S1 et S2. 


# Sommet1 : sommet de départ
# Sommet2 : sommet d'arrivée

# ------------------------------------------------------------------------------

def deleteArcGraphe (Sommet1, Sommet2):

    # le segment entre sommet1 et sommet2 est invalidé (mis à -1)
    Graphe [Sommet1][Sommet2]= -1
    # le segment entre sommet2 et sommet1 est invalidé (mis à -1)
    Graphe [Sommet2][Sommet1]= -1


    # il faut verifier que si le sommet1 etait inactif (aucun voisin) la creation de ce nouveau segment le rend de nouveau actif
    SommetActif=0
    
    for v in range (NombreSommet):
        if Graphe [Sommet1][v]!=-1:

            SommetActif = 1

    # si le Sommet devient inactif par la suppression de ce segment il faut invalider le sommet dans la table TableSommets
    if SommetActif == 0:
        TableSommets[Sommet1][2]=-1




    # il faut verifier que si le sommet1 etait inactif (aucun voisin) la creation de ce nouveau segment le rend de nouveau actif
    SommetActif=0

    for v in range (NombreSommet):

        if Graphe [Sommet2][v]!=-1:

            SommetActif = 1

    # si le Sommet devient inactif par la suppression de ce segment il faut invalider le sommet dans la table TableSommets
    if SommetActif == 0:

        TableSommets[Sommet2][2]=-1


# ------------------------------------------------------------------------------
# Cette fonction desactive le sommet
# il faut mettre a jour les table Graphe et TableSommets


# Sommet : sommet à desactiver

# ------------------------------------------------------------------------------
def desactiverSommet (Sommet):

    #il faut supprimer tous les segments de ce sommet avec ses voisins dans la table Graphe et mettre la table TableSommets à -1 pour indiquer que le sommet est inactif
    for i in range (NombreSommet):

        TableSommets[Sommet][2]=-1

        Graphe [Sommet][i]=-1

    for j in range (NombreSommet):

        Graphe [j][Sommet]=-1

# ------------------------------------------------------------------------------
# Cette fonction creer ou detruit un stop sur un sommet
# C'est une fonction 'flipflop' qui creer ou detruit le stop 

# Sommet : sommet sur lequel creer/detruite le stop

# ------------------------------------------------------------------------------

def createDeleteStop (Sommet):

    # si il n'existe pas de stop : creation d'un stop
    if TableSommets[Sommet][2]==0:

        TableSommets[Sommet][2]=1

    # si il existe un stop : destruction du stop
    elif TableSommets[Sommet][2]==1:

        TableSommets[Sommet][2]=0
        
    # mis a jour de l'image du graphe pour tenir compte du nouveau feu rouge
    updateGraphe()    


# ------------------------------------------------------------------------------
# Cette fonction creer ou detruit un feu rouge sur un sommet
# C'est une fonction 'flipflop' qui creer ou detruit le stop 

# Sommet : sommet sur lequel creer/detruite le feu rouge
# ------------------------------------------------------------------------------
def createDeleteFeuRouge (Sommet):

    # si il n'existe pas de feu rouge : creation d'un feu rouge
    if TableSommets[Sommet][2]==0:

        TableSommets[Sommet][2]=2

    # si il existe un feu rouge : destruction du feu rouge
    elif TableSommets[Sommet][2]==2:

        TableSommets[Sommet][2]=0

    # mis a jour de l'image du graphe pour tenir compte du nouveau feu rouge
    updateGraphe()    


# ------------------------------------------------------------------------------
# Cette fonction creer ou detruit un sens interdit sur un sommet
# C'est une fonction 'flipflop' qui creer ou detruit le stop 

#  Sommet : sommet sur lequel creer/detruite le sens interdit

# ------------------------------------------------------------------------------

def createDeleteSensInterdit (Sommet):

    # si il n'existe pas de sens interdit : creation d'un sens interdit
    if TableSommets[Sommet][2]==0:

        TableSommets[Sommet][2]=3

    # si il existe un sens interdit : destruction d'un sens interdit
    elif TableSommets[Sommet][2]==3:

        TableSommets[Sommet][2]=0

    # mis a jour de l'image du graphe pour tenir compte du nouveau sens interdit
    updateGraphe()   



"""

CONTROLEUR

Les fonctions de gestion du plan de vol sont:

    - planVol ()

    - dijkstra ()

    - resetList ()

"""   


# ------------------------------------------------------------------------------
# Cette fonction defini un plan par un enchainement de sommet consecutifs

# Sommet : sommet qui se rajoute au plan de vol en cours d'elaboration

# ------------------------------------------------------------------------------
def definePlanVol (Sommet):
    
    # chaque appel de cette fonction vient rajouter un sommet au plan de vol (chemin)
    Chemin.append(Sommet)


# ------------------------------------------------------------------------------
# Cette fonction trouve le plus court chemin entre 2 sommets
# Cette fonction utilise l'algorithme du plus court chemin de djisktra

# Le code s'est inspiré de l'algorithme de dijkstra de Gilles Bertrand
# www.gilles-bertrand.com/2014/03/dijkstra-algorithm-python-example-source-code-shortest-path.html

# graph : 
# src : sommet de depart
# dest : somme d'arrivee
# visited : liste servant a memoriser les sommets visités lors de l'exploration
# distances : calcaul de la distance la plus courte
# predecessors : liste servant a memoriser l'exploration du graphe

# ------------------------------------------------------------------------------

def dijkstra(Graph,Src,Dest,Visited=[],Distances={},Predecessors={}):

    global Chemin, Distance


    #calcul du plus court chemin depuis src

    # condition de fin
    if Src == Dest:

        # construction du chemin le plus court et affichage
        Path=[]
        Pred=Dest

        while Pred != None:

            Path.append(Pred)
            Pred=Predecessors.get(Pred,None)

            # affectation du chemin et de la distance
            Distance=Distances[Dest]
            Chemin=Path

    else :

        # la premiere fois on initialise la distance de A vers A
        if not Visited:

            Distances[Src]=0

        # visite des voisin
        for Sommet in range (NombreSommet) :

            if Graph [Src][Sommet] != -1 :

                Neighbor = Sommet

                if Neighbor not in Visited:

                    Angle = Graph[Src][Neighbor]

                    if Angle == 0 or Angle == 90 or Angle == -90 or Angle == 180 :

                        Dist = 1

                    else :

                        Dist = 1.41

                    New_distance = Distances[Src] + Dist

                    if New_distance < Distances.get(Neighbor,float('inf')):

                        Distances[Neighbor] = New_distance

                        Predecessors[Neighbor] = Src

        # on note le sommet dans visited
        Visited.append(Src)


        # lorsque tout les voisin ont ete visite : recursion
        # on choisi le sommet non visite avec le chemin le plus court
        # run Dijskstra avec src='x'

        Unvisited={}

        for k in range (NombreSommet) :

            if k not in Visited:

                Unvisited[k] = Distances.get(k,float('inf'))

        X=min(Unvisited, key=Unvisited.get)

        dijkstra(Graph,X,Dest,Visited,Distances,Predecessors)



# ------------------------------------------------------------------------------
# Cette fonction remet a zero un ensemble de liste/table
# Cette fonction est utilisé lors de changement de scenario (plan de vol, pilotage automatique ou manuel, ...)

# ------------------------------------------------------------------------------

def resetListe ():

    global Vol
    global Planvol
    global Chemin
    global Visites
    global Distances
    global Precedents
    global PointConduite
    global Sv
    global SommetCourant, CurrentDirection


    # repositionnement du drone
    SommetCourant = 21
    # mis a jour de l'orientation du drone dans la direction courante (CurrentDirection)
    CurrentDirection = 0

    # chemin volé remis a zero
    Vol[:] = []
    
    # plan de vol remis a zero
    Planvol[:] = []
    
    # plus court chemin de djisktra remis a zero
    Chemin[:] = []
    
    # remis a zero chemin visites lors du calcul de djisktra
    Visites=[]
    
    # remis a zero des distances lors du calcul de djisktra
    Distances={}
    
    # remis a zero des predecesseurs lors du calcul de djisktra
    Precedents={}
    
    # remise a 12 du compteur de permis a points
    Sv.set ("12")
   
    # mis a jour de l'image du graphe pour tenir de la mise a jour des donnees
    updateGraphe()



"""
CONTROLEUR

Les fonctions de l'execution d'un plan de vol sont:

    - initOrientationDrone ()

    - executeFlightPlan ()

"""   

# ------------------------------------------------------------------------------
# Cette fonction definie l'orientation du drone

# Direction : angle du drone par rapport a un referentiel Nord

# ------------------------------------------------------------------------------
def initOrientationDrone (direction):

    global CurrentDirection

    # mis a jour de l'orientation du drone dans la direction courante (CurrentDirection)
    CurrentDirection = direction
    
    # mis a jour de l'image du graphe pour tenir de la mise a jour des donnees
    updateGraphe()


# ------------------------------------------------------------------------------
# Cette fonction execute le plan de vol defini et fait voler le drone

# ------------------------------------------------------------------------------
def executeFlightPlan():

    global CurrentDirection
    global SommetCourant

 
    # le premier sommet du plan de vol est affecté au sommet courant
    SommetCourant = Chemin[0]

    # établissement connection bluetooth avec le drone
    connectDroneX ()

    # decollage du drone
    takeoff ()

    # pour tous les sommets successifs du plan de vol 
    for i in range (len(Chemin)-1):

        # Test si le prochain sommet destinataire necessite un changement de direction du drone (rotation)
        SommetOrientation = Graphe [Chemin [i]][Chemin[i+1]]
        SommetCourant = Chemin[i+1]

        # il y a rotation si il y a un angle differentiel par rapport au Nord entre le sommet depart et le sommet destinataire 
        CorrectionRotationAngle = SommetOrientation - CurrentDirection
        CurrentDirection = SommetOrientation

        if CorrectionRotationAngle != 0:
            rotate (CorrectionRotationAngle);


        # La rotation est terminee, marche en avant du drone
        forward ()


    # tous les sommets ont été volé, donc atterissage
    landing ()

    # deconnextion du drone
    disconnectDroneX ()

"""
CONTROLEUR

Les fonctions de gestion des contraintes et permis à points sont:

    - constraintManagement ()

    - permisPoint ()

"""   


# ------------------------------------------------------------------------------
# Cette fonction gere les contraintes du graphe (stop, sens interdit, feu rouge, route inexistante, ....)

# S0 : Sommet depart
# S1 : Sommet destination
# ------------------------------------------------------------------------------

def constraintManagement (SO, SD):

    global ActionStop

    # Test si chemin entre S0 et SD est un stop au depart de SO
    if TableSommets [SO][2]==1:

        # Si le drone s'était arreté au stop
        if ActionStop == 1:
            
            # remise a zero de l'action stop
            ActionStop = 0

        else:
            # le drone n'a pas marqué le stop : retrait de points du permis
            permisPoint(PointStop)



    # Test si chemin entre S0 et SD est en situation feu rouge au depart de S0
    if TableSommets [SO][2]==2:

        # le drone est passé au feu rouge
        if FeuRouge == 1:
            
            # le drone n'a pas marqué le stop : retrait de points du permis
            permisPoint(PointStop)

            

    # Test si chemin entre S0 et SD est un sens interdit
    if TableSommets [SD][2]==3:

        # le drone est passé dans un sens interdit
        # le drone n'a pas marqué le stop : retrait de points du permis
        permisPoint (PointSensInterdit)


# ------------------------------------------------------------------------------
# Cette fonction gere les points du permis

# Point : nombre de point à enlever

# ------------------------------------------------------------------------------

def permisPoint (Point):
    global Sv

    # recuperation du nombre de points courants
    val = int(Sv.get())
    
    # mise a jour du nombre de point
    val=val-Point
    Sv.set (str(val))

    print ("Points Restants : ", val)

    

"""

CONTROLEUR

Les fonctions de gestion des commandes du drone sont:

    - connectDrone ()

    - disconnectDrone ()

    - takeoff ()

    - landing ()

    

fonctions spécifiques à l'execution d'un vol libre sans plan de vol: 

    - xmoveW ()

    - xmoveE ()

    - xmoveNE ()

    - xmoveSE ()

    - xmoveNO ()

    - xmoveN ()

    - xmoveS ()

    - xmoveforward ()

    - xstop ()

    - calculRotationAngle ()

    

fonctions spécifiques à l'execution d'un plan de vol:

    - left ()

    - right ()

    - moveNE ()

    - moveSE ()

    - moveNO ()

    - moveSO ()

    - moveN ()

    - moveS ()

    - forward ()

    - rotate ()

"""   


# ------------------------------------------------------------------------------
# Cette fonction connecte le drone en bluetooth avec le programme Drone IT qui tourne sur raspberry
# connexion pour vol manuel
# ------------------------------------------------------------------------------

def connectDrone ():

    global bouton_connect
    global DroneOn

    # connection du drone active
    DroneOn=1


    print("trying to connect")

    # connection du drone mambo
    success = mambo.connect(num_retries=3)

    print("connected: %s" % success)

    # si le drone s'est connecté avec success au raspberry
    if (success):
        
        # bouton connect est mis en vert pour signaler la connection 
        bouton_connect.destroy ()

        bouton_connect=Button(Fen,text="Connect",bg='green',fg='blue',command=manageconnectDrone)

        bouton_connect.place(x=700,y=130)

# ------------------------------------------------------------------------------
# Cette fonction connecte le drone en bluetooth avec le programme Drone IT qui tourne sur raspberry
# connexion pour execution d'un plan de vol
# ------------------------------------------------------------------------------

def connectDroneX ():
    global DroneOn

    DroneOn = 1


    # connection du drone active
    if DroneOn==1:


        print("trying to connect")

        # connection du drone mambo
        success = mambo.connect(num_retries=3)

        print("connected: %s" % success)

  

# ------------------------------------------------------------------------------
# Cette fonction deconnecte le drone en bluetooth avec le programme Drone IT qui tourne sur raspberry
# deconnexion apres execution d'un vol manuel
# ------------------------------------------------------------------------------

def disconnectDrone ():
    global DroneOn
    global bouton_connect

    print("disconnect drone")

    # deconnexion du drone
    # test si le drone est connecté
    if DroneOn==1:

        mambo.disconnect()

        DroneOn = 0


        # bouton connect est mis en rouge pour signaler la deconnexion
        bouton_connect.destroy ()

        bouton_connect=Button(Fen,text="Connect",bg='red',fg='blue',command=manageconnectDrone)

        bouton_connect.place(x=700,y=130)

# ------------------------------------------------------------------------------
# Cette fonction deconnecte le drone en bluetooth avec le programme Drone IT qui tourne sur raspberry
# deconnexion apres execution d'un plan de vol
# ------------------------------------------------------------------------------

def disconnectDroneX ():
    global DroneOn
    global bouton_connect

    print("disconnect drone")

    # deconnexion du drone
    # test si le drone est connecté
    if DroneOn==1:

        mambo.disconnect()
        droneOn = 0
 


# ------------------------------------------------------------------------------
# Cette fonction fait decoller le drone 
# ------------------------------------------------------------------------------
def takeoff():

    global Vol

    print("--> takeoff")

    # on affecte le sommet de depart à la liste des sommets volés
    Vol.append(SommetCourant)

    # test si drone est connecté
    if DroneOn==1:

        # get the state information

        print("sleeping")

        # procedure : appel de differente fonction du drone pour preparer le decollage
        mambo.smart_sleep(2)
        mambo.ask_for_state_update()
        mambo.smart_sleep(2)

        print("taking off!")
        # decollage du drone
        mambo.safe_takeoff(5)


# ------------------------------------------------------------------------------
# Cette fonction fait atterir le drone 
# ------------------------------------------------------------------------------
def landing():

    print("--> landing")

    # test si drone est connecté
    if DroneOn==1:

        # atterissage du drone
        mambo.safe_land(5)
        mambo.smart_sleep(5)

             
# ------------------------------------------------------------------------------
# Cette fonction fait une rotation West au drone et recalcule le referentiel de direction

# ------------------------------------------------------------------------------
                
def xmoveW():

    global CurrentDirection

    print("hello pretty left")

    # calcul du nouveau referentiel de direction
    RotationAngle=calculRotationAngle (-90) 
    CurrentDirection = -90

    # test si drone est connecte
    if DroneOn==1:

        # rotation du drone
        mambo.turn_degrees(RotationAngle)
        mambo.smart_sleep(1)

    print ("========> ", CurrentDirection)

    updateGraphe ()
    

# ------------------------------------------------------------------------------
# Cette fonction fait une rotation East au drone et recalcule le referentiel de direction

# ------------------------------------------------------------------------------

def xmoveE():

    global CurrentDirection

    print("hello pretty right")

    # calcul du nouveau referentiel de direction
    RotationAngle=calculRotationAngle (90) 
    CurrentDirection = 90

    # test si drone est connecte
    if DroneOn==1:

        # rotation du drone
        mambo.turn_degrees(RotationAngle)
        mambo.smart_sleep(1)

    print ("========> ", CurrentDirection)

    updateGraphe ()

# ------------------------------------------------------------------------------
# Cette fonction fait une rotation North East au drone et recalcule le referentiel de direction

# ------------------------------------------------------------------------------

def xmoveNE():

    global CurrentDirection

    print("hello pretty move NE")
    
    # calcul du nouveau referentiel de direction
    RotationAngle=calculRotationAngle (45) 
    CurrentDirection = 45

    # test si drone est connecte
    if DroneOn==1:

        # rotation du drone
        mambo.turn_degrees(RotationAngle)
        mambo.smart_sleep(1)

    print ("========> ", CurrentDirection)

    updateGraphe ()

# ------------------------------------------------------------------------------
# Cette fonction fait une rotation South East au drone et recalcule le referentiel de direction
# ------------------------------------------------------------------------------ 

def xmoveSE():

    global CurrentDirection

    print("hello pretty move SE")

    # calcul du nouveau referentiel de direction
    RotationAngle=calculRotationAngle (135) 
    CurrentDirection = 135

    # test si drone est connecte
    if DroneOn==1:

        # rotation du drone
        mambo.turn_degrees(RotationAngle)
        mambo.smart_sleep(1)

    print ("========> ", CurrentDirection)

    updateGraphe ()

# ------------------------------------------------------------------------------
# Cette fonction fait une rotation North Ouest au drone et recalcule le referentiel de direction

# ------------------------------------------------------------------------------

def xmoveNO():

    global CurrentDirection

    print("hello pretty move NO")

    # calcul du nouveau referentiel de direction
    RotationAngle=calculRotationAngle (-45) 
    CurrentDirection = -45

    # test si drone est connecte
    if DroneOn==1:

        # rotation du drone
        mambo.turn_degrees(RotationAngle)
        mambo.smart_sleep(1)

    print ("========> ", CurrentDirection)

    updateGraphe ()

# ------------------------------------------------------------------------------
# Cette fonction fait une rotation South Ouest au drone et recalcule le referentiel de direction

# ------------------------------------------------------------------------------

def xmoveSO():

    global CurrentDirection

    print("hello pretty move SO")

    # calcul du nouveau referentiel de direction
    RotationAngle=calculRotationAngle (-135) 
    CurrentDirection = -135

    # test si drone est connecte
    if DroneOn==1:

        # rotation du drone
        mambo.turn_degrees(RotationAngle)
        mambo.smart_sleep(1)

    print ("========> ", CurrentDirection)

    updateGraphe () 

# ------------------------------------------------------------------------------
# Cette fonction fait une rotation North au drone et recalcule le referentiel de direction

# ------------------------------------------------------------------------------

def xmoveN():

    global CurrentDirection

    print("hello pretty move S")

    # calcul du nouveau referentiel de direction
    RotationAngle=calculRotationAngle (0) 
    CurrentDirection = 0

    # test si drone est connecte
    if DroneOn==1:

        # rotation du drone
        mambo.turn_degrees(RotationAngle)
        mambo.smart_sleep(1)

    print ("========> ", CurrentDirection)

    updateGraphe ()

# ------------------------------------------------------------------------------
# Cette fonction fait une rotation South au drone et recalcule le referentiel de direction

# ------------------------------------------------------------------------------

def xmoveS():

    global CurrentDirection

    print("hello pretty move S")

    # calcul du nouveau referentiel de direction
    RotationAngle=calculRotationAngle (180) 
    CurrentDirection = 180

    # test si drone est connecte
    if DroneOn==1:

        # rotation du drone
        mambo.turn_degrees(RotationAngle)
        mambo.smart_sleep(1)

    print ("========> ", CurrentDirection)

    updateGraphe ()    

    
# ------------------------------------------------------------------------------
# Cette fonction fait avancer le drone

# ------------------------------------------------------------------------------
def xmoveforward():

    global Vol
    global CurrentDirection
    global SommetCourant

    trouve = 0


    print("Flying direct: going forward (positive pitch) 0.65/metre")

    # recherche sommet voisin destination par rapport à l'orientation courante du drone
    for i in range (NombreSommet):

        # test si le sommet voisin correspond à la direction recherchee
        if Graphe [SommetCourant][i]==CurrentDirection:

            # le sommet voisin a ete trouve
            trouve=1
            SommetDestination = i
            SommetOrigine = SommetCourant

    # si le sommet voisin a été trouve 
    if trouve == 1:

            # si le sommet voisin a été trouve il faut verifier si il y a une contrainte vers ce sommet destination (stop, feu rouge, sens interdit, chemin non possible, ....)
        constraintManagement (SommetOrigine, SommetDestination)

        
        SommetCourant = SommetDestination

        # le sommet destination est ajoute
        Vol.append(SommetDestination)

        # mis a jour du graphe pour prise en compte de la trajectoire volé
        updateGraphe ()

        # test si drone connecté
        if DroneOn==1:
    
            # commande au drone pour le faire avancer
            mambo.fly_direct(roll=0, pitch=50, yaw=0, vertical_movement=0, duration=0.65)
            mambo.smart_sleep(1)

    else:

        # si le sommet voisin n'a pas ete trouve cela veut dire que le drone se dirige dans une direction ou il n'y pas de chemin
        print ("Pas de chemin : ACCIDENT !")

        permisPoint(PointAccident)


# ------------------------------------------------------------------------------
# Cette fonction met le drone en vol stationnaire

# ------------------------------------------------------------------------------
def xstop ():

    global ActionStop

    ActionStop = 0

    print ("hello pretty stop")

    # test si le drone s'est mis en pause parcequ'il y avait un stop a respecter
    if TableSommets [SommetCourant][2]== 1:

        # on marque le fait que le drone se met en pause sur une contrainte stop
        ActionStop = 1

    if DroneOn==1:

        # mise du drone en vol stationnaire
        mambo.smart_sleep(3)

# ------------------------------------------------------------------------------
# Cette fonction calcule la rotation que doit faire le drone entre son angle/nord actuel et celui pour rejoindre 
# le prochain sommet sachant que le drone fonctionne avec une rotation positive de 0 à 180 ou une rotation 
# negative de 0 à -180

# ------------------------------------------------------------------------------

def calculRotationAngle (Rot):

    global CurrentDirection

    # calcule de l'ecart entre la direction actuelle et la rotation demandé par l'utilisateur pour le pilotage du drone
    EcartAngle = Rot - CurrentDirection

    # il faut savoir si on doit faire une rotation  positive ou une rotation negative selon que la direction actuelle est positive (0 a 180) ou negative (0 a -180)
    if EcartAngle != 0:

        if EcartAngle < 0:

            # test si c'est vraiment une rotation negative

            if EcartAngle < -180:

                # rotation positive

                RotationAngle = 360 - abs (EcartAngle)

                print ("Rotation Angle positive", RotationAngle)

            else:   

                #rotation negative

                RotationAngle = abs (EcartAngle)

                RotationAngle = 0 - RotationAngle

                print ("Rotation Angle negative", RotationAngle)

        elif EcartAngle > 0:

            # test si c'est vraiment une rotation positive

            if EcartAngle > 180:

                # rotation negative

                RotationAngle = 360 - abs (EcartAngle)

                RotationAngle = 0 - RotationAngle

                print ("Rotation Angle negative", RotationAngle)

            else:   

                #rotation positive

                RotationAngle = abs (EcartAngle)

                print ("Rotation Angle positive", RotationAngle)

    else:

        RotationAngle = 0


    return RotationAngle  

     
# ------------------------------------------------------------------------------
# Cette fonction fait une rotation a -90 deg en vol automatique

# ------------------------------------------------------------------------------

def left():

    global CurrentDirection

    print("hello pretty left")

    CurrentDirection = CurrentDirection - 90

    # calcul de la nouvelle direction selon que la direction actuelle se trouve entre 0 et 180 degres ou 0 et -180 degres
    
    if CurrentDirection < -180:

        CurrentDirection=CurrentDirection + 360

    # test si drone est connecté
    if DroneOn==1:

        # commande pour rotation du drone
        mambo.turn_degrees(-90)
        mambo.smart_sleep(1)



    updateGraphe ()


# ------------------------------------------------------------------------------
# Cette fonction fait une rotation a 90 deg en vol automatique

# ------------------------------------------------------------------------------
def right():

    global CurrentDirection

    print("hello pretty right")

    CurrentDirection = CurrentDirection + 90


    # calcul de la nouvelle direction selon que la direction actuelle se trouve entre 0 et 180 degres ou 0 et -180 degres
    if CurrentDirection > 180:

            CurrentDirection = CurrentDirection - 360

    # test si drone est connecté
    if DroneOn==1:

        # commande pour rotation du drone
        mambo.turn_degrees(90)
        mambo.smart_sleep(1)

    updateGraphe ()


# ------------------------------------------------------------------------------
# Cette fonction fait une rotation a 45 deg en vol automatique
# ------------------------------------------------------------------------------"""
def moveNE():

    global CurrentDirection

    print("hello pretty move NE")

    CurrentDirection = CurrentDirection + 45

    # calcul de la nouvelle direction selon que la direction actuelle se trouve entre 0 et 180 degres ou 0 et -180 degres
    if CurrentDirection > 180:

            CurrentDirection = CurrentDirection - 360
            
    # test si drone est connecté
    if DroneOn==1:

        # commande pour rotation du drone
        mambo.turn_degrees(45)
        mambo.smart_sleep(1)


    updateGraphe ()

    
# ------------------------------------------------------------------------------
# Cette fonction fait une rotation a 135 deg en vol automatique
# ------------------------------------------------------------------------------"""
def moveSE():

    global CurrentDirection

    print("hello pretty move SE")

    CurrentDirection = CurrentDirection + 135
    
    # calcul de la nouvelle direction selon que la direction actuelle se trouve entre 0 et 180 degres ou 0 et -180 degres
    if CurrentDirection > 180:

            CurrentDirection = CurrentDirection - 360


    # test si drone est connecté
    if DroneOn==1:

        # commande pour rotation du drone
        mambo.turn_degrees(135)
        mambo.smart_sleep(1)



    updateGraphe ()  

# ------------------------------------------------------------------------------
# Cette fonction fait une rotation a -45 deg en vol automatique

# ------------------------------------------------------------------------------
def moveNO():

    global CurrentDirection

    print("hello pretty move NO")

    CurrentDirection = CurrentDirection -45
    
    # calcul de la nouvelle direction selon que la direction actuelle se trouve entre 0 et 180 degres ou 0 et -180 degres
    if CurrentDirection < -180:

        CurrentDirection=CurrentDirection + 360
        
    # test si drone est connecté
    if DroneOn==1:
        
        # commande pour rotation du drone
        mambo.turn_degrees(-45)
        mambo.smart_sleep(1)



    updateGraphe ()

    
# ------------------------------------------------------------------------------
# Cette fonction fait une rotation a -135 deg en vol automatique

# ------------------------------------------------------------------------------
def moveSO():

    global CurrentDirection

    print("hello pretty move SO")

    CurrentDirection = CurrentDirection - 135
    
    # calcul de la nouvelle direction selon que la direction actuelle se trouve entre 0 et 180 degres ou 0 et -180 degres
    if CurrentDirection < -180:

        CurrentDirection=CurrentDirection + 360
        
    # test si drone est connecté
    if DroneOn==1:
        
        # commande pour rotation du drone
        mambo.turn_degrees(-135)
        mambo.smart_sleep(1)


    updateGraphe ()  

# ------------------------------------------------------------------------------
# Cette fonction fait une rotation a zero deg en vol automatique
# ------------------------------------------------------------------------------"""
def moveN():

    global CurrentDirection

    print("hello pretty move S")

    CurrentDirection = CurrentDirection + 0

    # calcul de la nouvelle direction selon que la direction actuelle se trouve entre 0 et 180 degres ou 0 et -180 degres
    if CurrentDirection > 180:

            CurrentDirection = CurrentDirection - 360

    # test si drone est connecté
    if DroneOn==1:
        
        # commande pour rotation du drone
        mambo.turn_degrees(0)
        mambo.smart_sleep(1)



    updateGraphe ()  

# ------------------------------------------------------------------------------
# Cette fonction fait une rotation a 180 deg en vol automatique

# ------------------------------------------------------------------------------
def moveS():

    global CurrentDirection

    print("hello pretty move S")

    CurrentDirection = CurrentDirection + 180

    # calcul de la nouvelle direction selon que la direction actuelle se trouve entre 0 et 180 degres ou 0 et -180 degres
    if CurrentDirection > 180:

            CurrentDirection = CurrentDirection - 360


    # test si drone est connecté
    if DroneOn==1:

        # commande pour rotation du drone
        mambo.turn_degrees(180)
        mambo.smart_sleep(1)

    updateGraphe ()  


# ------------------------------------------------------------------------------
# Cette fonction fait avancer le drone en vol automatique
# ------------------------------------------------------------------------------"""
def forward():

    print("--> forward")

    # le sommet vole est mis dans la liste des sommets volés
    Vol.append(SommetCourant)


    # test si drone est connecté
    if DroneOn==1:

        print("Flying direct: going backwards (negative pitch) 0.65/metre")

        # commande pour faire avancer le drone
        mambo.fly_direct(roll=0, pitch=50, yaw=0, vertical_movement=0, duration=0.65)
        mambo.smart_sleep(1)



# ------------------------------------------------------------------------------
# Cette fonction fait une rotation du drone en vol automatique

# ------------------------------------------------------------------------------
def rotate(angle):

    print("--> rotate " + str (angle))

    updateGraphe ()
    
    # test si drone est connecté
    if DroneOn==1:

        print("Showing turning (in place) using turn_degrees " + str (angle))
        
        # commande pour faire rotation du drone
        mambo.turn_degrees(angle)
        mambo.smart_sleep(2)





"""

VUE

Les fonctions utilitaires pour la visualisation graphique

    - testBordure ()

    - recupererCoord ()

    - convertPixelEnSommet ()

    - convertSommetEnPixel ()

    - convertPointEnCoord ()

    - convertCoordEnPoint ()

    - flipflop ()

"""   

 

# ------------------------------------------------------------------------------
# Cette fonction convertie des coordonnees pixel (x,y) en un numero de sommet du graphe. 
# La fonction retourne la valeur du Sommet

# NumeroSommet : Numero de sommet du graphe

# pixel_x : coordonnee X de l'evenement souris

# pixel_y : coordonnee Y de l'evenement souris

# ------------------------------------------------------------------------------"
def convertPixelEnSommet (pixel_x, pixel_y) :



    # Pour chaque Sommet recherche si les coordoonnees pixel_x, pixel_y appartiennent a son environement
    # on parcourt l'ensemble des sommets pour trouver lequel correspond aux coordonnées pixel x,y
    
    for i in range (NombreSommet): 

        # chaque sommet du graphe est converti en borne min/max x,y 
        # en effet chaque sommet est virtuellement a l'interieur d'une maille
        # ensuite on teste si les coordonnees pixel x,y se trouve à l'interieur de la maille
        # si c'est le cas, le sommet est trouve
        Y,X = convertPointEnCoord (i)

        x0 = ((X*EcartPixel) - EcartPixel/2) + Offset_x

        x1 = ((X*EcartPixel) + EcartPixel/2) + Offset_x

        y0 = ((Y*EcartPixel) - EcartPixel/2) + Offset_y

        y1 = ((Y*EcartPixel) + EcartPixel/2) + Offset_y

        if pixel_x > x0:

            if pixel_x <= x1:

                if pixel_y > y0:

                    if pixel_y <= y1:

                        return (i)



# ------------------------------------------------------------------------------
# Cette fonction convertie un numero de sommet en ses coordonnees pixel (x,y). La fonction retourne la valeur x,y

# NumeroSommet : Numero de sommet du graphe

# pixel_x : coordonnee X de l'evenement souris

# pixel_y : coordonnee Y de l'evenement souris
# ------------------------------------------------------------------------------
def convertSommetEnPixel (sommet) :

 
    # Conversion sommet en coordonnee Ligne, Colonne
    (L,C)=convertPointEnCoord(sommet)


    # Conversion de la coordonnee X,Y en coordonnee pixel x,y
    # il faut tenir compte de l'ecart pixel entre les ligne/colonne et également du decalage/offset de la fenetre
    # principal par rapport au bord de l'ecran
    pixel_x = (C*EcartPixel) + Offset_x
    pixel_y = (L*EcartPixel) + Offset_y

    return (pixel_x, pixel_y)


# ------------------------------------------------------------------------------
# Cette fonction convertie un numero de sommet de du graphe en coordonnees Ligne, Colonne du graphe. 
# La fonction retourne les valeurs Ligne, Colonne

# NumeroSommet : Numero de sommet du graphe

# Maille : nombre maximum de maille sur une ligne/colonne

# L : coordonnee Y
# C : coordonnee X
# ------------------------------------------------------------------------------
def convertPointEnCoord (NumeroSommet) :

    # Les coordoonnees ligne/colonne sont fonction du numero de sommet et du nombre de maille
    L= (NumeroSommet)//Maille
    C= (NumeroSommet - (L*Maille))

    return(L,C)



# ------------------------------------------------------------------------------
# Cette fonction convertie les coordonnees X,Y de la MNT en numero de Sommet de la MNT. La fonction retourne la valeur # NumeroSommet

# NumeroSommet : Numero de sommet du graphe

# Maille : nombre de maille sur une ligne/colonne

# L : coordonnee Y
# C : coordonnee X
# ------------------------------------------------------------------------------
def convertCoordEnPoint (X, Y) :

    # le numero de sommet est fonction de sa position ligne/colonne et du nombre de maille sur une ligne/colonne
    NumeroSommet = (Y* Maille) + (X)

    return(NumeroSommet)


# ------------------------------------------------------------------------------
# Cette fonction change la couleur d'une maille pour indiquer à l'utilisateur la zone qu'il a selectionné lorsqu'il 
# selectionne un sommet avec la souris
#
# NumeroSommet : Numero de sommet du graphe selectionné à la souris
# ------------------------------------------------------------------------------
def flipflop (S):

        # conversion du sommet en ligne/colonne
        (Y,X)=convertPointEnCoord (S)


        # calcul borne max/min x,y de la maille correspondant au sommet
        x0 = ((X*EcartPixel) - EcartPixel/2) + Offset_x

        x1 = ((X*EcartPixel) + EcartPixel/2) + Offset_x

        y0 = ((Y*EcartPixel) - EcartPixel/2) + Offset_y

        y1 = ((Y*EcartPixel) + EcartPixel/2) + Offset_y

        # la maille est affiché en couleur jaune pour indiquer la zone selectionné
        Can.create_rectangle(x0,y0,x1,y1,fill='yellow',width=2)

        # le graphe est redessiné avec la nouvelle couleur de la maille
        dessineGraphe ()

        



"""

VUE

Les fonctions de visualisation graphique

    - dessineMaille ()

    - dessineGraphe ()

    - dessineContrainte ()

        - displayStop ()

        - display SensInterdit ()

        - display FeuRouge ()

    - dessinePlanVol ()

    - dessinePlanVolDjisktra ()

    - dessineOrientationDrone ()

    - dessineVol ()

    - dessineNew ()

    - updateGraphe ()

"""   



# ------------------------------------------------------------------------------

# Cette fonction dessine une trame maille contenant en son centre un Sommet

# ------------------------------------------------------------------------------

def dessineMaille():
    
    global TableSommets

    # boucle pour dessiner une maille pour chaque sommet
    for u in range (NombreSommet):

        # conversion du sommet en ligne/colonne
        (Y,X)=convertPointEnCoord (u)

        # a partir des coordonnees ligne/colonne calcul des pixel x,y du sommet

        x0 = ((X*EcartPixel) - EcartPixel/2) + Offset_x

        x1 = ((X*EcartPixel) + EcartPixel/2) + Offset_x

        y0 = ((Y*EcartPixel) - EcartPixel/2) + Offset_y

        y1 = ((Y*EcartPixel) + EcartPixel/2) + Offset_y


        # test si le sommet est actif (il possede des routes avec ses voisins) la maille sera de couleur grise
        if TableSommets[u][2]!=-1:

            Can.create_rectangle(x0,y0,x1,y1,fill='light slate gray',width=1)

        else:
            # si le sommet n'a pas de route avec ses voisins, il est inactif, la maille sera de couleur verte
            Can.create_rectangle(x0,y0,x1,y1,fill='forest green',width=1)





# ------------------------------------------------------------------------------

# Fonction qui dessine le graphe en entier a partir du dictionnaire Graphe,

# de la table des sommets (coordonnees) et de la liste des acces (pour faire

# un point rouge sur les acces)

# ------------------------------------------------------------------------------

def dessineGraphe():

    global Graphe, TableSommets

    # liste des sommets qu'on aura deja traite pour ne pas dessiner plusieurs fois
    # le meme trait

    SommetsTraites=[]

    # boucle pour dessiner les traits
    # pour tous les sommets du graphe

    for u in range (NombreSommet):


        # on ajoute le sommet dans la liste des sommets traites
        SommetsTraites.append(u)


        # on recupere la ligne et la colonne
        ligne1=TableSommets[u][1]
        colonne1=TableSommets[u][0]

        # on recupere les coordonnes en pixel
        (x1,y1)=convertSommetEnPixel(u)


        # pour tous les voisins du sommet u
        for v in range (NombreSommet):

            if Graphe [u][v]!=-1:

                # on verifie que le sommet n'a pas deja ete traite
                if not v in SommetsTraites:

                    # on recupere les coordonnees pixel du sommet
                    (x2,y2)=convertSommetEnPixel (v)


                    # on trace la ligne entre le sommet u et le sommet v
                    Can.create_line(x1,y1,x2,y2,fill='white',width=5,dash=(2,2))


    # boucle pour dessiner les sommets-points rouges
    for s in range (NombreSommet):

        # on recupere les coordonnees pixel du sommet
        (x,y)=convertSommetEnPixel (s)

        x1=x+6
        y1=y+6
        x2=x-6
        y2=y-6

        # test si le sommet est actif
        if TableSommets[s][2]!=-1:

            # on dessine le sommet puisqu'il est actif
            Can.create_oval(x1,y1,x2,y2, fill='red', width=0)



# ------------------------------------------------------------------------------

# Fonction dessine les contraintes sur le reseau de route (stop, feu rouge, sens interdit, ...)

# ------------------------------------------------------------------------------

def dessineContrainte():

    global TableSommets

    # boucle pour dessiner une contrainte pour chaque sommet
    for u in range (NombreSommet):

        # test si il y a une signalisation stop sur ce sommet
        if TableSommets [u][2]==1:

            # affichage du stop
            displayStop (u)

        # test si il y a une signalisation feu rouge sur ce sommet
        elif TableSommets [u][2]==2:

            # affichage du feu rouge
            displayFeuRouge(u)

        # test si il y a une signalisation sens interdit sur ce sommet
        elif TableSommets [u][2]==3:

            # affichage sens interdit
            displaySensInterdit(u)


# ------------------------------------------------------------------------------

# Fonction dessine une signalisation stop

# Sommet : Sommet sur lequel il faut afficher une signalisation stop
# ------------------------------------------------------------------------------
def displayStop (Sommet):

    global Fen, imagestop

    # recuperation des pixel x,y correspondant au sommet
    (x1,y1)=convertSommetEnPixel (Sommet)

    # affichage de l'image stop
    Can.create_image(x1, y1, image=imagestop, anchor=CENTER)

    Can.pack(fill=BOTH, expand=1)


# ------------------------------------------------------------------------------

# Fonction dessine une signalisation feu rouge

# Sommet : Sommet sur lequel il faut afficher une signalisation feu rouge
# ------------------------------------------------------------------------------
def displaySensInterdit (Sommet):

    global Fen, imagestop

     # recuperation des pixel x,y correspondant au sommet
    (x1,y1)=convertSommetEnPixel (Sommet)

    # affichage de l'image feu rouge
    Can.create_image(x1, y1, image=imagesensinterdit, anchor=CENTER)

    Can.pack(fill=BOTH, expand=1)

# ------------------------------------------------------------------------------

# Fonction dessine une signalisation sens interdit

# Sommet : Sommet sur lequel il faut afficher une signalisation sens interdit
# ------------------------------------------------------------------------------

def displayFeuRouge (Sommet):

    global Fen, imagestop

    # recuperation des pixel x,y correspondant au sommet
    (x1,y1)=convertSommetEnPixel (Sommet)

    # test si le feu est orange
    if FeuRouge == -1:

        # affichage du feu orange
        Can.create_image(x1, y1, image=imagefeuorange, anchor=CENTER)

        Can.pack(fill=BOTH, expand=1)

    # test si le feu est vert
    elif FeuRouge == 0:

        # affichage du feu vert
        Can.create_image(x1, y1, image=imagefeuvert, anchor=CENTER)

        Can.pack(fill=BOTH, expand=1)

    # test si le feu est rouge
    elif FeuRouge == 1:

        # affichage du feu rouge
        Can.create_image(x1, y1, image=imagefeurouge, anchor=CENTER)

        Can.pack(fill=BOTH, expand=1)



# ------------------------------------------------------------------------------

# Fonction dessine le plan de vol

# ------------------------------------------------------------------------------

def dessinePlanVol ():

    # boucle pour dessiner le chemin vole par le drone
    for i in range (len(Chemin)-1):

        s1 = Chemin [i]
        s2 = Chemin [i+1]


        # on recupere les coordonnees pixel du sommet1
        (x1,y1)=convertSommetEnPixel (s1)

        # on recupere les coordonnees pixel du sommet2
        (x2,y2)=convertSommetEnPixel (s2)

        # on trace la ligne entre le sommet u et le sommet v
        Can.create_line(x1,y1,x2,y2,fill='black',width=6)




# ------------------------------------------------------------------------------

# Fonction dessine le plan de vol Djisktra (plus court chemin)

# ------------------------------------------------------------------------------
def dessinePlanVolDjisktra (Chemin):

    # pour l'ensemble des sommets representant le plus court chemin
    for i in range (len(Chemin)-1):

        s1 = Chemin [i]
        s2 = Chemin [i+1]

        # on recupere les coordonnees pixel du sommet1
        (x1,y1)=convertSommetEnPixel (s1)

        # on recupere les coordonnees pixel du sommet2
        (x2,y2)=convertSommetEnPixel (s2)

        # on trace la ligne entre le sommet u et le sommet v
        Can.create_line(x1,y1,x2,y2,fill='black',width=6,dash=(2,2))



# ------------------------------------------------------------------------------

# Fonction dessine les sommets voles en temps reel par le drone

# ------------------------------------------------------------------------------
def dessineVol ():

    # boucle pour dessiner le chemin vole par le drone
    for i in range (len(Vol)-1):

        s1 = Vol [i]
        s2 = Vol [i+1]

        # on recupere les coordonnees pixel du sommet1
        (x1,y1)=convertSommetEnPixel (s1)

        # on recupere les coordonnees pixel du sommet2
        (x2,y2)=convertSommetEnPixel (s2)

        # on trace la ligne entre le sommet u et le sommet v
        Can.create_line(x1,y1,x2,y2,fill='green',width=6,dash=(2,2))


# ------------------------------------------------------------------------------

# Fonction dessine sur le graphe l'orientation du drone a chaque changement de direction du drone
# l'orientation du drone est representée par une fleche bleu de direction à la position actuelle du drone

# ------------------------------------------------------------------------------

def dessineOrientationDrone ():

    global Fen, image

    # conversion du sommet en coordonnee pixel x,y
    (x1,y1)=convertSommetEnPixel (SommetCourant)


    # test sur la direction actuelle du drone (par rapport au Nord geographique)
    if CurrentDirection == 0:
        
        # direction Nord
        Can.create_image(x1, y1, image=imageflecheN, anchor=S)

    elif CurrentDirection == 45:

        # direction Nord Est
        Can.create_image(x1, y1, image=imageflecheNE, anchor=SW)

    elif CurrentDirection == 90:

        # direction Est
        Can.create_image(x1, y1, image=imageflecheE, anchor=W)

    elif CurrentDirection == 135:

        # direction Sud Est
        Can.create_image(x1, y1, image=imageflecheSE, anchor=NW)

    elif CurrentDirection == 180:

        # direction Sud
        Can.create_image(x1, y1, image=imageflecheS, anchor=N)

    elif CurrentDirection == -45:

        # direction Nord Ouest
        Can.create_image(x1, y1, image=imageflecheNW, anchor=SE)

    elif CurrentDirection == -90:

        # direction Ouest
        Can.create_image(x1, y1, image=imageflecheW, anchor=E)

    elif CurrentDirection == -135:

        # direction Sud Ouest
        Can.create_image(x1, y1, image=imageflecheSW, anchor=NE)

    elif CurrentDirection == -180:

        # direction Sud
        Can.create_image(x1, y1, image=imageflecheS, anchor=N) 


    Can.pack(fill=BOTH, expand=1)


# ------------------------------------------------------------------------------

# Fonction affiche le nombre de points restants du Permis

# ------------------------------------------------------------------------------

def dessinePermisPoint ():
    
    # acces au nombre de pointsndu permis
    comptPilote=getComptPilote()
    
    # test si on se trouve dans l'ihm pilotage (contexte comptpilote)
    if comptPilote == 1:
        # CANVAS
        # affichage du nombre de points du permis
        Can.create_rectangle(650,10,810,100,fill='palegreen',width=0)


# ------------------------------------------------------------------------------

# Remise à zero de du graphe

# ------------------------------------------------------------------------------

def dessineNew ():

    # remise à zero des contraintes
    # chaque sommet à une route vers tous ses voisins
    # tous les sommets sont actifs
    for u in range (NombreSommet):

       TableSommets[u][2]=0

    newGraphe (Graphe, NombreSommet)

    updateGraphe ()



# ------------------------------------------------------------------------------

# Cette fonction vient mettre à jour le Graphe afin de visualiser tous les changements en terme
# - nouvelle routes
# - sommets inactifs
# - contraintes
# - plan de vol en cours de definition
# - plan de vol en cours d'execution
# - orientation temps reel du drone
# - compteur du permis a points

# ------------------------------------------------------------------------------
def updateGraphe ():

    if HmiContext != 4:

        Can.delete('all')

        dessineMaille ()

        dessineGraphe ()

        dessineContrainte ()

        dessinePlanVolDjisktra (Chemin)

        dessinePlanVol ()

        dessineVol ()

        dessineOrientationDrone()

        dessinePermisPoint ()





"""

VUE

Les fonctions de gestion d'evenement graphique spécifique lié a un contexte (listener)

    - manageCreatePath ()

    - manageDeletePath ()

    - manageDesactiverSommet ()

    - manageStop ()

    - manageSensInterdit ()

    - manageFeuRouge ()

    - manageConnectDrone ()

    - manageDisconnectDrone ()

    - managePlanVolStart ()

    - managePlanVolStop ()

    - manageDjisktra ()

    - changerCouleurFeuRouge ()



"""   

# ------------------------------------------------------------------------------
# Cette fonction vient mettre à jour le contexte courant pour indiquer que les clic souris vont etre capturés pour
# la construction d'une route entre 2 sommets
# ------------------------------------------------------------------------------
def manageCreatePath ():

    global HmiContext

    # contextte de création de route entre 2 sommets
    HmiContext = 10

    NbSelectedPoint = 0  


# ------------------------------------------------------------------------------
# Cette fonction vient mettre à jour le contexte courant pour indiquer que les clic souris vont etre capturés pour
# la suppression d'une route entre 2 sommets
# ------------------------------------------------------------------------------
def manageDeletePath ():

    global HmiContext

    # contexte de suppression de route
    HmiContext = 9

    NbSelectedPoint = 0

    
# ------------------------------------------------------------------------------
# Cette fonction vient mettre à jour le contexte courant pour indiquer que les clic souris vont etre capturés pour
# la desactivation d'un sommet (tous les routes a ses sommets voisins sont supprimés
# ------------------------------------------------------------------------------
def managedesactiverSommet ():

    global HmiContext

    # contexte de desactivation d'un sommet
    HmiContext = 5

    
# ------------------------------------------------------------------------------
# Cette fonction vient mettre à jour le contexte courant pour indiquer que les clic souris vont etre capturés pour
# ajouter/supprimer une signalisation stop sur un sommet
# ------------------------------------------------------------------------------
def manageStop ():

    global HmiContext

    # contexte de creation/suppression signalisation stop
    HmiContext = 1


# ------------------------------------------------------------------------------
# Cette fonction vient mettre à jour le contexte courant pour indiquer que les clic souris vont etre capturés pour
# ajouter/supprimer une signalisation sens interdit sur un sommet
# ------------------------------------------------------------------------------
def manageSensInterdit () :

    global HmiContext

    # contexte de creation/suppression signalisation sens interdit
    HmiContext = 3


# ------------------------------------------------------------------------------
# Cette fonction vient mettre à jour le contexte courant pour indiquer que les clic souris vont etre capturés pour
# ajouter/supprimer une signalisation feu rouge sur un sommet
# ------------------------------------------------------------------------------
def manageFeuRouge () :

    global HmiContext

    # contexte de creation/suppression signalisation feu rouge
    HmiContext = 2


# ------------------------------------------------------------------------------
# Cette fonction vient activer la connection du drone
# ------------------------------------------------------------------------------
def manageconnectDrone ():

    global DroneOn

    # le drone est activé
    DroneOn =1
    
    # connection du drone
    connectDrone ()


# ------------------------------------------------------------------------------
# Cette fonction vient activer la deconnexion du drone
# ------------------------------------------------------------------------------
def manageDisconnectDrone ():

    global DroneOn

    # le drone est desactivé
    DroneOn =0

    # deconnexion du drone
    disconnectDrone ()


# ------------------------------------------------------------------------------
# Cette fonction vient mettre à jour le contexte courant pour indiquer que le Plan de Vol est activé et que tous
# les sommets selectionnés constitueront le plan de vol
# ------------------------------------------------------------------------------
def managePlanVolStart () :

    global HmiContext

    # remise a zero des listes constituant un plan de vol
    resetListe ()
    # contexte d'ouverture du plan de vol
    HmiContext = 4


# ------------------------------------------------------------------------------
# Cette fonction vient mettre à jour le contexte courant pour indiquer que le Plan de Vol est complet
# ------------------------------------------------------------------------------
def managePlanVolStop () :

    global start, SommetCourant
    global HmiContext

    # contexte de fermeture du plan de vol
    HmiContext = 0

    # initialisation du sommet de depart (premier sommet du plan de vol)
    start = Chemin[0]
    # sommet courant est le sommet de depart
    SommetCourant = Chemin[0]

    updateGraphe()


# ------------------------------------------------------------------------------
# Cette fonction vient mettre à jour le contexte courant pour indiquer que les clics souris
# vont definir le sommet de depart et le sommet d'arrivée pour trouver le chemin le plus court (djisktra)
# ------------------------------------------------------------------------------
def manageDjisktra ():

    global mb,label_permis,label_info,score

    global label_depart,button_stop,button_sensinterdit, button_feu,button_barrage,button_depart,label_crea,button_barrage2,button_barrage3

    global bouton_connect,bouton_disconnect,bouton_SO,bouton_SE,bouton_NE,bouton_nordO,label_commande,bouton_gauche,bouton_avancer,bouton_stop2, bouton_droit,bouton_S,bouton_decoller,bouton_atterir

    global HmiContext

    # obtention contexte IHM configuration routes/contraintes
    comptContrainte=getComptContrainte()

    # obtention contexte IHM configuration routes/contraintes
    comptPilote=getComptPilote()

    # si il y a les IHMde configuration routes, configuration contraintes, pilotage : il faut les effacer
    # pour visualiser IHM de selection djisktra
    if comptContrainte==1:#si il y a les boutons de contrainte

        button_stop.destroy()

        button_feu.destroy()

        button_barrage.destroy()

        button_barrage2.destroy()

        button_barrage3.destroy()

        button_depart.destroy()

        label_crea.destroy()

        label_depart.destroy()

        button_sensinterdit.destroy()

        setComptContrainte(0)

        print("trace 4")



    elif comptPilote==1: #si il y a les boutons de pilote

        print("trace 5")

        label_commande.destroy()

        bouton_gauche.destroy()

        bouton_droit.destroy()

        bouton_avancer.destroy()

        bouton_stop2.destroy()

        bouton_S.destroy()

        bouton_decoller.destroy()

        bouton_atterir.destroy()

        bouton_NE.destroy()

        bouton_N.destroy()

        bouton_nordO.destroy()

        bouton_SO.destroy()

        bouton_SE.destroy()

        bouton_connect.destroy()

        bouton_disconnect.destroy()

        label_info.destroy()

        label_permis.destroy()

        score.destroy()

        setComptPilote(0)

    
    # contexte de selection des sommets depart et arrivé
    HmiContext=6

    # remise a zero des listes constituant un plan de vol
    resetListe ()

# ------------------------------------------------------------------------------
# Cette fonction est thread qui vient changer les signaux du feu rouge (vert, orange, rouge) sur evenement timer.
# Cela cree un effet dynamique et plus realiste dans l'interface
# Le thread est activé toutes les secondes pour verifier le timer et changer etat feu rouge
# ------------------------------------------------------------------------------
def ChangerCouleurFeuRouge ():

    global FeuRouge
    global HmiContext

    # recuperation du temps reel
    chaine = str(datetime.now().time())

    # recuperation du champs [secondes]
    chaine1 = chaine[6:8]
    toto = int(chaine1)

    # selon l'intervalle au cours de 60 secondes, le feu est dans l'état vert, orange ou rouge
    # feu passe au rouge toutes les 7 secondes
    if 0 <= toto < 3 or 10 <= toto < 13 or 20 <= toto < 23 or 30 <= toto < 33 or 40 <= toto < 43 or 50 <= toto < 53 :

        if FeuRouge == 1 or FeuRouge == 0:

            FeuRouge = -1

        
    # feu passe a orange toute les 7 secondes
    if 3 <= toto < 6 or 13 <= toto < 16 or 23 <= toto < 26 or 33 <= toto < 36 or 43 <= toto < 46 or 53 <= toto < 56 :

        if FeuRouge == 0 or FeuRouge == -1:

            FeuRouge = 1

    # feu passe au vert toute les 7 secondes
    if 6 <= toto < 10 or 16 <= toto < 20 or 26 <= toto < 30 or 36 <= toto < 40 or 46 <= toto < 50 or 56 <= toto < 60 :

        if FeuRouge == 1 or FeuRouge == -1:

            FeuRouge = 0

    # Comme le thread tourne en tache de fond il ne faut pas tout le temps updater le graphe pour mise a jour
    # des etats du feu rouge
    # en particulier il ne faut pas updater le graphe si il y un contexte deja ouvert dessus (par exemple saisie 
    # des sommets d'un plan de vol
    if HmiContext ==0:
        updateGraphe()

    # relance du thread
    Can.after (1000, ChangerCouleurFeuRouge)



"""

VUE

Les fonctions de visualisation des menus principaux

    - debut ()

    - initChoixContrainte ()

    - initCHoixDirection ()

    - initChoixRoute ()

    - orientationUp ()

    - orientationDown ()

    - orientationRight ()

    - orientationLeft ()

    - choix_depart()

    - contrainte ()

    - route ()

    - pilote ()

    - setComptContrainte ()

    - setComptRoute ()

    - setComptPilote ()

    - getComptContrainte ()

    - getComptRoute ()

    - getComptPilote ()

"""   


# ------------------------------------------------------------------------------
# Cette fonction affiche le menu principal du programme
# ------------------------------------------------------------------------------
def debut():

    global comptpilote
    global comptcontrainte
    global HmiContext
    global Chemin
    global Visites
    global Distances
    global Precedents
    global bouton_tuto
    global bouton_debut

    setComptContrainte(0)
    setComptPilote(0)
    setComptRoute(0)

    
    # destruction des elements ihm de la page d'acceuil
    bouton_tuto.destroy()
    bouton_debut.destroy()


    HmiContext = 0


    # affichage d'un graphe par defaut
    newGraphe (Graphe, NombreSommet)
    dessineMaille ()
    dessineGraphe ()


    # affiche les sous menus de la fenetre (file, configuration, plan de vol, pilotage)
    menubar=Menu(Fen)



    menu1=Menu(menubar,tearoff=0)

    menu2=Menu(menubar,tearoff=0)

    menu3=Menu(menubar,tearoff=0)

    menu4=Menu(menubar,tearoff=0)



    menubar.add_cascade(label="File",menu=menu1)

    menubar.add_cascade(label="Configuration",menu=menu2)

    menubar.add_cascade(label="Plan Vol",menu=menu3)

    menubar.add_cascade(label="Pilotage",menu=menu4)


    # sous menu de 'file' (New, Save, Load)
    menu1.add_command(label="New",command=dessineNew)

    menu1.add_command(label="Save",command=boutonSave)

    menu1.add_command(label="Load",command=boutonLoad)

    
    # sous menu de configuration
    menu2.add_command(label="Start",command=contrainte)


    # sous menu de plan de vol (manuel, djisktra, resetListe)
    menu3.add_command(label="Manuel",command=route)

    menu3.add_command(label="Djisktra",command=manageDjisktra)

    menu3.add_command(label="Reset",command=resetListe)


    # sous menu de pilotage (manuel, executer plan de vol)
    menu4.add_command(label="Manuel",command=pilote)

    menu4.add_command(label="Executer Plan Vol",command=executeFlightPlan)



    Fen.config(menu=menubar)

    # initialisation de l'orientation du drone
    initOrientationDrone(0)
    updateGraphe()



    # on initialise les listes et dictionnaires utilise par dijkstra

    Chemin=[]
    Visites=[]
    Distances={}
    Precedents={}

    # lancement du thread pour animer dynamiquement les changements d'états des feu rouge
    Can.after (5000, ChangerCouleurFeuRouge)



# ------------------------------------------------------------------------------
# Cette fonction affiche le menu pour configurer les routes et les contraintes
# ------------------------------------------------------------------------------
def initChoixContrainte():

    global label_depart,label_crea,button_stop,button_feu,button_sensinterdit,button_barrage,button_depart,button_barrage2,button_barrage3

    #Can.create_rectangle(560,0,760,200,fill='pink',width=0)



    label_crea=Label(Fen,text="CONTRAINTES & ROUTES")

    label_crea.place(x=650,y=300)


    # sur clic bouton stop, declenchement du listener manageStop
    button_stop=Button(Fen,text='STOP',command=manageStop)
    button_stop.place(x=690,y=350)

    # sur clic bouton feu rouge, declenchement du listener manageFeuRouge 
    button_feu=Button(Fen,text='FEU ROUGE',command=manageFeuRouge)
    button_feu.place(x=673,y=400)

    # sur clic bouton sens interdit, declenchement du listener sens interdit
    button_sensinterdit=Button(Fen,text='SENS INTERDIT',command=manageSensInterdit)
    button_sensinterdit.place(x=660,y=450)

    # sur clic bouton barrer route, declenchement du listener manageDeletePath
    button_barrage=Button(Fen,text='BARRER ROUTE',command=manageDeletePath)
    button_barrage.place(x=660,y=500)

    # sur clic bouton creer route, declenchement du listener manageCreatePath
    button_barrage2=Button(Fen,text='CREER ROUTE',command=manageCreatePath)
    button_barrage2.place(x=665,y=550)

    # sur clic bouton enlever sommet, declenchement du listener managedesactiverSommet
    button_barrage3=Button(Fen,text='ENLEVER SOMMET',command=managedesactiverSommet)

    button_barrage3.place(x=650,y=600)


    # choix de l'orientation du drone au depart
    label_depart=Label(Fen,text="Choix du départ")
    label_depart.place(x=670,y=60)


    button_depart=Button(Fen,text='DEPART',command=choix_depart)
    button_depart.place(x=684,y=110)


# ------------------------------------------------------------------------------
# Cette fonction affiche le menu pour piloter le drone (commandes directionnelles)
# ------------------------------------------------------------------------------
def initChoixDirection():

    global bouton_connect,bouton_disconnect,bouton_SE,bouton_SO,bouton_nordO,bouton_NE,bouton_N, bouton_gauche,bouton_droit,bouton_avancer,bouton_S,bouton_demitour,bouton_atterir,label_commande,bouton_decoller, bouton_stop2

    global label_permis,label_info,score
    global Sv



    # CANVAS

    Can.create_rectangle(650,10,810,100,fill='palegreen',width=0)



    # LABEL

    label_commande=Label(Fen,text="COMMANDES DIRECTIONNELLES")
    label_commande.place(x=640,y=310)


    # affichage des points de permis
    label_permis=Label(Fen,text="Vos points de permis")
    label_permis.place(x=675,y=30)

    label_info=Label(Fen,text="/12")
    label_info.place(x=760,y=80)


    score=Label(Fen,textvariable=Sv)

    Sv.set("12")

    score.place(x=740,y=80)

    

    # BOUTONS


    #bouton pour connecter le drone : connection bluetooth entre l'application et le drone
    bouton_connect=Button(Fen,text="Connect",bg='red',fg='blue',command=manageconnectDrone)
    bouton_connect.place(x=700,y=130)


    #bouton pour déconnecter le drone : connection bluetooth entre l'application et le drone
    bouton_disconnect=Button(Fen,text="Disconnect",command=manageDisconnectDrone)
    bouton_disconnect.place(x=690,y=170)


    #bouton pour faire decoller le drone
    bouton_decoller=Button(Fen,text="decoller",command=takeoff)
    bouton_decoller.place(x=700,y=210)


    #bouton pour faire atterir le drone
    bouton_atterir=Button(Fen,text="atterrir",command=landing)
    bouton_atterir.place(x=702,y=250)

    
    #bouton pour faire avancer le drone
    bouton_avancer=Button(Fen,image=imagego,command=xmoveforward)
    bouton_avancer.place(x=750,y=350)

     
    #bouton pour mise en vol stationnaire du drone
    bouton_stop2=Button(Fen,image=imagepause,command=xstop)
    bouton_stop2.place(x=685,y=350) 


    # bouton pour orienter le drone West
    bouton_gauche=Button(Fen,image=imagedirectionW,command=xmoveW)
    bouton_gauche.place(x=650,y=485)



    # bouton pour orienter le drone East
    bouton_droit=Button(Fen,image=imagedirectionE,command=xmoveE)
    bouton_droit.place(x=780,y=485)


    #bouton pour orienter le drone South
    bouton_S=Button(Fen,image=imagedirectionS,command=xmoveS)
    bouton_S.place(x=715,y=550)


    #bouton pour orienter le drone North
    bouton_N=Button(Fen,image=imagedirectionN,command=xmoveN)
    bouton_N.place(x=715,y=420)


    #bouton pour orienter le drone North East
    bouton_NE=Button(Fen,image=imagedirectionNE,command=xmoveNE)
    bouton_NE.place(x=780,y=420)


    #drone pour orienter le drone North West
    bouton_nordO=Button(Fen,image=imagedirectionNW,command=xmoveNO)
    bouton_nordO.place(x=650,y=420)


    #bouton pour orienter le drone South West
    bouton_SO=Button(Fen,image=imagedirectionSW,command=xmoveSO)
    bouton_SO.place(x=650,y=550)



    #bouton pour orienter le drone South East
    bouton_SE=Button(Fen,image=imagedirectionSE,command=xmoveSE)
    bouton_SE.place(x=780,y=550)



# ------------------------------------------------------------------------------
# Cette fonction affiche le menu pour definir un plan de vol (route)
# ------------------------------------------------------------------------------
def initChoixRoute():

    global button_start,button_stop2


    #bouton activant la saisie des sommets constituant le plan de vol
    button_start=Button(Fen,text='START',command=managePlanVolStart)
    button_start.place(x=690,y=300)

    #bouton terminant la saisis des sommets constituant le plan de vol
    button_stop2=Button(Fen,text='STOP',command=managePlanVolStop)
    button_stop2.place(x=690,y=350)


# ------------------------------------------------------------------------------
# Cette fonction initialise l'orientation du drone à 0 degré par rapport au Nord
# ------------------------------------------------------------------------------
def orientationUp():

    initOrientationDrone (0)

    
# ------------------------------------------------------------------------------
# Cette fonction initialise l'orientation du drone à 180 degré par rapport au Nord
# ------------------------------------------------------------------------------
def orientationDown():

    initOrientationDrone (180)

     
# ------------------------------------------------------------------------------
# Cette fonction initialise l'orientation du drone à 90 degré par rapport au Nord
# ------------------------------------------------------------------------------
def orientationRight():

    initOrientationDrone (90)

                
# ------------------------------------------------------------------------------
# Cette fonction initialise l'orientation du drone à -90 degré par rapport au Nord
# ------------------------------------------------------------------------------
def orientationLeft():

    initOrientationDrone (-90)


# ------------------------------------------------------------------------------
# Cette fonction visualise le choix pour l'orientation initiale du drone
# ------------------------------------------------------------------------------
def choix_depart():

    global mb

    mb=Menubutton( Fen, text="CHOISIR ORIENTATION", relief=RAISED)

    mb.place(x=655,y=160)

    mb.menu =  Menu ( mb, tearoff = 0 )

    mb["menu"] =  mb.menu


    # orientation à 0 degré
    mb.menu.add_command(label="up",command=orientationUp)

    # orientation à -90 degré
    mb.menu.add_command(label="left",command=orientationLeft)

    # orientation à +90 degré
    mb.menu.add_command(label="right",command=orientationRight)

    # orientation à +180 degré
    mb.menu.add_command(label="down",command=orientationDown)




# ------------------------------------------------------------------------------
# Cette fonction visualise le choix des configuration de contraintes
# ------------------------------------------------------------------------------
def contrainte():

    global mb,label_info,label_permis,score

    global bouton_connect,bouton_disconnect,bouton_SO,bouton_SE,bouton_NE,bouton_N, bouton_nordO,label_commande,bouton_gauche,bouton_avancer,bouton_droit,bouton_S,bouton_decoller,bouton_atterir, bouton_stop2

    global button_start,button_stop2


    # recuperation des contextes affichage ihm pilote et route
    comptRoute=getComptRoute()
    comptPilote=getComptPilote()

    print("depuis contrainte(): "+str(comptPilote))

    #si il y a les boutons pilotes dans la fenetre il faut les effacer
    if comptPilote==1: 

        print("trace 1")

        label_commande.destroy()

        bouton_gauche.destroy()

        bouton_droit.destroy()

        bouton_avancer.destroy()

        bouton_stop2.destroy ()

        bouton_S.destroy()

        bouton_decoller.destroy()

        bouton_atterir.destroy()

        bouton_NE.destroy()

        bouton_N.destroy()

        bouton_nordO.destroy()

        bouton_SO.destroy()

        bouton_SE.destroy()

        bouton_connect.destroy()

        bouton_disconnect.destroy()

        label_info.destroy()

        label_permis.destroy()

        score.destroy()

        setComptPilote(0)

        initChoixContrainte()

        setComptContrainte(1)

    #si il y a les boutons de route
    elif comptRoute==1: 

        print("trace 2")

        button_start.destroy()

        button_stop2.destroy()

        setComptRoute(0)

        initChoixContrainte()

        setComptContrainte(1)

    else:

        # affichage pour configuration des contraintes
        print("trace 3")

        initChoixContrainte()
        setComptContrainte(1)


# ------------------------------------------------------------------------------
# Cette fonction visualise le choix des configuration des routes
# ------------------------------------------------------------------------------
def route():

    global mb,label_permis,label_info,score

    global label_depart,button_stop,button_sensinterdit, button_feu,button_barrage,button_depart,label_crea,button_barrage2,button_barrage3

    global bouton_connect,bouton_disconnect,bouton_SO,bouton_SE,bouton_NE,bouton_nordO,label_commande,bouton_gauche,bouton_avancer,bouton_stop2, bouton_droit,bouton_S,bouton_decoller,bouton_atterir


    # recuperation des contextes affichage ihm pilote et contrainte
    comptContrainte=getComptContrainte()
    comptPilote=getComptPilote()

    #si il y a les boutons de contrainte
    if comptContrainte==1:

        button_stop.destroy()

        button_feu.destroy()

        button_barrage.destroy()

        button_barrage2.destroy()

        button_barrage3.destroy()

        button_depart.destroy()

        label_crea.destroy()

        label_depart.destroy()

        button_sensinterdit.destroy()

        setComptContrainte(0)

        print("trace 4")

        initChoixRoute()

        setComptRoute(1)

    #si il y a les boutons de pilote
    elif comptPilote==1:

        print("trace 5")

        label_commande.destroy()

        bouton_gauche.destroy()

        bouton_droit.destroy()

        bouton_avancer.destroy()

        bouton_stop2.destroy()

        bouton_S.destroy()

        bouton_decoller.destroy()

        bouton_atterir.destroy()

        bouton_NE.destroy()

        bouton_N.destroy()

        bouton_nordO.destroy()

        bouton_SO.destroy()

        bouton_SE.destroy()

        bouton_connect.destroy()

        bouton_disconnect.destroy()

        label_info.destroy()

        label_permis.destroy()

        score.destroy()

        setComptPilote(0)

        initChoixRoute()

        setComptRoute(1)

    else:

        # affichage pour configuration des contraintes
        print("trace 6")

        setComptRoute(1)

        initChoixRoute()




# ------------------------------------------------------------------------------
# Cette fonction visualise le menu pour pilotage du drone
# ------------------------------------------------------------------------------
def pilote():

    global button_barrage2,button_barrage3,button_stop,label_depart,button_stop,button_sensinterdit, button_feu,button_barrage,button_depart,label_crea

    global button_start,button_stop2


    # recuperation des contextes affichage ihm route et contrainte
    comptContrainte=getComptContrainte()
    comptRoute=getComptRoute()

    print("depuis pilote(): "+str(comptContrainte))

    #si il y a les boutons creation danxs la fenetre
    if comptContrainte==1: 

        button_stop.destroy()

        button_sensinterdit.destroy()

        button_feu.destroy()

        button_barrage.destroy()

        button_barrage2.destroy()

        button_barrage3.destroy()

        button_depart.destroy()

        label_crea.destroy()

        label_depart.destroy()

        button_stop.destroy()

        setComptContrainte(0)

        print("trace 7")

        initChoixDirection()

        setComptPilote(1)

    #si il y a les boutons de route
    elif comptRoute==1: 

        print("trace 8")

        button_start.destroy()

        button_stop2.destroy()

        setComptRoute(0)

        initChoixDirection()

        setComptPilote(1)

    else:

        # affichage pour pilotage
        print("trace 9")

        initChoixDirection()

        setComptPilote(1)



 
# ------------------------------------------------------------------------------
# Cette fonction met a jour le contexte du menu contrainte
# ------------------------------------------------------------------------------
def setComptContrainte(val):

    global comptcontrainte

    comptcontrainte=val


# ------------------------------------------------------------------------------
# Cette fonction met a jour le contexte du menu configuration route
# ------------------------------------------------------------------------------
def setComptRoute(val):

    global comptroute

    comptroute=val

# ------------------------------------------------------------------------------
# Cette fonction met a jour le contexte du menu de pilotage
# ------------------------------------------------------------------------------
def setComptPilote(val):

    global comptpilote

    comptpilote=val

# ------------------------------------------------------------------------------
# Cette fonction recupere le contexte du menu configuration contraintes
# ------------------------------------------------------------------------------
def getComptContrainte():

    global comptcontrainte

    return comptcontrainte


# ------------------------------------------------------------------------------
# Cette fonction recupere le contexte du menu configuration routes
# ------------------------------------------------------------------------------
def getComptRoute():

    global comptroute

    return comptroute


# ------------------------------------------------------------------------------
# Cette fonction recupere le contexte du menu de pilotage
# ------------------------------------------------------------------------------
def getComptPilote():

    global comptpilote

    return comptpilote


def null():

    print ("null")



def boutonSave():
    global saisie,fsave
    fsave=Tk()
    fsave.title("Sauvegarde")
    
    labelBoutonSave=Label(fsave,text="Entrez le nom de votre carte")
    labelBoutonSave.pack()
    
    saisie=Entry(fsave,width=10)
    saisie.pack()
    
    boutonOkSave=Button(fsave,text="Valider",command=OkSave)
    boutonOkSave.pack()
    
   
    
def OkSave():
    global saisie,nomMapSave,fsave
    
    nomMapSave=saisie.get()
    print("nomMapSave 1 :", nomMapSave)
    save()
    fsave.destroy()
    
def boutonLoad():
    global lbx,selected_item,listeNomMap
    global fload,list
    fload=Tk()
    fload.title("Récupération")
    
    #label
    labelBoutonLoad=Label(fload,text="Choisissez votre carte : ")
    labelBoutonLoad.grid(row=0,column=0)
    
    # création listbox
    lbx = Listbox(fload)
    
    getName()
    print ("xxxx :", listeNomMap)

    list_a = list(listeNomMap)
    len_a = len(listeNomMap)
    liste = list(range(0, len_a))
    message = ""
    wordlist = [ch for ch in message]
    len_wl = len(wordlist)
    for x in liste:
        print (list_a[x])
        valeur=list_a[x]
        lbx.insert(x, valeur)
    
    lbx.select_set(0)
    lbx.grid(row=1, column=0)
    
    # on crée une variable StringVar() pour stocker la
    # valeur de l'item sélectionné
    selected_item = StringVar()
 

    # bouton
    bt = Button(fload, text="Valider", command=OkLoad)
    bt.grid(row=2, column=0)
    
    
def OkLoad():
    global lbx,selected_item, nomMapLoad

    line = lbx.curselection()[0]
    item = lbx.get(line)
    # on affecte la valeur de l'item à la variable :
    selected_item.set(item)
    print(selected_item.get())
    nomMapLoad=selected_item.get()
    load()
    fload.destroy()
#--------------------------------------------------------------------------------------------------------------

# Interface tutoriel de l'application

# Elle reprend la quasi totalité du programme remanié afin de na pouvoir executer que certaines actions

# et ainsi guider le joue en ne pouvant selectionner que certaines actions.

#

#--------------------------------------------------------------------------------------------------------------



def tuto():

    global comptpilote

    global comptcreate

    global HmiContext

    global chemin

    global visites

    global distances

    global precedents

    global menu1

    global menu2

    global menu3

    global menu4



    

    

    setComptContrainte(0)

    setComptPilote(0)

    setComptRoute(0)

    

    bouton_tuto.destroy()

    bouton_debut.destroy()







    HmiContext = 0



    newGraphe (Graphe, NombreSommet)

    dessineMaille ()

    dessineGraphe ()





    menubar=Menu(Fen)



    menu1=Menu(menubar,tearoff=0)

    menu2=Menu(menubar,tearoff=0)

    menu3=Menu(menubar,tearoff=0)

    menu4=Menu(menubar,tearoff=0)



    menubar.add_cascade(label="File",menu=menu1)

    menubar.add_cascade(label="Configuration",menu=menu2)

    menubar.add_cascade(label="Plan Vol",menu=menu3)

    menubar.add_cascade(label="Pilotage",menu=menu4)

    

    menu2.add_command(label="Start",command=initChoixContrainteTuto)



    Fen.config(menu=menubar)



    initOrientationDrone(0)

    updateGraphe()



    # on initialise les listes et dictionnaires utilise par dijkstra

    chemin=[]

    visites=[]

    distances={}

    precedents={}





    Can.after (5000, ChangerCouleurFeuRouge)



    afficheAideTuto()



def routeTuto():

    global mb,label_permis,label_info,score

    global label_depart,button_stop,button_sensinterdit, button_feu,button_barrage,button_depart,label_crea,button_barrage2,button_barrage3

    global bouton_connect,bouton_disconnect,bouton_SO,bouton_SE,bouton_NE,bouton_nordO,label_commande,bouton_gauche,bouton_avancer,bouton_stop2, bouton_droit,bouton_S,bouton_decoller,bouton_atterir



    comptCreate=getComptContrainte()

    comptPilote=getComptPilote()



    Can10.destroy()



    button_stop.destroy()

    button_feu.destroy()

    button_barrage.destroy()

    button_barrage2.destroy()

    button_barrage3.destroy()

    button_depart.destroy()

    label_crea.destroy()

    label_depart.destroy()

    button_sensinterdit.destroy()

    setComptContrainte(0)

    initChoixRoute()

    setComptRoute(1)



    afficheAideR1()



def piloteTuto():

    global button_barrage2,button_barrage3,button_stop,label_depart,button_stop,button_sensinterdit, button_feu,button_barrage,button_depart,label_crea

    global button_start,button_stop2



    CanR5.destroy()



    comptCreate=getComptContrainte()

    comptRoute=getComptRoute()

    print("depuis pilote(): "+str(comptCreate))

    

    print("trace 9")

    initChoixDirection()

    setComptPilote(1)



    afficheAideP1()



# Affichage de la première fenêtre d'aide



def afficheAideTuto():

    global CanT

    CanT=Canvas(Fen,width=550,height=110,relief="groove",bd=5)

    CanT.create_text(275,55,text="Bienvenue dans le tutoriel de cete application. Vous allez apprendre ici à utiliser\ncette application et piloter votre drone en découvrant les différentes options\nmises à votre disposition.\n\nPour commencer, selectionnez \"configuration\" puis \"start\"")

    CanT.place(x=600, y=60)



def initChoixContrainteTuto():

    global label_depart,label_crea,button_stop,button_feu,button_sensinterdit,button_barrage,button_depart,button_barrage2,button_barrage3



    CanT.destroy()



    label_crea=Label(Fen,text="CONTRAINTES")

    label_crea.place(x=680,y=300)



    button_stop=Button(Fen,text='STOP',command=manageStop)

    button_stop.place(x=690,y=350)



    button_feu=Button(Fen,text='FEU ROUGE',command=manageFeuRouge)

    button_feu.place(x=673,y=400)

    

    button_sensinterdit=Button(Fen,text='SENS INTERDIT',command=manageSensInterdit)

    button_sensinterdit.place(x=660,y=450)



    button_barrage=Button(Fen,text='BARRER ROUTE',command=manageDeletePath)

    button_barrage.place(x=660,y=500)



    button_barrage2=Button(Fen,text='CREER ROUTE',command=manageCreatePath)

    button_barrage2.place(x=665,y=550)

    

    button_barrage3=Button(Fen,text='ENLEVER SOMMET',command=managedesactiverSommet)

    button_barrage3.place(x=650,y=600)



    label_depart=Label(Fen,text="Choix du départ")

    label_depart.place(x=670,y=60)



    button_depart=Button(Fen,text='DEPART',command=choix_depart)

    button_depart.place(x=684,y=110)



    afficheAide1()



#affichage des aides de la partie réation de carte

def afficheAide1():

    global Can1

    global button_aide2

    Can1=Canvas(Fen,width=505, height=95,relief='groove',bd=5)

    Can1.create_text(255,35,text="Le cadre ci-dessus représente la carte sur laquelle le drone va se déplacer.\nLes points rouges représentent les intersections, tandis que\nles traits blancs représentent les chemins que le drone peut emprunter.")

    Can1.place(x=60, y=600)

    button_aide2=Button(Fen,text="Suivant",command=afficheAide2)

    button_aide2.place(x=470,y=665)



def afficheAide2():

    global Can2

    global button_aide3

    Can1.destroy()

    button_aide2.destroy()

    Can2=Canvas(Fen,width=350, height=165,relief='groove',bd=5)

    Can2.create_text(180,70,text="L'emplacement choix de départ permet de choisir\nl'orientation de départ du drone sur le plan.\n\nATTENTION ! Le sens de départ du drone sur\nl'interface de l'applicaion doit être identique\nà la position du drone dans votre espace physique.")

    Can2.place(x=800, y=60)

    button_aide3=Button(Fen,text="Suivant",command=afficheAide3)

    button_aide3.place(x=1050,y=195)



def afficheAide3():

    global Can3

    global button_aide4

    Can2.destroy()

    button_aide3.destroy()

    Can3=Canvas(Fen,width=350, height=110,relief='groove',bd=5)

    Can3.create_text(180,40,text="L'emplacement contraintes permet de choisir\nles différents obstacles que vous pourrez placer\nsur le plan.")

    Can3.place(x=800, y=360)

    button_aide4=Button(Fen,text="Suivant",command=afficheAide4)

    button_aide4.place(x=1050,y=440)



def afficheAide4():

    global Can4

    global button_aide5

    Can3.destroy()

    button_aide4.destroy()

    Can4=Canvas(Fen,width=350, height=165,relief='groove',bd=5)

    Can4.create_text(180,70,text="Sélectionnez \"départ\" puis la direction\ndans laquelle vous souhaitez que le drone parte puis\nplacez le sur le plan.\n\nATTENTION ! Le sens de départ du drone sur\nl'interface de l'applicaion doit être identique\nà la position du drone dans votre espace physique.")

    Can4.place(x=825, y=60)

    button_aide5=Button(Fen,text="Suivant",command=afficheAide5)

    button_aide5.place(x=1075,y=195)



def afficheAide5():

    global Can5

    global button_aide6

    Can4.destroy()

    button_aide5.destroy()

    Can5=Canvas(Fen,width=365,height=130,relief='groove',bd=5)

    Can5.create_text(187,45,text="Vous souhaitez placer un STOP, un FEU\nTRICOLORE ou un SENS INTERDIT sur votre carte ?\nSélectionnez l'une de ces trois options puis placez-la à\nl'intersection de votre choix.")

    Can5.place(x=820,y=360)

    button_aide6=Button(Fen,text="Suivant",command=afficheAide6)

    button_aide6.place(x=1060,y=460)



def afficheAide6():

    global Can6

    global button_aide7

    Can5.destroy()

    button_aide6.destroy()

    Can6=Canvas(Fen,width=320,height=140,relief='groove',bd=5)

    Can6.create_text(170,60,text="Vous souhaitez barrer une route et la\nfaire disparaître ?\nSélectionnez l'option BARRER ROUTE puis\nsélectionnez deux intersections adjacentes\nentre lesquelles vous souhaitez supprimer\nla route.")

    Can6.place(x=825,y=360)

    button_aide7=Button(Fen,text="Suivant",command=afficheAide7)

    button_aide7.place(x=1050,y=470)



def afficheAide7():

    global Can7

    global button_aide8

    Can6.destroy()

    button_aide7.destroy()

    Can7=Canvas(Fen,width=320,height=140,relief='groove',bd=5)

    Can7.create_text(170,60,text="Vous souhaitez recréer une route et la\nfaire réaparaître ?\nSélectionnez l'option CREER ROUTE puis\nsélectionnez deux intersections adjacentes\nentre lesquelles vous souhaitez recréer\nla route.")

    Can7.place(x=825,y=360)

    button_aide8=Button(Fen,text="Suivant",command=afficheAide8)

    button_aide8.place(x=1050,y=470)



def afficheAide8():

    global Can8

    global button_aide9

    Can7.destroy()

    button_aide8.destroy()

    Can8=Canvas(Fen,width=320,height=140,relief='groove',bd=5)

    Can8.create_text(170,60,text="Vous pouvez supprimer un sommet et toutes\nses routes en selectionnant\nl'option SUPPRIMER SOMMET puis en\nsélectionnant un sommet.\nVous pourrer ensuite le recréer avec\nl'option CREER ROUTE.")

    Can8.place(x=825,y=360)

    button_aide9=Button(Fen,text="Suivant",command=afficheAide9)

    button_aide9.place(x=1050,y=470)



def afficheAide9():

    global Can9

    global button_aide10

    Can8.destroy()

    button_aide9.destroy()

    Can9=Canvas(Fen,width=320,height=175,relief='groove',bd=5)

    Can9.create_text(170,80,text="Si votre carte ne vous convient pas, vous\npouvez en créer une nouvelle en\nsélectionnant \"File\" dans la barre de menu\npuis \"New\".\n\nSi la carte vous convient, vous\npouvez la sauvegarder en selectionnant\n\"File\" puis \"Save\".")

    Can9.place(x=825,y=360)



    menu1.add_command(label="New",command=dessineNew)

    menu1.add_command(label="Save",command=boutonSave)

    menu1.add_command(label="Load",command=boutonLoad)



    button_aide10=Button(Fen,text="Suivant",command=afficheAide10)

    button_aide10.place(x=1050,y=500)



def afficheAide10():

    global Can10

    Can9.destroy()

    button_aide10.destroy()

    Can10=Canvas(Fen,width=320,height=100,relief='groove',bd=5)

    Can10.create_text(170,50,text="Pour passer au tutoriel de plan de vol,\nselectionnez \"Plan Vol\" puis\n\"Manuel\" dans la barre de menu.")

    Can10.place(x=825,y=360)



    menu3.add_command(label="Manuel",command=routeTuto)



#affichage des aides de la partie plan de vol

def afficheAideR1():

    global CanR1

    global button_aideR1

    CanR1=Canvas(Fen,width=550,height=210,relief='groove',bd=5)

    CanR1.create_text(275,85,text="Vous voici dans l'interface de plan de vol, vous pourrez ici donnez à votre drone\nun chemin à effectuer.\n\nAfin de créer un plan de vol, sélectionnez d'abord le bouton \"START\".\n\nSélectionnez ensuite une suite de cases reliées par des routes qui vont définir\nvotre chemin\n\nUne fois votre chemin terminé cliquez sur \"STOP\" pour confirmer votre chemin.")

    CanR1.place(x=600, y=60)

    button_aideR1=Button(Fen,text="Suivant",command=afficheAideR2)

    button_aideR1.place(x=1050,y=230)



def afficheAideR2():

    global CanR2

    global button_aideR2

    CanR1.destroy()

    button_aideR1.destroy()

    CanR2=Canvas(Fen,width=550,height=125,relief='groove',bd=5)

    CanR2.create_text(275,50,text="Afin d'éxecuter votre plan de vol, sélectionnez dans la barre de menu \"Pilotage\"\npuis \"Executer plan vol\".\n\nSi vous souhaitez modifier votre trajet, sélectionnez \"Reset\" dans le menu\n\"Plan vol\".")

    CanR2.place(x=600, y=60)

    button_aideR2=Button(Fen,text="Suivant",command=afficheAideR3)

    button_aideR2.place(x=1050,y=155)



    menu3.add_command(label="Reset",command=resetListe)

    menu4.add_command(label="Executer Plan Vol",command=executeFlightPlan)



def afficheAideR3():

    global CanR3

    global button_aideR3

    CanR2.destroy()

    button_aideR2.destroy()

    CanR3=Canvas(Fen,width=550,height=125,relief='groove',bd=5)

    CanR3.create_text(275,50,text="Vous avez maintenant débloqué la création de plan de vol avec Dijkstra dans\nle menu \"Plan vol\".\n\nSélectionnez-le.")

    CanR3.place(x=600, y=60)

    button_aideR3=Button(Fen,text="Suivant",command=afficheAideR4)

    button_aideR3.place(x=1050,y=155)



    button_start.destroy()

    button_stop2.destroy()



    menu3.add_command(label="Dijkstra",command=manageDjisktra)



def afficheAideR4():

    global CanR4

    global button_aideR4

    CanR3.destroy()

    button_aideR3.destroy()

    CanR4=Canvas(Fen,width=550,height=125,relief='groove',bd=5)

    CanR4.create_text(275,50,text="Pour créer un chemin à l'aide de Dijkstra, sélectionnez deux cases\nqui représenteront respectivement le départ et\nl'arrivée du parcours.\n\nPour éxecuter ce plan de vol, utilisez \"Pilotage\" puis \"Executer plan vol\".")

    CanR4.place(x=600, y=60)

    button_aideR4=Button(Fen,text="Suivant",command=afficheAideR5)

    button_aideR4.place(x=1050,y=155)



def afficheAideR5():

    global CanR5

    CanR4.destroy()

    button_aideR4.destroy()

    CanR5=Canvas(Fen,width=550,height=100,relief='groove',bd=5)

    CanR5.create_text(275,50,text="Sélectionnez maintenant l'option \"Manuel\" dans l'onglet\n\"Pilotage\"")

    CanR5.place(x=600, y=60)



    menu4.add_command(label="Manuel",command=piloteTuto)



#affichage des aides de la partie pilotage

def afficheAideP1():

    global CanP1

    global button_aideP1

    CanP1=Canvas(Fen,width=350, height=165,relief='groove',bd=5)

    CanP1.create_text(180,70,text="Bienvenue sur l'interface de pilotage manuel.\n\nLe Permis ci-contre vous indique le nombre\nde points vous restants.\n\nLes boutons \"connect\" et \"disconnect\" permettent\nde connecter et déconnecter votre drone.")

    CanP1.place(x=820, y=60)

    button_aideP1=Button(Fen,text="Suivant",command=afficheAideP2)

    button_aideP1.place(x=1070,y=195)



def afficheAideP2():

    global CanP2

    global button_aideP2

    CanP1.destroy()

    button_aideP1.destroy()

    CanP2=Canvas(Fen,width=350, height=100,relief='groove',bd=5)

    CanP2.create_text(180,50,text="Les boutons \"decoller\" et \"atterir\" permettent\nrespectivement de faire décoller et attérir le drone.")

    CanP2.place(x=820, y=100)

    button_aideP2=Button(Fen,text="Suivant",command=afficheAideP3)

    button_aideP2.place(x=1070,y=170)



def afficheAideP3():

    global CanP3

    global button_aideP3

    CanP2.destroy()

    button_aideP2.destroy()

    CanP3=Canvas(Fen,width=350, height=100,relief='groove',bd=5)

    CanP3.create_text(180,50,text="Les flèches directionnelles permettent de tourner\nle drone dans la direction indiquée par celles-ci.")

    CanP3.place(x=820, y=100)

    button_aideP3=Button(Fen,text="Suivant",command=afficheAideP4)

    button_aideP3.place(x=1070,y=170)



def afficheAideP4():

    global CanP4

    global button_aideP4

    CanP3.destroy()

    button_aideP3.destroy()

    CanP4=Canvas(Fen,width=350, height=100,relief='groove',bd=5)

    CanP4.create_text(180,50,text="Le bouton rouge permet de valider un arrêt\nsur un panneau STOP.")

    CanP4.place(x=820, y=100)

    button_aideP4=Button(Fen,text="Suivant",command=afficheAideP5)

    button_aideP4.place(x=1070,y=170)



def afficheAideP5():

    global CanP5

    global button_aideP5

    CanP4.destroy()

    button_aideP4.destroy()

    CanP5=Canvas(Fen,width=350, height=100,relief='groove',bd=5)

    CanP5.create_text(180,50,text="Le bouton vert permet d'avancer le drone\ndans la direction définie par la flèche bleue.")

    CanP5.place(x=820, y=100)

    button_aideP5=Button(Fen,text="Suivant",command=afficheAideP6)

    button_aideP5.place(x=1070,y=170)



def afficheAideP6():

    global CanP6

    global button_aideP6

    CanP5.destroy()

    button_aideP5.destroy()

    CanP6=Canvas(Fen,width=350, height=100,relief='groove',bd=5)

    CanP6.create_text(180,50,text="Vous connaisez maintenant totalement\nle fonctionnement de l'interface de pilotage manuel.")

    CanP6.place(x=820, y=100)

    button_aideP6=Button(Fen,text="Terminer",command=finTuto)

    button_aideP6.place(x=1070,y=170)



def finTuto():

    global CanF

    global buttonFin



    label_commande.destroy()

    bouton_gauche.destroy()

    bouton_droit.destroy()

    bouton_avancer.destroy()

    bouton_stop2.destroy()

    bouton_S.destroy()

    bouton_decoller.destroy()

    bouton_atterir.destroy()

    bouton_NE.destroy()

    bouton_N.destroy()

    bouton_nordO.destroy()

    bouton_SO.destroy()

    bouton_SE.destroy()

    bouton_connect.destroy()

    bouton_disconnect.destroy()

    label_info.destroy()

    label_permis.destroy()

    score.destroy()

    CanP6.destroy()

    button_aideP6.destroy()



    CanF=Canvas(Fen,width=550, height=175,relief='groove',bd=5)

    CanF.create_text(300,100,text="Félicitation !\n\nVous venez de terminer le tutoriel de cette application\net êtes désormais apte à l'utiliser.\nVous pouvez maintenant cliquer sur le bouton ci-dessous pour\nretourner au menu et démarrer un utilisation\noubien recommencer le didacticiel.\n\nBonne conduite et soyez prudent !")

    CanF.place(x=600,y=50)

    buttonFin=Button(Fen,text="Retourner au menu",command=terminer)

    buttonFin.place(x=1000,y=195)



def terminer():

    global Can
    global bouton_debut
    global bouton_tuto
    global imageintroduction

    CanF.destroy()

    buttonFin.destroy()

    Can.destroy()

    # caneva pour visualiser le graphe

    Can=Canvas(Fen,width=900,height=650)


    # affichage de l'image introduction
    Can.create_image(400, 400, image=imageintroduction)
    Can.pack(fill=BOTH, expand=1)

    # affichage page acceuil, choix tutoriel
    bouton_debut=Button(Fen,text="DRONE IT!",bg='red',command=debut)
    bouton_debut.place(x=280,y=100)


    # affichage page acceuil pour le tutoriel
    bouton_tuto=Button(Fen,bg='red', text="TUTO",command=tuto)
    bouton_tuto.place(x=480,y=100)

    Can.bind("<Button-1>",recuperer_coord)

#--------------------------------------------------------------------------------------------------------------

# Fin du tutoriel

#



# ------------------------------------------------------------------------------



"""

PROGRAMME PRINCIPAL

"""

global imageintroduction

# initialisation des images de l'interface graphique



# images orientation du drone
imageflecheNW = PhotoImage(file='flechedroneNW.gif')
imageflecheN = PhotoImage(file='flechedroneN.gif')
imageflecheNE = PhotoImage(file='flechedroneNE.gif')
imageflecheW = PhotoImage(file='flechedroneW.gif')
imageflecheE = PhotoImage(file='flechedroneE.gif')
imageflecheSW = PhotoImage(file='flechedroneSW.gif')
imageflecheS = PhotoImage(file='flechedroneS.gif')
imageflecheSE = PhotoImage(file='flechedroneSE.gif')


# images pour pilotage directionnelle du drone
imagedirectionNW = PhotoImage(file='flecheNO.gif')
imagedirectionN = PhotoImage(file='flecheN.gif')
imagedirectionNE = PhotoImage(file='flecheNE.gif')
imagedirectionW = PhotoImage(file='flecheO.gif')
imagedirectionE = PhotoImage(file='flecheE.gif')
imagedirectionSW = PhotoImage(file='flecheSO.gif')
imagedirectionS = PhotoImage(file='flecheS.gif')
imagedirectionSE = PhotoImage(file='flecheSE.gif')

imagego = PhotoImage(file='go.gif')
imagepause = PhotoImage(file='pause.gif')


# images signalisation stop, sens interdit, etat feu rouge
imagestop = PhotoImage(file='Stop.gif')
imagesensinterdit = PhotoImage(file='sens_interdit.gif')
imagefeuvert = PhotoImage(file='feu_vert.gif')
imagefeuorange = PhotoImage(file='feu_orange.gif')
imagefeurouge = PhotoImage(file='feu_rouge.gif')

# image introduction
imageintroduction = PhotoImage(file='droneIT_image.gif')

# declaration du drone, utilisation de transmission bluetooth
if DroneOn ==1:
    mambo = Mambo(MamboAddr, use_wifi=False)

# initialisation position par defaut du drone sur le graphe

SommetCourant = 21


# affichage de l'image introduction
Can.create_image(400, 400, image=imageintroduction)
Can.pack(fill=BOTH, expand=1)

# affichage page acceuil, choix tutoriel
bouton_debut=Button(Fen,text="DRONE IT!",bg='red',command=debut)
bouton_debut.place(x=280,y=100)


# affichage page acceuil pour le tutoriel
bouton_tuto=Button(Fen,bg='red', text="TUTO",command=tuto)
bouton_tuto.place(x=480,y=100)


Fen.mainloop()





