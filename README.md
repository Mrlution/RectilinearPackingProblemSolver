# Problem description
Packing and layout problems are common in both engineering and non-engineering applications. In the Very Large Scale Integrated Circuit design, we often pack different IP Cores into a rectangular container. Usually, the IP Core is a rectilinear shape. To cut down the cost, we need to minimize the container. So the EDA software needs a fast and robust and high performance algorithm to solve the packing problem. Apart from EDA Software, many other industrial applications such as cloth cutting and newspaper layout are involved with this algorithm.

The term rectilinear means the interior angles of the packed blocks are either 90 degrees or 270 degrees. The container is usually a rectangle with a fixed width and unrestricted height. The algorithm will pack all the polygonal blocks into the container without overlapping, and generate a height as small as possible.
![](images/problem_description.png)

# How to run
python main.py -d data_file.txt

# result
This is an packing example. In our dataset, the average occupation rate is 85%.
![](images\beforePacking.png)
![](images\afterPacking.png)

# How this work
## NFP 
Out NFP is used to avoid overlap between objects. Inner NFP is used to ensure the objects in the bin.
![](images\nfp.png)

## below left stratage
Any Object is packed at the below left position.
![](images\belowleft.png)

## complex and big first stratage
![](images\bigfirst.png)


