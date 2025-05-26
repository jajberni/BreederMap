# Breeder Map
Breeder Map is a QGIS plugin for assisting with the processing and extracting field phenomics data.

This plugin allows you to create a vector grid for extracting individual plot data in typical breeding trials organised in rows and columns. 

## Instalation

You need QGIS version > 3.0. In the Plugin menu (Manage and Install Plugins...), search for "Breeder" and select it:

![image](https://github.com/user-attachments/assets/bf370379-45cc-44cf-a129-dbdcdac537f2)

## Running Breeder Map

Load your raster data. Ideally, you want to use the highest-resolution data so you can clearly see the experiment's layout.

Click on the Breeder Map icon in your toolbox to show the panel with the Breeder Map tool:
![image](https://github.com/user-attachments/assets/67220e00-1f24-4772-863e-8df92052f05c)

This will show the parameters for the row and columns, spacing and so on:
![image](https://github.com/user-attachments/assets/46181432-39e6-40dc-a1d6-a574225eabec)

Define the number of Rows and Columns and gaps and click on "Start"

![image](https://github.com/user-attachments/assets/069d683a-8dea-4eb3-9039-554830eb5fa9)

### Row / Column convention

In Breeder Map, Columns are each line in the direction of sowing, while Rows are each plot along the Columns. 

This will show a grid on top of your map:
![image](https://github.com/user-attachments/assets/e10dfc9b-a507-4654-8b9e-ba1f51637e70)


There are two modes for adjusting the plots:
* Stretching the width and length of the grid layout
* Editing the four individual corners

Note that the green dot marks the 1-1 plot. You can adjust it by clicking on Reverse Rows or Reverse Columns. 

Once your layout is aligned with the plots, click Save and the plugin will create two new temporary layers.
One layer contains the rectangles for each plot and the second layer are points created in the alleys for terrain extraction. 
These points can be used to extract the bare ground height from a digital surface model, allowing the extraction of canopy height. 

## Funding and citation

This plugin has been developed under the project CERESTRES: Advanced phenomics for screening physiological traits in cereals aimed at quantification and early detection of leaf fungal diseases and of water stress. Project PID2020-118650RR-C33 funded by MICIU/AEI/10.13039/501100011033.
![image](https://github.com/user-attachments/assets/2ec23bd9-7489-4946-90ac-88b9a8435148)

