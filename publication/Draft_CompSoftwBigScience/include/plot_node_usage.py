import csv
import numpy as np
import datetime as dt
import matplotlib.pyplot as plt


read_file = open("vre-usage-nemo.csv")
csvf = csv.reader(read_file)

months       = []
bare_metals  = []
vres         = []
shareholders = []

for l in csvf:
    if not l[0].startswith('2'): continue

    month            = dt.datetime.strptime(l[0],"%Y-%m")
    bmns          = float(l[1])
    vrens         = float(l[2])
    shareholderns = float(l[3])

    total     = vrens+bmns
    vrens_rel = vrens/total
    bmns_rel  = bmns/total
    months.append       (month            )
    bare_metals.append  (bmns_rel          )
    vres.append         (vrens_rel         )
    shareholders.append (shareholderns )

time_axis = np.array(months)
vre_array = np.array(vres)
bm_array  = np.array(bare_metals)
sh_array  = np.array(shareholders)

width = 15 #days

vre_array = vre_array*100
bm_array = bm_array*100

vre = plt.bar(time_axis, vre_array,width, label="Virtual Machines")
bm  = plt.bar(time_axis, bm_array, width, bottom=vre_array, label = "Bare Metal")

plt.ylabel("Job Slots")
plt.xlabel("Month")

plt.yticks(np.arange(0, 101, 10))
plt.gcf().autofmt_xdate()

plt.legend()
plt.show()

